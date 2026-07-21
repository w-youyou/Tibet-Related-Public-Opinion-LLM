from __future__ import annotations

import json
import re
from typing import Any, List, Optional, Tuple

from django.conf import settings

from ..llm_service import get_llm_service
from .graph_builder import build_flow_graph
from .schemas import FlowEdge, FlowGraph, FlowNode, FlowStep


class AgentError(RuntimeError):
    pass


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise AgentError("LLM未返回内容")

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        return json.loads(m.group(1).strip())

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])

    raise AgentError(f"无法解析LLM返回JSON: {text[:200]}")


class FileParseAgent:
    def __init__(self, api_key: str, model_name: str = "qwen-plus") -> None:
        self.llm = get_llm_service(api_key=api_key, model_name=model_name)

    def _extract_matter_titles(self, text: str) -> List[str]:
        prompt = f"""
你是政务文件事项识别专家。请从文本中识别“事项名称”列表。
仅返回JSON，不要解释。

输出格式：
{{
  "matter_titles": ["事项A", "事项B"]
}}

要求：
1) 只返回可作为独立办理流程的事项；
2) 保持标题简洁、去重；
3) 若只有一个事项也返回长度为1；
4) 无法判断时返回空数组。

文本如下：
{text}
"""
        resp = self.llm.generate_answer(prompt=prompt, system_prompt="你是严谨的JSON信息抽取助手。")
        data = _extract_json(resp)
        titles_raw = data.get("matter_titles") if isinstance(data, dict) else None
        if not isinstance(titles_raw, list):
            return []

        titles: List[str] = []
        seen = set()
        for t in titles_raw:
            title = str(t or "").strip()[:60]
            if not title:
                continue
            k = title.lower()
            if k in seen:
                continue
            seen.add(k)
            titles.append(title)
        return titles

    def _extract_steps_for_matter(self, text: str, matter_title: str, matter_idx: int) -> List[FlowStep]:
        prompt = f"""
你是政务文件流程抽取专家。请仅抽取“{matter_title}”这一事项的办理流程步骤。
仅返回JSON，不要解释。

输出格式：
{{
  "steps": [
    {{
      "raw_text": "步骤概括",
      "action": "动作",
      "department": "责任部门或null",
      "materials": ["材料1", "材料2"],
      "time_limit": "时限或null",
      "condition": "条件或null",
      "branch_true_text": "满足条件流向或null",
      "branch_false_text": "不满足条件流向或null",
      "confidence": 0.0
    }}
  ]
}}

要求：
1) 只抽取该事项，不要混入其他事项；
2) raw_text最多50个汉字，action尽量不超过12个字；
3) confidence范围0~1；
4) 无法确定字段填null或[]。

文本如下：
{text}
"""
        resp = self.llm.generate_answer(prompt=prompt, system_prompt="你是严谨的JSON信息抽取助手。")
        data = _extract_json(resp)
        return self._normalize_steps(data.get("steps") if isinstance(data, dict) else None, prefix=f"m{matter_idx}_step")

    def _normalize_steps(self, steps_raw: Any, prefix: str = "step") -> List[FlowStep]:
        if not isinstance(steps_raw, list):
            return []

        steps: List[FlowStep] = []
        for i, s in enumerate(steps_raw, 1):
            if not isinstance(s, dict):
                continue
            raw_text = str(s.get("raw_text") or "").strip()
            if len(raw_text) > 50:
                raw_text = raw_text[:50]
            action = str(s.get("action") or "").strip() or (raw_text[:20] if raw_text else f"步骤{i}")
            if len(action) > 20:
                action = action[:20]
            if not raw_text:
                continue
            mats = s.get("materials")
            if not isinstance(mats, list):
                mats = []
            conf = s.get("confidence", 0.75)
            try:
                conf = float(conf)
            except Exception:
                conf = 0.75
            conf = max(0.0, min(1.0, conf))

            steps.append(
                FlowStep(
                    id=f"{prefix}_{i}",
                    raw_text=raw_text,
                    action=action,
                    department=(s.get("department") or None),
                    materials=[str(x) for x in mats if str(x).strip()],
                    time_limit=(s.get("time_limit") or None),
                    condition=(s.get("condition") or None),
                    branch_true_text=(s.get("branch_true_text") or None),
                    branch_false_text=(s.get("branch_false_text") or None),
                    confidence=conf,
                )
            )
        return steps

    def run(self, text: str) -> List[Tuple[str, List[FlowStep]]]:
        max_chars = int(getattr(settings, "FLOW_AGENT_MAX_INPUT_CHARS", 120000))
        text_for_llm = text if len(text) <= max_chars else text[:max_chars]

        prompt = f"""
你是政务文件流程抽取专家。请从给定文本中识别“多个事项”的办理流程。
仅返回JSON，不要输出解释。

输出格式：
{{
  "matters": [
    {{
      "matter_title": "事项名称",
      "steps": [
        {{
          "raw_text": "步骤概括",
          "action": "动作",
          "department": "责任部门或null",
          "materials": ["材料1", "材料2"],
          "time_limit": "时限或null",
          "condition": "条件或null",
          "branch_true_text": "满足条件流向或null",
          "branch_false_text": "不满足条件流向或null",
          "confidence": 0.0
        }}
      ]
    }}
  ]
}}

要求：
1) 若文档包含多个事项，必须拆分为多个matter；若只有一个事项，也放在matters数组里；
2) 对每个步骤自主缩减概括，raw_text最多50个汉字；
3) action简洁明确，尽量不超过12个字；
4) confidence范围0~1；
5) 无法确定字段填null或[]；
6) 只抽取流程相关句子，避免无关政策背景说明。

文本如下：
{text_for_llm}
"""
        resp = self.llm.generate_answer(prompt=prompt, system_prompt="你是严谨的JSON信息抽取助手。")
        data = _extract_json(resp)

        matters_raw = data.get("matters") if isinstance(data, dict) else None
        result: List[Tuple[str, List[FlowStep]]] = []

        if isinstance(matters_raw, list) and matters_raw:
            for idx, m in enumerate(matters_raw, 1):
                if not isinstance(m, dict):
                    continue
                title = str(m.get("matter_title") or f"事项{idx}").strip()[:60] or f"事项{idx}"
                steps = self._normalize_steps(m.get("steps"), prefix=f"m{idx}_step")
                if steps:
                    result.append((title, steps))

        if result:
            if len(result) > 1:
                return result

            # 兜底：当首轮只抽到单事项时，再做一次事项枚举与按事项抽取，尽量避免“多事项被合并”。
            try:
                titles = self._extract_matter_titles(text_for_llm)
                if len(titles) > 1:
                    refined: List[Tuple[str, List[FlowStep]]] = []
                    for idx, t in enumerate(titles, 1):
                        steps = self._extract_steps_for_matter(text_for_llm, matter_title=t, matter_idx=idx)
                        if steps:
                            refined.append((t, steps))
                    if len(refined) > 1:
                        return refined
            except Exception:
                pass

            return result

        # 兼容旧格式：直接返回 steps 时，同样尝试多事项细分。
        steps = self._normalize_steps(data.get("steps") if isinstance(data, dict) else None, prefix="step")
        if steps:
            try:
                titles = self._extract_matter_titles(text_for_llm)
                if len(titles) > 1:
                    refined: List[Tuple[str, List[FlowStep]]] = []
                    for idx, t in enumerate(titles, 1):
                        part_steps = self._extract_steps_for_matter(text_for_llm, matter_title=t, matter_idx=idx)
                        if part_steps:
                            refined.append((t, part_steps))
                    if len(refined) > 1:
                        return refined
            except Exception:
                pass

            return [("默认事项", steps)]

        raise AgentError("解析文件Agent未提取到有效流程步骤")


class FlowChartAgent:
    def __init__(self, api_key: str, model_name: str = "qwen-plus") -> None:
        self.llm = get_llm_service(api_key=api_key, model_name=model_name)

    def run(self, steps: List[FlowStep], title: str, source_file: Optional[str]) -> FlowGraph:
        if len(steps) <= 1:
            return build_flow_graph(steps, title=title, source_file=source_file)

        steps_payload = [
            {
                "id": s.id,
                "raw_text": s.raw_text,
                "action": s.action,
                "department": s.department,
                "materials": s.materials,
                "time_limit": s.time_limit,
                "condition": s.condition,
                "branch_true_text": s.branch_true_text,
                "branch_false_text": s.branch_false_text,
                "confidence": s.confidence,
            }
            for s in steps
        ]

        prompt = f"""
你是流程图建模Agent。请把步骤数据转换成流程图JSON。
只输出JSON，不要解释。

输出格式：
{{
  "nodes": [{{"id":"start","type":"start","label":"开始"}}, ...],
  "edges": [{{"from":"start","to":"n1","label":null}}, ...]
}}

节点type只允许：start, step, condition, parallel_start, parallel_join, end。
要求：
1) 节点id唯一；
2) edges中的from/to必须出现在nodes中；
3) 主干流程必须从start到end连通。

步骤数据：
{json.dumps(steps_payload, ensure_ascii=False)}
"""
        try:
            resp = self.llm.generate_answer(prompt=prompt, system_prompt="你是严谨的流程图JSON建模助手。")
            data = _extract_json(resp)
            nodes_raw = data.get("nodes") if isinstance(data, dict) else None
            edges_raw = data.get("edges") if isinstance(data, dict) else None
            if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
                raise AgentError("流程图Agent返回缺少nodes/edges")

            nodes: List[FlowNode] = []
            node_ids = set()
            valid_types = {"start", "step", "condition", "parallel_start", "parallel_join", "end"}
            for n in nodes_raw:
                if not isinstance(n, dict):
                    continue
                nid = str(n.get("id") or "").strip()
                ntype = str(n.get("type") or "step").strip()
                label = str(n.get("label") or nid).strip() or nid
                if not nid or nid in node_ids or ntype not in valid_types:
                    continue
                node_ids.add(nid)
                nodes.append(FlowNode(id=nid, type=ntype, label=label, meta={}))

            edges: List[FlowEdge] = []
            for e in edges_raw:
                if not isinstance(e, dict):
                    continue
                f = str(e.get("from") or "").strip()
                t = str(e.get("to") or "").strip()
                if not f or not t or f not in node_ids or t not in node_ids:
                    continue
                edges.append(FlowEdge(from_node=f, to_node=t, label=(e.get("label") or None)))

            if not nodes or not edges:
                raise AgentError("流程图Agent输出无效，回退规则构图")

            return FlowGraph(
                version="2.0-agent",
                title=title,
                source_file=source_file,
                nodes=nodes,
                edges=edges,
                steps=steps,
                meta={"builder": "flowchart_agent", "total_steps": len(steps)},
            )
        except Exception:
            return build_flow_graph(steps, title=title, source_file=source_file)


class FlowAgentPipeline:
    def __init__(self) -> None:
        api_key = getattr(settings, "DASHSCOPE_API_KEY", None)
        if not api_key:
            raise AgentError("未配置 DASHSCOPE_API_KEY，无法使用Agent流程")
        model_name = getattr(settings, "FLOW_AGENT_MODEL_NAME", "qwen-plus")
        self.parse_agent = FileParseAgent(api_key=api_key, model_name=model_name)
        self.graph_agent = FlowChartAgent(api_key=api_key, model_name=model_name)

    def run_all(self, text: str, *, title: str, source_file: Optional[str]) -> List[FlowGraph]:
        matters = self.parse_agent.run(text)
        graphs: List[FlowGraph] = []
        for idx, (matter_title, steps) in enumerate(matters, 1):
            g_title = matter_title if len(matters) > 1 else title
            graph = self.graph_agent.run(steps, title=g_title, source_file=source_file)
            graph.meta = {
                **(graph.meta or {}),
                "matter_index": idx,
                "matter_title": matter_title,
                "matter_count": len(matters),
            }
            graphs.append(graph)
        return graphs

    def run(self, text: str, *, title: str, source_file: Optional[str]) -> FlowGraph:
        graphs = self.run_all(text=text, title=title, source_file=source_file)
        return graphs[0]
