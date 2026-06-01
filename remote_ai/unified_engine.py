"""Unified inference engine.

This layer keeps the existing retrieval / user-key / platform-key flow,
and optionally enriches the reference samples with the V2.02 intelligence
module before handing them to the current AI providers.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from local_search.data_types import SearchContext, SearchResult
from local_search.search_engine import LocalSearchEngine

from .platform_engine import PlatformEngine
from .user_key_engine import UserKeyAIEngine

try:
    from local_intelligence import IntelligenceManager
except ImportError:  # pragma: no cover - optional enhancement layer
    IntelligenceManager = None


class UnifiedInferenceEngine:
    """Unified inference engine for retrieval + AI generation."""

    def __init__(
        self,
        local_search_engine: LocalSearchEngine = None,
        intelligence_manager=None,
    ):
        self.local_engine = local_search_engine or LocalSearchEngine()
        self.user_key_engine = UserKeyAIEngine()
        self.platform_engine = PlatformEngine()
        self.intelligence_manager = intelligence_manager

        if self.intelligence_manager is None and IntelligenceManager is not None:
            try:
                self.intelligence_manager = IntelligenceManager()
            except Exception:
                self.intelligence_manager = None

    def search(self, context: SearchContext) -> List[SearchResult]:
        start_time = time.time()

        if context.inference_mode == "retrieval_only":
            return self._do_retrieval_only(context, start_time)
        if context.inference_mode == "user_api_key":
            return self._do_user_key_inference(context, start_time)
        if context.inference_mode == "platform_key":
            return self._do_platform_inference(context, start_time)

        raise ValueError(f"Unknown inference mode: {context.inference_mode}")

    def _do_retrieval_only(self, context: SearchContext, start_time: float) -> List[SearchResult]:
        del start_time
        return self.local_engine.search(context)

    def _do_user_key_inference(self, context: SearchContext, start_time: float) -> List[SearchResult]:
        retrieval_results = self.local_engine.search(context)

        if not retrieval_results:
            return self._generate_with_user_key(context, [], start_time)

        best_result = retrieval_results[0]
        if best_result.confidence >= 0.9:
            return retrieval_results

        context_samples = self._build_intelligent_context_samples(context.query, retrieval_results)
        ai_result = self._generate_with_user_key(context, context_samples, start_time)
        return [ai_result] + retrieval_results[: context.top_k - 1]

    def _do_platform_inference(self, context: SearchContext, start_time: float) -> List[SearchResult]:
        retrieval_results = self.local_engine.search(context)

        if not retrieval_results:
            return self._generate_with_platform(context, [], start_time)

        best_result = retrieval_results[0]
        if best_result.confidence >= 0.9:
            return retrieval_results

        context_samples = self._build_intelligent_context_samples(context.query, retrieval_results)
        ai_result = self._generate_with_platform(context, context_samples, start_time)
        return [ai_result] + retrieval_results[: context.top_k - 1]

    def _build_intelligent_context_samples(
        self,
        query: str,
        retrieval_results: List[SearchResult],
    ) -> List[str]:
        base_samples = [r.content for r in retrieval_results[:3] if r.content]
        if not base_samples or not self.intelligence_manager:
            return base_samples

        try:
            _, enriched_samples = self.intelligence_manager.analyze_and_enrich(query, base_samples)
        except Exception:
            return base_samples

        merged: List[str] = []
        seen = set()
        for sample in base_samples + enriched_samples:
            normalized = sample.strip()
            if not normalized or normalized in seen:
                continue
            merged.append(sample)
            seen.add(normalized)

        return merged[:5] if merged else base_samples

    def _generate_with_user_key(
        self,
        context: SearchContext,
        context_samples: List[str],
        start_time: float,
    ) -> SearchResult:
        if not context.user_api_key:
            return SearchResult(
                reply_id="ai_user_key_error",
                content="未配置用户 API Key",
                confidence=0.0,
                source_type="ai_user_key_error",
                source_detail="缺少 API Key 配置",
                total_latency_ms=int((time.time() - start_time) * 1000),
            )

        provider_name = context.api_provider or "deepseek"
        self.user_key_engine.configure_provider(provider_name, context.user_api_key)
        return self.user_key_engine.generate(context.query, provider_name, context_samples)

    def _generate_with_platform(
        self,
        context: SearchContext,
        context_samples: List[str],
        start_time: float,
    ) -> SearchResult:
        if not context.platform_token or not context.platform_user_id:
            return SearchResult(
                reply_id="ai_platform_error",
                content="未配置平台认证",
                confidence=0.0,
                source_type="ai_platform_error",
                source_detail="缺少平台认证",
                total_latency_ms=int((time.time() - start_time) * 1000),
            )

        self.platform_engine.authenticate(context.platform_token, context.platform_user_id)
        return self.platform_engine.generate(context.query, context_samples)

    def configure_user_key_provider(
        self,
        provider_name: str,
        api_key: str,
        api_base: str = None,
        model: str = None,
    ):
        self.user_key_engine.configure_provider(provider_name, api_key, api_base, model)

    def authenticate_platform(self, user_token: str, user_id: str) -> bool:
        return self.platform_engine.authenticate(user_token, user_id)

    def get_available_modes(self) -> List[str]:
        return ["retrieval_only", "user_api_key", "platform_key"]

    def get_mode_description(self, mode: str) -> str:
        descriptions = {
            "retrieval_only": "纯检索 - 仅使用本地样本匹配",
            "user_api_key": "自带Key - 检索+AI生成（用户自带API Key）",
            "platform_key": "平台Key - 检索+AI生成（平台统一付费）",
        }
        return descriptions.get(mode, "未知模式")

    def get_stats(self) -> Dict:
        return {
            "local_engine": self.local_engine.get_stats(),
            "user_key_providers": self.user_key_engine.get_config_summary(),
            "platform_available": self.platform_engine.is_available(),
            "intelligence_available": self.intelligence_manager is not None,
        }
