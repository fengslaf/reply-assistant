"""Preview mode adapter.

This adapter keeps the V1 UI contract intact while wiring in:
- V2.00 local search / remote AI
- V2.01 context and clustering helpers
- V2.02 intelligence enhancement helpers
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from local_cluster import LocalClusterManager
from local_context import LocalContextManager, WindowStrategy
from local_search.data_types import SearchContext, SearchResult, SOURCE_TYPE_LABELS, WeightConfig
from local_search.search_engine import LocalSearchEngine
from local_search.search_engine_v204 import LocalSearchEngineV204
from remote_ai.unified_engine import UnifiedInferenceEngine

try:
    from local_intelligence import IntelligenceManager
except ImportError:  # pragma: no cover - optional enhancement layer
    IntelligenceManager = None


class PreviewModeAdapter:
    """V1-compatible adapter that exposes the newer backend modules."""

    def __init__(self, preview_manager):
        self.preview_manager = preview_manager

        self.intelligence_manager = self._create_intelligence_manager()
        self.local_engine = self._build_local_engine()
        self.unified_engine = self._build_unified_engine()
        self.context_manager = self._create_context_manager()
        self.cluster_manager = LocalClusterManager()

        self.inference_mode = "retrieval_only"
        self.current_provider = "deepseek"
        self._last_synced_signature = self.preview_manager.get_data_signature()
        self._last_v204_enabled = self._use_v204_generation()

    def _get_context_storage_path(self) -> str:
        return str(Path(self.preview_manager.data_dir) / "local_context.json")

    def _create_context_manager(self) -> LocalContextManager:
        return LocalContextManager(storage_path=self._get_context_storage_path())

    def _create_intelligence_manager(self):
        if IntelligenceManager is None:
            return None
        try:
            return IntelligenceManager()
        except Exception:
            return None

    def _use_v204_generation(self) -> bool:
        return bool(
            getattr(self.preview_manager, "get_v204_generation_enabled", lambda: False)()
        )

    def _build_local_engine(self):
        engine_cls = LocalSearchEngineV204 if self._use_v204_generation() else LocalSearchEngine
        kwargs = {"data_path": str(self.preview_manager.data_path)}
        if engine_cls is LocalSearchEngineV204:
            kwargs.update(
                {
                    "enable_generators": True,
                    "generation_mode": "hybrid",
                }
            )
        return engine_cls(**kwargs)

    def _build_unified_engine(self):
        return UnifiedInferenceEngine(
            self.local_engine,
            intelligence_manager=self.intelligence_manager,
        )

    def _rebuild_runtime(self):
        self.local_engine = self._build_local_engine()
        self.unified_engine = self._build_unified_engine()
        self._last_v204_enabled = self._use_v204_generation()

    def _sync_context_manager(self):
        desired_path = self._get_context_storage_path()
        current_store = getattr(self.context_manager, "store", None)
        current_path = getattr(current_store, "storage_path", None)

        if current_path != desired_path:
            self.context_manager = self._create_context_manager()

    def refresh(self):
        """Refresh local engines from the current preview data."""
        current_signature = self.preview_manager.get_data_signature()
        v204_enabled = self._use_v204_generation()
        if self._last_synced_signature == current_signature and self._last_v204_enabled == v204_enabled:
            self._sync_context_manager()
            return

        if self._last_v204_enabled != v204_enabled:
            self._rebuild_runtime()

        self.local_engine.data_path = self.preview_manager.data_path
        self.local_engine.reload_samples()
        self._sync_context_manager()
        self._last_synced_signature = current_signature

    def start_context_session(self, session_id: str = None) -> str:
        self._sync_context_manager()
        return self.context_manager.start_session(session_id)

    def add_context_user_message(self, content: str, metadata: Optional[Dict] = None):
        self._sync_context_manager()
        return self.context_manager.add_user_message(content, metadata=metadata)

    def add_context_assistant_reply(self, content: str, metadata: Optional[Dict] = None):
        self._sync_context_manager()
        return self.context_manager.add_assistant_reply(content, metadata=metadata)

    def add_context_system_message(self, content: str):
        self._sync_context_manager()
        return self.context_manager.add_system_message(content)

    def build_prompt_context(
        self,
        max_turns: Optional[int] = None,
        format_template: Optional[str] = None,
    ) -> str:
        self._sync_context_manager()
        return self.context_manager.build_prompt_context(
            max_turns=max_turns,
            format_template=format_template,
        )

    def get_context_summary(self) -> Dict:
        self._sync_context_manager()
        return self.context_manager.get_session_summary()

    def search_context_by_keywords(self, keywords: List[str]) -> List:
        self._sync_context_manager()
        return self.context_manager.search_by_keywords(keywords)

    def search_context_by_time(self, start_time=None, end_time=None) -> List:
        self._sync_context_manager()
        return self.context_manager.search_by_time(start_time=start_time, end_time=end_time)

    def get_conversation_pairs(self, limit: Optional[int] = None) -> List[Dict]:
        self._sync_context_manager()
        return self.context_manager.get_conversation_pairs(limit=limit)

    def set_context_window_strategy(
        self,
        strategy: WindowStrategy,
        max_turns: Optional[int] = None,
        max_time_minutes: Optional[int] = None,
    ):
        self._sync_context_manager()
        self.context_manager.switch_strategy(
            strategy,
            max_turns=max_turns,
            max_time_minutes=max_time_minutes,
        )

    def _get_sample_texts(self, text_field: str = "parent_message") -> List[str]:
        texts: List[str] = []
        for sample in self.preview_manager.get_all_samples():
            if text_field == "reply":
                texts.extend([reply for reply in sample.get("replies", []) if reply])
            else:
                parent_message = sample.get("parent_message", "")
                if parent_message:
                    texts.append(parent_message)
        return texts

    def cluster_saved_samples(self, method: str = "greedy", text_field: str = "parent_message"):
        texts = self._get_sample_texts(text_field=text_field)
        if not texts:
            return None
        return self.cluster_manager.cluster_samples(texts, method=method)

    def get_cluster_summary(
        self,
        method: str = "greedy",
        text_field: str = "parent_message",
    ) -> Optional[str]:
        report = self.cluster_saved_samples(method=method, text_field=text_field)
        if not report:
            return None
        return self.cluster_manager.get_cluster_summary(report)

    def find_similar_saved_samples(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
        text_field: str = "parent_message",
    ) -> List[Dict]:
        texts = self._get_sample_texts(text_field=text_field)
        if not texts:
            return []
        return self.cluster_manager.find_similar_samples(
            query,
            texts,
            top_k=top_k,
            threshold=threshold,
        )

    def suggest_saved_sample_categories(
        self,
        max_categories: int = 10,
        text_field: str = "parent_message",
    ) -> List[Dict]:
        texts = self._get_sample_texts(text_field=text_field)
        if not texts:
            return []
        return self.cluster_manager.suggest_categories(
            texts,
            max_categories=max_categories,
        )

    def analyze_intelligence(self, query: str, samples: Optional[List[str]] = None) -> Dict:
        if not self.intelligence_manager:
            return {
                "available": False,
                "prompt": {},
                "enriched_samples": [],
                "summary": {
                    "intent": "unknown",
                    "sample_count": len(samples or []),
                },
            }

        result = self.intelligence_manager.analyze(query, samples=samples)
        payload = asdict(result)
        payload["available"] = True
        return payload

    def build_intelligent_prompt(
        self,
        query: str,
        context_messages: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        if not self.intelligence_manager:
            return {}
        return self.intelligence_manager.build_context_enriched_prompt(
            query,
            context_messages=context_messages,
        )

    def get_best_intelligent_sample(self, query: str, samples: List[str]) -> Dict:
        if not self.intelligence_manager or not samples:
            return {}

        best_sample, best_score, intent_result = self.intelligence_manager.get_best_sample(query, samples)
        return {
            "sample": best_sample,
            "score": asdict(best_score),
            "intent": asdict(intent_result),
        }

    def expand_samples_for_intent(
        self,
        intent: str,
        base_samples: List[str],
        max_total: int = 20,
    ) -> List[str]:
        if not self.intelligence_manager:
            return base_samples
        return self.intelligence_manager.expand_samples_for_intent(
            intent,
            base_samples,
            max_total=max_total,
        )

    def get_intent_statistics(self, texts: List[str]) -> Dict[str, int]:
        if not self.intelligence_manager:
            return {}
        return self.intelligence_manager.get_intent_statistics(texts)

    def get_entity_statistics(self, texts: List[str]) -> Dict[str, int]:
        if not self.intelligence_manager:
            return {}
        return self.intelligence_manager.get_entity_statistics(texts)

    def match_v2(
        self,
        query: str,
        top_k: int = 3,
        inference_mode: str = None,
        scene_hint: str = None,
        stage_hint: str = None,
    ) -> Dict:
        inference_mode = inference_mode or self.inference_mode
        self.refresh()

        context = SearchContext(
            query=query,
            scene_hint=scene_hint,
            top_k=top_k,
            mode="hybrid",
            inference_mode=inference_mode,
            user_api_key=self.preview_manager.data.get("config", {}).get("api_key"),
            api_provider=self.current_provider,
        )

        results = self.unified_engine.search(context)
        intelligence = self.analyze_intelligence(
            query,
            samples=[r.content for r in results[:3]] if results else None,
        )
        return self._convert_to_v1_format(results, query, intelligence=intelligence)

    def _convert_to_v1_format(
        self,
        results: List[SearchResult],
        query: str,
        intelligence: Optional[Dict] = None,
    ) -> Dict:
        if not results:
            return {
                "match_type": "none",
                "candidates": [],
                "total": 0,
                "query": query,
                "intelligence": intelligence or {},
            }

        candidates = []
        for result in results:
            display_source = self._format_display_source(result)
            candidates.append(
                {
                    "reply_id": result.reply_id,
                    "content": result.content,
                    "confidence": result.confidence,
                    "source": display_source,
                    "source_detail": result.source_detail,
                    "source_type": result.source_type,
                    "style_tag": self._guess_style(result.source_type),
                    "matched_parent": result.matched_parent_message,
                    "matched_sample_id": result.matched_sample_id,
                }
            )

        if any(r.is_ai_generated() for r in results):
            match_type = "ai"
        elif any(r.source_type == "local_exact" for r in results):
            match_type = "exact"
        else:
            match_type = "similar"

        return {
            "match_type": match_type,
            "candidates": candidates,
            "total": len(candidates),
            "query": query,
            "intelligence": intelligence or {},
        }

    def _format_display_source(self, result: SearchResult) -> str:
        source_label = SOURCE_TYPE_LABELS.get(result.source_type, result.source_detail or "匹配")

        if result.matched_parent_message:
            preview = result.matched_parent_message[:15]
            if len(result.matched_parent_message) > 15:
                preview += "..."
            return f'"{preview}" —— {source_label}'

        return result.source_detail or source_label

    def _guess_style(self, source_type: str) -> str:
        if source_type.startswith("local_"):
            return "模板回复"
        if source_type.startswith("ai_user_key_"):
            return "AI生成"
        if source_type == "ai_platform":
            return "平台生成"
        return "未知来源"

    def set_inference_mode(self, mode: str):
        self.inference_mode = mode

    def set_provider(self, provider_name: str):
        self.current_provider = provider_name

    def configure_user_key(
        self,
        provider_name: str,
        api_key: str,
        api_base: str = None,
        model: str = None,
    ):
        self.unified_engine.configure_user_key_provider(provider_name, api_key, api_base, model)
        self.preview_manager.set_api_key(api_key, api_base)

    def update_weights(
        self,
        vector: float = 0.4,
        keyword: float = 0.3,
        scene: float = 0.15,
        quality: float = 0.15,
    ):
        weight_config = WeightConfig(
            vector=vector,
            keyword=keyword,
            scene=scene,
            quality=quality,
        )
        self.local_engine.update_weights(weight_config)

    def get_available_modes(self) -> List[str]:
        return self.unified_engine.get_available_modes()

    def get_available_providers(self) -> List[str]:
        return ["deepseek", "zhipu", "wenxin", "openai"]

    def get_stats(self) -> Dict:
        stats = self.unified_engine.get_stats()
        stats.update(
            {
                "context_available": True,
                "cluster_available": True,
                "intelligence_available": self.intelligence_manager is not None,
            }
        )
        return stats
