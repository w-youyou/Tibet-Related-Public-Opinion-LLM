# prompt.py
"""
Prompt 模块（画像驱动 RAG）
核心目标：
- 不只是语气调整
- 而是明确回答重点、结构、信息密度
"""

from typing import Dict


def build_answer_strategy(
    *,
    role: str,
    age_group: str,
    frequency: str,
) -> Dict[str, str]:
    """
    根据用户画像生成回答策略
    返回：
    {
        focus: 回答重点,
        style: 表达方式,
        detail: 详细程度,
        structure: 回答结构要求
    }
    """

    # ===== 角色维度 =====
    if role == "enterprise":
        focus = "流程、所需材料、责任主体、办理时限、政策依据"
        structure = "按【是否可办 → 办理流程 → 材料清单 → 时限 → 政策依据】组织回答"
    elif role == "external":
        focus = "是否可以办理、前置条件、适用对象"
        structure = "先明确【能不能办】，再说明【需要满足的条件】"
    else:  # local
        focus = "具体问题的直接答案、最便捷路径"
        structure = "直接给出结论，如有多个方案说明最快或最省事的"

    # ===== 年龄段维度 =====
    if age_group == "elder":
        style = "口语化、耐心、分步骤说明，避免专业术语"
        detail = "详细说明，每一步尽量解释清楚"
    else:  # youth
        style = "简洁、直接、偏操作指引"
        detail = "步骤化说明，避免冗余解释"

    # ===== 活跃度维度 =====
    if frequency == "new":
        detail += "，并增加必要的引导说明，避免信息过载"
    elif frequency == "high":
        detail = "在保证完整的前提下，尽量精简，假设用户熟悉背景"

    return {
        "focus": focus,
        "style": style,
        "detail": detail,
        "structure": structure,
    }


def format_strategy_text(strategy: Dict[str, str]) -> str:
    """
    将策略转为 Prompt 可直接使用的文本
    """
    return f"""
回答策略要求：
1. 回答重点：{strategy['focus']}
2. 表达方式：{strategy['style']}
3. 信息密度：{strategy['detail']}
4. 回答结构：{strategy['structure']}
""".strip()


def get_judge_prompt(kb_description: str, question: str) -> str:
    """
    是否需要走知识库检索
    """
    return f"""你是一个问题判断专家，请判断以下问题是否必须依赖知识库内容才能回答。

知识库范围：
{kb_description}

判断标准：
- 涉及具体政策、流程、材料、条件、办理方式、时限 → YES
- 问候、常识、闲聊、泛泛而谈 → NO

用户问题：
{question}

仅回答 YES 或 NO，不要输出其他内容。
"""


def get_rag_template(strategy_text: str) -> str:
    """
    RAG 场景 Prompt
    """
    return f"""你是一个政务/政策类问答助手，请严格基于提供的上下文信息回答问题。

{{history_context}}

【检索到的知识内容】
{{context}}

【用户问题】
{{question}}

{strategy_text}

严格要求（违反任一条即为错误回答）：
- **只能使用【检索到的知识内容】中已有的信息**，不得补充任何知识内容中未提及的细节
- **严禁编造引用编号**：不得出现上下文不存在的方括号编号（如[1][2][3]），所有引用必须严格对应上文的[文档N]
- **严禁虚构案例/法规/事件**：任何案例、法规名称、事件描述必须在知识内容中有明确出处
- 如果信息不足以回答，请明确说"根据现有资料，尚无法完整回答该问题"，不要尝试猜测或补全
- 如涉及流程或条件，使用列表或步骤说明

你的回答：
"""


def get_direct_template(strategy_text: str) -> str:
    """
    不需要检索，直接回答
    """
    return f"""你是一个专业、可信赖的智能助手。

{{history_context}}

用户问题：
{{question}}

{strategy_text}

请基于常识或对话上下文直接回答，不要提及“知识库”。

你的回答：
"""


def get_no_context_template(strategy_text: str) -> str:
    """
    检索不到有效内容时
    """
    return f"""用户问题：
{{question}}

{{history_context}}

当前知识库中未检索到直接相关的信息。

请按照以下原则回答：
- 明确告知“当前资料不足以支撑准确回答”
- 不要猜测或编造
- 如可能，给出咨询方向或官方渠道建议

{strategy_text}

你的回答：
"""
