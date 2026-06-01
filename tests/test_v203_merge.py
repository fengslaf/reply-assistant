import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from local_search.chroma_repo import LocalChromaRepo
from local_search.data_types import SearchContext
from local_search.embedding_service import LocalEmbeddingService
from local_search.retrievers import ExactRetriever, VectorRetriever
from local_search.search_engine import LocalSearchEngine


class _DummyEmbeddingService:
    def is_available(self):
        return False

    def embed(self, text):
        return None

    def get_model_info(self):
        return {
            "model_name": "dummy",
            "dimension": 0,
            "available": False,
            "has_sentence_transformers": False,
        }


class _DummyChromaRepo:
    def is_available(self):
        return False

    def sync_from_local_data(self, samples, embedding_service, user_id=None):
        return 0

    def get_count(self):
        return 0

    def search_similar(self, query_embedding, top_k=5, user_id=None):
        return []


class _StubIntelligenceManager:
    def analyze(self, query):
        intent_result = SimpleNamespace(
            intent="price",
            confidence=0.91,
            matched_keywords=["价格", "多少钱"],
        )
        entity_result = SimpleNamespace(entities={})
        return SimpleNamespace(intent_result=intent_result, entity_result=entity_result)


def test_embedding_service_graceful_fallback(monkeypatch):
    import local_search.embedding_service as embedding_module

    monkeypatch.setattr(embedding_module, "HAS_SENTENCE_TRANSFORMERS", False)

    service = LocalEmbeddingService()

    assert service.is_available() is False
    assert service.model_name == "moka-ai/m3e-small"
    assert service.embed("课程多少钱") is None
    assert service.embed_batch(["课程多少钱", ""]) == [None, None]


def test_embedding_service_does_not_attempt_remote_download_by_default(monkeypatch, tmp_path):
    import local_search.embedding_service as embedding_module

    calls = []

    class _FakeSentenceTransformer:
        def __init__(self, model_name):
            calls.append(model_name)

    monkeypatch.setattr(embedding_module, "HAS_SENTENCE_TRANSFORMERS", True)
    monkeypatch.setattr(embedding_module, "SentenceTransformer", _FakeSentenceTransformer, raising=False)
    monkeypatch.setattr(embedding_module, "M3E_SMALL_MODEL_PATH", tmp_path / "missing-model")
    monkeypatch.setattr(embedding_module, "ALLOW_REMOTE_EMBEDDING_DOWNLOAD", False)

    service = LocalEmbeddingService()

    assert service.is_available() is False
    assert calls == []


def test_chroma_repo_accepts_user_id_keyword(monkeypatch):
    import local_search.chroma_repo as chroma_module

    monkeypatch.setattr(chroma_module, "HAS_CHROMA", False)

    repo = LocalChromaRepo()

    assert repo.is_available() is False
    assert repo.search_similar([0.1, 0.2, 0.3], top_k=3, user_id="default_user") == []


def test_chroma_repo_sync_sanitizes_metadata_and_rebuilds_collection(tmp_path):
    repo = LocalChromaRepo(persist_dir=str(tmp_path / "chroma"))
    if not repo.is_available():
        pytest.skip("chromadb is unavailable in this environment")

    class _DummyEmbeddingService:
        def is_available(self):
            return True

        def embed(self, text):
            return [0.1, 0.2, 0.3]

    samples = [
        {
            "parent_message": "你们这个太贵了",
            "replies": ["还好，不贵"],
            "scene_tag": "问价格",
            "stage_tag": None,
            "quality_score": None,
        }
    ]

    first_sync_count = repo.sync_from_local_data(samples, _DummyEmbeddingService())
    assert first_sync_count == 1

    first_hit = repo.search_similar([0.1, 0.2, 0.3], top_k=1)
    assert first_hit
    assert first_hit[0]["parent_message"] == "你们这个太贵了"
    assert first_hit[0]["metadata"]["stage_tag"] == ""

    samples[0]["parent_message"] = "现在便宜了"
    samples[0]["replies"] = ["可以看看优惠"]

    second_sync_count = repo.sync_from_local_data(samples, _DummyEmbeddingService())
    assert second_sync_count == 1

    second_hit = repo.search_similar([0.1, 0.2, 0.3], top_k=1)
    assert second_hit
    assert second_hit[0]["parent_message"] == "现在便宜了"
    assert second_hit[0]["metadata"]["stage_tag"] == ""


def test_exact_retriever_preserves_original_sample_index():
    retriever = ExactRetriever()
    context = SearchContext(query="价格 多少", mode="exact", top_k=5)
    samples = [
        {
            "parent_message": "其他 内容",
            "replies": ["reply-0"],
            "scene_tag": "其他",
            "keywords": ["其他"],
        },
        {
            "parent_message": "价格 多少",
            "replies": ["reply-1"],
            "scene_tag": "价格",
            "keywords": ["价格", "多少"],
        },
    ]

    results = retriever.retrieve(context, samples)

    assert results
    assert results[0].matched_sample_id == "1"
    assert results[0].reply_id.startswith("local_exact_1_")


def test_vector_fallback_preserves_original_sample_index():
    retriever = VectorRetriever(embedding_service=None, chroma_repo=None)
    context = SearchContext(query="课程 多少钱", mode="vector", top_k=5)
    samples = [
        {
            "parent_message": "其他 内容",
            "replies": ["reply-0"],
        },
        {
            "parent_message": "课程 多少钱 优惠",
            "replies": ["reply-1"],
        },
    ]

    results = retriever.retrieve(context, samples)

    assert results
    assert results[0].matched_sample_id == "1"
    assert results[0].reply_id.startswith("local_vector_fallback_1_")


def test_intent_filter_pipeline_preserves_filtered_sample_index(tmp_path):
    data_file = tmp_path / "local_data.json"
    data_file.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "parent_message": "其他 内容",
                        "replies": ["reply-0"],
                        "scene_tag": "其他",
                        "keywords": ["其他"],
                    },
                    {
                        "parent_message": "价格 多少",
                        "replies": ["reply-1"],
                        "scene_tag": "价格",
                        "keywords": ["价格", "多少"],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    engine = LocalSearchEngine(
        data_path=str(data_file),
        embedding_service=_DummyEmbeddingService(),
        chroma_repo=_DummyChromaRepo(),
        enable_intelligence=False,
    )
    engine.intelligence_manager = _StubIntelligenceManager()
    engine.enable_intelligence = True

    context = SearchContext(query="价格 多少", mode="exact", top_k=1)
    results = engine.search(context)
    stats = engine.get_stats()

    assert context.intent == "price"
    assert results
    assert results[0].matched_sample_id == "1"
    assert stats["sample_count"] == 2
    assert "vector_available" in stats
    assert "chroma_available" in stats
    assert "intelligence_enabled" in stats
