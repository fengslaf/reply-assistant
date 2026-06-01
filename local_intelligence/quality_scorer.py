"""
回复质量评分器 - 多维度评估
无外部模型依赖，基于规则+统计评估样本质量
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class QualityScore:
    total_score: float
    dimension_scores: Dict[str, float]
    dimension_details: Dict[str, Dict] = field(default_factory=dict)
    grade: str = 'C'
    recommendations: List[str] = field(default_factory=list)


class QualityScorer:
    QUALITY_DIMENSIONS: Dict[str, Dict] = {
        'length': {
            'min_length': 10,
            'optimal_min': 50,
            'optimal_max': 200,
            'max_length': 500,
            'weight': 0.2,
            'description': '回复长度适中',
        },
        'keyword_coverage': {
            'weight': 0.25,
            'description': '关键词覆盖充分',
        },
        'structure': {
            'weight': 0.15,
            'description': '结构清晰',
        },
        'information_density': {
            'weight': 0.2,
            'description': '信息密度高',
        },
        'politeness': {
            'weight': 0.1,
            'description': '礼貌友好',
        },
        'actionability': {
            'weight': 0.1,
            'description': '具有行动指导',
        },
    }

    KEYWORD_INDICATORS: Dict[str, List[str]] = {
        'price': ['元', '价格', '费用', '收费', '价位'],
        'course': ['课程', '内容', '学习', '培训', '教学'],
        'teacher': ['老师', '教师', '讲师', '师资', '导师'],
        'schedule': ['时间', '课时', '安排', '周期', '周'],
        'location': ['地址', '地点', '位置', '校区', '在哪'],
        'contact': ['电话', '微信', '联系方式', '客服', '咨询'],
    }

    STRUCTURE_PATTERNS: Dict[str, List[str]] = {
        'has_list': [r'第一', r'第二', r'第三', r'1\.', r'2\.', r'3\.', r'①', r'②', r'③', r'一是', r'二是', r'三是'],
        'has_paragraph': [r'首先', r'其次', r'然后', r'最后', r'另外', r'此外'],
        'has_summary': [r'总结', r'总之', r'综上所述', r'总的来说'],
        'has_question': [r'您', r'请问', r'还有什么', r'需要了解'],
    }

    INFORMATION_INDICATORS: List[str] = [
        '具体', '详细', '包含', '提供', '例如', '比如', '如', '包括',
        '范围', '方式', '条件', '流程', '步骤', '要求',
    ]

    POLITENESS_PATTERNS: List[str] = [
        '您好', '谢谢', '感谢', '请', '很高兴', '乐意', '欢迎',
        '为您', '帮助您', '解答', '服务', '期待',
    ]

    ACTION_INDICATORS: List[str] = [
        '可以', '建议', '推荐', '欢迎', '点击', '联系', '咨询',
        '报名', '预约', '了解', '查看', '下载',
    ]

    GRADE_THRESHOLDS: Dict[str, float] = {
        'A+': 0.95,
        'A': 0.85,
        'B+': 0.75,
        'B': 0.65,
        'C+': 0.55,
        'C': 0.45,
        'D': 0.35,
        'F': 0.0,
    }

    def __init__(self, custom_dimensions: Optional[Dict] = None):
        self.dimensions = self.QUALITY_DIMENSIONS.copy()
        if custom_dimensions:
            self.dimensions.update(custom_dimensions)

    def score(self, reply: str, query: Optional[str] = None, intent: Optional[str] = None) -> QualityScore:
        dimension_scores: Dict[str, float] = {}
        dimension_details: Dict[str, Dict] = {}

        length_score = self._score_length(reply)
        dimension_scores['length'] = length_score['score']
        dimension_details['length'] = length_score

        coverage_score = self._score_keyword_coverage(reply, query, intent)
        dimension_scores['keyword_coverage'] = coverage_score['score']
        dimension_details['keyword_coverage'] = coverage_score

        structure_score = self._score_structure(reply)
        dimension_scores['structure'] = structure_score['score']
        dimension_details['structure'] = structure_score

        density_score = self._score_information_density(reply)
        dimension_scores['information_density'] = density_score['score']
        dimension_details['information_density'] = density_score

        politeness_score = self._score_politeness(reply)
        dimension_scores['politeness'] = politeness_score['score']
        dimension_details['politeness'] = politeness_score

        actionability_score = self._score_actionability(reply)
        dimension_scores['actionability'] = actionability_score['score']
        dimension_details['actionability'] = actionability_score

        total_score = sum(
            dimension_scores[dim] * self.dimensions[dim]['weight']
            for dim in dimension_scores
        )

        grade = self._get_grade(total_score)
        recommendations = self._generate_recommendations(dimension_scores, dimension_details)

        return QualityScore(
            total_score=total_score,
            dimension_scores=dimension_scores,
            dimension_details=dimension_details,
            grade=grade,
            recommendations=recommendations,
        )

    def _score_length(self, text: str) -> Dict:
        length = len(text)
        config = self.dimensions['length']
        
        if length < config['min_length']:
            score = 0.2
            reason = '回复太短，信息不足'
        elif length < config['optimal_min']:
            score = 0.5 + (length - config['min_length']) / (config['optimal_min'] - config['min_length']) * 0.3
            reason = '回复偏短，可适当补充'
        elif length <= config['optimal_max']:
            score = 1.0
            reason = '回复长度适中'
        elif length < config['max_length']:
            score = 0.8 - (length - config['optimal_max']) / (config['max_length'] - config['optimal_max']) * 0.3
            reason = '回复偏长，可能冗余'
        else:
            score = 0.3
            reason = '回复过长，需要精简'

        return {
            'score': score,
            'length': length,
            'reason': reason,
        }

    def _score_keyword_coverage(self, reply: str, query: Optional[str], intent: Optional[str]) -> Dict:
        reply_lower = reply.lower()
        covered_keywords = []
        missing_keywords = []
        
        if intent and intent in self.KEYWORD_INDICATORS:
            expected_keywords = self.KEYWORD_INDICATORS[intent]
            for kw in expected_keywords:
                if kw in reply_lower:
                    covered_keywords.append(kw)
                else:
                    missing_keywords.append(kw)
        
        if query:
            query_keywords = re.findall(r'[a-zA-Z\u4e00-\u9fa5]{2,}', query)
            for kw in query_keywords:
                if kw.lower() in reply_lower and kw not in covered_keywords:
                    covered_keywords.append(kw)

        total_expected = len(self.KEYWORD_INDICATORS.get(intent, [])) if intent else 5
        covered_count = len(covered_keywords)
        score = covered_count / max(total_expected, 1)

        return {
            'score': min(score, 1.0),
            'covered_keywords': covered_keywords,
            'missing_keywords': missing_keywords,
            'coverage_rate': covered_count / max(total_expected, 1) if total_expected > 0 else 0,
        }

    def _score_structure(self, text: str) -> Dict:
        structure_features = {}
        score = 0.0
        
        for feature, patterns in self.STRUCTURE_PATTERNS.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, text):
                    found = True
                    break
            structure_features[feature] = found
            if found:
                score += 0.25

        score = min(score, 1.0)
        
        return {
            'score': score,
            'features': structure_features,
            'has_clear_structure': score >= 0.5,
        }

    def _score_information_density(self, text: str) -> Dict:
        found_indicators = []
        for indicator in self.INFORMATION_INDICATORS:
            if indicator in text:
                found_indicators.append(indicator)

        numbers = re.findall(r'\d+', text)
        specific_info = len(numbers) > 0

        score = 0.0
        score += len(found_indicators) * 0.15
        if specific_info:
            score += 0.3

        score = min(score, 1.0)
        
        return {
            'score': score,
            'found_indicators': found_indicators,
            'has_numbers': specific_info,
            'number_count': len(numbers),
        }

    def _score_politeness(self, text: str) -> Dict:
        found_patterns = []
        for pattern in self.POLITENESS_PATTERNS:
            if pattern in text:
                found_patterns.append(pattern)

        score = len(found_patterns) * 0.25
        score = min(score, 1.0)
        
        return {
            'score': score,
            'found_patterns': found_patterns,
            'is_polite': score >= 0.5,
        }

    def _score_actionability(self, text: str) -> Dict:
        found_indicators = []
        for indicator in self.ACTION_INDICATORS:
            if indicator in text:
                found_indicators.append(indicator)

        score = len(found_indicators) * 0.2
        score = min(score, 1.0)
        
        return {
            'score': score,
            'found_indicators': found_indicators,
            'is_actionable': score >= 0.4,
        }

    def _get_grade(self, score: float) -> str:
        for grade, threshold in sorted(self.GRADE_THRESHOLDS.items(), key=lambda x: -x[1]):
            if score >= threshold:
                return grade
        return 'F'

    def _generate_recommendations(self, dimension_scores: Dict[str, float], dimension_details: Dict) -> List[str]:
        recommendations = []
        
        if dimension_scores['length'] < 0.5:
            recommendations.append('建议增加回复内容，补充更多信息')
        elif dimension_scores['length'] < 0.7:
            recommendations.append('回复可以适当扩展，增加细节')
        
        if dimension_scores['keyword_coverage'] < 0.5:
            missing = dimension_details['keyword_coverage'].get('missing_keywords', [])
            if missing:
                recommendations.append(f'建议包含以下关键词: {", ".join(missing[:3])}')
        
        if dimension_scores['structure'] < 0.5:
            recommendations.append('建议使用列表或分段结构，提高可读性')
        
        if dimension_scores['information_density'] < 0.5:
            recommendations.append('建议添加具体数据、案例或详细说明')
        
        if dimension_scores['politeness'] < 0.5:
            recommendations.append('建议添加礼貌用语，提升用户体验')
        
        if dimension_scores['actionability'] < 0.4:
            recommendations.append('建议添加行动建议，如联系方式、报名方式等')
        
        return recommendations

    def score_batch(self, replies: List[str], queries: Optional[List[str]] = None, intents: Optional[List[str]] = None) -> List[QualityScore]:
        results = []
        for i, reply in enumerate(replies):
            query = queries[i] if queries and i < len(queries) else None
            intent = intents[i] if intents and i < len(intents) else None
            results.append(self.score(reply, query, intent))
        return results

    def filter_high_quality(self, replies: List[str], min_score: float = 0.6) -> List[Tuple[str, QualityScore]]:
        scored = [(reply, self.score(reply)) for reply in replies]
        return [(reply, score) for reply, score in scored if score.total_score >= min_score]

    def get_best_reply(self, replies: List[str]) -> Tuple[str, QualityScore]:
        scored = [(reply, self.score(reply)) for reply in replies]
        return max(scored, key=lambda x: x[1].total_score)