# Prompt.py
"""
Prompt模块: 提供自定义的Prompt模板
根据用户画像调整Prompt的语气和详细程度
"""

from typing import Dict, Optional


def categorize_user_profile(age: Optional[int] = None, user_type: Optional[str] = None,
                            frequency: Optional[str] = None) -> Dict[str, str]:
    """
    根据传入参数分类用户画像
    - age: 如果 >60 为'old', 否则'youth'
    - user_type: 'public' (对公) 或 'employee' (对私/员工)
    - frequency: 'new', 'active', 'senior'
    """
    profile = {}
    try:
        parsed_age = int(age) if age not in (None, "") else None
    except (TypeError, ValueError):
        parsed_age = None

    if parsed_age is not None:
        profile['age'] = 'old' if parsed_age > 60 else 'youth'
    else:
        profile['age'] = 'youth'  # 默认青年
    profile['user_type'] = user_type or 'public'  # 默认对公
    profile['frequency'] = frequency or 'active'  # 默认活跃用户
    return profile


def get_tone_instructions(profile: Dict[str, str]) -> str:
    """
    根据用户画像生成语气指导
    """
    tone = "友好、专业"
    detail_level = "适中"

    if profile['age'] == 'old':
        tone += "、严谨学术"
        detail_level = "详细解释每个要点，提供更多研究背景"
    else:
        tone += "、简洁直接"
        detail_level = "简明扼要，突出关键信息"

    if profile['frequency'] == 'new':
        detail_level += "，为新用户提供额外背景说明"
    elif profile['frequency'] == 'senior':
        detail_level += "，假设用户熟悉研究领域，直接给出深度分析"

    if profile['user_type'] == 'employee':
        tone += "，研究员视角，使用专业术语"
    else:
        tone += "，决策者视角，注重实用性"

    return f"语气: {tone}\n详细程度: {detail_level}\n始终确保回答准确、有依据，涉及政策时引用具体文件"


def get_judge_prompt(kb_description: str, question: str) -> str:
    """
    获取判断问题是否需要知识库的Prompt
    """
    return f"""你是一个问题分类专家。请判断用户的问题是否需要查询知识库才能回答。

当前知识库内容:{kb_description}

判断规则:
1. 如果问题是关于知识库涵盖领域的具体信息(政策、流程、条件、材料、时间等),回答"YES"
2. 如果问题是以下类型,回答"NO":
   - 日常问候(你好、早上好等)
   - 通用知识问题(什么是机器学习、如何编程等)
   - 常识性问题(天气、时间、常识等)
   - 个人意见或建议(推荐、评价等)
   - 数学计算、代码编写等技术问题

用户问题:{question}

请只回答"YES"或"NO",不要有任何其他内容。
你的判断:"""


def get_rag_template(profile: Dict[str, str]) -> str:
    """
    获取RAG Prompt模板(带历史)
    """
    tone_instructions = get_tone_instructions(profile)
    return f"""你是一个专业的涉藏舆情研究知识助手。请根据以下检索到的上下文信息和对话历史，准确回答用户的问题。

{{history_context}}

检索到的相关内容:
{{context}}

用户问题:{{question}}

回答要求:
1. 优先基于提供的上下文信息回答，引用具体来源
2. 可以参考对话历史理解用户意图
3. {tone_instructions}
4. 涉及舆情案例时，按时间线梳理事件脉络
5. 涉及政策时，引用具体政策文件名称和条款
6. 涉及研究方法时，说明技术原理和适用场景
7. 如果检索内容不足以回答，明确说明信息缺口

8. **引用标注**：在回答中每句话或每个关键信息点后面，用方括号标注来源编号，如[1]、[2]等。编号对应检索到的相关内容的序号（即[文档1]对应[1]，[文档2]对应[2]）。例如："根据《民族区域自治法》[1]，藏区实行区域自治制度[2]。"
你的回答:"""


def get_direct_template(profile: Dict[str, str]) -> str:
    """
    获取直接对话Prompt模板。
    """
    if profile.get('age') == 'old':
        tone_instructions = "语气: 友好、专业、严谨；回答控制在2-4句。"
    else:
        tone_instructions = "语气: 友好、专业、简洁直接；回答控制在1-3句。"
    return f"""你是一个涉藏舆情研究知识问答助手。

用户问题:{{question}}

回答要求:
1. 如果用户是问候、致谢、询问你是谁或你能做什么，可以正常友好回复，并说明你主要提供涉藏舆情研究、政策分析、舆情监测等方面的知识帮助。
2. 如果用户询问天气、股票、娱乐推荐等非研究相关话题，不要直接回答具体内容。
3. 对上述非研究话题，请回复：“抱歉，这不是我的业务范畴。我主要为您提供涉藏舆情研究、政策分析、舆情监测与溯源等方面的知识帮助。”
4. 如果用户询问通用知识、写作、翻译、代码或简单计算等普通问题，可以直接回答，但要说明该回答并不来自涉藏舆情知识库。
5. {tone_instructions}
6. 简洁回答，不要展开无关内容，不要编造政策依据或研究数据。

你的回答:"""


def get_refusal_response(profile: Dict[str, str], reason: str = "LOW_SCORE") -> str:
    """
    根据用户画像返回预设拒答文案。不调 LLM，零延迟。

    Args:
        profile: categorize_user_profile() 的输出
        reason: "LOW_SCORE" | "NO_EVIDENCE" | "OUT_OF_SCOPE"
    Returns:
        拒答回复文本
    """
    return _get_researcher_refusal(reason)


def _get_researcher_refusal(reason: str) -> str:
    """研究人员/决策者拒答文案。"""
    return (
        "抱歉，当前知识库中未找到与该问题匹配的内容。\n\n"
        "建议：\n"
        "- 更换关键词重新搜索（如使用更具体的政策名称、事件名称或时间范围）\n"
        "- 查阅相关学术文献或官方发布文件\n"
        "- 尝试从舆情监测平台获取实时数据"
    )


def get_refusal_response_for_qa_view(profile: Dict[str, str], reason: str = "LOW_SCORE") -> str:
    """
    供 qa_views.py 在 SSE 流中直接使用的拒答文案。
    与 get_refusal_response 功能相同，独立导出便于依赖注入。
    """
    return get_refusal_response(profile, reason)
