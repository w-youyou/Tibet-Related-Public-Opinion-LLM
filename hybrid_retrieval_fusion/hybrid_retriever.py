# -*- coding: utf-8 -*-
import os
import hashlib
from typing import Any, Dict, List, Tuple
import numpy as np
from rapidfuzz import fuzz
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
try:
    from langchain_core.pydantic_v1 import PrivateAttr
except Exception:  # pragma: no cover
    try:
        from pydantic.v1 import PrivateAttr  # type: ignore
    except Exception:  # pragma: no cover
        from pydantic import PrivateAttr  # type: ignore

from .bm25_indexer import BM25Indexer
from .cross_encoder import CrossEncoderWrapper, RemoteCrossEncoderWrapper
from .types import Candidate
from .rrf_merger import RRFMerger, _stable_uid
from .adaptive_threshold import AdaptiveThresholdFilter
from .mmr_reranker import MMRDiversityReranker


class HybridRetriever:
    """
    增强版混合检索器：RRF融合 + 自适应阈值 + MMR多样性重排
    语义检索 + BM25 → RRF融合 → 交叉编码器重排 → 自适应阈值 → MMR多样性重排 → 去重 → top-k
    """

    def __init__(
        self,
        vectorstore,
        bm25_indexer: BM25Indexer,
        cross_encoder: CrossEncoderWrapper | RemoteCrossEncoderWrapper,
        embeddings,
        *,
        # RRF参数
        rrf_k: int = 10,
        # 重排序参数
        m_for_rerank: int = 50,
        top_k: int = 6,
        min_docs: int = 3,
        # 自适应阈值参数
        quantile_threshold: float = 0.3,
        min_gap_ratio: float = 0.15,
        # MMR参数
        mmr_lambda: float = 0.6,
        mmr_similarity_threshold: float = 0.85,
        # 去重参数
        dup_text_threshold: int = 85,
        per_source_max: int = 1,
        meta_exact_boost: float = 0.05,
        search_kwargs: dict = None
    ):
        self.vs = vectorstore
        self.bm25 = bm25_indexer
        self.ce = cross_encoder
        self.embeddings = embeddings
        
        # RRF参数
        self.rrf_k = rrf_k
        
        # 重排序参数
        self.m_for_rerank = m_for_rerank
        self.top_k = top_k
        self.min_docs = min_docs
        
        # 自适应阈值参数
        self.quantile_threshold = quantile_threshold
        self.min_gap_ratio = min_gap_ratio
        
        # MMR参数
        self.mmr_lambda = mmr_lambda
        self.mmr_reranker = MMRDiversityReranker(embeddings, mmr_lambda)
        self.mmr_similarity_threshold = mmr_similarity_threshold
        
        # 去重参数
        self.dup_text_threshold = dup_text_threshold
        self.per_source_max = per_source_max
        self.meta_exact_boost = meta_exact_boost
        self.search_kwargs = search_kwargs or {}

    # 可直接使用
    def get_relevant_documents(self, query: str) -> List[Document]:
        cands = self._retrieve(query)
        out: List[Document] = []
        for c in cands:
            meta = dict(c.doc.metadata or {})
            meta.update({
                "_cos": round(c.cos, 6),
                "_bm25": round(c.bm25, 6),
                "_rrf_score": round(c.rrf_score, 6),
                "_s_ce": round(c.s_ce, 6),
                "_s_ce_norm": round(c.s_ce_norm, 6),
                "_mmr_score": round(c.mmr_score, 6),
            })
            out.append(Document(page_content=c.doc.page_content, metadata=meta))
        return out

    # 核心流程
    def _retrieve(self, query: str) -> List[Candidate]:
        # 1) 语义检索
        vec_hits = []
        try:
            vec_hits = self.vs.similarity_search_with_score(query, k=self.m_for_rerank, **self.search_kwargs)
        except Exception:
            docs = self.vs.similarity_search(query, k=self.m_for_rerank, **self.search_kwargs)
            vec_hits = [(d, 0.0) for d in docs]

        # 2) BM25检索
        bm25_hits = self.bm25.search(query, k=self.m_for_rerank)

        # 3) RRF融合
        rrf_results = RRFMerger.reciprocal_rank_fusion(
            vec_hits, bm25_hits, self.bm25, self.rrf_k
        )
        
        # 4) 构建候选文档
        cands = []
        for doc, rrf_score in rrf_results[:self.m_for_rerank]:
            # 找到原始分数
            cos_score = 0.0
            bm25_score = 0.0
            
            for vec_doc, score in vec_hits:
                if _stable_uid(vec_doc) == _stable_uid(doc):
                    cos_score = 1.0 - float(score) if score <= 1.0 else float(score)
                    break
            
            for doc_id, score in bm25_hits:
                if doc_id == _stable_uid(doc):
                    bm25_score = float(score)
                    break
            
            cand = Candidate(
                doc=doc,
                cos=cos_score,
                bm25=bm25_score,
                rrf_score=rrf_score
            )
            cands.append(cand)

        if not cands:
            return []

        # 5) 交叉编码器重排序
        # 打点：候选规模与长度（用于解释 hybrid_invoke 波动）
        try:
            cand_texts = [c.doc.page_content or "" for c in cands]
            lens = [len(t) for t in cand_texts]
            print(
                f"[HYBRID][CE] m_for_rerank={self.m_for_rerank} cands={len(cands)} "
                f"len_total={sum(lens)} len_avg={int(sum(lens)/len(lens)) if lens else 0} len_max={max(lens) if lens else 0}"
            )
        except Exception:
            cand_texts = [c.doc.page_content or "" for c in cands]

        ce_scores = self.ce.score(query, cand_texts)
        for cand, score in zip(cands, ce_scores):
            cand.s_ce = float(score)

        # 6) CE分数归一化
        ce_scores_list = [c.s_ce for c in cands]
        min_ce = min(ce_scores_list)
        max_ce = max(ce_scores_list)
        
        if max_ce > min_ce:
            for cand in cands:
                cand.s_ce_norm = (cand.s_ce - min_ce) / (max_ce - min_ce)
        else:
            for i, cand in enumerate(cands):
                cand.s_ce_norm = 0.5 + (i - len(cands)/2) * 0.01

        # 7) 自适应阈值筛选
        threshold, keep_indices = AdaptiveThresholdFilter.find_optimal_threshold(
            [c.s_ce_norm for c in cands], 
            self.min_docs, 
            self.quantile_threshold,
            self.min_gap_ratio
        )
        
        filtered_cands = [cands[i] for i in keep_indices]

        # 8) 去重
        deduped_cands = self._dedupe(filtered_cands)

        # 9) MMR多样性重排（条件触发：仅在候选内容确实冗余时才执行）
        final_cands = self._maybe_run_mmr(query, deduped_cands)
        if len(final_cands) == len(deduped_cands) and all(
            hasattr(c, "mmr_score") and c.mmr_score == c.s_ce_norm for c in final_cands
        ):
            print("检索算法跳过mmr（候选内容已足够多样化，pairwise sim < threshold）")
        else:
            print("检索算法已到达mmr多样性重排（检测到内容冗余）")
        print(f"[HYBRID][FLOW] step9_mmr_done selected={len(final_cands)} top_k={self.top_k}")
        for rank, cand in enumerate(final_cands[: self.top_k], 1):
            meta = cand.doc.metadata or {}
            file_name = meta.get("file_name") or meta.get("source") or meta.get("source_file") or "unknown"
            chunk_id = meta.get("chunk_id") or meta.get("chunk_index") or "unknown"
            print(
                f"[HYBRID][SCORES] #{rank} file={file_name} chunk={chunk_id} "
                f"rrf={cand.rrf_score:.6f} ce={cand.s_ce:.6f} ce_norm={cand.s_ce_norm:.6f} mmr={cand.mmr_score:.6f}"
            )
        return final_cands[:self.top_k]

    def _dedupe(self, ranked: List[Candidate]) -> List[Candidate]:
        """去重逻辑"""
        kept: List[Candidate] = []
        src_counter: Dict[Tuple[str, str, str], int] = {}

        for cand in ranked:
            meta = cand.doc.metadata or {}
            source = (
                meta.get("file_name")
                or meta.get("source")
                or meta.get("source_file")
                or meta.get("file_path")
                or meta.get("original_file")
                or ""
            )
            sheet = meta.get("table_name") or meta.get("sheet") or ""
            page = (
                meta.get("pdf_page_number")
                or meta.get("page_number")
                or meta.get("page")
                or meta.get("chunk_id")
                or meta.get("chunk_index")
                or ""
            )
            key = (str(source), str(sheet), str(page))
            # 来源级限制
            cnt = src_counter.get(key, 0)
            if cnt >= self.per_source_max:
                continue

            # 文本近重复
            text = cand.doc.page_content or ""
            dup = False
            for k in kept:
                if fuzz.token_set_ratio(text, k.doc.page_content or "") >= self.dup_text_threshold:
                    dup = True
                    break
            if dup:
                continue

            kept.append(cand)
            src_counter[key] = cnt + 1

            if len(kept) >= max(self.top_k * 2, self.min_docs * 2):
                break

        return kept

    def _maybe_run_mmr(self, query: str, candidates: List[Candidate]) -> List[Candidate]:
        """
        条件触发 MMR：仅当候选内容存在实质性文本重叠时才运行 MMR。
        
        - 若 mmr_similarity_threshold < 0：无条件运行 MMR（消融实验用）
        - 否则：使用 token_set_ratio 检测文本重叠度
        """
        n = len(candidates)
        if n <= self.top_k:
            for cand in candidates:
                cand.mmr_score = cand.s_ce_norm
            return candidates

        # 无条件模式（阈值 < 0）
        if self.mmr_similarity_threshold < 0:
            return self.mmr_reranker.compute_mmr_scores(query, candidates, self.top_k)

        # 计算 post-dedupe 候选的 max pairwise token_set_ratio
        max_text_sim = 0.0
        texts = [(i, c.doc.page_content or "") for i, c in enumerate(candidates)]
        compare_count = min(n, max(2 * self.top_k, 10))
        for i in range(compare_count):
            for j in range(i + 1, compare_count):
                sim = fuzz.token_set_ratio(texts[i][1], texts[j][1])
                if sim > max_text_sim:
                    max_text_sim = sim

        text_threshold = max(60, self.dup_text_threshold - 10)
        
        if max_text_sim >= text_threshold:
            print(f"[HYBRID][MMR] max_text_overlap={max_text_sim:.0f}% >= {text_threshold}%, running MMR")
            return self.mmr_reranker.compute_mmr_scores(query, candidates, self.top_k)
        else:
            print(f"[HYBRID][MMR] max_text_overlap={max_text_sim:.0f}% < {text_threshold}%, skipping MMR (candidates already diverse)")
            sorted_cands = sorted(candidates, key=lambda c: c.s_ce_norm, reverse=True)
            for cand in sorted_cands:
                cand.mmr_score = cand.s_ce_norm
            return sorted_cands


# ------------ LangChain 兼容包装器 ------------
class HybridLCRetriever(BaseRetriever):
    """将增强版 HybridRetriever 适配为 LangChain 的 BaseRetriever。"""
    _hybrid: HybridRetriever = PrivateAttr()

    def __init__(self, hybrid: HybridRetriever, **kwargs):
        super().__init__(**kwargs)
        self._hybrid = hybrid

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return self._hybrid.get_relevant_documents(query)

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        import anyio
        return await anyio.to_thread.run_sync(self._hybrid.get_relevant_documents, query)
