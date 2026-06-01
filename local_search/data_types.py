"""Shared data types for local retrieval and inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import uuid


LOCAL_SOURCE_TYPES = [
    "local_exact",
    "local_vector",
    "local_keyword",
    "local_generated",
    "local_template_generated",
    "local_fusion_generated",
    "local_entity_substitution",
    "local_rule_inference",
]

AI_SOURCE_TYPES = [
    "ai_user_key_deepseek",
    "ai_user_key_zhipu",
    "ai_user_key_wenxin",
    "ai_user_key_openai",
    "ai_platform",
]


@dataclass
class SearchContext:
    """Normalized search input shared by retrieval and inference layers."""

    query: str
    scene_hint: Optional[str] = None
    top_k: int = 5
    mode: str = "hybrid"
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "vector": 0.4,
            "keyword": 0.3,
            "scene": 0.15,
            "quality": 0.15,
        }
    )
    inference_mode: str = "retrieval_only"
    user_api_key: Optional[str] = None
    api_provider: Optional[str] = None
    platform_token: Optional[str] = None
    platform_user_id: Optional[str] = None
    entities: Dict[str, List] = field(default_factory=dict)
    intent: Optional[str] = None
    context_messages: Optional[List[Dict]] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.query:
            raise ValueError("query cannot be empty")
        if self.mode not in {"hybrid", "vector", "keyword", "exact"}:
            raise ValueError("invalid search mode")
        if self.inference_mode not in {"retrieval_only", "user_api_key", "platform_key"}:
            raise ValueError("invalid inference mode")

    def validate_weights(self) -> bool:
        total = sum(self.weights.values())
        return abs(total - 1.0) < 0.001

    def normalize_weights(self) -> Dict[str, float]:
        total = sum(self.weights.values())
        if total == 0:
            return dict(self.weights)
        return {key: value / total for key, value in self.weights.items()}


@dataclass
class SearchResult:
    """Normalized retrieval or generation result."""

    reply_id: str
    content: str
    confidence: float
    source_type: str
    source_detail: str
    matched_sample_id: Optional[str] = None
    matched_parent_message: Optional[str] = None
    generation_model: Optional[str] = None
    generation_latency_ms: Optional[int] = None
    reference_samples: List[str] = field(default_factory=list)
    retrieval_latency_ms: Optional[int] = None
    total_latency_ms: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.reply_id:
            self.reply_id = f"result_{uuid.uuid4().hex[:8]}"
        if not self.content:
            raise ValueError("content cannot be empty")
        if not (0 <= self.confidence <= 1):
            raise ValueError("confidence must be between 0 and 1")
        if self.source_type not in LOCAL_SOURCE_TYPES + AI_SOURCE_TYPES:
            raise ValueError(f"invalid source_type: {self.source_type}")

    def is_local(self) -> bool:
        return self.source_type.startswith("local_")

    def is_ai_generated(self) -> bool:
        return self.source_type.startswith("ai_")

    def is_user_key(self) -> bool:
        return self.source_type.startswith("ai_user_key_")

    def is_platform_key(self) -> bool:
        return self.source_type == "ai_platform"

    def get_provider_name(self) -> Optional[str]:
        if self.is_user_key():
            return {
                "ai_user_key_deepseek": "DeepSeek",
                "ai_user_key_zhipu": "智谱AI",
                "ai_user_key_wenxin": "文心一言",
                "ai_user_key_openai": "OpenAI",
            }.get(self.source_type)
        if self.is_platform_key():
            return "平台统一"
        return None

    def to_dict(self) -> Dict:
        return {
            "reply_id": self.reply_id,
            "content": self.content,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "source_detail": self.source_detail,
            "matched_sample_id": self.matched_sample_id,
            "matched_parent_message": self.matched_parent_message,
            "generation_model": self.generation_model,
            "generation_latency_ms": self.generation_latency_ms,
            "reference_samples": self.reference_samples,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "total_latency_ms": self.total_latency_ms,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SearchResult":
        created_at = data.get("created_at")
        return cls(
            reply_id=data.get("reply_id", ""),
            content=data["content"],
            confidence=data["confidence"],
            source_type=data["source_type"],
            source_detail=data.get("source_detail", ""),
            matched_sample_id=data.get("matched_sample_id"),
            matched_parent_message=data.get("matched_parent_message"),
            generation_model=data.get("generation_model"),
            generation_latency_ms=data.get("generation_latency_ms"),
            reference_samples=data.get("reference_samples", []),
            retrieval_latency_ms=data.get("retrieval_latency_ms"),
            total_latency_ms=data.get("total_latency_ms"),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
        )


@dataclass
class WeightConfig:
    """User-tunable weight configuration for hybrid retrieval."""

    vector: float = 0.4
    keyword: float = 0.3
    scene: float = 0.15
    quality: float = 0.15
    user_id: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.validate():
            raise ValueError("weight sum must equal 1")

    def validate(self) -> bool:
        total = self.vector + self.keyword + self.scene + self.quality
        return abs(total - 1.0) < 0.001

    def to_dict(self) -> Dict[str, float]:
        return {
            "vector": self.vector,
            "keyword": self.keyword,
            "scene": self.scene,
            "quality": self.quality,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "WeightConfig":
        return cls(
            vector=data.get("vector", 0.4),
            keyword=data.get("keyword", 0.3),
            scene=data.get("scene", 0.15),
            quality=data.get("quality", 0.15),
        )


SOURCE_TYPE_LABELS = {
    "local_exact": "精确匹配",
    "local_vector": "向量检索",
    "local_keyword": "关键词匹配",
    "local_generated": "智能生成",
    "local_template_generated": "模板生成",
    "local_fusion_generated": "融合生成",
    "local_entity_substitution": "实体替换",
    "local_rule_inference": "规则推理",
    "ai_user_key_deepseek": "DeepSeek生成",
    "ai_user_key_zhipu": "智谱AI生成",
    "ai_user_key_wenxin": "文心生成",
    "ai_user_key_openai": "OpenAI生成",
    "ai_platform": "平台生成",
}

INFERENCE_MODE_LABELS = {
    "retrieval_only": "纯检索",
    "user_api_key": "自带Key",
    "platform_key": "平台Key",
}

