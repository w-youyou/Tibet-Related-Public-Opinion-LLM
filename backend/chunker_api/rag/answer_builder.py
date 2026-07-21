"""
AnswerBuilder — Prompt building, LLM generation, history formatting, title generation,
and suggested next questions. Extracted from RAGService.

Takes an LLM instance in its constructor — does NOT create its own LLM.
This makes it testable with mock LLMs.
"""
import logging
import os
import sys
import re
from typing import List, Dict, Optional

# Ensure project root is on sys.path for promt.prompt imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from chunker_api.llm_service import get_llm_service

logger = logging.getLogger(__name__)

# Prompt template functions — lazily loaded at first use
_prompt_imports: dict = {}


def _ensure_prompt_imports():
    """Lazy import of prompt template functions from promt.prompt.

    Mirrors _ensure_hybrid_imports() pattern from rag_service.py but imports
    only the prompt functions AnswerBuilder needs.
    """
    global _prompt_imports
    if _prompt_imports:
        return _prompt_imports
    try:
        from promt.prompt import (
            categorize_user_profile,
            get_rag_template,
            get_direct_template,
            get_refusal_response,
        )
        _prompt_imports = {
            'categorize_user_profile': categorize_user_profile,
            'get_rag_template': get_rag_template,
            'get_direct_template': get_direct_template,
            'get_refusal_response': get_refusal_response,
        }
    except Exception as e:
        logger.warning(f"Prompt template imports not available: {e}")
        _prompt_imports = {}
    return _prompt_imports


class AnswerBuilder:
    """Builds prompts, generates answers, formats history, and produces titles/suggestions.

    Takes a BaseLLM instance at construction time — does not create its own LLM,
    making it testable with mock LLMs.
    """

    def __init__(self, llm):
        """llm is a BaseLLM instance (e.g., QwenLLM)"""
        self.llm = llm

    # ------------------------------------------------------------------
    # format_history — exact copy of _format_history from rag_service.py:376-385
    # ------------------------------------------------------------------
    def format_history(self, history: Optional[List[Dict[str, str]]]) -> str:
        if not history:
            return ""
        out = ["对话历史:"]
        for m in history:
            role = m.get('role', 'user')
            content = m.get('content', '')
            role_name = '用户' if role == 'user' else '助手'
            out.append(f"{role_name}:{content}")
        return "\n".join(out) + "\n\n"

    # ------------------------------------------------------------------
    # generate_title — exact copy of generate_title from rag_service.py:881-901
    # ------------------------------------------------------------------
    def generate_title(self, user_question: str, assistant_answer: str, api_key: str) -> str:
        """
        根据第一轮问答生成对话标题。
        """
        system_prompt = "你是一个对话标题生成助手。"
        prompt = f"""请根据以下对话内容，生成一个简洁的、不超过10个字的标题。直接返回标题文本，不要包含任何多余的解释、引号或标点符号。

用户：{user_question}
助手：{assistant_answer}"""

        try:
            # 为保证性能，标题生成固定使用轻量级模型
            title_llm = get_llm_service(api_key=api_key, model_name="qwen3-omni-flash")
            title = title_llm.generate_answer(prompt, system_prompt=system_prompt)
            # 清理和截断标题
            title = title.strip().replace('"', '').replace("'", "").replace("标题：", "")
            return title[:50]  # 限制最大长度以适应数据库字段
        except Exception as e:
            logger.error(f"生成标题失败: {e}")
            # 如果LLM生成失败，回退到使用问题的前20个字符作为标题
            return user_question[:20] + ('...' if len(user_question) > 20 else '')

    # ------------------------------------------------------------------
    # generate_suggested_next_questions — exact copy of rag_service.py:903-972
    # ------------------------------------------------------------------
    def generate_suggested_next_questions(
        self,
        question: str,
        answer: str,
        sources_summary: str = "",
        is_refused: bool = False,
    ) -> List[str]:
        """生成最多 3 条引导式追问。

        Args:
            question: 本轮用户问题
            answer: 模型最终回答
            sources_summary: 检索资料的简要摘要
            is_refused: 是否拒答

        Returns:
            去重后的引导问题列表（最多 3 条），失败时返回空数组
        """
        system_prompt = (
            "你是一个涉藏舆情研究知识助手。根据用户的问题和回答，生成用户可能追问的引导式问题。"
            "要求：每个问题简洁明确，不超过30字；问题应具有研究价值，围绕涉藏舆情分析、政策研究展开；"
            "如果回答是拒答（未找到相关信息），问题应引导用户换个角度或范围提问；"
            "不要重复用户已经问过的问题；只返回问题文本，每行一个，不要编号、不要序号、不要任何额外说明。"
        )

        refusal_hint = ""
        if is_refused:
            refusal_hint = "（注意：刚才未能检索到相关信息，请生成可以引导用户换个角度或范围提问的问题）"

        sources_hint = ""
        if sources_summary:
            sources_hint = f"\n参考资料来源：{sources_summary}"

        prompt = (
            f"用户问题：{question}\n"
            f"回答：{answer[:500]}{refusal_hint}{sources_hint}\n\n"
            "请生成3个引导式追问："
        )

        try:
            raw = self.llm.generate_answer(prompt, system_prompt=system_prompt)
            if not raw or not raw.strip():
                return []

            # 拆行、清洗、去重、截断
            lines = []
            seen = set()
            for line in raw.strip().split("\n"):
                line = line.strip()
                # 去掉可能的编号前缀（如 "1." "1、" "1）" 等）
                line = re.sub(r'^[\d]+[\.\、\)）\s]+', '', line).strip()
                if not line:
                    continue
                if len(line) > 60:  # 过滤过长行
                    continue
                key = line.lower()
                if key not in seen:
                    seen.add(key)
                    # 去掉可能的首尾书名号、引号
                    line = line.strip('《》""\'\'「」')
                    lines.append(line)

            # 去重用户问题
            user_key = question.strip().lower()
            lines = [l for l in lines if l.strip().lower() != user_key]

            return lines[:3]
        except Exception as e:
            logger.warning(f"生成引导式追问失败: {e}")
            return []

    # ------------------------------------------------------------------
    # Prompt builders — use _ensure_prompt_imports() for template functions
    # ------------------------------------------------------------------
    def build_rag_prompt(self, context: str, question: str, history_context: str, profile: Dict[str, str]) -> str:
        """Build the RAG (retrieval-augmented) prompt with context, history, and profile-based tone."""
        imports = _ensure_prompt_imports()
        template = imports['get_rag_template'](profile)
        return template.format(history_context=history_context, context=context, question=question)

    def build_direct_prompt(self, question: str, profile: Dict[str, str]) -> str:
        """Build a direct (non-RAG) prompt with profile-based tone."""
        imports = _ensure_prompt_imports()
        template = imports['get_direct_template'](profile)
        return template.format(question=question)

    def build_refusal_response(self, reason: str, profile: Dict[str, str]) -> str:
        """Return a preset refusal response string based on user profile and reason."""
        imports = _ensure_prompt_imports()
        return imports['get_refusal_response'](profile, reason)

    def categorize_profile(self, age, is_employee: bool, frequency: str) -> Dict[str, str]:
        """Categorize user profile for prompt tone selection."""
        imports = _ensure_prompt_imports()
        user_type = 'employee' if is_employee else 'public'
        return imports['categorize_user_profile'](age, user_type, frequency)

    # ------------------------------------------------------------------
    # Generation — delegate to self.llm
    # ------------------------------------------------------------------
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return self.llm.generate_answer(user_prompt, system_prompt=system_prompt)

    def generate_stream(self, system_prompt: str, user_prompt: str):
        return self.llm.stream_answer(user_prompt, system_prompt=system_prompt)
