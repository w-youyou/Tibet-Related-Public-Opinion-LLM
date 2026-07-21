from __future__ import annotations

import os
import uuid
from typing import Dict, List

from docx import Document as DocxDocument
import pdfplumber

from .agents import FlowAgentPipeline
from .extractor import FlowExtractor
from .graph_builder import build_flow_graph
from .render_graphviz import render_flow_graph
from .schemas import FlowGraph


class FlowService:
    def __init__(self) -> None:
        self.extractor = FlowExtractor()
        self._agent_pipeline = None

    @property
    def agent_pipeline(self) -> FlowAgentPipeline:
        if self._agent_pipeline is None:
            self._agent_pipeline = FlowAgentPipeline()
        return self._agent_pipeline

    def read_file_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".docx":
            doc = DocxDocument(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())
        if ext == ".pdf":
            parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        raise ValueError(f"暂不支持该文件类型: {ext}")

    def extract_flows_from_text(
        self,
        text: str,
        *,
        title: str = "政务流程",
        source_file: str | None = None,
        use_agent: bool = True,
    ) -> List[FlowGraph]:
        if use_agent:
            try:
                return self.agent_pipeline.run_all(text=text, title=title, source_file=source_file)
            except Exception:
                pass

        steps = self.extractor.extract(text)
        return [build_flow_graph(steps, title=title, source_file=source_file)]

    def extract_flow_from_text(
        self,
        text: str,
        *,
        title: str = "政务流程",
        source_file: str | None = None,
        use_agent: bool = True,
    ) -> FlowGraph:
        return self.extract_flows_from_text(
            text=text,
            title=title,
            source_file=source_file,
            use_agent=use_agent,
        )[0]

    def extract_and_render_flow(self, file_path: str, title: str | None = None, use_agent: bool = True, request=None) -> Dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        file_name = os.path.basename(file_path)
        text = self.read_file_text(file_path)

        graphs = self.extract_flows_from_text(
            text,
            title=title or f"流程图-{file_name}",
            source_file=file_name,
            use_agent=use_agent,
        )

        matters = []
        for idx, graph in enumerate(graphs, 1):
            file_stem = f"flow_{uuid.uuid4().hex[:8]}_{idx}"
            render_result = render_flow_graph(graph, file_stem=file_stem)

            # 统一改写为 /api/flow/media/<file_name>，避免前端3000端口直接访问 /media 失败
            for key in ("svg_url", "png_url", "mermaid_url"):
                u = render_result.get(key) or ""
                if isinstance(u, str) and u:
                    media_file_name = os.path.basename(u)
                    render_result[key] = f"/api/flow/media/{media_file_name}"

            if request:
                base = f"{request.scheme}://{request.get_host()}"
                for key in ("svg_url", "png_url", "mermaid_url"):
                    u = render_result.get(key) or ""
                    if isinstance(u, str) and u.startswith("/"):
                        render_result[key] = f"{base}{u}"

            matters.append(
                {
                    "matter_index": idx,
                    "matter_title": graph.meta.get("matter_title") if isinstance(graph.meta, dict) else graph.title,
                    "flow_graph": graph.to_dict(),
                    "render": render_result,
                }
            )

        first = matters[0]
        return {
            "flow_graph": first["flow_graph"],
            "render": first["render"],
            "matters": matters,
            "matter_count": len(matters),
        }


_service = FlowService()


def extract_flow_from_text(text: str, title: str = "政务流程", source_file: str | None = None, use_agent: bool = True):
    return _service.extract_flow_from_text(text=text, title=title, source_file=source_file, use_agent=use_agent)


def extract_and_render_flow(file_path: str, title: str | None = None, use_agent: bool = True, request=None) -> Dict:
    return _service.extract_and_render_flow(file_path=file_path, title=title, use_agent=use_agent, request=request)
