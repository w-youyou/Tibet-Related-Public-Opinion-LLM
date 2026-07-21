"""
Tests for RetrievalEngine — all tests run without real ChromaDB.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from django.conf import settings as django_settings


# ============================================================================
# Bootstrap Django with minimal settings BEFORE importing retrieval_engine.
# The module does `from django.conf import settings` at import time, so Django
# must be configured first.
# ============================================================================
if not django_settings.configured:
    django_settings.configure(
        RAG_RELEVANCE_THRESHOLD=0.04,
        RAG_CE_RELEVANCE_THRESHOLD=0.3,
        RERANK_SERVICE_URL='http://127.0.0.1:5001/rerank',
        INSTALLED_APPS=[],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        SECRET_KEY='test-retrieval-engine-key',
    )

from chunker_api.rag.retrieval_engine import RetrievalEngine, TongyiEmbeddings, _ensure_hybrid_imports  # noqa: E402


# ============================================================================
# Fake document for testing format_docs / is_relevant / evaluate_quality
# ============================================================================
class FakeDoc:
    """Minimal document stand-in for langchain_core.documents.Document."""
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}


# ============================================================================
# Helpers
# ============================================================================
def make_engine(**overrides):
    """Create a RetrievalEngine with defaults suitable for testing."""
    defaults = dict(
        api_key="test-key",
        encoder_model="tongyi-embedding-vision-plus",
        chroma_db_path="./chroma_db",
    )
    defaults.update(overrides)
    return RetrievalEngine(**defaults)


# ============================================================================
# Tests
# ============================================================================
class TestRetrievalEngineInit:
    """Tests that don't need any heavy imports or ChromaDB."""

    def test_init_sets_api_key(self):
        engine = make_engine(api_key="sk-abc123")
        assert engine.api_key == "sk-abc123"

    def test_init_sets_encoder_model(self):
        engine = make_engine(encoder_model="custom-embed-model")
        assert engine.encoder_model == "custom-embed-model"

    def test_init_sets_chroma_db_path(self):
        engine = make_engine(chroma_db_path="/tmp/test_chroma")
        assert engine.chroma_db_path == "/tmp/test_chroma"

    def test_init_lazy_loading__hf_embeddings_is_none(self):
        engine = make_engine()
        assert engine._hf_embeddings is None

    def test_init_lazy_loading__cross_encoder_is_none(self):
        engine = make_engine()
        assert engine._cross_encoder is None

    def test_init_lazy_loading__retriever_cache_is_empty(self):
        engine = make_engine()
        assert engine._retriever_cache == {}

    def test_init_default_thresholds(self):
        engine = make_engine()
        assert engine.RELEVANCE_THRESHOLD == 0.04
        assert engine.CE_RELEVANCE_THRESHOLD == 0.3

    def test_bm25_indexer_dir_path(self):
        engine = make_engine(chroma_db_path="/data/chroma")
        result = engine._get_bm25_indexer_dir("my_collection")
        assert result == os.path.join("/data/chroma", "bm25", "my_collection")

    def test_bm25_indexer_dir_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = make_engine(chroma_db_path=tmp)
            engine._get_bm25_indexer_dir("test_coll")
            expected = Path(tmp) / "bm25" / "test_coll"
            assert expected.is_dir()

    def test_is_legacy_chroma_schema_error_detects_topic(self):
        engine = make_engine()
        err = Exception("table collections.topic has no column named foo")
        assert engine._is_legacy_chroma_schema_error(err)

    def test_is_legacy_chroma_schema_error_ignores_other(self):
        engine = make_engine()
        err = Exception("something else entirely")
        assert not engine._is_legacy_chroma_schema_error(err)

    def test_resolve_fallback_chroma_path_returns_none_when_absent(self):
        engine = make_engine(chroma_db_path="/nonexistent/path/chroma_db")
        assert engine._resolve_fallback_chroma_path() is None

    def test_resolve_fallback_chroma_path_returns_path_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp) / "chroma_db_runtime"
            runtime_dir.mkdir()
            engine = make_engine(chroma_db_path=str(Path(tmp) / "chroma_db"))
            result = engine._resolve_fallback_chroma_path()
            assert result is not None
            assert "chroma_db_runtime" in result


class TestFormatDocs:
    def test_format_docs_empty_list(self):
        engine = make_engine()
        assert engine.format_docs([]) == ""

    def test_format_docs_single_document(self):
        engine = make_engine()
        doc = FakeDoc("这是测试文档内容", {"_s_fused": 0.123, "_s_ce_norm": 0.456})
        result = engine.format_docs([doc])
        assert "[文档1]" in result
        assert "融合分:0.123" in result
        assert "重排分:0.456" in result
        assert "这是测试文档内容" in result

    def test_format_docs_multiple_documents(self):
        engine = make_engine()
        docs = [
            FakeDoc("文档A", {"_s_fused": 0.1, "_s_ce_norm": 0.2}),
            FakeDoc("文档B", {"_s_fused": 0.3, "_s_ce_norm": 0.4}),
        ]
        result = engine.format_docs(docs)
        assert "[文档1]" in result
        assert "[文档2]" in result
        assert "文档A" in result
        assert "文档B" in result

    def test_format_docs_falls_back_to_rrf_score(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_rrf_score": 0.05, "_s_ce_norm": 0.0})
        result = engine.format_docs([doc])
        assert "融合分:0.050" in result

    def test_format_docs_missing_metadata_defaults_to_zero(self):
        engine = make_engine()
        doc = FakeDoc("内容", {})
        result = engine.format_docs([doc])
        assert "融合分:0.000" in result
        assert "重排分:0.000" in result


class TestIsRelevant:
    def test_is_relevant_empty_docs(self):
        engine = make_engine()
        assert not engine.is_relevant([])

    def test_is_relevant_below_rrf_threshold(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_fused": 0.01})  # below 0.04
        assert not engine.is_relevant([doc])

    def test_is_relevant_above_rrf_threshold(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_fused": 0.05})  # above 0.04
        assert engine.is_relevant([doc])

    def test_is_relevant_uses_ce_when_present(self):
        engine = make_engine()
        # CE score below threshold but fused above — CE is preferred
        doc = FakeDoc("内容", {"_s_fused": 0.9, "_s_ce": 0.1})
        assert not engine.is_relevant([doc])

    def test_is_relevant_ce_above_threshold(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_ce": 0.5})  # above 0.3
        assert engine.is_relevant([doc])

    def test_is_relevant_max_across_docs(self):
        engine = make_engine()
        docs = [
            FakeDoc("low", {"_s_fused": 0.01}),
            FakeDoc("high", {"_s_fused": 0.08}),
        ]
        assert engine.is_relevant(docs)


class TestEvaluateQuality:
    def test_evaluate_quality_empty_docs(self):
        engine = make_engine()
        result = engine.evaluate_quality([])
        assert result["level"] == "none"
        assert result["max_ce"] == 0.0
        assert result["max_fused"] == 0.0

    def test_evaluate_quality_below_rrf(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_fused": 0.01})
        result = engine.evaluate_quality([doc])
        assert result["level"] == "none"

    def test_evaluate_quality_above_rrf(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_fused": 0.05})
        result = engine.evaluate_quality([doc])
        assert result["level"] == "relevant"

    def test_evaluate_quality_ce_scores(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_fused": 0.9, "_s_ce": 0.1})
        result = engine.evaluate_quality([doc])
        assert result["level"] == "none"
        assert result["max_ce"] == 0.1

    def test_evaluate_quality_ce_scores_relevant(self):
        engine = make_engine()
        doc = FakeDoc("内容", {"_s_ce": 0.5})
        result = engine.evaluate_quality([doc])
        assert result["level"] == "relevant"
        assert result["max_ce"] == 0.5


class TestTongyiEmbeddings:
    def test_init_sets_attributes(self):
        emb = TongyiEmbeddings(api_key="key123", model_name="my-model")
        assert emb.api_key == "key123"
        assert emb.model_name == "my-model"

    def test_default_model_name(self):
        emb = TongyiEmbeddings(api_key="key123")
        assert emb.model_name == "tongyi-embedding-vision-plus"

    def test_embed_query_empty_text(self):
        emb = TongyiEmbeddings(api_key="key123")
        assert emb.embed_query("") == []

    def test_embed_documents_empty_list(self):
        emb = TongyiEmbeddings(api_key="key123")
        assert emb.embed_documents([]) == []
