"""
智能增强管理器 - 统一协调各模块
整合意图识别、实体抽取、质量评分、样本扩充、动态提示词
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .intent_classifier import IntentClassifier, IntentResult
from .entity_extractor import EntityExtractor, EntityResult
from .quality_scorer import QualityScorer, QualityScore
from .sample_expander import SampleExpander, ExpansionResult
from .prompt_builder import PromptBuilder


@dataclass
class IntelligenceResult:
    intent_result: IntentResult
    entity_result: EntityResult
    quality_scores: List[QualityScore] = field(default_factory=list)
    expansion_results: List[ExpansionResult] = field(default_factory=list)
    prompt: Dict[str, str] = field(default_factory=dict)
    enriched_samples: List[Dict] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class IntelligenceManager:
    def __init__(
        self,
        custom_intent_rules: Optional[Dict] = None,
        custom_entity_patterns: Optional[Dict] = None,
        custom_entity_dict: Optional[Dict] = None,
        custom_synonyms: Optional[Dict] = None,
        custom_templates: Optional[Dict] = None,
        custom_prompts: Optional[Dict] = None,
    ):
        self.intent_classifier = IntentClassifier(custom_rules=custom_intent_rules)
        self.entity_extractor = EntityExtractor(
            custom_patterns=custom_entity_patterns,
            custom_dict=custom_entity_dict,
        )
        self.quality_scorer = QualityScorer()
        self.sample_expander = SampleExpander(
            custom_synonyms=custom_synonyms,
            custom_templates=custom_templates,
        )
        self.prompt_builder = PromptBuilder(custom_prompts=custom_prompts)

    def analyze(self, query: str, samples: Optional[List[str]] = None) -> IntelligenceResult:
        intent_result = self.intent_classifier.classify(query)
        entity_result = self.entity_extractor.extract(query)
        
        quality_scores = []
        expansion_results = []
        enriched_samples = []
        
        if samples:
            for sample in samples:
                quality_score = self.quality_scorer.score(sample, query, intent_result.intent)
                quality_scores.append(quality_score)
                
                if quality_score.total_score >= 0.5:
                    expansion = self.sample_expander.expand(sample, max_variants=3)
                    expansion_results.append(expansion)
                    
                    enriched_sample = {
                        'original': sample,
                        'quality_score': quality_score.total_score,
                        'grade': quality_score.grade,
                        'variants': expansion.variants[:2] if expansion.variants else [],
                        'intent_match': intent_result.intent,
                        'entities': entity_result.get_all_values('money') if intent_result.intent == 'price' else [],
                    }
                    enriched_samples.append(enriched_sample)

        prompt = self.prompt_builder.build(
            intent=intent_result.intent,
            query=query,
            entities=entity_result.entities,
            context=None,
        )

        summary = self._generate_summary(
            intent_result,
            entity_result,
            quality_scores,
            expansion_results,
        )

        return IntelligenceResult(
            intent_result=intent_result,
            entity_result=entity_result,
            quality_scores=quality_scores,
            expansion_results=expansion_results,
            prompt=prompt,
            enriched_samples=enriched_samples,
            summary=summary,
        )

    def _generate_summary(
        self,
        intent_result: IntentResult,
        entity_result: EntityResult,
        quality_scores: List[QualityScore],
        expansion_results: List[ExpansionResult],
    ) -> Dict[str, Any]:
        avg_quality = 0.0
        if quality_scores:
            avg_quality = sum(s.total_score for s in quality_scores) / len(quality_scores)

        total_variants = sum(len(r.variants) for r in expansion_results)

        high_quality_count = sum(1 for s in quality_scores if s.total_score >= 0.7)

        return {
            'intent': intent_result.intent,
            'intent_confidence': intent_result.confidence,
            'sub_intent': intent_result.sub_intent,
            'matched_keywords': intent_result.matched_keywords,
            'entity_count': sum(len(e) for e in entity_result.entities.values()),
            'entity_types': list(entity_result.entities.keys()),
            'sample_count': len(quality_scores),
            'avg_quality_score': avg_quality,
            'high_quality_count': high_quality_count,
            'total_expanded_variants': total_variants,
            'recommendation': self._get_recommendation(intent_result, avg_quality, entity_result),
        }

    def _get_recommendation(self, intent_result: IntentResult, avg_quality: float, entity_result: EntityResult) -> str:
        if avg_quality < 0.5:
            return '建议扩充高质量样本，提高匹配效果'
        
        if intent_result.confidence < 0.5:
            return '意图识别置信度较低，建议优化意图规则或扩充意图关键词'
        
        if not entity_result.entities:
            return '未检测到实体，建议添加实体信息以提升回复准确性'
        
        return '分析完成，建议使用动态提示词调用AI生成回复'

    def analyze_and_enrich(self, query: str, samples: List[str]) -> Tuple[IntelligenceResult, List[str]]:
        result = self.analyze(query, samples)
        
        enriched = []
        for sample_data in result.enriched_samples:
            enriched.append(sample_data['original'])
            if sample_data['variants']:
                enriched.extend(sample_data['variants'])

        enriched = list(set(enriched))
        
        return result, enriched

    def get_best_sample(self, query: str, samples: List[str]) -> Tuple[str, QualityScore, IntentResult]:
        intent_result = self.intent_classifier.classify(query)
        
        scored_samples = []
        for sample in samples:
            score = self.quality_scorer.score(sample, query, intent_result.intent)
            scored_samples.append((sample, score))
        
        best_sample, best_score = max(scored_samples, key=lambda x: x[1].total_score)
        
        return best_sample, best_score, intent_result

    def build_context_enriched_prompt(self, query: str, context_messages: Optional[List[str]] = None) -> Dict[str, str]:
        intent_result = self.intent_classifier.classify(query)
        entity_result = self.entity_extractor.extract(query)
        
        entity_dict = {}
        for entity_type, entities in entity_result.entities.items():
            entity_dict[entity_type] = [e.value for e in entities]
        
        return self.prompt_builder.build(
            intent=intent_result.intent,
            query=query,
            entities=entity_dict,
            context=context_messages,
        )

    def filter_samples_by_intent(self, samples: List[str], target_intent: str) -> List[str]:
        filtered = []
        for sample in samples:
            sample_intent = self.intent_classifier.classify(sample)
            if sample_intent.intent == target_intent:
                filtered.append(sample)
        return filtered

    def expand_samples_for_intent(self, intent: str, base_samples: List[str], max_total: int = 20) -> List[str]:
        return self.sample_expander.expand_intent_samples(intent, base_samples, max_total)

    def get_intent_statistics(self, texts: List[str]) -> Dict[str, int]:
        stats = {}
        for text in texts:
            intent_result = self.intent_classifier.classify(text)
            intent = intent_result.intent
            stats[intent] = stats.get(intent, 0) + 1
        return stats

    def get_entity_statistics(self, texts: List[str]) -> Dict[str, int]:
        stats = {}
        for text in texts:
            entity_result = self.entity_extractor.extract(text)
            for entity_type in entity_result.entities.keys():
                stats[entity_type] = stats.get(entity_type, 0) + 1
        return stats

    def quick_intent(self, text: str) -> str:
        return self.intent_classifier.classify(text).intent

    def quick_entities(self, text: str) -> Dict[str, List[Any]]:
        result = self.entity_extractor.extract(text)
        return {k: [e.value for e in v] for k, v in result.entities.items()}

    def quick_quality(self, reply: str) -> float:
        return self.quality_scorer.score(reply).total_score

    def quick_prompt(self, query: str) -> str:
        intent = self.quick_intent(query)
        return self.prompt_builder.get_quick_prompt(intent)