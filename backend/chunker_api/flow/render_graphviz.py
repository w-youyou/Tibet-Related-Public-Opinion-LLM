from __future__ import annotations

import os
from typing import Dict

from django.conf import settings

from .schemas import FlowGraph

try:
    from graphviz import Digraph
    from graphviz.backend import ExecutableNotFound
    GRAPHVIZ_AVAILABLE = True
except Exception:
    GRAPHVIZ_AVAILABLE = False
    ExecutableNotFound = RuntimeError


def _node_shape(node_type: str) -> str:
    return {
        "start": "circle",
        "end": "doublecircle",
        "condition": "diamond",
        "parallel_start": "hexagon",
        "parallel_join": "hexagon",
        "step": "box",
    }.get(node_type, "box")


def _node_style(node_type: str) -> Dict[str, str]:
    base = {
        "fontname": "Microsoft YaHei",
        "fontsize": "12",
        "style": "filled,rounded",
        "color": "#334155",
        "fontcolor": "#0f172a",
        "penwidth": "1.2",
    }
    by_type: Dict[str, Dict[str, str]] = {
        "start": {"fillcolor": "#dcfce7", "color": "#16a34a", "fontsize": "13", "style": "filled"},
        "end": {"fillcolor": "#fee2e2", "color": "#dc2626", "fontsize": "13", "style": "filled"},
        "condition": {"fillcolor": "#fef3c7", "color": "#d97706", "style": "filled"},
        "parallel_start": {"fillcolor": "#e0f2fe", "color": "#0284c7", "style": "filled"},
        "parallel_join": {"fillcolor": "#e0f2fe", "color": "#0284c7", "style": "filled"},
        "step": {"fillcolor": "#eef2ff", "color": "#4f46e5", "style": "filled,rounded"},
    }
    return {**base, **by_type.get(node_type, {})}


def _render_dot(dot: Digraph, output_path_no_ext: str, fmt: str) -> str:
    dot.format = fmt
    return dot.render(output_path_no_ext, cleanup=True)


def _render_mermaid_fallback(flow: FlowGraph, output_dir: str, file_stem: str) -> Dict[str, str]:
    mermaid_lines = ["flowchart TD"]

    for n in flow.nodes:
        safe_label = (n.label or "").replace('"', "'").replace("\n", "<br/>")
        if n.type == "start":
            mermaid_lines.append(f"    {n.id}(({safe_label}))")
        elif n.type == "end":
            mermaid_lines.append(f"    {n.id}(({safe_label}))")
        elif n.type == "condition":
            mermaid_lines.append(f"    {n.id}{{{safe_label}}}")
        else:
            mermaid_lines.append(f"    {n.id}[\"{safe_label}\"]")

    for e in flow.edges:
        if e.label:
            mermaid_lines.append(f"    {e.from_node} -->|{e.label}| {e.to_node}")
        else:
            mermaid_lines.append(f"    {e.from_node} --> {e.to_node}")

    mermaid_text = "\n".join(mermaid_lines)
    mmd_path = os.path.join(output_dir, f"{file_stem}.mmd")
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_text)

    return {
        "svg_path": "",
        "png_path": "",
        "svg_url": "",
        "png_url": "",
        "mermaid_path": mmd_path,
        "mermaid_url": f"{settings.MEDIA_URL}flow_diagrams/{file_stem}.mmd",
        "renderer": "mermaid_fallback",
        "render_message": "未检测到Graphviz系统dot命令，已降级生成Mermaid流程图文本。",
    }


def render_flow_graph(flow: FlowGraph, file_stem: str) -> Dict[str, str]:
    output_dir = os.path.join(settings.MEDIA_ROOT, "flow_diagrams")
    os.makedirs(output_dir, exist_ok=True)

    if not GRAPHVIZ_AVAILABLE:
        raise RuntimeError("graphviz python包不可用，请安装 graphviz")

    dot = Digraph(comment=flow.title)
    dot.attr(rankdir="TB", bgcolor="#f8fafc", splines="spline", nodesep="0.45", ranksep="0.55")
    dot.attr("graph", fontname="Microsoft YaHei", labelloc="t", label=flow.title)
    dot.attr("node", fontname="Microsoft YaHei")
    dot.attr("edge", fontname="Microsoft YaHei", fontsize="11", color="#64748b", penwidth="1.2", arrowsize="0.8")

    for n in flow.nodes:
        node_style = _node_style(n.type)
        dot.node(n.id, n.label, shape=_node_shape(n.type), **node_style)

    for e in flow.edges:
        dot.edge(e.from_node, e.to_node, label=e.label or "")

    output_no_ext = os.path.join(output_dir, file_stem)

    try:
        _render_dot(dot, output_no_ext, "svg")
        _render_dot(dot, output_no_ext, "png")
    except ExecutableNotFound:
        return _render_mermaid_fallback(flow, output_dir, file_stem)

    return {
        "svg_path": f"{output_no_ext}.svg",
        "png_path": f"{output_no_ext}.png",
        "svg_url": f"{settings.MEDIA_URL}flow_diagrams/{file_stem}.svg",
        "png_url": f"{settings.MEDIA_URL}flow_diagrams/{file_stem}.png",
        "mermaid_path": "",
        "mermaid_url": "",
        "renderer": "graphviz",
        "render_message": "",
    }
