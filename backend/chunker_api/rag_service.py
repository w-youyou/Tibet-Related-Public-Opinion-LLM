"""RAGService backward compatibility shim.

For new code, import directly from chunker_api.rag:
    from chunker_api.rag import RAGPipeline, get_rag_service, QuestionRouter

The old RAGService class is preserved as an alias for any caller that
still references it directly.
"""
from .rag.question_router import QuestionRouter  # noqa: F401
from .rag.retrieval_engine import (  # noqa: F401
    RetrievalEngine,
    TongyiEmbeddings,
    _ensure_hybrid_imports,
    HYBRID_AVAILABLE,
)
from .rag.answer_builder import AnswerBuilder  # noqa: F401
from .rag.rag_pipeline import RAGPipeline  # noqa: F401
from .rag.rag_factory import get_rag_service, invalidate_rag_service  # noqa: F401

# Backward-compat alias
RAGService = RAGPipeline
