"""本地检索模块 - V2.03向量检索+智能增强"""

from .data_types import (
    SearchContext,
    SearchResult,
    WeightConfig,
    SOURCE_TYPE_LABELS,
    INFERENCE_MODE_LABELS
)

from .embedding_service import LocalEmbeddingService, get_embedding_service
from .chroma_repo import LocalChromaRepo, get_chroma_repo
from .search_engine import LocalSearchEngine
from .search_engine_v204 import LocalSearchEngineV204

__all__ = [
    'SearchContext',
    'SearchResult',
    'WeightConfig',
    'SOURCE_TYPE_LABELS',
    'INFERENCE_MODE_LABELS',
    'LocalEmbeddingService',
    'get_embedding_service',
    'LocalChromaRepo',
    'get_chroma_repo',
    'LocalSearchEngine',
    'LocalSearchEngineV204'
]
