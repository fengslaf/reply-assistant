"""
上下文加权器 - V2.04
根据历史对话上下文调整检索结果的权重
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re


@dataclass
class ContextMessage:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    entities: Dict[str, List] = field(default_factory=dict)


@dataclass
class ContextWindow:
    messages: List[ContextMessage]
    window_size: int
    time_range: timedelta


@dataclass
class WeightAdjustment:
    base_confidence: float
    context_boost: float
    final_confidence: float
    adjustment_reasons: List[str] = field(default_factory=list)


class ContextWeighter:
    INTENT_CONTINUITY_WEIGHTS: Dict[str, Dict[str, float]] = {
        'price': {
            'price': 1.5,
            'course': 1.2,
            'enroll': 1.3,
            'refund': 0.9,
        },
        'course': {
            'course': 1.5,
            'teacher': 1.2,
            'schedule': 1.2,
            'price': 1.1,
        },
        'teacher': {
            'teacher': 1.5,
            'course': 1.2,
            'schedule': 1.1,
        },
        'schedule': {
            'schedule': 1.5,
            'location': 1.2,
            'course': 1.1,
        },
        'location': {
            'location': 1.5,
            'schedule': 1.3,
            'contact': 1.1,
        },
        'enroll': {
            'enroll': 1.5,
            'contact': 1.3,
            'price': 1.2,
        },
        'contact': {
            'contact': 1.5,
            'location': 1.2,
        },
        'greeting': {
            'greeting': 1.0,
            'price': 0.8,
            'course': 0.8,
        },
    }

    ENTITY_RELEVANCE_BOOST: Dict[str, float] = {
        'money': 0.15,
        'course_name': 0.12,
        'teacher_name': 0.10,
        'location': 0.08,
        'phone': 0.05,
        'wechat': 0.05,
    }

    TIME_DECAY_FACTOR: float = 0.85

    RECENT_INTENT_BOOST: float = 0.2

    CONTEXT_KEYWORDS_BOOST: Dict[str, float] = {
        '你们': 0.05,
        '这个': 0.08,
        '刚才': 0.10,
        '之前': 0.08,
        '还是': 0.05,
        '那': 0.06,
    }

    def __init__(
        self,
        window_size: int = 5,
        time_decay_minutes: int = 30,
        custom_continuity_weights: Optional[Dict] = None
    ):
        self.window_size = window_size
        self.time_decay = timedelta(minutes=time_decay_minutes)
        self.intent_weights = self.INTENT_CONTINUITY_WEIGHTS.copy()
        
        if custom_continuity_weights:
            for intent, weights in custom_continuity_weights.items():
                if intent in self.intent_weights:
                    self.intent_weights[intent].update(weights)
                else:
                    self.intent_weights[intent] = weights

    def adjust_weight(
        self,
        base_confidence: float,
        current_intent: str,
        current_entities: Dict[str, List],
        context: ContextWindow
    ) -> WeightAdjustment:
        reasons = []
        total_boost = 0.0
        
        intent_boost = self._calc_intent_continuity_boost(current_intent, context)
        if intent_boost > 0:
            total_boost += intent_boost
            reasons.append(f'意图连续性增益: +{intent_boost:.2f}')
        
        entity_boost = self._calc_entity_relevance_boost(current_entities, context)
        if entity_boost > 0:
            total_boost += entity_boost
            reasons.append(f'实体相关性增益: +{entity_boost:.2f}')
        
        keyword_boost = self._calc_keyword_continuity_boost(current_entities, context)
        if keyword_boost > 0:
            total_boost += keyword_boost
            reasons.append(f'关键词连续性增益: +{keyword_boost:.2f}')
        
        time_decay = self._calc_time_decay(context)
        if time_decay < 1.0:
            total_boost *= time_decay
            reasons.append(f'时间衰减因子: {time_decay:.2f}')
        
        final_confidence = min(base_confidence + total_boost, 1.0)
        
        return WeightAdjustment(
            base_confidence=base_confidence,
            context_boost=total_boost,
            final_confidence=final_confidence,
            adjustment_reasons=reasons
        )

    def _calc_intent_continuity_boost(
        self,
        current_intent: str,
        context: ContextWindow
    ) -> float:
        if not context.messages:
            return 0.0
        
        recent_messages = context.messages[-self.window_size:]
        
        boost = 0.0
        
        for i, msg in enumerate(reversed(recent_messages)):
            if msg.intent:
                weight_map = self.intent_weights.get(msg.intent, {})
                intent_boost = weight_map.get(current_intent, 1.0)
                
                position_weight = 1.0 - (i * 0.15)
                boost += (intent_boost - 1.0) * position_weight
        
        return min(boost, self.RECENT_INTENT_BOOST)

    def _calc_entity_relevance_boost(
        self,
        current_entities: Dict[str, List],
        context: ContextWindow
    ) -> float:
        if not current_entities or not context.messages:
            return 0.0
        
        boost = 0.0
        
        context_entities = {}
        for msg in context.messages[-self.window_size:]:
            for entity_type, values in msg.entities.items():
                if entity_type not in context_entities:
                    context_entities[entity_type] = []
                context_entities[entity_type].extend(values)
        
        for entity_type, values in current_entities.items():
            if entity_type in context_entities:
                overlap = set(values) & set(context_entities[entity_type])
                if overlap:
                    base_boost = self.ENTITY_RELEVANCE_BOOST.get(entity_type, 0.05)
                    overlap_ratio = len(overlap) / len(values)
                    boost += base_boost * overlap_ratio
        
        return boost

    def _calc_keyword_continuity_boost(
        self,
        current_entities: Dict[str, List],
        context: ContextWindow
    ) -> float:
        boost = 0.0
        
        if not context.messages:
            return 0.0
        
        recent_content = ' '.join([m.content if hasattr(m, 'content') else m.get('content', '') for m in context.messages[-3:]])
        
        for keyword, weight in self.CONTEXT_KEYWORDS_BOOST.items():
            if keyword in recent_content:
                boost += weight
        
        return boost

    def _calc_time_decay(self, context: ContextWindow) -> float:
        if not context.messages:
            return 1.0
        
        now = datetime.now()
        last_message = context.messages[-1]
        
        time_diff = now - last_message.timestamp
        
        if time_diff > self.time_decay:
            decay_count = int(time_diff / self.time_decay)
            return self.TIME_DECAY_FACTOR ** decay_count
        
        return 1.0

    def build_context_window(
        self,
        messages: List[Dict],
        max_size: Optional[int] = None
    ) -> ContextWindow:
        window_size = max_size or self.window_size
        
        context_messages = []
        for msg in messages[-window_size:]:
            context_msg = ContextMessage(
                role=msg.get('role', 'user'),
                content=msg.get('content', ''),
                timestamp=msg.get('timestamp', datetime.now()),
                intent=msg.get('intent'),
                entities=msg.get('entities', {})
            )
            context_messages.append(context_msg)
        
        time_range = timedelta(minutes=0)
        if len(context_messages) >= 2:
            time_range = context_messages[-1].timestamp - context_messages[0].timestamp
        
        return ContextWindow(
            messages=context_messages,
            window_size=window_size,
            time_range=time_range
        )

    def adjust_batch_weights(
        self,
        results: List[Dict],
        context: ContextWindow,
        current_intent: str,
        current_entities: Dict[str, List]
    ) -> List[Dict]:
        adjusted_results = []
        
        for result in results:
            base_confidence = result.get('confidence', 0.5)
            
            adjustment = self.adjust_weight(
                base_confidence,
                current_intent,
                current_entities,
                context
            )
            
            adjusted_result = result.copy()
            adjusted_result['confidence'] = adjustment.final_confidence
            adjusted_result['context_adjustment'] = {
                'boost': adjustment.context_boost,
                'reasons': adjustment.adjustment_reasons
            }
            
            adjusted_results.append(adjusted_result)
        
        adjusted_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return adjusted_results

    def get_context_relevance_score(
        self,
        result_content: str,
        context: ContextWindow
    ) -> float:
        if not context.messages:
            return 0.0
        
        recent_keywords = []
        for msg in context.messages[-3:]:
            words = self._extract_keywords(msg.content)
            recent_keywords.extend(words)
        
        result_keywords = self._extract_keywords(result_content)
        
        if not recent_keywords or not result_keywords:
            return 0.0
        
        overlap = len(set(recent_keywords) & set(result_keywords))
        union = len(set(recent_keywords) | set(result_keywords))
        
        return overlap / union if union > 0 else 0.0

    def _extract_keywords(self, content: str) -> List[str]:
        content = re.sub(r'[^\w\s\u4e00-\u9fff]', '', content)
        words = content.split()
        
        keywords = [w for w in words if len(w) >= 2]
        
        return keywords

    def predict_next_intent(self, context: ContextWindow) -> Tuple[str, float]:
        if not context.messages:
            return ('unknown', 0.0)
        
        last_intent = context.messages[-1].intent
        
        if not last_intent:
            return ('unknown', 0.0)
        
        transition_probs = {
            'price': [('enroll', 0.4), ('contact', 0.3), ('price', 0.2)],
            'course': [('price', 0.35), ('teacher', 0.25), ('schedule', 0.2)],
            'teacher': [('course', 0.4), ('schedule', 0.3)],
            'schedule': [('location', 0.4), ('enroll', 0.3)],
            'location': [('contact', 0.4), ('schedule', 0.2)],
            'greeting': [('price', 0.3), ('course', 0.3), ('location', 0.2)],
        }
        
        predictions = transition_probs.get(last_intent, [('unknown', 0.5)])
        
        return predictions[0]

    def get_weight_stats(self, adjustment: WeightAdjustment) -> Dict:
        return {
            'base_confidence': adjustment.base_confidence,
            'context_boost': adjustment.context_boost,
            'final_confidence': adjustment.final_confidence,
            'boost_percentage': (adjustment.context_boost / adjustment.base_confidence * 100) if adjustment.base_confidence > 0 else 0,
            'reasons': adjustment.adjustment_reasons,
        }

    def update_window_size(self, new_size: int):
        self.window_size = new_size

    def add_intent_transition(
        self,
        from_intent: str,
        to_intent: str,
        weight: float
    ):
        if from_intent not in self.intent_weights:
            self.intent_weights[from_intent] = {}
        
        self.intent_weights[from_intent][to_intent] = weight