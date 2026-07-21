from dataclasses import dataclass
from langchain_core.documents import Document

@dataclass
class Candidate:
    doc: Document
    cos: float = 0.0
    bm25: float = 0.0
    cos_norm: float = 0.0
    bm25_norm: float = 0.0
    s_fused: float = 0.0
    s_ce: float = 0.0
    s_ce_norm: float = 0.0
    # 新增字段
    rrf_score: float = 0.0
    mmr_score: float = 0.0