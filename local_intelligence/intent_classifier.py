"""
意图识别器 - 基于规则引擎
无外部模型依赖，纯关键词+正则匹配
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IntentResult:
    intent: str
    confidence: float
    matched_keywords: List[str]
    matched_patterns: List[str]
    sub_intent: Optional[str] = None


class IntentClassifier:
    INTENT_RULES: Dict[str, Dict] = {
        'price': {
            'keywords': ['价格', '多少钱', '费用', '收费', '价位', '价钱', '多少钱', '报价', '费用', '学费', '优惠', '折扣', '打折', '便宜'],
            'patterns': [r'\d+元', r'\d+块', r'多少钱'],
            'sub_intents': {
                'price_discount': ['优惠', '折扣', '打折', '便宜', '减免', '活动价'],
                'price_compare': ['对比', '比较', '哪个便宜', '性价比'],
            }
        },
        'course': {
            'keywords': ['课程', '内容', '学什么', '教学内容', '课程内容', '培训内容', '学习内容'],
            'patterns': [r'课程.*包含', r'学习.*什么'],
            'sub_intents': {
                'course_intro': ['介绍', '简介', '是什么', '详情'],
                'course_outline': ['大纲', '目录', '章节', '模块'],
            }
        },
        'teacher': {
            'keywords': ['老师', '教师', '讲师', '师资', '教学老师', '授课老师', '谁教'],
            'patterns': [r'谁.*教', r'老师.*是谁'],
            'sub_intents': {
                'teacher_intro': ['介绍', '简介', '是谁', '背景'],
                'teacher_qualify': ['资质', '证书', '经验', '资格'],
            }
        },
        'schedule': {
            'keywords': ['时间', '课时', '安排', '课程安排', '上课时间', '学习时间', '周期', '多久'],
            'patterns': [r'\d+课时', r'\d+周', r'每天.*时间'],
            'sub_intents': {
                'schedule_duration': ['多久', '周期', '时长', '课时'],
                'schedule_timetable': ['时间表', '日程', '具体时间', '几点'],
            }
        },
        'location': {
            'keywords': ['地址', '地点', '位置', '在哪', '地址在哪', '校区', '上课地点'],
            'patterns': [r'在哪', r'地址.*在哪'],
            'sub_intents': {
                'location_address': ['地址', '具体位置', '详细地址'],
                'location_nearby': ['附近', '周边', '离我'],
            }
        },
        'enroll': {
            'keywords': ['报名', '怎么报', '如何报名', '报名流程', '怎么报名', '报名方式', '入学'],
            'patterns': [r'怎么.*报', r'报名.*流程'],
            'sub_intents': {
                'enroll_process': ['流程', '步骤', '怎么报'],
                'enroll_requirement': ['条件', '要求', '资格'],
            }
        },
        'material': {
            'keywords': ['资料', '教材', '学习资料', '课程资料', '课本', '书籍', '材料'],
            'patterns': [r'需要.*资料', r'资料.*包含'],
            'sub_intents': {
                'material_include': ['包含', '提供', '有哪些'],
                'material_download': ['下载', '获取', '领取'],
            }
        },
        'certificate': {
            'keywords': ['证书', '资格证', '结业证', '认证', '证书考试', '考证'],
            'patterns': [r'证书.*考试', r'考.*证'],
            'sub_intents': {
                'certificate_type': ['什么证书', '证书类型', '有哪些证'],
                'certificate_exam': ['考试', '考什么', '怎么考'],
            }
        },
        'refund': {
            'keywords': ['退款', '退费', '退课', '退款政策', '退费政策', '不满意退款'],
            'patterns': [r'退款.*政策', r'退费.*规则'],
            'sub_intents': {
                'refund_policy': ['政策', '规则', '条件'],
                'refund_process': ['流程', '怎么退', '如何退'],
            }
        },
        'contact': {
            'keywords': ['联系方式', '电话', '客服', '咨询', '联系', '客服电话', '联系电话'],
            'patterns': [r'\d{3,4}-?\d{7,8}', r'电话.*是多少'],
            'sub_intents': {
                'contact_phone': ['电话', '客服电话', '热线'],
                'contact_wechat': ['微信', '公众号', '客服微信'],
            }
        },
        'greeting': {
            'keywords': ['你好', '您好', '在吗', '有人吗', 'hello', 'hi'],
            'patterns': [r'你好', r'您好', r'在吗'],
            'sub_intents': {}
        },
        'thanks': {
            'keywords': ['谢谢', '感谢', '好的谢谢', '知道了谢谢', 'thanks'],
            'patterns': [r'谢谢', r'感谢'],
            'sub_intents': {}
        },
        'complaint': {
            'keywords': ['投诉', '不满意', '抱怨', '问题', '反馈', '意见', '投诉渠道', '态度', '服务差', '太差'],
            'patterns': [r'投诉', r'不满意'],
            'sub_intents': {
                'complaint_service': ['服务', '态度', '质量'],
                'complaint_course': ['课程', '内容', '效果'],
            }
        },
    }

    DEFAULT_INTENT = 'unknown'
    MIN_CONFIDENCE = 0.3

    def __init__(self, custom_rules: Optional[Dict] = None):
        self.rules = self.INTENT_RULES.copy()
        if custom_rules:
            self._merge_rules(custom_rules)
        self._compile_patterns()

    def _merge_rules(self, custom_rules: Dict):
        for intent, rule in custom_rules.items():
            if intent in self.rules:
                self.rules[intent]['keywords'].extend(rule.get('keywords', []))
                self.rules[intent]['patterns'].extend(rule.get('patterns', []))
                if 'sub_intents' in rule:
                    self.rules[intent]['sub_intents'].update(rule['sub_intents'])
            else:
                self.rules[intent] = rule

    def _compile_patterns(self):
        for intent, rule in self.rules.items():
            rule['compiled_patterns'] = [
                re.compile(p) for p in rule.get('patterns', [])
            ]

    def classify(self, text: str) -> IntentResult:
        text = text.strip().lower()
        scores: Dict[str, float] = {}
        matched_info: Dict[str, Dict] = {}

        for intent, rule in self.rules.items():
            keyword_score = 0.0
            pattern_score = 0.0
            matched_keywords = []
            matched_patterns = []

            keywords = rule.get('keywords', [])
            for kw in keywords:
                if kw.lower() in text:
                    keyword_score += 1.0
                    matched_keywords.append(kw)

            patterns = rule.get('compiled_patterns', [])
            for pattern in patterns:
                if pattern.search(text):
                    pattern_score += 1.0
                    matched_patterns.append(pattern.pattern)

            total_score = keyword_score + pattern_score * 1.5
            if total_score > 0:
                scores[intent] = total_score
                matched_info[intent] = {
                    'keywords': matched_keywords,
                    'patterns': matched_patterns,
                    'keyword_count': keyword_score,
                    'pattern_count': pattern_score,
                }

        if not scores:
            return IntentResult(
                intent=self.DEFAULT_INTENT,
                confidence=0.0,
                matched_keywords=[],
                matched_patterns=[]
            )

        max_intent = max(scores, key=scores.get)
        max_score = scores[max_intent]
        
        total_matches = sum(scores.values())
        confidence = max_score / max(total_matches, 1.0)

        sub_intent = self._detect_sub_intent(text, max_intent, matched_info[max_intent])

        return IntentResult(
            intent=max_intent,
            confidence=min(confidence, 1.0),
            matched_keywords=matched_info[max_intent]['keywords'],
            matched_patterns=matched_info[max_intent]['patterns'],
            sub_intent=sub_intent,
        )

    def _detect_sub_intent(self, text: str, intent: str, matched_info: Dict) -> Optional[str]:
        sub_intents = self.rules[intent].get('sub_intents', {})
        if not sub_intents:
            return None

        for sub_intent, keywords in sub_intents.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    return sub_intent
        return None

    def classify_batch(self, texts: List[str]) -> List[IntentResult]:
        return [self.classify(text) for text in texts]

    def get_intent_distribution(self, text: str) -> Dict[str, float]:
        text = text.strip().lower()
        distribution: Dict[str, float] = {}

        for intent, rule in self.rules.items():
            score = 0.0
            keywords = rule.get('keywords', [])
            patterns = rule.get('compiled_patterns', [])

            for kw in keywords:
                if kw.lower() in text:
                    score += 1.0

            for pattern in patterns:
                if pattern.search(text):
                    score += 1.5

            if score > 0:
                distribution[intent] = score

        if distribution:
            total = sum(distribution.values())
            return {k: v / total for k, v in distribution.items()}
        return {}

    def get_all_intents(self) -> List[str]:
        return list(self.rules.keys())

    def add_intent(self, intent: str, keywords: List[str], patterns: Optional[List[str]] = None, sub_intents: Optional[Dict] = None):
        self.rules[intent] = {
            'keywords': keywords,
            'patterns': patterns or [],
            'sub_intents': sub_intents or {},
            'compiled_patterns': [re.compile(p) for p in (patterns or [])],
        }