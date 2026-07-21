"""QuestionRouter — 问题路由模块。

纯决策模块，根据关键词和正则规则判断问题是否需要进入知识库检索，
不依赖 ChromaDB、embeddings 或任何网络调用。
"""

import re
from typing import Tuple


class QuestionRouter:
    """问题路由器：判断问题是否属于涉藏舆情研究领域、是否需要知识库检索。"""

    # ========================================================================
    # 非政务业务范围关键词与模式（_is_out_of_scope_direct_question）
    # ========================================================================

    OUT_OF_SCOPE_KEYWORDS: list[str] = [
        "天气", "气温", "下雨", "下雪", "空气质量", "穿什么衣服",
        "现在几点", "今天几号", "今天星期几",
        "讲笑话", "说笑话", "讲个笑话", "说个笑话", "讲故事", "聊天", "陪我聊",
        "星座", "运势", "算命", "占卜",
        "股票", "基金", "彩票", "中奖", "涨停", "跌停",
        "买哪只股票", "推荐股票", "投资建议",
        "代购", "微商", "外卖", "快递查询",
        "吃什么", "去哪玩", "旅游攻略", "电影推荐", "音乐推荐",
    ]

    OUT_OF_SCOPE_PATTERNS: list[str] = [
        r"^(今天|明天|后天|现在)?.{0,10}(天气|气温|会不会下雨|下雨吗|冷不冷|热不热|多少度).{0,10}$",
        r"^.{0,10}(天气怎么样|天气如何|气温多少|多少度|空气质量).{0,10}$",
        r"^.{0,10}(股票|基金|彩票).{0,20}(怎么样|能买吗|会涨吗|会跌吗|推荐|预测).{0,10}$",
        r"^.{0,10}(星座|运势|算命|占卜).{0,20}$",
    ]

    # ========================================================================
    # 政务/政策强信号关键词与模式（_judge_need_kb → True）
    # ========================================================================

    KB_KEYWORDS: list[str] = [
        # 核心领域
        "涉藏", "西藏", "藏族", "藏区", "甘孜", "阿坝", "迪庆", "甘南",
        "意识形态", "舆情", "舆论", "社会稳定", "安全监测", "跨网络",
        # 舆情相关
        "舆情监测", "舆情分析", "舆情预警", "舆情溯源", "舆情传播",
        "舆论引导", "舆论管控", "舆论态势", "网络舆情", "社交网络",
        "信息传播", "传播路径", "传播源头", "热点事件", "敏感话题",
        # 政策与法规
        "民族政策", "宗教政策", "民族区域自治", "藏传佛教", "寺庙管理",
        "反分裂", "维护稳定", "民族团结", "依法治藏", "富民兴藏",
        "长期建藏", "凝聚人心", "长治久安",
        # 研究方法
        "大数据分析", "文本挖掘", "情感分析", "话题检测", "关键词提取",
        "社会网络分析", "传播模型", "溯源算法", "知识图谱",
        # 干预与治理
        "舆论干预", "舆情应对", "危机公关", "正面宣传", "话语体系",
        "国际传播", "对外宣传", "软实力",
        # 历史与文化
        "农奴制", "民主改革", "和平解放", " tibet ", "达赖", "班禅",
        "转世", "活佛", "藏文化", "非遗",
    ]

    KB_PATTERNS: list[str] = [
        # 舆情分析类提问
        r"(舆情|舆论|传播|溯源).{0,20}(分析|监测|预警|检测|追踪|溯源|态势|趋势)",
        r"(怎么|如何|怎样).{0,10}(监测|分析|应对|引导|管控|溯源).{0,10}(舆情|舆论|传播)",
        # 政策法规类提问
        r"(民族|宗教|藏区|涉藏).{0,20}(政策|法规|条例|规定|办法)",
        r"(什么|哪些).{0,10}(民族政策|宗教政策|涉藏政策|舆情案例)",
        # 研究方法类提问
        r"(文本挖掘|情感分析|话题检测|知识图谱|传播模型).{0,20}(怎么|如何|方法|算法|技术)",
        # 案例与事件类提问
        r"(涉藏|西藏|藏区).{0,20}(事件|案例|热点|舆情).{0,20}(是什么|有哪些|背景|原因)",
    ]

    # ========================================================================
    # 寒暄/致谢/能力咨询（_judge_need_kb → False）
    # ========================================================================

    DIRECT_PHRASES: set[str] = {
        "你好", "您好", "hi", "hello", "hey", "在吗", "有人吗", "早上好", "上午好",
        "中午好", "下午好", "晚上好", "谢谢", "感谢", "多谢", "辛苦了", "再见",
        "拜拜", "bye", "你是谁", "你叫什么", "你能做什么", "你会什么",
        "你有什么功能", "介绍一下你自己", "自我介绍", "讲个笑话", "说个笑话",
        "陪我聊聊", "聊聊天", "howareyou", "whoareyou", "thankyou",
        "现在几点", "今天几号", "今天星期几", "天气怎么样",
    }

    DIRECT_CHAT_PATTERNS: list[str] = [
        r"^(你好|您好|hi|hello|hey|在吗|有人吗|早上好|上午好|中午好|下午好|晚上好)[啊呀吗]*$",
        r"^(谢谢|感谢|多谢|辛苦了|再见|拜拜|bye)[啦啊呀]*$",
        r"^(你是谁|你叫什么|你能做什么|你会什么|你有什么功能|介绍一下你自己|自我介绍)$",
        r"^(你好|您好|hi|hello|hey)?(请问)?(你是(谁|什么)?|你是谁|你叫什么|你能做什么|你会什么|你有什么功能|介绍一下你自己|自我介绍)[啊呀吗]*$",
        r"^(讲|说)个?笑话$",
    ]

    # ========================================================================
    # 通用任务关键词与模式（_judge_need_kb → False）
    # ========================================================================

    GENERAL_KEYWORDS: list[str] = [
        "python", "javascript", "typescript", "java", "sql", "html", "css", "vue",
        "django", "linux", "git", "npm", "json", "api", "代码", "编程", "函数",
        "报错", "bug", "算法", "数据库", "翻译", "改写", "润色", "写一", "写个",
        "写封", "写篇", "作文", "邮件", "文案", "诗", "故事", "总结下面", "概括",
        "列个提纲", "帮我算", "计算",
    ]

    GENERAL_PATTERNS: list[str] = [
        r"^(什么是|解释一下|介绍一下|讲一下|说说|科普一下|为什么|怎么理解|如何理解|怎么学习|如何学习).{1,80}$",
        r"^.{1,40}(是什么|为什么|怎么办|怎么解决|怎么处理|如何处理)$",
        r"^(what is|why|how to|explain|introduce)\b",
    ]

    # ========================================================================
    # 公共方法
    # ========================================================================

    def _normalize(self, question: str) -> Tuple[str, str, str]:
        """标准化问题文本。

        Returns:
            (q_lower, q_compact, q_plain)
            - q_lower: 去首尾空格、合并空白、转小写
            - q_compact: q_lower 再去全部空白
            - q_plain: q_compact 再去标点符号
        """
        q = (question or "").strip()
        q_lower = re.sub(r"\s+", " ", q).lower().strip()
        q_compact = re.sub(r"\s+", "", q_lower)
        q_plain = re.sub(r"[。.!！?？,，、;；:：~～]+", "", q_compact)
        return q_lower, q_compact, q_plain

    def is_out_of_scope(self, question: str) -> bool:
        """判断问题是否明显超出政务业务范围。"""
        _, q_compact, _ = self._normalize(question)
        if not q_compact:
            return False

        if any(word in q_compact for word in self.OUT_OF_SCOPE_KEYWORDS):
            return True
        if any(re.search(pattern, q_compact) for pattern in self.OUT_OF_SCOPE_PATTERNS):
            return True
        return False

    def needs_knowledge_base(self, question: str, kb_desc: str) -> bool:
        """判断是否需要进入知识库检索。

        策略：只对白名单内的普通问答直连 LLM；其余问题默认进入检索系统。
        这样政务/政策类低相关问题会进入后续拒答机制，而不是被分类器误判后绕过检索。

        Args:
            question: 用户问题文本
            kb_desc: 知识库描述（保留参数，当前未使用）

        Returns:
            True 表示需要检索知识库，False 表示可直接交给 LLM。
        """
        q = (question or "").strip()
        if not q:
            return False

        q_lower, q_compact, q_plain = self._normalize(q)

        def _has_any(words: list[str]) -> bool:
            return any(word in q_compact for word in words)

        # 政务、政策、办事、材料等强信号优先进入检索，避免普通问答规则误放行。
        if _has_any(self.KB_KEYWORDS) or any(
            re.search(pattern, q_compact) for pattern in self.KB_PATTERNS
        ):
            return True

        # 明确寒暄、致谢、能力咨询：普通对话，直接交给 LLM。
        if q_plain in self.DIRECT_PHRASES:
            return False

        # 明确非政务业务范围问题：不进检索，后续直答分支会直接返回固定"非业务范畴"文案。
        if self.is_out_of_scope(q):
            return False

        if any(re.search(pattern, q_plain) for pattern in self.DIRECT_CHAT_PATTERNS):
            return False

        # 数学表达式、代码/技术、写作/翻译等通用任务，没有政务强信号时直接交给 LLM。
        if re.fullmatch(r"[\d\s+\-*/×÷().=^%]+", q) and re.search(r"\d", q):
            return False
        if re.search(r"\d", q_compact) and re.search(
            r"(等于|多少|几|加|减|乘|除|算|计算)", q_compact
        ):
            return False

        if _has_any(self.GENERAL_KEYWORDS) or any(
            re.search(pattern, q_lower) for pattern in self.GENERAL_PATTERNS
        ):
            return False

        # 兜底：非明确普通问答一律检索，让后续相关性评估/拒答机制接管。
        return True
