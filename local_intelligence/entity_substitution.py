"""
实体替换生成器 - V2.04
从检索结果中抽取实体，替换生成定制化回复
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class EntityMapping:
    entity_type: str
    original_value: str
    new_value: str
    position: Tuple[int, int]


@dataclass
class SubstitutionRule:
    target_type: str
    substitution_map: Dict[str, str]
    default_fallback: Optional[str] = None


@dataclass
class GeneratedResult:
    content: str
    original_content: str
    substitutions: List[EntityMapping]
    entities_used: Dict[str, str]
    confidence: float
    generation_method: str = 'entity_substitution'


class EntitySubstitutionGenerator:
    ENTITY_SUBSTITUTION_RULES: Dict[str, SubstitutionRule] = {
        'price': SubstitutionRule(
            target_type='money',
            substitution_map={
                '5000': '3000',
                '500': '299',
                '200': '158',
            },
            default_fallback=None
        ),
        'course_name': SubstitutionRule(
            target_type='course_name',
            substitution_map={
                'Python课程': 'Python进阶课程',
                'Java课程': 'Java高级班',
                '基础课程': '精品基础课程',
            },
            default_fallback=None
        ),
        'duration': SubstitutionRule(
            target_type='duration',
            substitution_map={
                '3个月': '2个月',
                '12周': '8周',
                '30课时': '24课时',
            },
            default_fallback=None
        ),
    }

    ENTITY_PATTERNS: Dict[str, List[str]] = {
        'money': [
            r'\d+元',
            r'\d+块',
            r'\d+万',
        ],
        'course_name': [
            r'Python课程',
            r'Java课程',
            r'前端课程',
            r'UI设计课程',
            r'数据分析课程',
            r'基础课程',
            r'进阶课程',
        ],
        'duration': [
            r'\d+个月',
            r'\d+周',
            r'\d+课时',
            r'\d+节课',
        ],
        'teacher': [
            r'张老师',
            r'李老师',
            r'王老师',
        ],
        'location': [
            r'北京校区',
            r'上海校区',
            r'广州校区',
            r'深圳校区',
        ],
    }

    SLOT_FILLERS: Dict[str, str] = {
        '价格': '{price_value}',
        '课程': '{course_name}',
        '时长': '{duration_value}',
        '老师': '{teacher_name}',
        '校区': '{location_name}',
    }

    def __init__(
        self,
        custom_rules: Optional[Dict] = None,
        custom_patterns: Optional[Dict] = None
    ):
        self.substitution_rules = self.ENTITY_SUBSTITUTION_RULES.copy()
        self.entity_patterns = self.ENTITY_PATTERNS.copy()
        
        if custom_rules:
            for rule_name, rule in custom_rules.items():
                self.substitution_rules[rule_name] = rule
        
        if custom_patterns:
            for entity_type, patterns in custom_patterns.items():
                if entity_type in self.entity_patterns:
                    self.entity_patterns[entity_type].extend(patterns)
                else:
                    self.entity_patterns[entity_type] = patterns

    def generate(
        self,
        template_content: str,
        entities: Dict[str, Any],
        substitution_strategy: str = 'direct_fill'
    ) -> GeneratedResult:
        substitutions = []
        entities_used = {}
        content = template_content
        
        for entity_type, values in entities.items():
            if not values:
                continue
            
            value = str(values[0])
            
            if entity_type in self.entity_patterns:
                pattern_list = self.entity_patterns[entity_type]
                
                for pattern in pattern_list:
                    matches = list(re.finditer(pattern, content))
                    
                    for match in matches:
                        original = match.group()
                        new_value = self._get_substitution_value(
                            entity_type,
                            original,
                            value,
                            substitution_strategy
                        )
                        
                        if new_value:
                            start, end = match.start(), match.end()
                            content = content[:start] + new_value + content[end:]
                            
                            mapping = EntityMapping(
                                entity_type=entity_type,
                                original_value=original,
                                new_value=new_value,
                                position=(start, end)
                            )
                            substitutions.append(mapping)
                            entities_used[entity_type] = new_value
        
        slot_fillers = self._build_slot_fillers(entities)
        content = self._fill_slots(content, slot_fillers)
        
        confidence = self._calc_confidence(substitutions, entities)
        
        return GeneratedResult(
            content=content,
            original_content=template_content,
            substitutions=substitutions,
            entities_used=entities_used,
            confidence=confidence,
            generation_method='entity_substitution'
        )

    def _get_substitution_value(
        self,
        entity_type: str,
        original: str,
        provided_value: str,
        strategy: str
    ) -> str:
        if strategy == 'direct_fill':
            return provided_value
        elif strategy == 'rule_based':
            rule = self.substitution_rules.get(entity_type)
            if rule:
                return rule.substitution_map.get(original, rule.default_fallback or original)
        
        return provided_value

    def _build_slot_fillers(self, entities: Dict[str, Any]) -> Dict[str, str]:
        fillers = {}
        
        entity_slot_map = {
            'money': '价格',
            'course_name': '课程',
            'duration': '时长',
            'teacher': '老师',
            'location': '校区',
        }
        
        for entity_type, values in entities.items():
            if entity_type in entity_slot_map and values:
                slot_name = entity_slot_map[entity_type]
                slot_placeholder = self.SLOT_FILLERS.get(slot_name, '')
                if slot_placeholder:
                    fillers[slot_placeholder] = str(values[0])
        
        return fillers

    def _fill_slots(self, content: str, fillers: Dict[str, str]) -> str:
        for placeholder, value in fillers.items():
            content = content.replace(placeholder, value)
        
        return content

    def _calc_confidence(
        self,
        substitutions: List[EntityMapping],
        entities: Dict[str, Any]
    ) -> float:
        base_confidence = 0.7
        
        substitution_bonus = len(substitutions) * 0.05
        substitution_bonus = min(substitution_bonus, 0.15)
        
        entity_coverage = len(entities) / 5.0
        entity_coverage = min(entity_coverage, 0.15)
        
        return base_confidence + substitution_bonus + entity_coverage

    def generate_with_extraction(
        self,
        template_content: str,
        user_query: str,
        substitution_strategy: str = 'direct_fill'
    ) -> GeneratedResult:
        entities = self._extract_entities_from_query(user_query)
        
        return self.generate(template_content, entities, substitution_strategy)

    def _extract_entities_from_query(self, query: str) -> Dict[str, List]:
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            values = []
            for pattern in patterns:
                matches = re.findall(pattern, query)
                values.extend(matches)
            
            if values:
                entities[entity_type] = list(set(values))
        
        return entities

    def apply_template_with_entities(
        self,
        template: str,
        entities: Dict[str, Any],
        preserve_unmatched: bool = True
    ) -> GeneratedResult:
        content = template
        
        for entity_type, values in entities.items():
            if not values:
                continue
            
            value = str(values[0])
            placeholder_map = {
                'money': '{价格}',
                'course_name': '{课程}',
                'duration': '{时长}',
                'teacher': '{老师}',
                'location': '{校区}',
            }
            
            if entity_type in placeholder_map:
                placeholder = placeholder_map[entity_type]
                content = content.replace(placeholder, value)
        
        if not preserve_unmatched:
            content = re.sub(r'\{[^}]+\}', '', content)
        
        return GeneratedResult(
            content=content,
            original_content=template,
            substitutions=[],
            entities_used=entities,
            confidence=0.8,
            generation_method='template_entity_fill'
        )

    def customize_entity_value(
        self,
        entity_type: str,
        original: str,
        new_value: str
    ):
        if entity_type not in self.substitution_rules:
            self.substitution_rules[entity_type] = SubstitutionRule(
                target_type=entity_type,
                substitution_map={}
            )
        
        self.substitution_rules[entity_type].substitution_map[original] = new_value

    def add_entity_pattern(self, entity_type: str, pattern: str):
        if entity_type not in self.entity_patterns:
            self.entity_patterns[entity_type] = []
        
        self.entity_patterns[entity_type].append(pattern)

    def get_entity_types(self) -> List[str]:
        return list(self.entity_patterns.keys())

    def get_substitution_rules_info(self) -> Dict:
        return {
            rule_name: {
                'target_type': rule.target_type,
                'map_count': len(rule.substitution_map),
                'has_default': rule.default_fallback is not None,
            }
            for rule_name, rule in self.substitution_rules.items()
        }

    def generate_batch(
        self,
        template_content: str,
        entity_combinations: List[Dict[str, Any]]
    ) -> List[GeneratedResult]:
        return [
            self.generate(template_content, entities)
            for entities in entity_combinations
        ]

    def preview_substitution(
        self,
        content: str,
        entity_type: str,
        new_value: str
    ) -> str:
        patterns = self.entity_patterns.get(entity_type, [])
        
        preview = content
        for pattern in patterns:
            preview = re.sub(pattern, new_value, preview)
        
        return preview