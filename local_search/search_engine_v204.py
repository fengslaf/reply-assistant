"""V2.04 local search engine with optional local generation enhancement."""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from .data_types import SearchContext, SearchResult, WeightConfig
from .search_engine import LocalSearchEngine

try:
    from local_intelligence import IntelligenceManagerV204
except ImportError:  # pragma: no cover
    IntelligenceManagerV204 = None


V204_SOURCE_MAP = {
    "template_generated": "local_template_generated",
    "fusion_generated": "local_fusion_generated",
    "entity_substitution": "local_entity_substitution",
    "rule_inference": "local_rule_inference",
}


class LocalSearchEngineV204(LocalSearchEngine):
    """Wraps the V2.03 engine and adds V2.04 local generation on top."""

    def __init__(
        self,
        data_path: str = None,
        embedding_service=None,
        chroma_repo=None,
        weight_config_path: str = None,
        enable_intelligence: bool = True,
        enable_generators: bool = True,
        generation_mode: str = "hybrid",
    ):
        super().__init__(
            data_path=data_path,
            embedding_service=embedding_service,
            chroma_repo=chroma_repo,
            weight_config_path=weight_config_path,
            enable_intelligence=enable_intelligence,
        )
        self.enable_generators = enable_generators
        self.generation_mode = generation_mode
        self.intelligence_manager_v204 = self._create_v204_manager(enable_generators)

    def _create_v204_manager(self, enable_generators: bool):
        if IntelligenceManagerV204 is None:
            return None
        try:
            return IntelligenceManagerV204(enable_all_generators=enable_generators)
        except Exception:
            return None

    def set_generation_mode(self, mode: str):
        if mode not in self.get_available_generation_modes():
            raise ValueError(f"invalid generation mode: {mode}")
        self.generation_mode = mode

    def get_available_generation_modes(self) -> List[str]:
        if self.intelligence_manager_v204 is None:
            return ["retrieval_only"]
        return self.intelligence_manager_v204.get_available_generation_modes()

    def get_generation_mode_description(self, mode: str) -> str:
        return {
            "retrieval_only": "仅返回检索结果",
            "template": "模板生成",
            "fusion": "多样本融合",
            "entity_substitution": "实体替换",
            "context_weighted": "上下文加权",
            "rule_inference": "规则推理",
            "hybrid": "自动选择最合适的本地生成方式",
        }.get(mode, "未知模式")

    def search(self, context: SearchContext) -> List[SearchResult]:
        retrieval_results = super().search(context)
        if not self.enable_generators or self.intelligence_manager_v204 is None:
            return retrieval_results
        if context.inference_mode != "retrieval_only":
            return retrieval_results

        generated_results = self._build_generated_results(
            query=context.query,
            retrieval_results=retrieval_results,
            context_messages=context.context_messages or [],
            top_k=context.top_k,
        )
        if not generated_results:
            return retrieval_results

        combined: List[SearchResult] = []
        seen_contents = set()
        for result in generated_results + retrieval_results:
            normalized = result.content.strip()
            if not normalized or normalized in seen_contents:
                continue
            combined.append(result)
            seen_contents.add(normalized)
            if len(combined) >= context.top_k:
                break
        return combined

    def _build_generated_results(
        self,
        query: str,
        retrieval_results: List[SearchResult],
        context_messages: List[Dict],
        top_k: int,
    ) -> List[SearchResult]:
        matched_samples = [
            {
                "content": result.content,
                "confidence": result.confidence,
                "source_type": result.source_type,
            }
            for result in retrieval_results[:3]
        ]
        if not matched_samples:
            return []

        generated_payload = self.intelligence_manager_v204.generate_reply(
            query=query,
            matched_samples=matched_samples,
            generation_mode=self.generation_mode,
            context_messages=self._normalize_context_messages(context_messages),
        )
        generated_replies = generated_payload.get("generated_replies", [])

        results: List[SearchResult] = []
        for item in generated_replies[:top_k]:
            source_type = V204_SOURCE_MAP.get(item.get("source_type"), "local_generated")
            results.append(
                SearchResult(
                    reply_id=f"local_v204_{uuid.uuid4().hex[:8]}",
                    content=item.get("content", "").strip(),
                    confidence=min(max(item.get("confidence", 0.0), 0.0), 1.0),
                    source_type=source_type,
                    source_detail=f"V2.04本地生成({item.get('generation_method', self.generation_mode)})",
                    matched_sample_id=retrieval_results[0].matched_sample_id if retrieval_results else None,
                    matched_parent_message=retrieval_results[0].matched_parent_message if retrieval_results else None,
                    reference_samples=[result.content for result in retrieval_results[:3]],
                )
            )
        return results

    @staticmethod
    def _normalize_context_messages(context_messages: Optional[List]) -> List[Dict]:
        normalized: List[Dict] = []
        for item in context_messages or []:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "role": item.get("role", "user"),
                        "content": str(item.get("content", "")),
                    }
                )
            else:
                normalized.append({"role": "user", "content": str(item)})
        return normalized

    def search_and_generate(
        self,
        query: str,
        context_messages: Optional[List[Dict]] = None,
        top_k: int = 5,
        mode: str = "hybrid",
        generation_mode: str = "hybrid",
    ) -> Dict:
        self.set_generation_mode(generation_mode)
        start_time = time.time()
        search_context = SearchContext(
            query=query,
            top_k=top_k,
            mode=mode,
            context_messages=context_messages or [],
        )
        results = self.search(search_context)
        return {
            "query": query,
            "intent": self.analyze_query(query).get("intent", "unknown"),
            "retrieval_results": [result.to_dict() for result in results],
            "generation_results": [result.to_dict() for result in results if result.source_type.startswith("local_")],
            "retrieval_latency_ms": int((time.time() - start_time) * 1000),
            "generation_mode": self.generation_mode,
        }

    def analyze_query(self, query: str) -> Dict:
        analysis = super().analyze_query(query)
        analysis["generation_mode"] = self.generation_mode
        analysis["generators_enabled"] = self.enable_generators and self.intelligence_manager_v204 is not None
        return analysis

    def update_weights(
        self,
        weight_config: WeightConfig,
    ):
        super().update_weights(weight_config)

    def get_stats(self) -> Dict:
        stats = super().get_stats()
        stats.update(
            {
                "version": "V2.04",
                "generators_enabled": self.enable_generators,
                "generation_mode": self.generation_mode,
            }
        )
        if self.intelligence_manager_v204 and hasattr(self.intelligence_manager_v204, "get_generator_stats"):
            stats["generator_stats"] = self.intelligence_manager_v204.get_generator_stats()
        return stats
