"""
智能增强管理器 V2.04 - 统一协调各模块
整合意图识别、实体抽取、质量评分、样本扩充、模板生成、多样本融合、实体替换、上下文加权、规则推理链
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .intent_classifier import IntentClassifier, IntentResult
from .entity_extractor import EntityExtractor, EntityResult
from .quality_scorer import QualityScorer, QualityScore
from .sample_expander import SampleExpander, ExpansionResult
from .prompt_builder import PromptBuilder
from .template_generator import TemplateGenerator, GeneratedReply
from .multi_sample_fusion import MultiSampleFusion, FusionResult, SampleInfo
from .entity_substitution import EntitySubstitutionGenerator, GeneratedResult
from .context_weighter import ContextWeighter, WeightAdjustment, ContextWindow
from .rule_inference_chain import RuleInferenceChain, InferenceResult


@dataclass
class IntelligenceResultV204:
    intent_result: IntentResult
    entity_result: EntityResult
    quality_scores: List[QualityScore] = field(default_factory=list)
    expansion_results: List[ExpansionResult] = field(default_factory=list)
    prompt: Dict[str, str] = field(default_factory=dict)
    enriched_samples: List[Dict] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    template_reply: Optional[GeneratedReply] = None
    fusion_result: Optional[FusionResult] = None
    entity_gen_result: Optional[GeneratedResult] = None
    context_adjustment: Optional[WeightAdjustment] = None
    inference_result: Optional[InferenceResult] = None
    
    generation_mode: str = 'retrieval_only'
    final_confidence: float = 0.0
    final_content: str = ''


class IntelligenceManagerV204:
    def __init__(
        self,
        custom_intent_rules: Optional[Dict] = None,
        custom_entity_patterns: Optional[Dict] = None,
        custom_entity_dict: Optional[Dict] = None,
        custom_synonyms: Optional[Dict] = None,
        custom_templates: Optional[Dict] = None,
        custom_prompts: Optional[Dict] = None,
        custom_rules: Optional[Dict] = None,
        enable_all_generators: bool = True,
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
        
        if enable_all_generators:
            self.template_generator = TemplateGenerator(custom_templates)
            self.multi_sample_fusion = MultiSampleFusion()
            self.entity_substitution = EntitySubstitutionGenerator()
            self.context_weighter = ContextWeighter()
            self.rule_inference_chain = RuleInferenceChain(custom_rules)
        else:
            self.template_generator = None
            self.multi_sample_fusion = None
            self.entity_substitution = None
            self.context_weighter = None
            self.rule_inference_chain = None

    def analyze(
        self,
        query: str,
        samples: Optional[List[str]] = None,
        context_messages: Optional[List[Dict]] = None,
        generation_mode: str = 'retrieval_only'
    ) -> IntelligenceResultV204:
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
            context=context_messages,
        )

        template_reply = None
        fusion_result = None
        entity_gen_result = None
        context_adjustment = None
        inference_result = None
        
        entity_dict = {}
        if entity_result.entities:
            entity_dict = {k: [e.value for e in v] for k, v in entity_result.entities.items()}
        
        if generation_mode == 'template' and self.template_generator:
            template_reply = self.template_generator.generate_with_entity_mapping(
                intent_result.intent,
                entity_dict,
                confidence_threshold=0.7
            )
        
        if generation_mode == 'fusion' and self.multi_sample_fusion and samples:
            sample_infos = [
                SampleInfo(
                    content=s,
                    confidence=qs.total_score,
                    source_type='local'
                )
                for s, qs in zip(samples[:3], quality_scores[:3])
            ]
            fusion_result = self.multi_sample_fusion.fuse_by_intent(
                sample_infos,
                intent_result.intent
            )
        
        if generation_mode == 'entity_substitution' and self.entity_substitution:
            if samples and samples[0]:
                entity_gen_result = self.entity_substitution.generate(
                    samples[0],
                    entity_dict,
                    substitution_strategy='direct_fill'
                )
        
        if generation_mode == 'context_weighted' and self.context_weighter and context_messages:
            context_window = self.context_weighter.build_context_window(context_messages)
            context_adjustment = self.context_weighter.adjust_weight(
                base_confidence=quality_scores[0].total_score if quality_scores else 0.5,
                current_intent=intent_result.intent,
                current_entities=entity_dict,
                context=context_window
            )
        
        if generation_mode == 'rule_inference' and self.rule_inference_chain:
            context_strs = [m.get('content', '') for m in context_messages] if context_messages else None
            inference_result = self.rule_inference_chain.infer(
                query,
                intent_result.intent,
                entity_dict,
                context_strs
            )

        summary = self._generate_summary(
            intent_result,
            entity_result,
            quality_scores,
            expansion_results,
            template_reply,
            fusion_result,
            inference_result,
        )
        
        final_content, final_confidence = self._determine_final_output(
            generation_mode,
            template_reply,
            fusion_result,
            entity_gen_result,
            inference_result,
            quality_scores
        )

        return IntelligenceResultV204(
            intent_result=intent_result,
            entity_result=entity_result,
            quality_scores=quality_scores,
            expansion_results=expansion_results,
            prompt=prompt,
            enriched_samples=enriched_samples,
            summary=summary,
            template_reply=template_reply,
            fusion_result=fusion_result,
            entity_gen_result=entity_gen_result,
            context_adjustment=context_adjustment,
            inference_result=inference_result,
            generation_mode=generation_mode,
            final_confidence=final_confidence,
            final_content=final_content,
        )

    def _generate_summary(
        self,
        intent_result: IntentResult,
        entity_result: EntityResult,
        quality_scores: List[QualityScore],
        expansion_results: List[ExpansionResult],
        template_reply: Optional[GeneratedReply],
        fusion_result: Optional[FusionResult],
        inference_result: Optional[InferenceResult],
    ) -> Dict[str, Any]:
        avg_quality = 0.0
        if quality_scores:
            avg_quality = sum(s.total_score for s in quality_scores) / len(quality_scores)

        total_variants = sum(len(r.variants) for r in expansion_results)

        high_quality_count = sum(1 for s in quality_scores if s.total_score >= 0.7)

        summary = {
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
        
        if template_reply:
            summary['template_generated'] = template_reply.confidence > 0.7
        
        if fusion_result:
            summary['fusion_key_points'] = len(fusion_result.key_points)
        
        if inference_result:
            summary['rules_matched'] = len(inference_result.matched_rules)

        return summary

    def _determine_final_output(
        self,
        generation_mode: str,
        template_reply: Optional[GeneratedReply],
        fusion_result: Optional[FusionResult],
        entity_gen_result: Optional[GeneratedResult],
        inference_result: Optional[InferenceResult],
        quality_scores: List[QualityScore]
    ) -> Tuple[str, float]:
        if generation_mode == 'template' and template_reply and template_reply.confidence > 0.7:
            return template_reply.content, template_reply.confidence
        
        if generation_mode == 'fusion' and fusion_result and fusion_result.confidence > 0.6:
            return fusion_result.content, fusion_result.confidence
        
        if generation_mode == 'entity_substitution' and entity_gen_result and entity_gen_result.confidence > 0.5:
            return entity_gen_result.content, entity_gen_result.confidence
        
        if generation_mode == 'rule_inference' and inference_result and inference_result.final_confidence > 0.7:
            return inference_result.content, inference_result.final_confidence
        
        if quality_scores and quality_scores[0].total_score > 0.6:
            return '', quality_scores[0].total_score
        
        return '', 0.0

    def _get_recommendation(self, intent_result: IntentResult, avg_quality: float, entity_result: EntityResult) -> str:
        if avg_quality < 0.5:
            return '建议扩充高质量样本，提高匹配效果'
        
        if intent_result.confidence < 0.5:
            return '意图识别置信度较低，建议优化意图规则或扩充意图关键词'
        
        if not entity_result.entities:
            return '未检测到实体，建议添加实体信息以提升回复准确性'
        
        return '分析完成，建议使用动态提示词调用AI生成回复'

    def generate_reply(
        self,
        query: str,
        matched_samples: List[Dict],
        generation_mode: str = 'hybrid',
        context_messages: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        intent_result = self.intent_classifier.classify(query)
        entity_result = self.entity_extractor.extract(query)
        
        entity_dict = {}
        if entity_result.entities:
            entity_dict = {k: [e.value for e in v] for k, v in entity_result.entities.items()}
        
        results = []
        
        if generation_mode in ['template', 'hybrid'] and self.template_generator:
            template_reply = self.template_generator.generate_with_entity_mapping(
                intent_result.intent,
                entity_dict,
                confidence_threshold=0.7
            )
            if template_reply.confidence > 0.7:
                results.append({
                    'content': template_reply.content,
                    'confidence': template_reply.confidence,
                    'source_type': 'template_generated',
                    'generation_method': 'template_filling'
                })
        
        if generation_mode in ['fusion', 'hybrid'] and self.multi_sample_fusion and matched_samples:
            sample_infos = [
                SampleInfo(
                    content=s.get('content', s.get('replies', [''])[0]),
                    confidence=s.get('confidence', 0.5),
                    source_type=s.get('source_type', 'local')
                )
                for s in matched_samples[:3]
            ]
            fusion_result = self.multi_sample_fusion.fuse_by_intent(
                sample_infos,
                intent_result.intent
            )
            if fusion_result.confidence > 0.6:
                results.append({
                    'content': fusion_result.content,
                    'confidence': fusion_result.confidence,
                    'source_type': 'fusion_generated',
                    'generation_method': 'key_point_fusion',
                    'key_points': fusion_result.key_points
                })
        
        if generation_mode in ['entity_substitution', 'hybrid'] and self.entity_substitution and matched_samples:
            if matched_samples[0]:
                entity_gen_result = self.entity_substitution.generate(
                    matched_samples[0].get('content', matched_samples[0].get('replies', [''])[0]),
                    entity_dict,
                    substitution_strategy='direct_fill'
                )
                if entity_gen_result.confidence > 0.5:
                    results.append({
                        'content': entity_gen_result.content,
                        'confidence': entity_gen_result.confidence,
                        'source_type': 'entity_substitution',
                        'generation_method': 'entity_substitution'
                    })
        
        if generation_mode in ['rule_inference', 'hybrid'] and self.rule_inference_chain:
            context_strs = [m.get('content', '') for m in context_messages] if context_messages else None
            inference_result = self.rule_inference_chain.infer(
                query,
                intent_result.intent,
                entity_dict,
                context_strs
            )
            if inference_result.final_confidence > 0.7:
                results.append({
                    'content': inference_result.content,
                    'confidence': inference_result.final_confidence,
                    'source_type': 'rule_inference',
                    'generation_method': 'rule_inference',
                    'matched_rules': inference_result.matched_rules
                })
        
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            'intent': intent_result.intent,
            'entities': entity_dict,
            'generated_replies': results[:3],
            'generation_mode': generation_mode,
        }

    def adjust_retrieval_weights(
        self,
        retrieval_results: List[Dict],
        context_messages: List[Dict],
        query: str
    ) -> List[Dict]:
        if not self.context_weighter or not context_messages:
            return retrieval_results
        
        intent_result = self.intent_classifier.classify(query)
        entity_result = self.entity_extractor.extract(query)
        
        entity_dict = {}
        if entity_result.entities:
            entity_dict = {k: [e.value for e in v] for k, v in entity_result.entities.items()}
        
        context_window = self.context_weighter.build_context_window(context_messages)
        
        adjusted_results = self.context_weighter.adjust_batch_weights(
            retrieval_results,
            context_window,
            intent_result.intent,
            entity_dict
        )
        
        return adjusted_results

    def analyze_query(self, query: str) -> Dict:
        return self.analyze(query).summary

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

    def get_available_generation_modes(self) -> List[str]:
        return [
            'retrieval_only',
            'template',
            'fusion',
            'entity_substitution',
            'context_weighted',
            'rule_inference',
            'hybrid'
        ]

    def get_generator_stats(self) -> Dict:
        stats = {
            'intent_rules': len(self.intent_classifier.rules),
            'entity_patterns': len(self.entity_extractor.patterns),
            'synonym_groups': len(self.sample_expander.synonyms),
            'template_types': 0,
            'fusion_patterns': 0,
            'entity_rules': 0,
            'context_rules': 0,
            'inference_rules': 0,
        }
        
        if self.template_generator:
            stats['template_types'] = len(self.template_generator.templates)
        
        if self.multi_sample_fusion:
            stats['fusion_patterns'] = len(self.multi_sample_fusion.key_point_patterns)
        
        if self.entity_substitution:
            stats['entity_rules'] = len(self.entity_substitution.substitution_rules)
        
        if self.context_weighter:
            stats['context_rules'] = len(self.context_weighter.intent_weights)
        
        if self.rule_inference_chain:
            stats['inference_rules'] = len(self.rule_inference_chain.rules)
        
        return stats