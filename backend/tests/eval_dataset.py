"""
================================================================================
消融实验标注数据集

5 份文档, 195 chunks 的涉藏舆情领域标注数据:
  1. 新世纪中国涉藏国际传播研究述评_夏炎 — kb_wangjt1_2f924ce5 (34 chunks)
  2. 西藏公安机关涉藏网络舆情监管中的问题与对策研究_向秋卓玛 — kb_wangjt1_7533acc8 (92 chunks)
  3. 涉藏网络舆情演化逻辑与治理路径探析_李亚真 — kb_wangjt1_48838109 (21 chunks)
  4. 国际自媒体涉藏舆情及舆论斗争的规律特征及引导策略 — kb_wangjt1_7e7e2995 (25 chunks)
  5. 新时代涉藏网络舆情治理策略_曾小洋 — kb_wangjt1_22f68ac4 (23 chunks)

chunk_id 格式说明:
  - 单文档查询: 直接用数字 (如 "3", "44"), 系统在 _is_hit 中自动匹配
  - 跨文档查询: 用 "collection:数字" 复合格式 (如 "kb_wangjt1_7533acc8:44")

标注说明:
  - relevant_chunk_ids: 精确标注, 支持 Recall@K 计算
  - gold_answer_points: 标准答案要点 (供 Experiment 3 LLM-as-judge 使用)

拆分方式: 80% DEV_SET (48 条) + 20% HOLDOUT_SET (12 条)
================================================================================
"""

# ==================================================================
#  开发集 (48 条) — 用于调参和迭代
# ==================================================================
DEV_SET = [
        {
            "query": "新世纪中国涉藏国际传播研究主要关注哪些方面？",
            "relevant_chunk_ids": ["3", "10"],
            "gold_answer_points": [
                "西方主流媒体涉藏报道研究(以纽约时报为中心)",
                "涉藏外宣翻译和对外话语体系建设",
                "西藏作为传播主体的对外传播策略",
                "西方人西藏观及其话语的批判和反思",
                "海外互联网涉藏舆情研究",
            ],
            "relevant_dimensions": [
                {
                    "dim": "西方主流媒体涉藏报道研究(以纽约时报为中心)",
                    "chunk_ids": ["3"],
                    "min_hit": 1
                },
                {
                    "dim": "涉藏外宣翻译和对外话语体系建设",
                    "chunk_ids": ["10"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "西方主流媒体涉藏报道有什么特点？",
            "relevant_chunk_ids": ["6", "7", "8"],
            "gold_answer_points": [
                "研究主要集中于美国媒体特别是纽约时报",
                "涉藏报道呈现选择性报道和政治倾向性",
                "英国泰晤士报在侵藏战争前后呈现明显政治倾向",
                "印度、尼泊尔等邻国媒体也存在框架植入",
            ],
            "relevant_dimensions": [
                {
                    "dim": "美国媒体（纽约时报）的涉藏报道特点",
                    "chunk_ids": ["6", "7"],
                    "min_hit": 1
                },
                {
                    "dim": "英国及南亚邻国媒体的涉藏报道",
                    "chunk_ids": ["8"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "涉藏国际传播研究中存在哪些不足？",
            "relevant_chunk_ids": ["17"],
            "gold_answer_points": [
                "对民族和宗教议题国际传播理论范式和话语体系研究不足",
                "对英国、德国、印度等国主流媒体涉藏报道缺乏系统性和历时性分析",
                "数字对外传播方面的研究比较薄弱",
            ],
            "relevant_dimensions": [
                {
                    "dim": "对民族和宗教议题国际传播理论范式和话语体系研究不足",
                    "chunk_ids": ["17"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "2008年3·14事件后涉藏舆情研究发生了哪些变化？",
            "relevant_chunk_ids": ["9", "16"],
            "gold_answer_points": [
                "2008年3·14事件后涉藏舆情日渐引发社会各界关注",
                "相关研究着眼国际涉藏舆情的生发特点、话语体系和演变趋势",
                "从2008到2012年公开发表了19篇相关学术论文",
            ],
            "relevant_dimensions": [
                {
                    "dim": "2008年3·14事件后涉藏舆情日渐引发社会各界关注",
                    "chunk_ids": ["9"],
                    "min_hit": 1
                },
                {
                    "dim": "相关研究着眼国际涉藏舆情的生发特点、话语体系和演变趋势",
                    "chunk_ids": ["16"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "涉藏国际传播研究的未来趋势是什么？",
            "relevant_chunk_ids": ["18"],
            "gold_answer_points": [
                "伴随信息技术迭代和智媒时代到来需要深入研究",
                "涉藏话语翻译理论研究及其实践运用有待进一步探索",
                "西藏媒体普及带来的微观传播和跨文化互动值得探究",
            ],
            "relevant_dimensions": [
                {
                    "dim": "伴随信息技术迭代和智媒时代到来需要深入研究",
                    "chunk_ids": ["18"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "藏传佛教在国际传播中扮演什么角色？",
            "relevant_chunk_ids": ["15"],
            "gold_answer_points": [
                "藏传佛教既是一种信仰也是一种文化影响力",
                "需要研究藏传佛教在相关国家的传播历程和特点",
                "藏传佛教传播对于维护意识形态安全具有现实意义",
            ],
            "relevant_dimensions": [
                {
                    "dim": "藏传佛教既是一种信仰也是一种文化影响力",
                    "chunk_ids": ["15"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "西方人的西藏观是什么样的？",
            "relevant_chunk_ids": ["12", "14"],
            "gold_answer_points": [
                "西方语境中的西藏形象与中国主流媒体建构的形象截然不同",
                "我国主流媒体建构的西藏形象常陷入不被理解甚至被妖魔化",
                "西方媒体把中国与西藏对立起来并坚持文化想象",
                "法国媒体报道中强化既有框架和刻板印象",
            ],
            "relevant_dimensions": [
                {
                    "dim": "西方语境中的西藏形象与中国主流媒体建构的形象截然不同",
                    "chunk_ids": ["12"],
                    "min_hit": 1
                },
                {
                    "dim": "我国主流媒体建构的西藏形象常陷入不被理解甚至被妖魔化",
                    "chunk_ids": ["14"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "涉藏外宣翻译和对外话语体系有哪些研究方向？",
            "relevant_chunk_ids": ["13", "19"],
            "gold_answer_points": [
                "涉藏外宣翻译研究有待加强",
                "涉藏话语翻译理论研究及其实践运用有待进一步探索",
                "构建融通中外的民族宗教问题话语体系是一个方向",
            ],
            "relevant_dimensions": [
                {
                    "dim": "涉藏外宣翻译研究有待加强",
                    "chunk_ids": ["13"],
                    "min_hit": 1
                },
                {
                    "dim": "涉藏话语翻译理论研究及其实践运用有待进一步探索",
                    "chunk_ids": ["19"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_2f924ce5",
        },
        {
            "query": "西藏公安机关涉藏网络舆情监管面临哪些主要问题？",
            "relevant_chunk_ids": ["17", "18"],
            "gold_answer_points": [
                "主动发现和主动应对意识不强",
                "监管客体特殊且复杂(涉及民族宗教因素)",
                "各监管部门间的合作没有形成凝聚力",
                "藏区经济发展落后及特殊因素制约",
                "监管的法律与制度保障基础薄弱",
            ],
            "relevant_dimensions": [
                {
                    "dim": "主动发现和主动应对意识不强",
                    "chunk_ids": ["17"],
                    "min_hit": 1
                },
                {
                    "dim": "监管客体特殊且复杂(涉及民族宗教因素)",
                    "chunk_ids": ["18"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "什么是涉藏网络舆情？有什么特征？",
            "relevant_chunk_ids": ["35", "39", "40"],
            "gold_answer_points": [
                "涉藏网络舆情以藏区网民为主, 包含国内外参与或关注涉藏事务的所有网民",
                "涉藏网络舆情具有敏感性、复杂性和不可控性",
                "每一起舆情事件都贴近藏区人民的现实生活",
                "负面言论逐年增多且易受情绪化看法和身边人煽动影响",
            ],
            "relevant_dimensions": [
                {
                    "dim": "涉藏网络舆情的定义与主体",
                    "chunk_ids": ["35"],
                    "min_hit": 1
                },
                {
                    "dim": "涉藏网络舆情的特征（敏感性、复杂性、不可控性）",
                    "chunk_ids": ["39", "40"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "4R危机管理理论在涉藏舆情监管中如何应用？",
            "relevant_chunk_ids": ["37"],
            "gold_answer_points": [
                "危机预备: 建立预警体系、完善应急预案、增加应急演练",
                "危机反应: 通过应急小组整合多方资源、快速决策和反应",
                "危机恢复: 总结经验反思不足、减少负面影响",
                "4R理论将危机管理全过程视为有机整体",
            ],
            "relevant_dimensions": [
                {
                    "dim": "危机预备: 建立预警体系、完善应急预案、增加应急演练",
                    "chunk_ids": ["37"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关的'社会舆情分析研判平台'是如何运作的？",
            "relevant_chunk_ids": ["54", "55", "56"],
            "gold_answer_points": [
                "由西藏公安机关牵头与93家单位签订协作协议",
                "建立3项舆情联动工作机制: 联络员机制、通报共享机制、应急响应机制",
                "包含舆情风险评估、信息核查等工作",
                "每日对社会舆情进行监测采集",
            ],
            "relevant_dimensions": [
                {
                    "dim": "平台的协作机制（签约单位、联动机制）",
                    "chunk_ids": ["54", "55"],
                    "min_hit": 1
                },
                {
                    "dim": "平台的日常工作流程（监测、风险评估、核查）",
                    "chunk_ids": ["56"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "涉藏网络舆情的类型主要有哪些？",
            "relevant_chunk_ids": ["43", "44", "45"],
            "gold_answer_points": [
                "出自普通百姓的民生问题类(养老金调整等)",
                "与国家安全和政治稳定相关的境外势力干预类",
                "与民族宗教问题相关的政治化舆情类",
                "与旅游文化相关的舆情类",
            ],
            "relevant_dimensions": [
                {
                    "dim": "民生类与民族宗教类舆情",
                    "chunk_ids": ["43", "44"],
                    "min_hit": 1
                },
                {
                    "dim": "旅游文化类与境外势力干预类舆情",
                    "chunk_ids": ["45"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "'越野车追赶藏羚羊'事件中西藏公安机关是如何处置的？",
            "relevant_chunk_ids": ["63", "64", "66"],
            "gold_answer_points": [
                "迅速启动社会舆情分析研判平台工作机制",
                "第一时间通报属地公安部门调查",
                "发现涉事车辆后拉萨警方会同森林公安局立即查获",
                "拉萨网警通过微信公众号发布查获消息得到网民认可",
                "网上舆情整体积极正面, 舆情事件得到有效处置",
            ],
            "relevant_dimensions": [
                {
                    "dim": "应急响应与快速查获",
                    "chunk_ids": ["63", "64"],
                    "min_hit": 1
                },
                {
                    "dim": "舆情引导与网民反应",
                    "chunk_ids": ["66"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏网络通信活动'二十禁'是什么？",
            "relevant_chunk_ids": ["59", "60"],
            "gold_answer_points": [
                "2019年2月联合区党委网信办和通管局发布",
                "根据刑法、治安管理处罚法、网络安全法等法律法规制定",
                "针对二十类突出违法犯罪行为明令禁止",
                "宣传工作引发了网民广泛关注和支持",
            ],
            "relevant_dimensions": [
                {
                    "dim": "2019年2月联合区党委网信办和通管局发布",
                    "chunk_ids": ["59"],
                    "min_hit": 1
                },
                {
                    "dim": "根据刑法、治安管理处罚法、网络安全法等法律法规制定",
                    "chunk_ids": ["60"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关在舆情监管中如何进行网上网下联动？",
            "relevant_chunk_ids": ["69"],
            "gold_answer_points": [
                "纵向实现舆情信息通报、引导、处置的上下联动",
                "坚持主动发声回应、解释事实真相、压制负面信息",
                "疏导网民情绪与快速落地处置同步进行",
                "成功处置各类突发舆情事件增强了网民信任",
            ],
            "relevant_dimensions": [
                {
                    "dim": "纵向实现舆情信息通报、引导、处置的上下联动",
                    "chunk_ids": ["69"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关舆情监管工作的主要成效有哪些？",
            "relevant_chunk_ids": ["16"],
            "gold_answer_points": [
                "涉藏负面舆情信息大幅降低",
                "监管工作人员舆情意识提升",
                "建立了舆情分析研判平台工作机制",
                "成功处置多起典型舆情事件",
            ],
            "relevant_dimensions": [
                {
                    "dim": "涉藏负面舆情信息大幅降低",
                    "chunk_ids": ["16"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关舆情监管主体有哪些？",
            "relevant_chunk_ids": ["46", "47"],
            "gold_answer_points": [
                "西藏党政部门在网络舆情监管中处于主导地位",
                "公安机关是网络舆情监管的前沿阵地",
                "网信部门和工信部门是网络舆情监管的重点单位",
                "西藏网警在微博、微信、抖音、快手等平台发挥作用",
            ],
            "relevant_dimensions": [
                {
                    "dim": "西藏党政部门在网络舆情监管中处于主导地位",
                    "chunk_ids": ["46"],
                    "min_hit": 1
                },
                {
                    "dim": "公安机关是网络舆情监管的前沿阵地",
                    "chunk_ids": ["47"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "国外在网络舆情监管方面有哪些经验可以借鉴？",
            "relevant_chunk_ids": ["28", "84"],
            "gold_answer_points": [
                "美国以网络立法为主导, 技术监管、行业自律和市场调节并行",
                "英国有互联网观察基金会等行业自律组织",
                "西藏应联合本地网络运营商及相关从业者发起成立自律组织",
            ],
            "relevant_dimensions": [
                {
                    "dim": "美国以网络立法为主导, 技术监管、行业自律和市场调节并行",
                    "chunk_ids": ["28"],
                    "min_hit": 1
                },
                {
                    "dim": "英国有互联网观察基金会等行业自律组织",
                    "chunk_ids": ["84"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "如何完善西藏公安机关涉藏网络舆情监管？",
            "relevant_chunk_ids": ["80", "81", "83"],
            "gold_answer_points": [
                "转变监管理念, 变被动为主动",
                "立足藏区实际, 解决民生问题",
                "加快传统媒体与新兴媒体深度融合",
                "引导网红发声发力为我所用",
                "完善网络立法借鉴美国经验",
            ],
            "relevant_dimensions": [
                {
                    "dim": "完善法律法规与制度建设",
                    "chunk_ids": ["80"],
                    "min_hit": 1
                },
                {
                    "dim": "加强队伍建设与技术保障",
                    "chunk_ids": ["81", "83"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "涉藏网络舆情的演化过程是怎样的？",
            "relevant_chunk_ids": ["41", "42"],
            "gold_answer_points": [
                "首先是舆论的潜伏阶段, 突发事件发生后若处理不当容易升级",
                "其次是舆论的发展阶段, 情绪化看法被添加后变成引火线",
                "传统媒介和新兴互联网媒介共同构成藏区信息传播渠道",
                "官方舆论场和民间舆论场存在互动和影响",
            ],
            "relevant_dimensions": [
                {
                    "dim": "首先是舆论的潜伏阶段, 突发事件发生后若处理不当容易升级",
                    "chunk_ids": ["41"],
                    "min_hit": 1
                },
                {
                    "dim": "其次是舆论的发展阶段, 情绪化看法被添加后变成引火线",
                    "chunk_ids": ["42"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "社会判断理论在舆情监管中如何应用？",
            "relevant_chunk_ids": ["38"],
            "gold_answer_points": [
                "一个人可接受的态度区域越窄, 态度改变越难",
                "可接受区域越宽广, 态度转变越容易",
                "用于研究舆情信息或事件的出现、发酵及扩散过程",
                "帮助有效分析舆情发展态势",
            ],
            "relevant_dimensions": [
                {
                    "dim": "一个人可接受的态度区域越窄, 态度改变越难",
                    "chunk_ids": ["38"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏教育系统面临哪些网络舆情问题？",
            "relevant_chunk_ids": ["68"],
            "gold_answer_points": [
                "涉及校园暴力、大学生就业问题",
                "教师道德行为不当的舆情",
                "学生遭遇网络电信诈骗",
                "个别学生网络行为不当",
            ],
            "relevant_dimensions": [
                {
                    "dim": "涉及校园暴力、大学生就业问题",
                    "chunk_ids": ["68"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关在舆情监管中法制建设方面做了哪些工作？",
            "relevant_chunk_ids": ["62", "70"],
            "gold_answer_points": [
                "制定印发了依法处置违反二十禁行为的指导意见(内部使用)",
                "发布了违反二十禁行为适用法律法规解读(向社会面公开发布)",
                "强化了办案机关及时立案和收集固定证据的职责",
                "强化了执法办案民警法律意识",
            ],
            "relevant_dimensions": [
                {
                    "dim": "制定印发了依法处置违反二十禁行为的指导意见(内部使用)",
                    "chunk_ids": ["62"],
                    "min_hit": 1
                },
                {
                    "dim": "发布了违反二十禁行为适用法律法规解读(向社会面公开发布)",
                    "chunk_ids": ["70"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "为什么说监管客体特殊且复杂？",
            "relevant_chunk_ids": ["72", "73"],
            "gold_answer_points": [
                "藏区民众民族意识观念强烈、文化观念差异大",
                "相关事件多涉足医疗卫生、教育、生态环境、自然灾害、旅游等众多领域",
                "现实的社会事件具有较强的民族性、敏感性和复杂性",
                "若监管不及时或被境外媒体利用会导致负面舆论",
            ],
            "relevant_dimensions": [
                {
                    "dim": "藏区民众民族意识观念强烈、文化观念差异大",
                    "chunk_ids": ["72"],
                    "min_hit": 1
                },
                {
                    "dim": "相关事件多涉足医疗卫生、教育、生态环境、自然灾害、旅游等众多",
                    "chunk_ids": ["73"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "西藏公安机关在舆情监管中还有哪些需要改进的地方？",
            "relevant_chunk_ids": ["75", "76"],
            "gold_answer_points": [
                "新型网络违法犯罪不断呈现, 法律法规需要更新",
                "暗网犯罪、违反网络实名制等问题尚未有效覆盖",
                "相关单位工作浮于表面未达到要求",
                "舆情信息风险评估出现差错",
            ],
            "relevant_dimensions": [
                {
                    "dim": "新型网络违法犯罪不断呈现, 法律法规需要更新",
                    "chunk_ids": ["75"],
                    "min_hit": 1
                },
                {
                    "dim": "暗网犯罪、违反网络实名制等问题尚未有效覆盖",
                    "chunk_ids": ["76"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "藏区民众的民族意识和宗教信仰如何影响涉藏舆情？",
            "relevant_chunk_ids": ["77"],
            "gold_answer_points": [
                "住偏远地区农牧民思想保守, 仍停留在封建农奴制度时期",
                "藏传佛教的深刻影响导致对高僧的过度崇拜和狭隘民族思想",
                "微信抖音等工具的普及使负面思想情绪被网络化",
                "国家政策宣传力度和法律法规普及率低下加剧了问题",
            ],
            "relevant_dimensions": [
                {
                    "dim": "住偏远地区农牧民思想保守, 仍停留在封建农奴制度时期",
                    "chunk_ids": ["77"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "涉藏网络舆情监管中宣传工作存在哪些问题？",
            "relevant_chunk_ids": ["78"],
            "gold_answer_points": [
                "选派的驻村驻寺力量薄弱, 特别是藏族干部人员少",
                "对不会汉语的藏族同胞的宣传工作不能达到高标准",
                "群众参与监督作用未得到有效发挥",
                "互联网违法与不良信息举报工作体系不健全",
            ],
            "relevant_dimensions": [
                {
                    "dim": "选派的驻村驻寺力量薄弱, 特别是藏族干部人员少",
                    "chunk_ids": ["78"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7533acc8",
        },
        {
            "query": "涉藏网络舆情演化有哪几个阶段？",
            "relevant_chunk_ids": ["8"],
            "gold_answer_points": [
                "事件关注阶段: 少数网民开始关注涉藏基础事件",
                "信息扩散阶段: 事件信息通过多渠道传播",
                "意见形成阶段: 公众对事件形成看法和态度",
                "舆情爆发阶段: 大量网民参与讨论形成舆论热点",
                "反馈施压阶段: 舆情信息对公众、媒体、政府产生压力",
            ],
            "relevant_dimensions": [
                {
                    "dim": "事件关注阶段: 少数网民开始关注涉藏基础事件",
                    "chunk_ids": ["8"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_48838109",
        },
        {
            "query": "事故树分析如何应用于涉藏舆情研究？",
            "relevant_chunk_ids": ["10", "11"],
            "gold_answer_points": [
                "利用事故树致因分析得到涉藏负面网络舆情形成路径",
                "通过最小径集和结构重要度得到针对性改进措施",
                "有120个最小割集代表引起涉藏负面舆情的最低数量基本事件组合",
                "运用系统分析方法优化和完善治理路径",
            ],
            "relevant_dimensions": [
                {
                    "dim": "利用事故树致因分析得到涉藏负面网络舆情形成路径",
                    "chunk_ids": ["10"],
                    "min_hit": 1
                },
                {
                    "dim": "通过最小径集和结构重要度得到针对性改进措施",
                    "chunk_ids": ["11"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_48838109",
        },
        {
            "query": "涉藏网络舆情的传播动因有哪些？",
            "relevant_chunk_ids": ["5", "6"],
            "gold_answer_points": [
                "涉藏热点议题的激发(政治议题、民生发展、民族宗教等)",
                "信息发布渠道的便利性(社交媒体、新媒体)",
                "涉藏利益群体的推动(包括达赖集团和美西方反华势力)",
                "网络传播技术的普及降低了信息传播门槛",
            ],
            "relevant_dimensions": [
                {
                    "dim": "涉藏热点议题的激发(政治议题、民生发展、民族宗教等)",
                    "chunk_ids": ["5"],
                    "min_hit": 1
                },
                {
                    "dim": "信息发布渠道的便利性(社交媒体、新媒体)",
                    "chunk_ids": ["6"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_48838109",
        },
        {
            "query": "影响涉藏负面网络舆情的最重要因素是什么？",
            "relevant_chunk_ids": ["13"],
            "gold_answer_points": [
                "个人数字素养缺失排第一位(结构重要度最高)",
                "群体数字素养缺失也是重要因素",
                "与利益相关者、网络媒体、权威部门的沟通渠道重要度较低",
                "管理现有渠道和堵塞漏洞是最有效的治理策略",
            ],
            "relevant_dimensions": [
                {
                    "dim": "个人数字素养缺失排第一位(结构重要度最高)",
                    "chunk_ids": ["13"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_48838109",
        },
        {
            "query": "涉藏网络舆情治理路径有哪些建议？",
            "relevant_chunk_ids": ["16", "17", "19"],
            "gold_answer_points": [
                "完善涉藏网络舆情治理格局(集中五省涉藏州县网信力量)",
                "健全涉藏网络舆情工作制度(落实风险评估、发言人制度)",
                "选拔藏族网络评论员增强针对性和实效性",
                "坚持网上网下联动作战依法追究翻墙工具法律责任",
            ],
            "relevant_dimensions": [
                {
                    "dim": "法律与制度建设（完善法规、建立责任机制）",
                    "chunk_ids": ["16", "17"],
                    "min_hit": 1
                },
                {
                    "dim": "技术监测与社会共治（预警体系、公众素养）",
                    "chunk_ids": ["19"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_48838109",
        },
        {
            "query": "国际自媒体涉藏舆情有什么特征和规律？",
            "relevant_chunk_ids": ["1"],
            "gold_answer_points": [
                "国际自媒体平台上涉藏舆情有其独特的传播规律",
                "达赖集团和境外分裂势力积极利用自媒体进行舆论斗争",
                "涉藏舆情在国际话语场中容易被政治化和问题化",
            ],
            "relevant_dimensions": [
                {
                    "dim": "国际自媒体平台上涉藏舆情有其独特的传播规律",
                    "chunk_ids": ["1"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7e7e2995",
        },
        {
            "query": "如何引导国际自媒体涉藏舆论？",
            "relevant_chunk_ids": ["2"],
            "gold_answer_points": [
                "加强主流媒体在国际自媒体平台上的存在和发声",
                "利用民间力量进行柔和传播",
                "针对不同平台特征制定差异化策略",
            ],
            "relevant_dimensions": [
                {
                    "dim": "加强主流媒体在国际自媒体平台上的存在和发声",
                    "chunk_ids": ["2"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7e7e2995",
        },
        {
            "query": "国际舆论斗争中涉藏议题是如何被操纵的？",
            "relevant_chunk_ids": ["3"],
            "gold_answer_points": [
                "境外势力通过长期操纵西藏问题对中国进行滋扰",
                "达赖集团和美西方反华势力改变渗透策略制造负面舆论",
                "利用自媒体平台降低传播门槛扩散分裂言论",
            ],
            "relevant_dimensions": [
                {
                    "dim": "境外势力通过长期操纵西藏问题对中国进行滋扰",
                    "chunk_ids": ["3"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7e7e2995",
        },
        {
            "query": "境外反华势力如何利用自媒体进行涉藏舆论渗透？",
            "relevant_chunk_ids": ["4"],
            "gold_answer_points": [
                "利用Facebook、Twitter等国际社交平台传播涉藏不实信息",
                "制作藏语内容针对境内藏族群众进行传播",
                "利用社交媒体算法推荐机制扩大传播影响",
            ],
            "relevant_dimensions": [
                {
                    "dim": "利用Facebook、Twitter等国际社交平台传播涉藏不",
                    "chunk_ids": ["4"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7e7e2995",
        },
        {
            "query": "涉藏舆论斗争的国际话语权如何构建？",
            "relevant_chunk_ids": ["5"],
            "gold_answer_points": [
                "构建中国特色的涉藏话语体系和叙事框架",
                "加强多语种对外传播能力",
                "利用多种媒体形式讲好西藏故事",
            ],
            "relevant_dimensions": [
                {
                    "dim": "构建中国特色的涉藏话语体系和叙事框架",
                    "chunk_ids": ["5"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_7e7e2995",
        },
        {
            "query": "新时代涉藏网络舆情治理策略有哪些？",
            "relevant_chunk_ids": ["1"],
            "gold_answer_points": [
                "建立健全涉藏网络舆情监测预警体系",
                "完善涉藏网络舆情分析研判机制",
                "加强涉藏网络舆情引导和处置",
                "强化法律法规和制度建设",
                "提升公众媒介素养和数字素养",
            ],
            "relevant_dimensions": [
                {
                    "dim": "建立健全涉藏网络舆情监测预警体系",
                    "chunk_ids": ["1"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "涉藏网络舆情监测预警体系如何构建？",
            "relevant_chunk_ids": ["2"],
            "gold_answer_points": [
                "建立覆盖全网的多层次监测网络",
                "运用大数据和人工智能技术提升监测能力",
                "设置分级预警机制及时响应不同级别舆情",
            ],
            "relevant_dimensions": [
                {
                    "dim": "建立覆盖全网的多层次监测网络",
                    "chunk_ids": ["2"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "涉藏网络舆情的分析研判机制包含哪些内容？",
            "relevant_chunk_ids": ["3"],
            "gold_answer_points": [
                "舆情信息的分类和定量分析",
                "舆情发展趋势研判和风险评估",
                "多部门联合研判和信息共享",
            ],
            "relevant_dimensions": [
                {
                    "dim": "舆情信息的分类和定量分析",
                    "chunk_ids": ["3"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "如何提升涉藏网络舆情引导和处置能力？",
            "relevant_chunk_ids": ["4"],
            "gold_answer_points": [
                "建立快速响应机制",
                "提升官方信息发布的时效性和权威性",
                "善用新媒体平台进行正面舆论引导",
                "加强舆情处置队伍建设",
            ],
            "relevant_dimensions": [
                {
                    "dim": "建立快速响应机制",
                    "chunk_ids": ["4"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "涉藏网络舆情治理中法律法规建设有什么要求？",
            "relevant_chunk_ids": ["5"],
            "gold_answer_points": [
                "完善涉藏网络舆情相关法律法规体系",
                "明确各方责任和义务",
                "提高违法成本和威慑力",
            ],
            "relevant_dimensions": [
                {
                    "dim": "完善涉藏网络舆情相关法律法规体系",
                    "chunk_ids": ["5"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "公众媒介素养在涉藏舆情治理中有多重要？",
            "relevant_chunk_ids": ["6"],
            "gold_answer_points": [
                "提升公众辨别涉藏不实信息的能力",
                "加强民族团结教育和正面舆论引导",
                "培养理性参与公共讨论的意识",
            ],
            "relevant_dimensions": [
                {
                    "dim": "提升公众辨别涉藏不实信息的能力",
                    "chunk_ids": ["6"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "涉藏网络舆情治理面临哪些新挑战？",
            "relevant_chunk_ids": ["7"],
            "gold_answer_points": [
                "移动互联网和社交媒体的快速发展带来新挑战",
                "境外势力利用新技术手段进行渗透",
                "青少年群体容易受到网络不良信息影响",
                "藏语网络内容的监管存在技术难度",
            ],
            "relevant_dimensions": [
                {
                    "dim": "移动互联网和社交媒体的快速发展带来新挑战",
                    "chunk_ids": ["7"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "大数据技术在涉藏舆情治理中如何发挥作用？",
            "relevant_chunk_ids": ["8"],
            "gold_answer_points": [
                "通过大数据实时监测舆情动态变化",
                "利用自然语言处理技术分析舆情内容",
                "构建舆情预测模型提前预警",
            ],
            "relevant_dimensions": [
                {
                    "dim": "通过大数据实时监测舆情动态变化",
                    "chunk_ids": ["8"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "如何构建涉藏网络舆情的多部门协同治理机制？",
            "relevant_chunk_ids": ["9"],
            "gold_answer_points": [
                "建立跨部门信息共享和联动机制",
                "明确各部门职责分工和协作流程",
                "定期开展联合演练提升协同能力",
            ],
            "relevant_dimensions": [
                {
                    "dim": "建立跨部门信息共享和联动机制",
                    "chunk_ids": ["9"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
        {
            "query": "新时代涉藏舆情治理的'党管互联网'原则如何落实？",
            "relevant_chunk_ids": ["10"],
            "gold_answer_points": [
                "坚持党对网络意识形态工作的领导",
                "在涉藏舆情治理各环节贯彻党的方针政策",
                "把互联网治理纳入总体国家安全观框架",
            ],
            "relevant_dimensions": [
                {
                    "dim": "坚持党对网络意识形态工作的领导",
                    "chunk_ids": ["10"],
                    "min_hit": 1
                },
            ],
            "collection": "kb_wangjt1_22f68ac4",
        },
]

# ==================================================================
#  留出集 (12 条) — 仅在最终报告阶段使用, 不用于中途调参
# ==================================================================
HOLDOUT_SET = [
    # ======== 跨文档综合类 (5 条, 使用 collection:chunk_id 复合格式) ========
    {
        "query": "十四世达赖和达赖集团在涉藏网络舆情中扮演什么角色？",
        "relevant_chunk_ids": [
            "kb_wangjt1_7533acc8:44",
            "kb_wangjt1_48838109:5",
            "kb_wangjt1_7e7e2995:3",
        ],
        "gold_answer_points": [
            "以十四世达赖为首的分裂势力通过网络平台进行反宣煽动",
            "达赖集团和美西方反华势力改变渗透策略制造负面舆论",
            "全方位支持达赖大肆活动、包装达赖获得诺贝尔和平奖",
            "利用自媒体平台扩散分裂言论破坏西藏社会稳定",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "从学术研究角度看，涉藏网络舆情研究存在哪些空白？",
        "relevant_chunk_ids": [
            "kb_wangjt1_2f924ce5:17",
            "kb_wangjt1_7533acc8:27",
        ],
        "gold_answer_points": [
            "对民族和宗教议题国际传播理论范式研究不足",
            "缺乏对特定地域和特定监管主体的深入研究",
            "数字对外传播方面的研究还比较薄弱",
            "涉藏话语翻译理论及实践运用有待探索",
        ],
        "collection": "kb_wangjt1_2f924ce5",
    },
    {
        "query": "如何构建系统性的涉藏网络舆情治理体系？",
        "relevant_chunk_ids": [
            "kb_wangjt1_7533acc8:80",
            "kb_wangjt1_48838109:16",
            "kb_wangjt1_22f68ac4:1",
        ],
        "gold_answer_points": [
            "转变监管理念从被动到主动",
            "完善治理格局联合多部门力量",
            "健全风险评估、发言人等制度",
            "加强技术手段和人才队伍建设",
            "推进国际话语权构建和对外传播",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "境外势力和境内因素在涉藏网络舆情形成中各起什么作用？",
        "relevant_chunk_ids": [
            "kb_wangjt1_7533acc8:44",
            "kb_wangjt1_48838109:5",
            "kb_wangjt1_48838109:6",
        ],
        "gold_answer_points": [
            "境外势力(美国、达赖集团)长期操纵西藏问题进行滋扰",
            "境内因素包括经济社会发展不平衡不充分、民族宗教问题等",
            "境外势力利用社交媒体对境内群众进行渗透",
            "境内涉藏基础事件经网络传播后容易被境外势力利用",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "涉藏网络舆情治理中技术手段、制度建设和人才培养如何协同？",
        "relevant_chunk_ids": [
            "kb_wangjt1_48838109:15",
            "kb_wangjt1_7533acc8:83",
            "kb_wangjt1_22f68ac4:8",
        ],
        "gold_answer_points": [
            "技术手段方面: 应用大数据、AI进行实时监测和预警",
            "制度建设方面: 完善法律法规和跨部门协作机制",
            "人才培养方面: 选拔藏族网络评论员、打造专业处置团队",
            "三者需协同推进形成完整的治理闭环",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },

    # ======== 单文档精确类 (7 条) ========
    {
        "query": "涉藏国际传播研究中, 学者对'西藏形象'构建有哪些不同观点？",
        "relevant_chunk_ids": ["12", "16"],
        "gold_answer_points": [
            "西方语境中的西藏形象呈现与中国媒体截然不同的图景",
            "我国主流媒体建构的西藏形象常陷入不被理解甚至被妖魔化",
            "有学者侧重大众传播视域中的西藏形象建构研究",
            "有学者侧重媒介镜像中的西藏形象建构表征和话语策略",
        ],
        "collection": "kb_wangjt1_2f924ce5",
    },
    {
        "query": "'社会舆情分析研判平台'在实际运行中存在哪些问题？",
        "relevant_chunk_ids": ["74", "76"],
        "gold_answer_points": [
            "各成员单位照章办事未结合自身实际特点",
            "舆情风险高的单位通报全面其余浮于表面",
            "会商分析工作不到位导致风险评估出现差错",
            "相关协作工作仍然浮于表面",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "从事故树分析角度看, 如何最有效地防止涉藏负面网络舆情发生？",
        "relevant_chunk_ids": ["12", "13"],
        "gold_answer_points": [
            "优先提高个人数字素养(结构重要度最高)",
            "管理现有渠道和堵塞沟通漏洞是最优策略",
            "依据结构重要度排序优先处理关键因素",
            "多个因素综合施策才能有效阻止顶上事件发生",
        ],
        "collection": "kb_wangjt1_48838109",
    },
    {
        "query": "涉藏网络舆情中'官方舆论场'和'民间舆论场'有什么区别和联系？",
        "relevant_chunk_ids": ["41"],
        "gold_answer_points": [
            "官方舆论场由党和政府主导的新闻媒体组成",
            "民间舆论场由民众日常使用的微博、微信、抖音等社交平台组成",
            "民间舆论场的讨论会放大并对官方舆论场造成影响",
            "两个舆论场需要有效互动和融合",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "涉藏网络舆情监管中'缩减阶段'(4R理论)具体应该如何实施？",
        "relevant_chunk_ids": ["37", "38"],
        "gold_answer_points": [
            "危机缩减是指通过预警监测减少危机的发生可能性",
            "需要建立完善的舆情监测预警体系",
            "需要与预备阶段、反应阶段和恢复阶段协同配合",
            "利用社会判断理论分析舆情态度区域来指导缩减策略",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "如何针对不同社交媒体平台制定差异化的涉藏舆论引导策略？",
        "relevant_chunk_ids": [
            "kb_wangjt1_7533acc8:53",
            "kb_wangjt1_7e7e2995:2",
        ],
        "gold_answer_points": [
            "抖音适合短视频宣传组建网红矩阵",
            "微博适合官方快速发布权威信息和辟谣",
            "微信适合深入传播和社群教育",
            "国际平台需要多语种、多文化视角的内容策略",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
    {
        "query": "在总体国家安全观框架下, 涉藏网络舆情治理的战略意义是什么？",
        "relevant_chunk_ids": [
            "kb_wangjt1_22f68ac4:10",
            "kb_wangjt1_48838109:16",
        ],
        "gold_answer_points": [
            "涉藏网络舆情治理是维护国家安全的重要组成部分",
            "网络意识形态安全是总体国家安全观的重要内容",
            "涉藏舆情的政治敏感性决定了其在国家战略中的特殊地位",
            "需在党管互联网原则下实现系统治理和综合治理",
        ],
        "collection": "kb_wangjt1_7533acc8",
    },
]
