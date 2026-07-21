from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal, Optional


NodeType = Literal["start", "step", "condition", "parallel_start", "parallel_join", "end"]


@dataclass
class FlowStep:
    id: str
    raw_text: str
    action: str
    department: Optional[str] = None
    materials: List[str] = field(default_factory=list)
    time_limit: Optional[str] = None
    condition: Optional[str] = None
    branch_true_text: Optional[str] = None
    branch_false_text: Optional[str] = None
    confidence: float = 0.7


@dataclass
class FlowNode:
    id: str
    type: NodeType
    label: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowEdge:
    from_node: str
    to_node: str
    label: Optional[str] = None


@dataclass
class FlowGraph:
    version: str
    title: str
    source_file: Optional[str]
    nodes: List[FlowNode]
    edges: List[FlowEdge]
    steps: List[FlowStep]
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "title": self.title,
            "source_file": self.source_file,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "label": e.label,
                }
                for e in self.edges
            ],
            "steps": [asdict(s) for s in self.steps],
            "meta": self.meta,
        }
