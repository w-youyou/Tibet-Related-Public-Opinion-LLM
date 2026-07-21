# -*- coding: utf-8 -*-
import os
import pickle
import hashlib
from typing import List, Tuple, Dict, Any

import jieba
import numpy as np
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document


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


class BM25Indexer:
    """内存型 BM25 倒排索引器，支持持久化到目录。"""

    def __init__(self, store_dir: str = "./bm25_store"):
        self.store_dir = store_dir
        self._bm25: BM25Okapi | None = None
        self._doc_ids: List[str] = []
        self._doc_map: Dict[str, Dict[str, Any]] = {}
        self._corpus_tokens: List[List[str]] = []

    # ------------ build ------------
    def _build_text_for_bm25(self, doc: Document) -> str:
        meta = doc.metadata or {}
        parts = []
        if meta.get("table_name") or meta.get("sheet"):
            parts.append(str(meta.get("table_name") or meta.get("sheet")))
        if meta.get("file_name") or meta.get("source") or meta.get("source_file"):
            parts.append(str(meta.get("file_name") or meta.get("source") or meta.get("source_file")))
        parts.append(doc.page_content or "")
        return "\n".join(parts)

    def fit(self, documents: List[Document]) -> None:
        self._doc_ids, self._doc_map, self._corpus_tokens = [], {}, []
        for doc in documents:
            txt = self._build_text_for_bm25(doc)
            toks = jieba.lcut(txt)
            uid = _stable_uid(doc)
            self._doc_ids.append(uid)
            self._doc_map[uid] = {"text": doc.page_content or "", "meta": doc.metadata or {}}
            self._corpus_tokens.append(toks)
        if not self._corpus_tokens:
            raise RuntimeError("BM25Indexer.fit: empty corpus")
        self._bm25 = BM25Okapi(self._corpus_tokens)

    # ------------ persist ------------
    def save(self) -> None:
        os.makedirs(self.store_dir, exist_ok=True)
        with open(os.path.join(self.store_dir, "bm25.pkl"), "wb") as f:
            pickle.dump(self._bm25, f)
        with open(os.path.join(self.store_dir, "doc_ids.pkl"), "wb") as f:
            pickle.dump(self._doc_ids, f)
        with open(os.path.join(self.store_dir, "doc_map.pkl"), "wb") as f:
            pickle.dump(self._doc_map, f)

    def load(self) -> None:
        with open(os.path.join(self.store_dir, "bm25.pkl"), "rb") as f:
            self._bm25 = pickle.load(f)
        with open(os.path.join(self.store_dir, "doc_ids.pkl"), "rb") as f:
            self._doc_ids = pickle.load(f)
        with open(os.path.join(self.store_dir, "doc_map.pkl"), "rb") as f:
            self._doc_map = pickle.load(f)

    def try_load(self) -> bool:
        try:
            self.load()
            return self.is_ready()
        except Exception:
            return False

    def is_ready(self) -> bool:
        return self._bm25 is not None and len(self._doc_ids) > 0

    # ------------ search ------------
    def search(self, query: str, k: int = 50) -> List[Tuple[str, float]]:
        if not self.is_ready():
            raise RuntimeError("BM25Indexer not ready. Call fit()/load() first.")
        q_tokens = jieba.lcut(query or "")
        scores = self._bm25.get_scores(q_tokens)
        scores = np.array(scores, dtype=float)
        idx = scores.argsort()[::-1][:k]
        return [(self._doc_ids[int(i)], float(scores[int(i)])) for i in idx]

    def id_to_document(self, doc_id: str) -> Document:
        item = self._doc_map[doc_id]
        return Document(page_content=item["text"], metadata=item["meta"])
