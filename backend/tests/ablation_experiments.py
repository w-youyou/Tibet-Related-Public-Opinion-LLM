"""
================================================================================
RAG 系统消融实验脚本
================================================================================

本文件包含两个独立的消融实验，用于量化验证系统的检索效果与冷启动性能：

  Experiment 1 — 检索准确率消融评测
    对比四档配置下 top-K 命中率、MRR、Recall、NDCG：
      A. 纯向量检索 (baseline)
      B. 向量 + BM25 混合检索 (RRF 融合, 无CE)
      C. 向量 + BM25 + CrossEncoder 重排序 (无MMR去重)
      D. 向量 + BM25 + CE + 去重 + MMR (全链路)

  Experiment 2 — 冷启动性能基准测试
    测量三层惰性加载架构各环节的耗时：
      - Django 启动与首模块导入
      - _ensure_hybrid_imports() 重型依赖加载
      - 首次检索（含 ChromaDB 连接 + BM25 构建/加载 + CrossEncoder 初始化）
      - 后续缓存命中检索

================================================================================
使用方式
================================================================================

# ===== 准备测试数据集 =====
# 1. 在知识库中导入至少几份涉藏舆情相关文档（PDF/Word/Excel）
# 2. 在下方 DATASET 区域编辑 QUERIES 列表，每个 query 需标注预期应出现在结果中的
#    chunk 关键词（用于判断 hit）

# ===== 运行实验 1 =====
cd backend
uv run python -m tests.ablation_experiments --exp retrieval

# ===== 运行实验 2 =====
cd backend
uv run python -m tests.ablation_experiments --exp cold_start

# ===== 运行全部实验 =====
cd backend
uv run python -m tests.ablation_experiments --exp all

# ===== 无标注数据时使用 mock 数据做 smoke test =====
cd backend
uv run python -m tests.ablation_experiments --exp retrieval --mock
================================================================================
"""

import argparse
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ------------------------------------------------------------------
# 确保 backend/ 在 Python path 上
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # backend/
sys.path.insert(0, str(PROJECT_ROOT))

# ==================================================================
#  测试数据集 — 从独立文件导入 (请编辑 tests/eval_dataset.py)
# ==================================================================
try:
    from tests.eval_dataset import DEV_SET as _EVAL_DEV, HOLDOUT_SET as _EVAL_HOLDOUT
    # 默认使用开发集；最终报告阶段手动切换为 _EVAL_HOLDOUT
    DATASET = _EVAL_DEV
except ImportError:
    # 如果 eval_dataset.py 不存在, 使用内置占位集
    DATASET = [
        {
            "query": "__PLACEHOLDER__: 请创建 tests/eval_dataset.py 并添加标注数据",
            "relevant_keywords": ["PLACEHOLDER"],
            "collection": None,
        },
    ]


# ==================================================================
#  实验 1: 检索准确率消融评测
# ==================================================================
@dataclass
class QueryExample:
    query: str
    relevant_keywords: List[str] = field(default_factory=list)
    relevant_chunk_ids: List[str] = field(default_factory=list)
    collection: Optional[str] = None
    require_all_keywords: bool = False  # True=所有关键词必须同时出现；False=命中任意一个即算hit
    # Coverage@K 知识维度标注: [{"dim": "法律法规", "chunk_ids": ["5","11"], "min_hit": 1}, ...]
    relevant_dimensions: List[Dict] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """单次检索的命中结果"""
    query: str
    retrieved_chunks: List[Dict]  # [{chunk_id, text, score, rank}, ...]
    hits_at: Dict[int, bool]     # {1: True, 3: True, ...} 表示第K位命中
    found_relevant_ids: Set[str] = field(default_factory=set)  # 命中过的 ground-truth chunk_id 集合


@dataclass
class AblationMetrics:
    """一轮消融统计"""
    label: str                  # "向量" / "向量+BM25" / "向量+BM25+CE"
    hit_rate_at_k: Dict[int, float]  # {1: 0.45, 3: 0.72, 5: 0.85, 10: 0.92}
    mrr: float                        # Mean Reciprocal Rank
    recall_at_k: Dict[int, float]     # {5: 0.55, 10: 0.78} — 仅 chunk_id 标注时有意义
    ndcg_at_k: Dict[int, float]       # {5: 0.68, 10: 0.72}
    coverage_at_k: Dict[int, float] = field(default_factory=dict)  # {3: 0.65, 5: 0.82} — 知识维度覆盖
    per_query: List[RetrievalResult] = field(default_factory=list)  # 逐条明细


class AblationRetriever:
    """
    可控制的检索器, 支持四种消融模式:
      vec_only        — 仅向量语义检索
      hybrid_no_ce    — 向量 + BM25 + RRF, 但不做 CrossEncoder 重排序
      ce_no_mmr       — 向量 + BM25 + RRF + CE 重排序, 但跳过自适应阈值/去重/MMR
      full            — 全链路 (向量 + BM25 + RRF + CE + 自适应阈值 + 去重 + MMR)
    """

    def __init__(self, engine, collection_name: str, top_k: int = 10, mode: str = "full"):
        self.engine = engine
        self.collection_name = collection_name
        self.top_k = top_k
        self.mode = mode
        self._store = None
        self._bm25 = None
        self._cross_encoder = None

    def _ensure_store_and_bm25(self):
        if self._store is None:
            self._store = self.engine.get_chroma(self.collection_name)
        if self.mode != "vec_only" and self._bm25 is None:
            self._bm25 = self.engine.ensure_bm25_index(self.collection_name)

    # ---- 模式 A: 纯向量 ----
    def _retrieve_vec_only(self, query: str) -> List[Tuple]:
        """返回 [(Document, cosine_score), ...] 按余弦相似度降序"""
        self._ensure_store_and_bm25()
        hits = self._store.similarity_search_with_score(query, k=self.top_k)
        scored = []
        for doc, l2_score in hits:
            cos = 1.0 - float(l2_score) if float(l2_score) <= 2.0 else 1.0 / (1.0 + float(l2_score))
            scored.append((doc, cos))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ---- 模式 B: 向量 + BM25 (跳过 CE/去重/MMR) ----
    def _retrieve_no_ce(self, query: str) -> List[Tuple]:
        self._ensure_store_and_bm25()
        from chunker_api.rag.retrieval_engine import _ensure_hybrid_imports, _hybrid_imports
        _ensure_hybrid_imports()
        from hybrid_retrieval_fusion.rrf_merger import RRFMerger

        # 1) 语义检索
        vec_hits = self._store.similarity_search_with_score(
            query, k=max(self.top_k * 6, 20)
        )

        # 2) BM25
        bm25_hits = self._bm25.search(query, k=max(self.top_k * 6, 20))

        # 3) RRF 融合
        rrf_results = RRFMerger.reciprocal_rank_fusion(vec_hits, bm25_hits, self._bm25, k=10)

        # 直接按 RRF 排序取 top_k, 跳过 CE/去重/MMR
        results = []
        for doc, rrf_score in rrf_results[: self.top_k]:
            results.append((doc, float(rrf_score)))
        return results

    # ---- 模式 C: CE 重排序 (跳过自适应阈值/去重/MMR) ----
    def _ensure_cross_encoder(self):
        """获取 CrossEncoder（用于 ce_no_mmr 模式）"""
        if self._cross_encoder is None:
            self._cross_encoder = self.engine.get_cross_encoder()

    def _retrieve_ce_no_mmr(self, query: str) -> List[Tuple]:
        """向量 + BM25 + RRF + CE 重排序 + CE 归一化 → 按 s_ce_norm 排序取 top_k。
        注意：跳过 HybridRetriever 第 7-9 步（自适应阈值/去重/MMR），
        仅测试 CE 本身的排序提升。"""
        self._ensure_store_and_bm25()
        self._ensure_cross_encoder()
        from chunker_api.rag.retrieval_engine import _ensure_hybrid_imports
        _ensure_hybrid_imports()
        from hybrid_retrieval_fusion.rrf_merger import RRFMerger
        from hybrid_retrieval_fusion.hybrid_retriever import Candidate, _stable_uid

        m_for_rerank = max(20, self.top_k * 6)

        # 1) 语义检索
        vec_hits = self._store.similarity_search_with_score(query, k=m_for_rerank)

        # 2) BM25
        bm25_hits = self._bm25.search(query, k=m_for_rerank)

        # 3) RRF 融合
        rrf_results = RRFMerger.reciprocal_rank_fusion(vec_hits, bm25_hits, self._bm25, k=10)

        # 4) 构建候选 + 查找原始分数
        cands = []
        for doc, rrf_score in rrf_results[:m_for_rerank]:
            cos_score = 0.0
            bm25_score = 0.0
            for vec_doc, score in vec_hits:
                if _stable_uid(vec_doc) == _stable_uid(doc):
                    cos_score = 1.0 - float(score) if float(score) <= 1.0 else float(score)
                    break
            for doc_id, score in bm25_hits:
                if doc_id == _stable_uid(doc):
                    bm25_score = float(score)
                    break
            cand = Candidate(doc=doc, cos=cos_score, bm25=bm25_score, rrf_score=rrf_score)
            cands.append(cand)

        if not cands:
            return []

        # 5) CE 重排序
        cand_texts = [c.doc.page_content or "" for c in cands]
        ce_scores = self._cross_encoder.score(query, cand_texts)
        for cand, score in zip(cands, ce_scores):
            cand.s_ce = float(score)

        # 6) CE 分数归一化
        ce_scores_list = [c.s_ce for c in cands]
        min_ce = min(ce_scores_list)
        max_ce = max(ce_scores_list)
        if max_ce > min_ce:
            for cand in cands:
                cand.s_ce_norm = (cand.s_ce - min_ce) / (max_ce - min_ce)
        else:
            for i, cand in enumerate(cands):
                cand.s_ce_norm = 0.5 + (i - len(cands)/2) * 0.01

        # === 跳过步骤 7-9, 直接按 s_ce_norm 排序取 top_k ===
        cands.sort(key=lambda c: c.s_ce_norm, reverse=True)
        results = []
        for cand in cands[: self.top_k]:
            # 将分数写入 metadata 方便后续统计
            meta = dict(cand.doc.metadata or {})
            meta.update({
                "_s_ce": round(cand.s_ce, 6),
                "_s_ce_norm": round(cand.s_ce_norm, 6),
                "_rrf_score": round(cand.rrf_score, 6),
            })
            from langchain_core.documents import Document
            doc = Document(page_content=cand.doc.page_content, metadata=meta)
            results.append((doc, cand.s_ce_norm))
        return results

    # ---- 模式 D: 全链路 (无条件 MMR) ----
    def _retrieve_full(self, query: str) -> List[Tuple]:
        """全链路检索，MMR 无条件运行（阈值=-1.0）"""
        return self._retrieve_with_mmr_threshold(query, mmr_threshold=-1.0)

    # ---- 模式 E: 条件 MMR ----
    def _retrieve_conditional(self, query: str) -> List[Tuple]:
        """全链路检索，MMR 条件触发（默认阈值 0.85）"""
        return self._retrieve_with_mmr_threshold(query, mmr_threshold=0.85)

    def _retrieve_with_mmr_threshold(self, query: str, mmr_threshold: float) -> List[Tuple]:
        """直接创建 HybridRetriever（不走 engine 缓存），保证 MMR 阈值独立可控。"""
        self._ensure_store_and_bm25()
        self._ensure_cross_encoder()
        from chunker_api.rag.retrieval_engine import _ensure_hybrid_imports, _hybrid_imports
        _ensure_hybrid_imports()
        HybridRetriever = _hybrid_imports['HybridRetriever']
        HybridLCRetriever = _hybrid_imports['HybridLCRetriever']

        hybrid = HybridRetriever(
            vectorstore=self._store,
            bm25_indexer=self._bm25,
            cross_encoder=self._cross_encoder,
            embeddings=self.engine.get_embeddings(),
            m_for_rerank=max(20, self.top_k * 6),
            top_k=self.top_k,
            mmr_similarity_threshold=mmr_threshold,
            search_kwargs={"filter": {"is_active": {"$ne": False}}},
        )
        retriever = HybridLCRetriever(hybrid)
        docs = retriever.invoke(query)
        results = []
        for doc in docs:
            score = doc.metadata.get("_s_ce_norm", doc.metadata.get("_rrf_score", 0.0))
            results.append((doc, float(score)))
        return results

    def retrieve(self, query: str) -> List[Tuple]:
        if self.mode == "vec_only":
            return self._retrieve_vec_only(query)
        elif self.mode == "hybrid_no_ce":
            return self._retrieve_no_ce(query)
        elif self.mode == "ce_no_mmr":
            return self._retrieve_ce_no_mmr(query)
        elif self.mode == "full":
            return self._retrieve_full(query)
        elif self.mode == "conditional":
            return self._retrieve_conditional(query)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


# ---------- 评测指标 ----------

def _chunk_uid(meta: dict, collection_name: str = "") -> str:
    """从 metadata 中提取 chunk 的唯一标识。
    对于跨文档查询, 返回 'collection_name:chunk_id' 格式以做区分。"""
    base = str(
        meta.get("chunk_id")
        or meta.get("chunk_index")
        or meta.get("source")
        or meta.get("id")
        or ""
    )
    if collection_name and base:
        return f"{collection_name}:{base}"
    return base


def _is_hit(doc, example: QueryExample, collection_name: str = "") -> bool:
    """判断返回的文档是否命中 ground-truth。
    关键词匹配：默认宽松（至少命中一个关键词即算相关），
    设置 require_all_keywords=True 可恢复严格模式。"""
    text = doc.page_content or ""

    # 按 chunk_id 精确匹配 — 同时尝试纯 ID 和 collection:chunk_id 复合格式
    uid_raw = _chunk_uid(doc.metadata or {})
    uid_composite = _chunk_uid(doc.metadata or {}, collection_name)
    candidate_ids = {uid_raw, uid_composite}
    if example.relevant_chunk_ids:
        if any(cid in example.relevant_chunk_ids for cid in candidate_ids if cid):
            return True

    # 按关键词匹配 — 默认宽松：任意一个关键词出现在文本中即算 hit
    if example.relevant_keywords:
        if example.require_all_keywords:
            return all(kw in text for kw in example.relevant_keywords)
        else:
            return any(kw in text for kw in example.relevant_keywords)

    return False


def calculate_dcg(scores: List[float], k: int) -> float:
    """Discounted Cumulative Gain"""
    dcg = 0.0
    for i, score in enumerate(scores[:k]):
        dcg += score / math.log2(i + 2)
    return dcg


def _count_relevant_total(example: QueryExample) -> int:
    """返回该 query 的 ground-truth 相关 chunk 数量。
    仅 chunk_id 标注时能精确计数；关键词标注时返回 -1（N/A）。"""
    if example.relevant_chunk_ids:
        return len(example.relevant_chunk_ids)
    return -1


def evaluate_ablation(
    retriever: AblationRetriever,
    dataset: List[QueryExample],
    k_values: List[int] = [1, 3, 5, 10],
) -> AblationMetrics:
    """
    对给定检索器和数据集做评测, 返回 Hit Rate@K, MRR, Recall@K, NDCG@K。
    """
    per_query: List[RetrievalResult] = []
    reciprocal_ranks: List[float] = []
    ndcg_scores: Dict[int, List[float]] = {k: [] for k in k_values}
    recall_scores: Dict[int, List[float]] = {k: [] for k in k_values}
    coverage_scores: Dict[int, List[float]] = {k: [] for k in k_values}
    recall_applicable_count = 0  # 有多少条 query 适用于 Recall 计算

    for ex in dataset:
        query = ex.query
        results = retriever.retrieve(query)

        retrieved = []
        hits_at_k = {}
        first_hit_rank = None
        relevance_scores = []  # 1 for hit, 0 for miss
        relevant_total = _count_relevant_total(ex)

        for rank, (doc, score) in enumerate(results, 1):
            hit = _is_hit(doc, ex, retriever.collection_name)
            # 使用纯 chunk_id（不加 collection 前缀）与 eval_dataset 的 plain IDs 比对
            retrieved.append({
                "chunk_id": _chunk_uid(doc.metadata or {}),
                "text_snippet": (doc.page_content or "")[:120],
                "score": score,
                "rank": rank,
            })
            if hit:
                hits_at_k[rank] = True
                if first_hit_rank is None:
                    first_hit_rank = rank
            relevance_scores.append(1.0 if hit else 0.0)

        # MRR
        reciprocal_ranks.append(1.0 / first_hit_rank if first_hit_rank else 0.0)

        # Recall@K — 仅 chunk_id 标注模式下有意义
        if relevant_total > 0:
            recall_applicable_count += 1
            for k in k_values:
                # 统计 top-K 中命中的 distinct ground-truth chunk_id 数量
                distinct_found_in_top_k = len([
                    chunk for chunk in retrieved[:k]
                    if chunk["chunk_id"] in ex.relevant_chunk_ids
                ])
                recall_scores[k].append(distinct_found_in_top_k / relevant_total)

        # NDCG (ideal: all relevant first)
        for k in k_values:
            dcg = calculate_dcg(relevance_scores, k)
            ideal_relevance = sorted(relevance_scores, reverse=True)
            idcg = calculate_dcg(ideal_relevance, k)
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcg_scores[k].append(ndcg)

        # Coverage@K — 知识维度覆盖
        if ex.relevant_dimensions:
            total_dims = len(ex.relevant_dimensions)
            top_chunk_ids = {chunk["chunk_id"] for chunk in retrieved}
            for k in k_values:
                top_k_ids = {chunk["chunk_id"] for chunk in retrieved[:k]}
                covered = 0
                for dim in ex.relevant_dimensions:
                    dim_chunks = set(dim.get("chunk_ids", []))
                    min_hit = dim.get("min_hit", 1)
                    # 该维度在 top-K 中有 min_hit 个 chunk 命中即为覆盖
                    if len(top_k_ids & dim_chunks) >= min_hit:
                        covered += 1
                coverage_scores[k].append(covered / total_dims if total_dims > 0 else 0.0)

        per_query.append(RetrievalResult(
            query=query,
            retrieved_chunks=retrieved,
            hits_at=hits_at_k,
            found_relevant_ids=set(
                chunk["chunk_id"] for chunk in retrieved
                if chunk["chunk_id"] in ex.relevant_chunk_ids
            ) if relevant_total > 0 else set(),
        ))

    # 汇总 Hit Rate
    hit_rate_at_k = {}
    for k in k_values:
        hit_count = sum(1 for r in per_query if any(rk <= k for rk in r.hits_at))
        hit_rate_at_k[k] = hit_count / len(per_query) if per_query else 0.0

    # 汇总 Recall@K（只对 chunk_id 标注的 query 计算）
    recall_at_k = {}
    for k in k_values:
        scores = recall_scores.get(k, [])
        recall_at_k[k] = statistics.mean(scores) if scores else 0.0

    # 汇总 Coverage@K（只对 dimension 标注的 query 计算）
    coverage_at_k = {}
    for k in k_values:
        scores = coverage_scores.get(k, [])
        coverage_at_k[k] = statistics.mean(scores) if scores else 0.0

    return AblationMetrics(
        label=retriever.mode,
        hit_rate_at_k=hit_rate_at_k,
        mrr=statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
        recall_at_k=recall_at_k,
        ndcg_at_k={k: statistics.mean(v) if v else 0.0 for k, v in ndcg_scores.items()},
        coverage_at_k=coverage_at_k,
        per_query=per_query,
    )


def run_experiment_1(api_key: str, chroma_path: str) -> dict:
    """
    实验 1 主入口：依次执行四档消融 (vec_only / hybrid_no_ce / ce_no_mmr / full),
    每档只检索一次并存入 per_query_stats, 后续汇总直接从缓存读取, 避免重复检索。
    """
    from chunker_api.rag import get_rag_service

    rag = get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
    engine = rag.retriever  # RetrievalEngine 实例

    # 自动发现知识库
    from chunker_api.models import KnowledgeBase
    all_kbs = KnowledgeBase.objects.filter(status="active")
    collection_names = [kb.collection_name for kb in all_kbs]
    if not collection_names:
        print("[ERROR] 没有可用的知识库! 请先在 /kb 页面上传文档。")
        print("        如果没有真实数据, 可以先 mock 几条数据跑通流程。")
        return {}

    print(f"\n发现 {len(collection_names)} 个活跃知识库: {collection_names}")
    default_collection = collection_names[0]

    # 构造数据集
    dataset = []
    for item in DATASET:
        col = item.get("collection") or default_collection
        dataset.append(QueryExample(
            query=item["query"],
            relevant_keywords=item.get("relevant_keywords", item.get("relevant", [])),
            relevant_chunk_ids=item.get("relevant_chunk_ids", []),
            collection=col,
            require_all_keywords=item.get("require_all_keywords", False),
            relevant_dimensions=item.get("relevant_dimensions", []),
        ))

    k_values = [1, 3, 5, 10]
    MODES = [
        ("vec_only",     "A. 纯向量"),
        ("hybrid_no_ce", "B. 向量+BM25"),
        ("ce_no_mmr",    "C. 向量+BM25+CE"),
        ("full",         "D. 向量+BM25+CE+MMR(无条件)"),
        ("conditional",  "E. 向量+BM25+CE+MMR(条件触发)"),
    ]

    # ---- 单次循环：每档每个 query 只检索一次，存入 all_mode_stats ----
    all_mode_stats: Dict[str, List[AblationMetrics]] = {}  # {mode_label: [AblationMetrics per query]}

    for mode, label in MODES:
        print(f"\n{'='*60}")
        print(f"  运行消融配置: {label}")
        print(f"{'='*60}")

        per_query_stats: List[AblationMetrics] = []
        for ex in dataset:
            ret = AblationRetriever(
                engine=engine,
                collection_name=ex.collection,
                top_k=10,
                mode=mode,
            )
            m = evaluate_ablation(ret, [ex], k_values)
            per_query_stats.append(m)
            # 打印单条进度
            hr1 = m.hit_rate_at_k.get(1, 0)
            hr3 = m.hit_rate_at_k.get(3, 0)
            hr10 = m.hit_rate_at_k.get(10, 0)
            print(f"  [{ex.query[:40]}...] HR@1={hr1:.0%} HR@3={hr3:.0%} HR@10={hr10:.0%}")

        all_mode_stats[label] = per_query_stats

    # ======= 汇总输出 (从缓存读取, 不重复检索) =======
    print(f"\n{'='*80}")
    print(f"  检索准确率消融实验 — 汇总结果")
    print(f"{'='*80}")
    print(f"  测试查询数: {len(dataset)}")
    print(f"  知识库数量: {len(collection_names)}")
    has_recall = any(ex.relevant_chunk_ids for ex in dataset)
    has_coverage = any(ex.relevant_dimensions for ex in dataset)
    if has_recall:
        recall_queries = sum(1 for ex in dataset if ex.relevant_chunk_ids)
        print(f"  支持 Recall@K 的查询数: {recall_queries}/{len(dataset)} (使用 chunk_id 标注)")
    else:
        print(f"  Recall@K: N/A (请使用 relevant_chunk_ids 标注以启用召回率评测)")
    if has_coverage:
        coverage_queries = sum(1 for ex in dataset if ex.relevant_dimensions)
        print(f"  支持 Coverage@K 的查询数: {coverage_queries}/{len(dataset)} (使用 relevant_dimensions 标注)")
    else:
        print(f"  Coverage@K: N/A (请使用 relevant_dimensions 标注以启用知识维度覆盖评测)")
    print(f"{'='*80}")

    summary = {}
    for mode, label in MODES:
        per_query_stats = all_mode_stats[label]

        hr = {}
        recall = {}
        ndcg = {}
        coverage = {}
        all_rr = [q.mrr for q in per_query_stats]
        for k in k_values:
            hits = sum(1 for q in per_query_stats if q.hit_rate_at_k.get(k, 0) > 0)
            hr[k] = hits / len(per_query_stats) if per_query_stats else 0.0
            all_ndcg = [q.ndcg_at_k.get(k, 0.0) for q in per_query_stats]
            ndcg[k] = statistics.mean(all_ndcg) if all_ndcg else 0.0
            all_recall = [q.recall_at_k.get(k, 0.0) for q in per_query_stats]
            recall[k] = statistics.mean(all_recall) if all_recall else 0.0
            all_coverage = [q.coverage_at_k.get(k, 0.0) for q in per_query_stats]
            coverage[k] = statistics.mean(all_coverage) if all_coverage else 0.0

        avg_mrr = statistics.mean(all_rr) if all_rr else 0.0

        print(f"\n--- {label} ---")
        print(f"  Hit Rate:  " + " | ".join(f"@{k}={hr[k]:.1%}" for k in k_values))
        print(f"  MRR:        {avg_mrr:.4f}")
        if has_recall:
            print(f"  Recall:     " + " | ".join(f"@{k}={recall[k]:.1%}" for k in k_values))
        else:
            print(f"  Recall:     N/A (请添加 relevant_chunk_ids 标注)")
        print(f"  NDCG:       " + " | ".join(f"@{k}={ndcg[k]:.4f}" for k in k_values))
        if has_coverage:
            # 只显示有意义的 K 值 (>= 总维度数比较合适的最小值)
            dim_counts = [len(ex.relevant_dimensions) for ex in dataset if ex.relevant_dimensions]
            avg_dims = int(statistics.mean(dim_counts)) if dim_counts else 3
            display_k = [k for k in k_values if k >= avg_dims - 1 or k == k_values[-1]]
            if not display_k:
                display_k = [k_values[-1]]
            print(f"  Coverage:   " + " | ".join(f"@{k}={coverage[k]:.1%}" for k in display_k))

        summary[label] = {
            "hit_rate_at_k": hr,
            "mrr": avg_mrr,
            "recall_at_k": recall,
            "ndcg_at_k": ndcg,
            "coverage_at_k": coverage,
        }

    # 计算提升百分比 (第一档 vs 最后一档)
    first_label, last_label = MODES[0][1], MODES[-1][1]
    if first_label in summary and last_label in summary:
        print(f"\n--- 对比: {last_label} vs {first_label} ---")
        for k in k_values:
            a = summary[first_label]["hit_rate_at_k"][k]
            c = summary[last_label]["hit_rate_at_k"][k]
            delta = (c - a) * 100
            print(f"  HR@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")
        if has_recall:
            for k in k_values:
                a = summary[first_label]["recall_at_k"][k]
                c = summary[last_label]["recall_at_k"][k]
                if a > 0 or c > 0:
                    delta = (c - a) * 100
                    print(f"  Recall@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")

        # E vs C: 条件 MMR 对比纯 CE（期望接近 C，不应该丢失召回）
        if "E. 向量+BM25+CE+MMR(条件触发)" in summary and "C. 向量+BM25+CE" in summary:
            print(f"\n--- 对比: E(条件MMR) vs C(CE) — 条件触发是否避免了无谓的召回损失 ---")
            for k in k_values:
                a = summary["C. 向量+BM25+CE"]["hit_rate_at_k"][k]
                c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["hit_rate_at_k"][k]
                delta = (c - a) * 100
                print(f"  HR@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")
            if has_recall:
                for k in k_values:
                    a = summary["C. 向量+BM25+CE"]["recall_at_k"][k]
                    c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["recall_at_k"][k]
                    if a > 0 or c > 0:
                        delta = (c - a) * 100
                        print(f"  Recall@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")
            if has_coverage and "C. 向量+BM25+CE" in summary:
                print(f"\n--- 对比: E vs C (条件触发 MMR 的 Coverage 价值) ---")
                for k in k_values:
                    a = summary["C. 向量+BM25+CE"]["coverage_at_k"][k]
                    c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["coverage_at_k"][k]
                    if a > 0 or c > 0:
                        delta = (c - a) * 100
                        print(f"  Coverage@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")

        # E vs D: 条件 MMR 对比无条件 MMR（期望 E 召回 > D，Coverage ≥ D）
        if "E. 向量+BM25+CE+MMR(条件触发)" in summary and "D. 向量+BM25+CE+MMR(无条件)" in summary:
            print(f"\n--- 对比: E(条件MMR) vs D(无条件MMR) — 条件触发是否避免了过度去重 ---")
            for k in k_values:
                a = summary["D. 向量+BM25+CE+MMR(无条件)"]["hit_rate_at_k"][k]
                c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["hit_rate_at_k"][k]
                delta = (c - a) * 100
                print(f"  HR@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")
            if has_recall:
                for k in k_values:
                    a = summary["D. 向量+BM25+CE+MMR(无条件)"]["recall_at_k"][k]
                    c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["recall_at_k"][k]
                    if a > 0 or c > 0:
                        delta = (c - a) * 100
                        print(f"  Recall@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")
            if has_coverage:
                for k in k_values:
                    a = summary["D. 向量+BM25+CE+MMR(无条件)"]["coverage_at_k"][k]
                    c = summary["E. 向量+BM25+CE+MMR(条件触发)"]["coverage_at_k"][k]
                    if a > 0 or c > 0:
                        delta = (c - a) * 100
                        print(f"  Coverage@{k}: {a:.1%} → {c:.1%} ({'+' if delta >= 0 else ''}{delta:.0f}pp)")

    return summary


# ==================================================================
#  实验 2: 冷启动性能基准测试
# ==================================================================

COLD_START_SCRIPT = r"""
'''
独立的冷启动基准脚本。
必须作为子进程运行以确保测量真实冷启动（无缓存、无预加载）。

v2: 新增模型缓存检查 + BM25 构建单独计时 + 明确口径说明
'''
import os
import sys
import time
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
sys.path.insert(0, ".")

results = {
    "stages": [],
    "total_elapsed_s": 0.0,
    "metadata": {
        "note": "被测耗时 = Python 进程内部耗时 (Django setup 到检索完成), "
                "不含 WSGI/Gunicorn worker 启动、网络往返等外层开销",
    },
}

t0_total = time.perf_counter()

# ---- Stage 1: Django 配置初始化 ----
t1 = time.perf_counter()
import django
django.setup()
from django.conf import settings
t2 = time.perf_counter()
results["stages"].append({
    "name": "1. Django setup (import django + settings)",
    "elapsed_s": round(t2 - t1, 4),
})

# ---- Stage 2: 获取 RAG 单例 (app 预热) ----
t1 = time.perf_counter()
from chunker_api.rag import get_rag_service
chroma_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
rag = get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
engine = rag.retriever
t2 = time.perf_counter()
results["stages"].append({
    "name": "2. get_rag_service() singleton",
    "elapsed_s": round(t2 - t1, 4),
})

# ---- Stage 3: _ensure_hybrid_imports() ----
t1 = time.perf_counter()
from chunker_api.rag.retrieval_engine import _ensure_hybrid_imports
imports = _ensure_hybrid_imports()
t2 = time.perf_counter()
results["stages"].append({
    "name": "3. _ensure_hybrid_imports() (langchain_chroma + dashscope + hybrid_retrieval_fusion + promt)",
    "elapsed_s": round(t2 - t1, 4),
})

# ---- Stage 4: 发现知识库 ----
from chunker_api.models import KnowledgeBase
kbs = list(KnowledgeBase.objects.filter(status="active"))
collections = [kb.collection_name for kb in kbs]

if not collections:
    results["warning"] = "没有可用的知识库, 跳过后续检索阶段"
else:
    collection_name = collections[0]

    # ---- 模型缓存检查 (不消耗时间, 仅记录状态) ----
    cross_encoder_path = getattr(settings, 'RERANKER_MODEL_PATH', '')
    cross_encoder_cached = os.path.isdir(cross_encoder_path) and any(
        f.endswith(('.bin', '.safetensors')) for f in os.listdir(cross_encoder_path) if os.path.isfile(os.path.join(cross_encoder_path, f))
    )
    results["metadata"]["cross_encoder_cached"] = cross_encoder_cached
    if not cross_encoder_cached:
        results["metadata"]["warning"] = (
            "CrossEncoder 模型未在本地缓存! "
            "请先手动跑一次完整流程下载模型, 否则本次测量会把下载耗时误算进冷启动。"
        )

    # ---- Stage 5a: ChromaDB 连接 + BM25 索引构建 (单独计时) ----
    t1 = time.perf_counter()
    store = engine.get_chroma(collection_name)
    bm25 = engine.ensure_bm25_index(collection_name)
    t2 = time.perf_counter()
    results["stages"].append({
        "name": "5a. Chroma 连接 + BM25 索引构建/加载",
        "elapsed_s": round(t2 - t1, 4),
    })

    # ---- Stage 5b: CrossEncoder 初始化 ----
    t1 = time.perf_counter()
    cross_encoder = engine.get_cross_encoder()
    t2 = time.perf_counter()
    results["stages"].append({
        "name": "5b. CrossEncoder 初始化 (模型加载到内存)",
        "elapsed_s": round(t2 - t1, 4),
    })

    # ---- Stage 5c: 完整首次检索 (向量+BM25+CE 推理) ----
    t1 = time.perf_counter()
    retriever = engine.get_retriever(collection_name, top_k=10)
    docs1 = retriever.invoke("西藏")
    t2 = time.perf_counter()
    results["stages"].append({
        "name": "5c. 首次检索完整链路 (含向量搜索+BM25+CE 推理+去重+MMR)",
        "elapsed_s": round(t2 - t1, 4),
        "docs_returned": len(docs1),
    })

    # ---- Stage 6: 第二次检索 (缓存命中) ----
    t1 = time.perf_counter()
    retriever2 = engine.get_retriever(collection_name, top_k=10)
    docs2 = retriever2.invoke("舆情")
    t2 = time.perf_counter()
    results["stages"].append({
        "name": "6. 二次检索 (缓存命中: retriever 复用)",
        "elapsed_s": round(t2 - t1, 4),
        "docs_returned": len(docs2),
    })

    # ---- Stage 7: 第三次检索 (不同 top_k, 不同查询) ----
    t1 = time.perf_counter()
    retriever3 = engine.get_retriever(collection_name, top_k=5)
    docs3 = retriever3.invoke("监测体系")
    t2 = time.perf_counter()
    results["stages"].append({
        "name": "7. 三次检索 (不同 top_k, 缓存场景)",
        "elapsed_s": round(t2 - t1, 4),
        "docs_returned": len(docs3),
    })

results["total_elapsed_s"] = round(time.perf_counter() - t0_total, 4)
print(json.dumps(results, ensure_ascii=False, indent=2))
"""


def run_experiment_2(num_runs: int = 5):
    """
    实验 2 主入口: 在独立子进程中运行冷启动脚本 N 次, 输出均值 ± 标准差。

    Args:
        num_runs: 重复运行次数 (默认 5 次)
    """
    print(f"\n{'='*80}")
    print(f"  冷启动性能基准测试")
    print(f"  (在独立子进程中运行, 确保零缓存初始状态)")
    print(f"{'='*80}")

    # 写入临时脚本
    script_path = PROJECT_ROOT / "tests" / "_cold_start_benchmark.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(COLD_START_SCRIPT)

    all_runs: List[dict] = []

    try:
        for run_idx in range(1, num_runs + 1):
            print(f"\n[Run {run_idx}/{num_runs}]", end=" ", flush=True)

            result = subprocess.run(
                [sys.executable, "-u", str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
                timeout=180,
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
            )

            if result.returncode != 0:
                print(f"ERROR (退出码={result.returncode})")
                print(f"STDERR:\n{result.stderr[:1000]}")
                continue

            stdout = result.stdout
            json_start = stdout.find("{")
            json_end = stdout.rfind("}")
            if json_start == -1 or json_end == -1:
                print("ERROR (无 JSON 输出)")
                continue

            data = json.loads(stdout[json_start:json_end + 1])
            all_runs.append(data)
            print(f" total={data['total_elapsed_s']:.3f}s")

        if not all_runs:
            print("\n[ERROR] 所有运行均失败, 无法统计")
            return None

        # ---- 汇总统计 ----
        stage_names = [s["name"] for s in all_runs[0].get("stages", [])]
        stage_stats: Dict[str, List[float]] = {name: [] for name in stage_names}
        total_times: List[float] = []

        for run in all_runs:
            total_times.append(run["total_elapsed_s"])
            for stage in run.get("stages", []):
                if stage["name"] in stage_stats:
                    stage_stats[stage["name"]].append(stage["elapsed_s"])

        print(f"\n{'='*80}")
        print(f"  冷启动各阶段耗时总览 (n={len(all_runs)}, 均值 ± 标准差)")
        print(f"{'='*80}")
        print(f"{'阶段':<6} {'描述':<55} {'均值(s)':>8} {'± 标准差':>8}")
        print(f"{'-'*6} {'-'*55} {'-'*8} {'-'*8}")

        for name in stage_names:
            values = stage_stats[name]
            mean_val = statistics.mean(values) if values else 0.0
            std_val = statistics.stdev(values) if len(values) >= 2 else 0.0
            marker = ""
            if "5b" in name:
                marker = "  << CrossEncoder 初始化"
            elif "5c" in name:
                marker = "  << 冷启动峰值"
            elif name.startswith("6."):
                marker = "  << 缓存命中"
            docs = all_runs[0].get("stages", [])[stage_names.index(name)].get("docs_returned", "")
            doc_info = f" (返回{docs}篇)" if docs else ""
            print(f"{'':>6} {name:<55s} {mean_val:>8.3f}s ±{std_val:>7.3f}s{marker}{doc_info}")

        print(f"{'-'*6} {'-'*55} {'-'*8} {'-'*8}")
        total_mean = statistics.mean(total_times)
        total_std = statistics.stdev(total_times) if len(total_times) >= 2 else 0.0
        print(f"{'':>6} {'总计 (Django setup 到三次检索完成)':<55s} {total_mean:>8.3f}s ±{total_std:>7.3f}s")

        # ---- 关键结论 ----
        cold_vals = [s["elapsed_s"] for s in all_runs[0].get("stages", []) if "5c" in s["name"]]
        warm_vals = [s["elapsed_s"] for s in all_runs[0].get("stages", []) if s["name"].startswith("6.")]
        bm25_vals = [s["elapsed_s"] for s in all_runs[0].get("stages", []) if "5a" in s["name"]]
        ce_vals = [s["elapsed_s"] for s in all_runs[0].get("stages", []) if "5b" in s["name"]]

        if cold_vals and warm_vals:
            cold_val = cold_vals[0]
            warm_val = warm_vals[0]
            ratio = cold_val / warm_val if warm_val > 0 else float("inf")
            print(f"\n[关键结论] 冷启动首次检索 vs 缓存命中:")
            print(f"  首次检索完整链路: {cold_val:.3f}s")
            print(f"  二次检索(缓存命中): {warm_val:.3f}s")
            print(f"  比值: {ratio:.1f}x (缓存加速)")
            print(f"  节省: {cold_val-warm_val:.3f}s ({((1-1/ratio)*100):.0f}%)")
            if bm25_vals:
                print(f"  BM25 构建/加载: {bm25_vals[0]:.3f}s (占首次检索的 {bm25_vals[0]/cold_val*100:.0f}%)")
            if ce_vals:
                print(f"  CrossEncoder 初始化: {ce_vals[0]:.3f}s (占首次检索的 {ce_vals[0]/cold_val*100:.0f}%)")

        # 稳定性检查
        if total_std > total_mean * 0.15:
            print(f"\n[WARNING] 标准差/均值={total_std/total_mean:.1%} > 15%, 测试环境噪声较大")

        # 输出口径说明
        metadata = all_runs[0].get("metadata", {})
        if metadata.get("note"):
            print(f"\n[口径] {metadata['note']}")
        if metadata.get("warning"):
            print(f"[WARNING] {metadata['warning']}")

        return {
            "num_runs": len(all_runs),
            "total_mean": total_mean,
            "total_std": total_std,
            "stage_stats": {name: {"mean": statistics.mean(v), "std": statistics.stdev(v) if len(v) >= 2 else 0.0}
                           for name, v in stage_stats.items()},
        }

    finally:
        if script_path.exists():
            try:
                script_path.unlink()
            except OSError:
                pass




# ==================================================================
#  辅助: Mock 数据生成 (用于无真实数据时的 smoke test)
# ==================================================================
def generate_mock_data(engine, collection_name: str, num_docs: int = 20) -> List[QueryExample]:
    """
    当没有标注数据时, 从知识库中随机抽取 chunk 作为 ground-truth,
    构造自测数据集。这种方法叫 "leave-one-out" 自检:
    — 从知识库随机挑一个 chunk 的文本前 30 字作为 query
    — 该 chunk 自身作为 relevant

    注意: 这只是 smoke test, 不能作为正式评测依据。
    """
    from langchain_core.documents import Document as LCDoc
    store = engine.get_chroma(collection_name)
    raw = store._collection.get(include=["documents", "metadatas"])
    all_docs: List[LCDoc] = []
    for text, meta in zip(raw.get("documents", []) or [], raw.get("metadatas", []) or []):
        meta = meta or {}
        all_docs.append(LCDoc(page_content=text or "", metadata=meta))

    import random
    random.shuffle(all_docs)
    selected = all_docs[:min(num_docs, len(all_docs))]

    dataset = []
    for doc in selected:
        text = doc.page_content or ""
        query_text = text[:30].strip()
        if not query_text:
            continue
        uid = (doc.metadata or {}).get("chunk_id", "")
        dataset.append(QueryExample(
            query=query_text,
            relevant_chunk_ids=[uid] if uid else [],
            relevant_keywords=[],
            collection=collection_name,
        ))
    return dataset


# ==================================================================
#  CLI 入口
# ==================================================================
# ==================================================================
#  Bootstrap 置信区间
# ==================================================================
def bootstrap_confidence_interval(
    values: List[float], n_resamples: int = 1000, alpha: float = 0.05
) -> Dict[str, float]:
    """
    对一组指标值做 bootstrap resampling, 返回 95% 置信区间。

    Args:
        values: 逐 query 的指标值列表 (e.g. HR@5 = 1 for hit, 0 for miss)
        n_resamples: bootstrap 重采样次数
        alpha: 显著性水平 (0.05 → 95% CI)

    Returns:
        {"mean": 0.72, "ci_lower": 0.65, "ci_upper": 0.77}
    """
    if not values:
        return {"mean": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    arr = list(values)
    means = []
    for _ in range(n_resamples):
        sample = [random.choice(arr) for _ in range(len(arr))]
        means.append(statistics.mean(sample))

    means.sort()
    lower_idx = int((alpha / 2) * n_resamples)
    upper_idx = int((1 - alpha / 2) * n_resamples)

    return {
        "mean": statistics.mean(arr),
        "ci_lower": means[max(0, lower_idx)],
        "ci_upper": means[min(n_resamples - 1, upper_idx)],
    }


def bootstrap_metric_per_query(
    per_query_stats: List["AblationMetrics"], k: int, metric: str = "hit_rate"
) -> Dict[str, float]:
    """
    从 per_query_stats 中提取逐 query 的指标值, 计算 bootstrap CI。

    metric: "hit_rate" | "recall" | "ndcg"
    """
    values = []
    for q in per_query_stats:
        if metric == "hit_rate":
            # 1 if any hit within top-k, else 0
            val = 1.0 if any(rk <= k for rk in q.per_query[0].hits_at) else 0.0
        elif metric == "recall":
            val = q.recall_at_k.get(k, 0.0)
        elif metric == "ndcg":
            val = q.ndcg_at_k.get(k, 0.0)
        else:
            val = 0.0
        # 只统计有效值（非 N/A）
        if val >= 0:
            values.append(val)

    return bootstrap_confidence_interval(values)


def print_metric_with_ci(label: str, value: float, ci: Optional[Dict[str, float]] = None) -> str:
    """格式化输出: "85.0% (95% CI: 78.2%-90.1%)" """
    if ci and ci.get("ci_lower", 0) > 0:
        return f"{value:.1%} (95% CI: {ci['ci_lower']:.1%}-{ci['ci_upper']:.1%})"
    return f"{value:.1%}"


def main():
    global DATASET
    parser = argparse.ArgumentParser(description="RAG 消融实验")
    parser.add_argument(
        "--exp", choices=["retrieval", "cold_start", "all"], default="all",
        help="选择要运行的实验 (默认 all)"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="实验 1: 使用自动生成的 mock 数据集 (仅 smoke test)"
    )
    parser.add_argument(
        "--mock-count", type=int, default=20,
        help="mock 数据集的样本数"
    )
    args = parser.parse_args()

    # ---- 初始化 Django ----
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    import django
    django.setup()
    from django.conf import settings

    api_key = getattr(settings, "DASHSCOPE_API_KEY", "")
    chroma_path = getattr(settings, "CHROMA_DB_PATH", "./chroma_db")

    if args.exp in ("retrieval", "all"):
        # 检查是否有真实数据集
        if args.mock or len(DATASET) == 0:
            print("[INFO] 使用 MOCK 数据模式 (smoke test)")
            from chunker_api.rag import get_rag_service
            rag = get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
            engine = rag.retriever
            from chunker_api.models import KnowledgeBase
            kbs = KnowledgeBase.objects.filter(status="active")
            if not kbs:
                print("[ERROR] 没有知识库, 无法生成 mock 数据")
            else:
                col = kbs.first().collection_name
                mock_dataset = generate_mock_data(engine, col, args.mock_count)
                for ex in mock_dataset:
                    DATASET.append({
                        "query": ex.query,
                        "relevant": ex.relevant_keywords,
                        "relevant_chunk_ids": ex.relevant_chunk_ids,
                        "collection": ex.collection,
                    })
                print(f"[INFO] 生成了 {len(mock_dataset)} 条 mock 数据")

        print("\n[实验 1] 检索准确率消融评测")
        run_experiment_1(api_key, chroma_path)

    if args.exp in ("cold_start", "all"):
        print("\n[实验 2] 冷启动性能基准测试")
        run_experiment_2()


if __name__ == "__main__":
    main()
