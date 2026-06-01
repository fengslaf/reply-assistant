"""
多样本融合器 - V2.04
从多个检索结果中提取信息，融合生成综合回复
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import re
from collections import Counter


@dataclass
class SampleInfo:
    content: str
    confidence: float
    source_type: str
    matched_parent: Optional[str] = None
    entities: Dict[str, List] = field(default_factory=dict)


@dataclass
class FusionResult:
    content: str
    sources: List[str]
    fusion_type: str
    confidence: float
    key_points: List[str]
    conflicts: List[Tuple[str, str]] = field(default_factory=list)


class MultiSampleFusion:
    KEY_POINT_PATTERNS: Dict[str, List[str]] = {
        'price': [
            r'(\d+)元',
            r'(\d+)块',
            r'费用为(\d+)',
            r'价格是(\d+)',
            r'收费(\d+)元',
        ],
        'duration': [
            r'(\d+)课时',
            r'(\d+)节课',
            r'(\d+)周',
            r'(\d+)个月',
            r'(\d+)天',
        ],
        'time': [
            r'(\d+)点',
            r'(\d+):\d+',
            r'早上|上午|下午|晚上',
            r'周一至周五',
            r'周末',
        ],
        'location': [
            r'地址[：:]\s*(.+)',
            r'位于(.+)',
            r'校区[：:]\s*(.+)',
        ],
        'contact': [
            r'电话[：:]\s*(\d+[\d-]*)',
            r'联系[：:]\s*(\d+)',
            r'微信[：:]\s*([a-zA-Z0-9_-]+)',
        ],
    }

    FUSION_PRIORITY: Dict[str, int] = {
        'price': 10,
        'duration': 8,
        'contact': 7,
        'location': 6,
        'time': 5,
        'content': 4,
    }

    SEPARATORS: Dict[str, str] = {
        'price': '价格方面：',
        'duration': '时间安排：',
        'contact': '联系方式：',
        'location': '地址信息：',
        'time': '',
    }

    def __init__(self, custom_patterns: Optional[Dict] = None):
        self.key_point_patterns = self.KEY_POINT_PATTERNS.copy()
        if custom_patterns:
            for key_type, patterns in custom_patterns.items():
                if key_type in self.key_point_patterns:
                    self.key_point_patterns[key_type].extend(patterns)
                else:
                    self.key_point_patterns[key_type] = patterns

    def fuse(
        self,
        samples: List[SampleInfo],
        intent: Optional[str] = None,
        max_sources: int = 3
    ) -> FusionResult:
        if not samples:
            return FusionResult(
                content='',
                sources=[],
                fusion_type='empty',
                confidence=0.0,
                key_points=[]
            )
        
        top_samples = samples[:max_sources]
        
        all_key_points = self._extract_all_key_points(top_samples)
        
        key_point_groups = self._group_key_points(all_key_points)
        
        conflicts = self._detect_conflicts(key_point_groups)
        
        resolved_points = self._resolve_conflicts(key_point_groups, conflicts)
        
        content = self._build_fused_content(resolved_points, intent)
        
        sources = [s.content[:50] + '...' if len(s.content) > 50 else s.content for s in top_samples]
        
        avg_confidence = sum(s.confidence for s in top_samples) / len(top_samples)
        
        return FusionResult(
            content=content,
            sources=sources,
            fusion_type='key_point_fusion',
            confidence=avg_confidence * 0.9,
            key_points=[p['value'] for p in resolved_points],
            conflicts=conflicts
        )

    def _extract_all_key_points(self, samples: List[SampleInfo]) -> List[Dict]:
        all_points = []
        
        for sample in samples:
            for key_type, patterns in self.key_point_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, sample.content)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        
                        point = {
                            'type': key_type,
                            'value': match,
                            'source': sample.content,
                            'confidence': sample.confidence,
                            'priority': self.FUSION_PRIORITY.get(key_type, 1)
                        }
                        all_points.append(point)
        
        return all_points

    def _group_key_points(self, points: List[Dict]) -> Dict[str, List[Dict]]:
        groups = {}
        
        for point in points:
            key_type = point['type']
            if key_type not in groups:
                groups[key_type] = []
            groups[key_type].append(point)
        
        for key_type in groups:
            groups[key_type].sort(key=lambda x: x['confidence'], reverse=True)
        
        return groups

    def _detect_conflicts(self, groups: Dict[str, List[Dict]]) -> List[Tuple[str, str]]:
        conflicts = []
        
        conflict_types = ['price', 'duration']
        
        for key_type in conflict_types:
            if key_type in groups:
                values = [p['value'] for p in groups[key_type]]
                unique_values = set(values)
                
                if len(unique_values) > 1:
                    conflicts.append((key_type, f'多个不同{key_type}值: {", ".join(unique_values)}'))
        
        return conflicts

    def _resolve_conflicts(
        self,
        groups: Dict[str, List[Dict]],
        conflicts: List[Tuple[str, str]]
    ) -> List[Dict]:
        resolved = []
        
        for key_type, points in groups.items():
            if key_type in ['price', 'duration']:
                best_point = points[0]
                resolved.append(best_point)
            else:
                seen_values = set()
                for point in points:
                    if point['value'] not in seen_values:
                        resolved.append(point)
                        seen_values.add(point['value'])
        
        resolved.sort(key=lambda x: x['priority'], reverse=True)
        
        return resolved

    def _build_fused_content(
        self,
        points: List[Dict],
        intent: Optional[str] = None
    ) -> str:
        if not points:
            return ''
        
        parts = []
        current_type = None
        
        for point in points:
            if point['type'] != current_type:
                separator = self.SEPARATORS.get(point['type'], '')
                if separator:
                    parts.append(separator)
                current_type = point['type']
            
            parts.append(point['value'])
        
        content = ' '.join(parts)
        
        if intent:
            content = self._add_intent_prefix(content, intent)
        
        return content

    def _add_intent_prefix(self, content: str, intent: str) -> str:
        prefixes = {
            'price': '关于价格问题，',
            'course': '关于课程内容，',
            'teacher': '关于师资情况，',
            'schedule': '关于时间安排，',
            'location': '关于上课地点，',
            'contact': '关于联系方式，',
        }
        
        prefix = prefixes.get(intent, '')
        return prefix + content if prefix else content

    def fuse_by_intent(
        self,
        samples: List[SampleInfo],
        intent: str
    ) -> FusionResult:
        intent_filters = {
            'price': ['price', 'duration'],
            'course': ['content'],
            'teacher': [],
            'schedule': ['duration', 'time'],
            'location': ['location'],
            'contact': ['contact'],
        }
        
        filtered_types = intent_filters.get(intent, [])
        
        if filtered_types:
            filtered_patterns = {
                k: self.key_point_patterns[k]
                for k in filtered_types
                if k in self.key_point_patterns
            }
            self.key_point_patterns = filtered_patterns
        
        result = self.fuse(samples, intent)
        
        self.key_point_patterns = self.KEY_POINT_PATTERNS.copy()
        
        return result

    def smart_merge(
        self,
        samples: List[SampleInfo],
        strategy: str = 'weighted'
    ) -> FusionResult:
        if strategy == 'weighted':
            return self._weighted_merge(samples)
        elif strategy == 'deduplicate':
            return self._deduplicate_merge(samples)
        else:
            return self.fuse(samples)

    def _weighted_merge(self, samples: List[SampleInfo]) -> FusionResult:
        weighted_samples = []
        
        for sample in samples:
            weight = sample.confidence
            
            if sample.source_type == 'local_exact':
                weight *= 1.2
            elif sample.source_type == 'local_vector':
                weight *= 1.0
            elif sample.source_type == 'local_keyword':
                weight *= 0.8
            
            weighted_samples.append((sample, weight))
        
        weighted_samples.sort(key=lambda x: x[1], reverse=True)
        
        sorted_samples = [s for s, w in weighted_samples[:3]]
        
        return self.fuse(sorted_samples)

    def _deduplicate_merge(self, samples: List[SampleInfo]) -> FusionResult:
        seen_content = set()
        unique_samples = []
        
        for sample in samples:
            normalized = self._normalize_content(sample.content)
            if normalized not in seen_content:
                seen_content.add(normalized)
                unique_samples.append(sample)
        
        return self.fuse(unique_samples[:3])

    def _normalize_content(self, content: str) -> str:
        content = re.sub(r'[^\w\s\u4e00-\u9fff]', '', content)
        content = content.lower().strip()
        return content

    def extract_entities_from_samples(
        self,
        samples: List[SampleInfo]
    ) -> Dict[str, List]:
        entities = {}
        
        for sample in samples:
            sample_entities = self._extract_entities(sample.content)
            for entity_type, values in sample_entities.items():
                if entity_type not in entities:
                    entities[entity_type] = []
                entities[entity_type].extend(values)
        
        for entity_type in entities:
            entities[entity_type] = list(set(entities[entity_type]))
        
        return entities

    def _extract_entities(self, content: str) -> Dict[str, List]:
        entities = {}
        
        patterns = {
            'money': [r'\d+元', r'\d+块'],
            'phone': [r'1[3-9]\d{9}', r'\d{3,4}-\d{7,8}'],
            'wechat': [r'[a-zA-Z][a-zA-Z0-9_-]{5,19}'],
            'number': [r'\d+课时', r'\d+节课', r'\d+周', r'\d+个月'],
        }
        
        for entity_type, pattern_list in patterns.items():
            values = []
            for pattern in pattern_list:
                matches = re.findall(pattern, content)
                values.extend(matches)
            if values:
                entities[entity_type] = values
        
        return entities

    def get_fusion_stats(self, result: FusionResult) -> Dict:
        return {
            'source_count': len(result.sources),
            'key_point_count': len(result.key_points),
            'conflict_count': len(result.conflicts),
            'fusion_type': result.fusion_type,
            'confidence': result.confidence,
        }