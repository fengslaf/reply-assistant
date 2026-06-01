"""
样本扩充器 - 同义词替换+句式变换
无外部模型依赖，基于词典和模板扩充样本
"""

import re
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ExpansionResult:
    original: str
    variants: List[str]
    expansion_methods: List[str]
    expansion_stats: Dict[str, int] = field(default_factory=dict)


class SampleExpander:
    SYNONYM_GROUPS: Dict[str, List[str]] = {
        '价格': ['费用', '收费', '价位', '价钱', '报价'],
        '课程': ['培训', '教学', '学习班', '培训课程', '教学内容'],
        '老师': ['教师', '讲师', '导师', '教员', '师资'],
        '时间': ['课时', '安排', '周期', '日程', '时间安排'],
        '报名': ['入学', '注册', '申请', '参与', '加入'],
        '地址': ['地点', '位置', '校区位置', '培训地点', '上课地点'],
        '联系方式': ['电话', '客服', '咨询电话', '联系电话', '客服热线'],
        '内容': ['课程内容', '学习内容', '培训内容', '教学内容', '课程大纲'],
        '证书': ['资格证', '结业证', '认证证书', '培训证书', '技能证书'],
        '资料': ['教材', '学习资料', '课程资料', '学习材料', '参考资料'],
        '多久': ['多长时间', '多长时间', '时长', '周期', '需要多长时间'],
        '怎么': ['如何', '怎样', '该怎么', '该如何', '怎样'],
        '你好': ['您好', '您好啊', '你好啊', '嗨', 'hello'],
        '谢谢': ['感谢', '多谢', '谢谢您', '感谢您', '感谢你的解答'],
        '请问': ['咨询', '想问', '想了解', '请教', '打听'],
        '可以': ['能够', '可以', '是否能', '是否可以', '可否'],
        '有哪些': ['有什么', '包含哪些', '包括哪些', '有什么样的'],
        '需要': ['需要准备', '要准备', '需要什么', '要什么'],
        '介绍': ['说明', '简介', '讲解', '解释', '概述'],
        '了解': ['知道', '了解', '清楚', '明白', '晓得'],
        '上课': ['授课', '讲课', '教学', '学习', '培训'],
        '线下': ['面授', '现场', '实体课', '实地课程'],
        '线上': ['网课', '网络课程', '在线课程', '网络培训'],
        '一周': ['一星期', '7天', '七天', '一周时间'],
        '一个月': ['一个月时间', '30天', '三十天', '一月'],
        '一天': ['一日', '24小时', '1天时间'],
    }

    SENTENCE_TEMPLATES: Dict[str, List[str]] = {
        'question_price': [
            '{课程}多少钱？',
            '{课程}价格是多少？',
            '我想了解{课程}的费用',
            '{课程}收费怎么样？',
            '请问{课程}的价位？',
        ],
        'question_course': [
            '{课程}学什么内容？',
            '{课程}包含哪些模块？',
            '我想了解{课程}的课程大纲',
            '{课程}的主要内容是什么？',
            '{课程}会学习哪些知识？',
        ],
        'question_time': [
            '{课程}需要多久？',
            '{课程}多长时间？',
            '{课程}有多少课时？',
            '{课程}的学习周期是多久？',
            '{课程}需要多长时间完成？',
        ],
        'question_teacher': [
            '{课程}的老师是谁？',
            '{课程}的师资怎么样？',
            '{课程}有哪些讲师？',
            '{课程}的授课老师介绍',
            '{课程}的老师水平如何？',
        ],
        'reply_price': [
            '{课程}费用为{价格}元，包含{课时}课时。',
            '{课程}的价格是{价格}元，整个课程有{课时}课时。',
            '我们{课程}收费{价格}元，包括{课时}课时内容。',
            '{课程}培训费用{价格}元，课时总数{课时}课时。',
            '关于{课程}的价格，收费标准是{价格}元，课时安排{课时}课时。',
        ],
        'reply_course': [
            '{课程}主要学习以下内容：{内容列表}',
            '{课程}包含{内容列表}等模块。',
            '{课程}的课程内容包括{内容列表}。',
            '我们{课程}主要教授{内容列表}。',
            '{课程}教学内容涵盖{内容列表}。',
        ],
        'reply_time': [
            '{课程}需要{时长}，每周{频率}。',
            '{课程}的学习周期是{时长}，建议每周学习{频率}。',
            '{课程}总时长{时长}，可以按照{频率}安排。',
            '我们{课程}课程周期为{时长}，推荐{频率}学习。',
            '{课程}大约需要{时长}，可以灵活安排{频率}。',
        ],
        'reply_teacher': [
            '{课程}的主讲老师是{老师介绍}。',
            '{课程}由{老师介绍}老师授课。',
            '我们的{课程}老师是{老师介绍}。',
            '{课程}授课老师{老师介绍}，教学经验丰富。',
            '{课程}的师资团队包括{老师介绍}。',
        ],
        'reply_contact': [
            '联系方式：电话{电话}，微信{微信}。',
            '您可以拨打{电话}或添加微信{微信}联系我们。',
            '客服电话{电话}，客服微信{微信}。',
            '如有疑问，请致电{电话}或微信联系{微信}。',
            '咨询热线{电话}，客服微信{微信}，欢迎联系。',
        ],
    }

    COMMON_COURSES: List[str] = [
        'Python课程', 'Java课程', '前端课程', 'UI设计课程',
        '数据分析课程', '人工智能课程', '基础课程', '进阶课程',
    ]

    def __init__(self, custom_synonyms: Optional[Dict] = None, custom_templates: Optional[Dict] = None):
        self.synonyms = self.SYNONYM_GROUPS.copy()
        self.templates = self.SENTENCE_TEMPLATES.copy()
        
        if custom_synonyms:
            for word, syns in custom_synonyms.items():
                if word in self.synonyms:
                    self.synonyms[word] = list(set(self.synonyms[word] + syns))
                else:
                    self.synonyms[word] = syns
        
        if custom_templates:
            self.templates.update(custom_templates)

    def expand(self, sample: str, max_variants: int = 5) -> ExpansionResult:
        variants = []
        methods = []
        stats = {}

        synonym_variants = self._expand_by_synonyms(sample)
        if synonym_variants:
            variants.extend(synonym_variants[:max_variants])
            methods.append('synonym_replacement')
            stats['synonym_count'] = len(synonym_variants)

        template_variants = self._expand_by_template_extraction(sample)
        if template_variants:
            remaining = max_variants - len(variants)
            if remaining > 0:
                variants.extend(template_variants[:remaining])
            methods.append('template_variation')
            stats['template_count'] = len(template_variants)

        tone_variants = self._expand_by_tone(sample)
        if tone_variants:
            remaining = max_variants - len(variants)
            if remaining > 0:
                variants.extend(tone_variants[:remaining])
            methods.append('tone_variation')
            stats['tone_count'] = len(tone_variants)

        variants = list(set(variants))
        variants = [v for v in variants if v != sample]

        return ExpansionResult(
            original=sample,
            variants=variants[:max_variants],
            expansion_methods=methods,
            expansion_stats=stats,
        )

    def _expand_by_synonyms(self, text: str) -> List[str]:
        variants = []
        
        for word, syns in self.synonyms.items():
            if word in text:
                for syn in syns[:3]:
                    variant = text.replace(word, syn)
                    if variant != text:
                        variants.append(variant)
        
        return variants

    def _expand_by_template_extraction(self, text: str) -> List[str]:
        variants = []
        
        for template_type, templates in self.templates.items():
            if template_type.startswith('reply_'):
                filled = self._try_fill_template(text, templates)
                if filled:
                    variants.extend(filled)
        
        return variants

    def _try_fill_template(self, text: str, templates: List[str]) -> List[str]:
        filled = []
        
        course_match = None
        for course in self.COMMON_COURSES:
            if course in text or course.replace('课程', '') in text:
                course_match = course
                break
        
        price_match = re.search(r'\d+元', text)
        time_match = re.search(r'\d+课时|\d+周|\d+个月', text)
        
        for template in templates[:2]:
            filled_template = template
            
            if course_match:
                filled_template = filled_template.replace('{课程}', course_match)
            
            if price_match:
                filled_template = filled_template.replace('{价格}', price_match.group())
            
            if time_match:
                filled_template = filled_template.replace('{课时}', time_match.group())
                filled_template = filled_template.replace('{时长}', time_match.group())
            
            placeholders = re.findall(r'\{[^}]+\}', filled_template)
            if len(placeholders) <= 2:
                for placeholder in placeholders:
                    filled_template = filled_template.replace(placeholder, '')
                
                filled_template = filled_template.strip()
                if filled_template and filled_template != text:
                    filled.append(filled_template)
        
        return filled

    def _expand_by_tone(self, text: str) -> List[str]:
        variants = []
        
        polite_prefixes = ['您好，', '感谢您的咨询，', '很高兴为您解答，', '关于您的问题，']
        if not any(prefix in text for prefix in polite_prefixes):
            for prefix in polite_prefixes[:2]:
                variant = prefix + text
                variants.append(variant)
        
        suffixes = ['如有疑问欢迎继续咨询。', '希望能帮到您。', '还有什么需要了解的吗？']
        if not any(suffix in text for suffix in suffixes):
            for suffix in suffixes[:2]:
                variant = text + suffix
                variants.append(variant)
        
        return variants

    def expand_batch(self, samples: List[str], max_variants_per_sample: int = 5) -> List[ExpansionResult]:
        return [self.expand(sample, max_variants_per_sample) for sample in samples]

    def expand_intent_samples(self, intent: str, base_samples: List[str], max_total: int = 20) -> List[str]:
        expanded = []
        for sample in base_samples:
            result = self.expand(sample, max_variants=3)
            expanded.extend(result.variants)
        
        expanded = list(set(expanded))
        return expanded[:max_total]

    def generate_from_template(self, template_type: str, params: Dict[str, str]) -> List[str]:
        templates = self.templates.get(template_type, [])
        filled = []
        
        for template in templates:
            result = template
            for key, value in params.items():
                placeholder = f'{{{key}}}'
                result = result.replace(placeholder, value)
            
            remaining = re.findall(r'\{[^}]+\}', result)
            if not remaining:
                filled.append(result)
        
        return filled

    def add_synonym_group(self, word: str, synonyms: List[str]):
        if word in self.synonyms:
            self.synonyms[word] = list(set(self.synonyms[word] + synonyms))
        else:
            self.synonyms[word] = synonyms

    def add_template(self, template_type: str, template: str):
        if template_type in self.templates:
            self.templates[template_type].append(template)
        else:
            self.templates[template_type] = [template]