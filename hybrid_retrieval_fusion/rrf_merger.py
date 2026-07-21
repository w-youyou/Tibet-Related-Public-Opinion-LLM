# -*- coding: utf-8 -*-
from typing import List, Tuple
from langchain_core.documents import Document
from .bm25_indexer import BM25Indexer
import hashlib

def _stable_uid(doc: Document) -> str:
    meta = doc.metadata or {}
    source = str(
        meta.get("file_name")
        or meta.get("source")
        or meta.get("source_file")
        or meta.get("file_path")
        or meta.get("original_file")
        or ""
    )
    sheet = str(meta.get("table_name") or meta.get("sheet") or "")
    page = str(
        meta.get("pdf_page_number")
        or meta.get("page_number")
        or meta.get("page")
        or meta.get("chunk_id")
        or meta.get("chunk_index")
        or ""
    )
    head = (doc.page_content or "")[:256]
    return hashlib.md5(f"{source}||{sheet}||{page}||{head}".encode("utf-8")).hexdigest()

class RRFMerger:
    """RRF融合器"""
    
    @staticmethod
    def reciprocal_rank_fusion(
        vec_results: List[Tuple[Document, float]], 
        bm25_results: List[Tuple[str, float]], 
        bm25_indexer: BM25Indexer,
        k: int = 10
    ) -> List[Tuple[Document, float]]:
        """
        RRF融合算法
        """
        doc_rank_map = {}
        
        # 处理向量检索结果
        for rank, (doc, score) in enumerate(vec_results):
            uid = _stable_uid(doc)
            if uid not in doc_rank_map:
                doc_rank_map[uid] = {'doc': doc, 'ranks': []}
            # 确保排名从1开始
            doc_rank_map[uid]['ranks'].append(rank + 1)
        
        # 处理BM25检索结果
        for rank, (doc_id, score) in enumerate(bm25_results):
            try:
                doc = bm25_indexer.id_to_document(doc_id)
                uid = _stable_uid(doc)
                if uid not in doc_rank_map:
                    doc_rank_map[uid] = {'doc': doc, 'ranks': []}
                doc_rank_map[uid]['ranks'].append(rank + 1)
            except Exception as e:
                continue
        
        # 计算RRF分数
        rrf_scores = []
        for uid, info in doc_rank_map.items():
            rrf_score = 0.0
            for rank in info['ranks']:
                rrf_score += 1.0 / (k + rank)
            rrf_scores.append((info['doc'], rrf_score))
        
        # 按RRF分数降序排序
        rrf_scores.sort(key=lambda x: x[1], reverse=True)
        return rrf_scores
