"""
RetrievalEngine — ChromaDB / BM25 / Embeddings / HybridRetrieval management.
Extracted from RAGService to keep retrieval concerns separate from generation.
"""

import logging
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# 确保可以导入项目根目录下的 promt 与 hybrid_retrieval_fusion
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy hybrid-import machinery
# ---------------------------------------------------------------------------
# 混合检索依赖默认未加载，由 _ensure_hybrid_imports() 惰性导入
HYBRID_AVAILABLE = False
_hybrid_imports: dict = {}


def _ensure_hybrid_imports():
    """惰性导入混合检索与画像 Prompt 所需的所有重型依赖。"""
    global HYBRID_AVAILABLE, _hybrid_imports
    if _hybrid_imports:
        return _hybrid_imports
    try:
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from dashscope import MultiModalEmbedding
        from http import HTTPStatus
        from hybrid_retrieval_fusion import (
            BM25Indexer,
            CrossEncoderWrapper,
            RemoteCrossEncoderWrapper,
            HybridRetriever,
            HybridLCRetriever,
        )
        from promt.prompt import (
            categorize_user_profile,
            get_judge_prompt,
            get_rag_template,
            get_direct_template,
            get_refusal_response,
        )
        _hybrid_imports = {
            'Chroma': Chroma,
            'Document': Document,
            'MultiModalEmbedding': MultiModalEmbedding,
            'HTTPStatus': HTTPStatus,
            'BM25Indexer': BM25Indexer,
            'CrossEncoderWrapper': CrossEncoderWrapper,
            'RemoteCrossEncoderWrapper': RemoteCrossEncoderWrapper,
            'HybridRetriever': HybridRetriever,
            'HybridLCRetriever': HybridLCRetriever,
            'categorize_user_profile': categorize_user_profile,
            'get_judge_prompt': get_judge_prompt,
            'get_rag_template': get_rag_template,
            'get_direct_template': get_direct_template,
            'get_refusal_response': get_refusal_response,
        }
        HYBRID_AVAILABLE = True
    except Exception as e:
        logger.warning(f"混合检索或Prompt模块不可用，将降级: {e}")
        HYBRID_AVAILABLE = False
        _hybrid_imports = {}
    return _hybrid_imports


# ---------------------------------------------------------------------------
# TongyiEmbeddings
# ---------------------------------------------------------------------------
class TongyiEmbeddings:
    def __init__(self, api_key: str, model_name: str = "tongyi-embedding-vision-plus"):
        self.api_key = api_key
        self.model_name = model_name

    def _encode(self, payload: list) -> list:
        imports = _ensure_hybrid_imports()
        MultiModalEmbedding = imports['MultiModalEmbedding']
        HTTPStatus = imports['HTTPStatus']
        resp = MultiModalEmbedding.call(model=self.model_name, input=payload, api_key=self.api_key)
        if resp.status_code == HTTPStatus.OK:
            return [item.get("embedding", []) for item in resp.output.get("embeddings", [])]
        raise RuntimeError(f"通义向量接口失败: {resp.code} - {resp.message}")

    def embed_query(self, text: str) -> list:
        if not text:
            return []
        res = self._encode([{"text": text}])
        return res[0] if res else []

    def embed_documents(self, texts: list) -> list:
        if not texts:
            return []
        payload = [{"text": t} for t in texts]
        return self._encode(payload)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# RetrievalEngine
# ---------------------------------------------------------------------------
class RetrievalEngine:
    """
    ChromaDB / BM25 / Embeddings / HybridRetrieval 管理。
    从 RAGService 提取，保持检索逻辑与生成逻辑分离。
    """

    def __init__(
        self,
        api_key: str,
        encoder_model: str = "tongyi-embedding-vision-plus",
        chroma_db_path: str = "./chroma_db"
    ):
        """
        初始化检索引擎。

        Args:
            api_key: 通义千问 API Key
            encoder_model: 使用的编码器模型名称
            chroma_db_path: ChromaDB 数据库路径
        """
        self.api_key = api_key
        self.encoder_model = encoder_model
        self.chroma_db_path = chroma_db_path

        # 延迟初始化编码器（只在需要时初始化）
        self._hf_embeddings = None
        self._cross_encoder = None
        self._retriever_cache: Dict[str, Any] = {}

        # 配置：从 settings 读取，提供默认值
        # 注意：RRF 分数通常在 0~0.2 左右（取决于 rrf_k / 候选规模），0.5 会导致几乎永远判定为"不相关"
        self.RELEVANCE_THRESHOLD: float = getattr(settings, 'RAG_RELEVANCE_THRESHOLD', 0.04)
        # CrossEncoder raw logit 达到阈值才回复，否则直接拒答。
        self.CE_RELEVANCE_THRESHOLD: float = getattr(settings, 'RAG_CE_RELEVANCE_THRESHOLD', 0.3)
        # MMR 条件触发阈值：仅当候选 chunk 之间最大 pairwise 余弦相似度 >= 此值时运行 MMR。
        self.MMR_SIMILARITY_THRESHOLD: float = getattr(settings, 'RAG_MMR_SIMILARITY_THRESHOLD', 0.85)

    # =============== 内部工具方法 ===============

    def _is_legacy_chroma_schema_error(self, err: Exception) -> bool:
        return "collections.topic" in str(err)

    def _resolve_fallback_chroma_path(self) -> Optional[str]:
        """若 chroma_db_runtime 存在则回退到该目录。"""
        try:
            base_dir = Path(self.chroma_db_path).parent
            runtime_dir = base_dir / "chroma_db_runtime"
            if runtime_dir.is_dir():
                return str(runtime_dir.resolve())
        except Exception:
            pass
        return None

    def _get_bm25_indexer_dir(self, collection_name: str) -> str:
        # 与 promt 方案一致：每个集合一个 bm25 子目录
        bm25_dir = os.path.join(self.chroma_db_path, 'bm25', collection_name)
        os.makedirs(bm25_dir, exist_ok=True)
        return bm25_dir

    # =============== 混合检索：公共方法 ===============

    def get_embeddings(self):
        _ensure_hybrid_imports()
        if not HYBRID_AVAILABLE:
            raise RuntimeError("混合检索依赖不可用")
        if self._hf_embeddings is None:
            from utils.chunk.LocalEmbeddingEncoder import LocalEmbeddingEncoder
            local_model_path = getattr(settings, 'LOCAL_EMBEDDING_MODEL', r'G:\models\bge-large-zh')
            encoder = LocalEmbeddingEncoder(model_path=local_model_path)
            self._hf_embeddings = encoder.hf_embeddings
        return self._hf_embeddings

    def get_cross_encoder(self):
        _ensure_hybrid_imports()
        if not HYBRID_AVAILABLE:
            raise RuntimeError("混合检索依赖不可用")
        if self._cross_encoder is None:
            imports = _hybrid_imports
            use_local = getattr(settings, 'RERANKER_USE_LOCAL', True)
            if use_local:
                model_path = getattr(settings, 'RERANKER_MODEL_PATH', 'BAAI/bge-reranker-large')
                logger.info("使用本地 CrossEncoder 重排序模型: %s", model_path)
                self._cross_encoder = imports['CrossEncoderWrapper'](model_path=model_path)
            else:
                service_url = getattr(settings, 'RERANK_SERVICE_URL', 'http://127.0.0.1:5001/rerank')
                logger.info("使用远程重排序服务: %s", service_url)
                self._cross_encoder = imports['RemoteCrossEncoderWrapper'](service_url=service_url)
        return self._cross_encoder

    def get_chroma(self, collection_name: str):
        _ensure_hybrid_imports()
        if not HYBRID_AVAILABLE:
            raise RuntimeError("混合检索依赖不可用")
        from chromadb.config import Settings
        imports = _hybrid_imports
        return imports['Chroma'](
            collection_name=collection_name,
            embedding_function=self.get_embeddings(),
            persist_directory=self.chroma_db_path,
            client_settings=Settings(
                is_persistent=True,
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

    def ensure_bm25_index(self, collection_name: str):
        _ensure_hybrid_imports()
        imports = _hybrid_imports
        bm25 = imports['BM25Indexer'](store_dir=self._get_bm25_indexer_dir(collection_name))
        if bm25.try_load():
            return bm25
        # 从 Chroma 读取所有文档，重建 BM25
        store = self.get_chroma(collection_name)
        try:
            raw = store._collection.get(include=["documents", "metadatas"])
            docs: List[imports['Document']] = []
            Document = imports['Document']
            for doc_content, meta in zip(raw.get('documents', []) or [], raw.get('metadatas', []) or []):
                if meta and meta.get('is_active') is False:
                    continue
                docs.append(Document(page_content=doc_content or "", metadata=meta or {}))
            if docs:
                bm25.fit(docs)
                bm25.save()
                logger.info(f"已为集合 {collection_name} 新建 BM25 索引，文档数: {len(docs)}")
            else:
                bm25.save()  # 空索引也保存，保持一致
        except Exception as e:
            logger.warning(f"构建 BM25 索引失败（将以语义检索为主）：{e}")
            bm25.save()
        return bm25

    def get_retriever(self, collection_name: str, top_k: int):
        _ensure_hybrid_imports()
        imports = _hybrid_imports
        cache_key = (collection_name, top_k)
        
        # 1. 探测硬盘缓存的新鲜度 (防止多进程状态下的缓存穿透)
        import time
        bm25_dir = self._get_bm25_indexer_dir(collection_name)
        current_mtime = os.path.getmtime(bm25_dir) if os.path.exists(bm25_dir) else 0.0
        
        cached_data = self._retriever_cache.get(cache_key)
        if cached_data:
            # 向下兼容：如果存的只是一个纯 retriever (遗留代码)，或者时间戳不匹配，则重建
            if isinstance(cached_data, tuple) and len(cached_data) == 2:
                cached_retriever, cached_mtime = cached_data
                if current_mtime != 0.0 and current_mtime == cached_mtime:
                    return cached_retriever
                else:
                    logger.info(f"Retriever cache for {collection_name} is stale or directory missing. Rebuilding...")
            else:
                logger.info(f"Retriever cache for {collection_name} is legacy format. Rebuilding...")
                
        store = self.get_chroma(collection_name)
        bm25 = self.ensure_bm25_index(collection_name)
        # m_for_rerank：候选规模（越大越准但越慢）。默认随 top_k 动态，并可通过环境变量覆盖。
        env_m = os.getenv("RAG_M_FOR_RERANK")
        if env_m:
            try:
                m_for_rerank = max(5, int(env_m))
            except Exception:
                m_for_rerank = max(20, top_k * 6)
        else:
            m_for_rerank = max(20, top_k * 6)

        retriever = imports['HybridLCRetriever'](imports['HybridRetriever'](
            vectorstore=store,
            bm25_indexer=bm25,
            cross_encoder=self.get_cross_encoder(),
            embeddings=self.get_embeddings(),
            m_for_rerank=m_for_rerank,
            top_k=top_k,
            mmr_similarity_threshold=self.MMR_SIMILARITY_THRESHOLD,
            search_kwargs={"filter": {"is_active": {"$ne": False}}},
        ))
        
        # 记录最新的目录修改时间，随 retriever 缓存
        new_mtime = os.path.getmtime(bm25_dir) if os.path.exists(bm25_dir) else time.time()
        self._retriever_cache[cache_key] = (retriever, new_mtime)
        return retriever

    def format_docs(self, docs: List['Document']) -> str:
        parts = []
        for i, d in enumerate(docs, 1):
            s_fused = float(d.metadata.get('_s_fused', d.metadata.get('_rrf_score', 0.0)) or 0)
            s_ce = float(d.metadata.get('_s_ce_norm', 0.0) or 0)
            parts.append(f"[文档{i}] (融合分:{s_fused:.3f}, 重排分:{s_ce:.3f})\n内容: {d.page_content}\n")
        return "\n".join(parts)

    def is_relevant(self, docs: List['Document']) -> bool:
        return self.evaluate_quality(docs)["level"] == "relevant"

    def evaluate_quality(self, docs: List['Document']) -> Dict[str, Any]:
        """
        评估检索质量，返回二级判断。

        - relevant: 命中强度足够，走 RAG 模板 + LLM
        - none: 命中强度不足，直接返回预设拒答文案，不调 LLM
        """
        if not docs:
            return {"level": "none", "max_ce": 0.0, "max_fused": 0.0}

        max_fused = 0.0
        max_ce = float("-inf")
        has_ce_score = False

        for d in docs:
            meta = d.metadata or {}
            fused = _safe_float(meta.get('_s_fused', meta.get('_rrf_score', 0.0)), 0.0)
            if '_s_ce' in meta:
                has_ce_score = True
                ce = _safe_float(meta.get('_s_ce'), 0.0)
                if ce > max_ce:
                    max_ce = ce
            if fused > max_fused:
                max_fused = fused

        if has_ce_score:
            level = "relevant" if max_ce >= self.CE_RELEVANCE_THRESHOLD else "none"
            return {"level": level, "max_ce": max_ce, "max_fused": max_fused}

        level = "relevant" if max_fused >= self.RELEVANCE_THRESHOLD else "none"
        return {"level": level, "max_ce": 0.0, "max_fused": max_fused}
