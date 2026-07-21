from __future__ import annotations

from typing import List

from .schemas import FlowEdge, FlowGraph, FlowNode, FlowStep


def _build_step_label(step: FlowStep) -> str:
    parts = [step.raw_text]
    if step.department:
        parts.append(f"责任部门: {step.department}")
    if step.materials:
        parts.append(f"材料: {'、'.join(step.materials)}")
    if step.time_limit:
        parts.append(f"时限: {step.time_limit}")
    return "\n".join(parts)


def build_flow_graph(steps: List[FlowStep], title: str, source_file: str | None = None) -> FlowGraph:
    nodes: List[FlowNode] = [FlowNode(id="start", type="start", label="开始")]
    edges: List[FlowEdge] = []

    prev = "start"
    for idx, step in enumerate(steps, 1):
        step_node_id = f"n_step_{idx}"
        nodes.append(
            FlowNode(
                id=step_node_id,
                type="step",
                label=_build_step_label(step),
                meta={"step_id": step.id},
            )
        )
        edges.append(FlowEdge(from_node=prev, to_node=step_node_id))

        if step.condition:
            cond_id = f"n_cond_{idx}"
            yes_id = f"n_yes_{idx}"
            no_id = f"n_no_{idx}"
            join_id = f"n_join_{idx}"

            nodes.extend([
                FlowNode(id=cond_id, type="condition", label=f"条件: {step.condition}"),
                FlowNode(id=yes_id, type="step", label=step.branch_true_text or "继续办理"),
                FlowNode(id=no_id, type="step", label=step.branch_false_text or "退回补正"),
                FlowNode(id=join_id, type="parallel_join", label="汇合"),
            ])
            edges.extend([
                FlowEdge(from_node=step_node_id, to_node=cond_id),
                FlowEdge(from_node=cond_id, to_node=yes_id, label="是"),
                FlowEdge(from_node=cond_id, to_node=no_id, label="否"),
                FlowEdge(from_node=yes_id, to_node=join_id),
                FlowEdge(from_node=no_id, to_node=join_id),
            ])
            prev = join_id
        else:
            prev = step_node_id

    nodes.append(FlowNode(id="end", type="end", label="结束"))
    edges.append(FlowEdge(from_node=prev, to_node="end"))

    return FlowGraph(
        version="1.0",
        title=title,
        source_file=source_file,
        nodes=nodes,
        edges=edges,
        steps=steps,
        meta={
            "total_steps": len(steps),
            "has_condition": any(s.condition for s in steps),
        },
    )
