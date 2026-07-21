from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .schemas import FlowStep


SECTION_PATTERNS = [
    r"办事流程",
    r"办理流程",
    r"办理步骤",
    r"审批流程",
    r"申请流程",
    r"受理流程",
]

STEP_LEAD_PATTERNS = [
    r"^\s*\d+[\.、]\s*",
    r"^\s*[（(]?[一二三四五六七八九十]+[)）、\.\s]",
    r"^\s*(首先|其次|然后|接着|最后|第一步|第二步|第三步)",
]

DEPT_KEYWORDS = [
    "医保局", "医保经办机构", "服务窗口", "窗口", "行政审批局", "人社局", "审核部门", "经办机构", "部门",
]

ACTION_KEYWORDS = [
    "提交", "受理", "审核", "审批", "办结", "发放", "补正", "退回", "公示", "复核", "登记",
]

MATERIAL_PATTERNS = [
    r"(?:提交|提供|上传|携带)([^。；\n]{2,40}?(?:材料|证明|证件|表|清单))",
]

TIME_PATTERNS = [
    r"(\d+\s*个?\s*工作日)",
    r"(\d+\s*日)",
    r"(当场办结)",
    r"(即时办结)",
]


class FlowExtractor:
    def _split_lines(self, text: str) -> List[str]:
        lines = []
        for raw in text.replace("\r\n", "\n").split("\n"):
            l = raw.strip()
            if l:
                lines.append(l)
        return lines

    def _find_section_span(self, lines: List[str]) -> Tuple[int, int]:
        start = 0
        end = len(lines)
        for i, line in enumerate(lines):
            if any(re.search(p, line) for p in SECTION_PATTERNS):
                start = i + 1
                break
        for j in range(start, len(lines)):
            if re.match(r"^[一二三四五六七八九十]+、", lines[j]) and j > start + 1:
                if not any(re.search(p, lines[j]) for p in SECTION_PATTERNS):
                    end = j
                    break
        return start, end

    def _is_step_line(self, line: str) -> bool:
        if any(re.search(p, line) for p in STEP_LEAD_PATTERNS):
            return True
        return any(k in line for k in ACTION_KEYWORDS) and len(line) >= 6

    def _extract_department(self, text: str) -> Optional[str]:
        for d in DEPT_KEYWORDS:
            if d in text:
                return d
        return None

    def _extract_action(self, text: str) -> str:
        for a in ACTION_KEYWORDS:
            if a in text:
                return a
        return text[:20]

    def _extract_materials(self, text: str) -> List[str]:
        materials: List[str] = []
        for p in MATERIAL_PATTERNS:
            for m in re.findall(p, text):
                materials.append(m.strip("：:，,。；; "))
        return list(dict.fromkeys(materials))

    def _extract_time_limit(self, text: str) -> Optional[str]:
        for p in TIME_PATTERNS:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return None

    def _extract_condition(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        m = re.search(r"(如果|若|如)([^，。,；;]+)(则|可|进入)([^，。,；;]+)(?:，|,)?(?:否则|不符合则)([^。；;\n]+)?", text)
        if not m:
            return None, None, None
        cond = m.group(2).strip()
        yes = m.group(4).strip()
        no = (m.group(5) or "退回补正").strip()
        return cond, yes, no

    def extract(self, text: str) -> List[FlowStep]:
        lines = self._split_lines(text)
        start, end = self._find_section_span(lines)
        target = lines[start:end] if lines else []
        if not target:
            target = lines

        steps: List[FlowStep] = []
        idx = 1
        for line in target:
            if not self._is_step_line(line):
                continue
            cond, yes_text, no_text = self._extract_condition(line)
            step = FlowStep(
                id=f"step_{idx}",
                raw_text=line,
                action=self._extract_action(line),
                department=self._extract_department(line),
                materials=self._extract_materials(line),
                time_limit=self._extract_time_limit(line),
                condition=cond,
                branch_true_text=yes_text,
                branch_false_text=no_text,
                confidence=0.78 if cond else 0.72,
            )
            steps.append(step)
            idx += 1

        return steps
