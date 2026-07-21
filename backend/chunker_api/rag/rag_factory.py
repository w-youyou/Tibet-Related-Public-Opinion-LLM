"""
RAGPipeline 的线程安全的单例工厂。

用法:
    from chunker_api.rag.rag_factory import get_rag_service, invalidate_rag_service

    svc = get_rag_service(api_key, model_name="qwen3-omni-flash")
    result = svc.run(question, collections, ...)
"""

from typing import Optional, Tuple

from django.conf import settings

from .rag_pipeline import RAGPipeline

_rag_service: Optional[RAGPipeline] = None
_signature: tuple = ()


def get_rag_service(
    api_key: str,
    model_name: str = "qwen3-omni-flash",
    chroma_db_path: str = None,
) -> RAGPipeline:
    """获取或创建 RAGPipeline 单例。

    Args:
        api_key: 通义千问 API Key
        model_name: LLM 模型名称
        chroma_db_path: ChromaDB 持久化目录（默认从 settings 读取）

    Returns:
        RAGPipeline 实例
    """
    global _rag_service, _signature

    if chroma_db_path is None:
        chroma_db_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')

    new_sig = (api_key, model_name, chroma_db_path)
    if _rag_service is None or _signature != new_sig:
        _rag_service = RAGPipeline(
            api_key=api_key,
            model_name=model_name,
            chroma_db_path=chroma_db_path,
        )
        _signature = new_sig

    return _rag_service


def invalidate_rag_service():
    """使缓存的 RAGPipeline 实例失效，下次调用将重新创建。"""
    global _rag_service
    _rag_service = None
