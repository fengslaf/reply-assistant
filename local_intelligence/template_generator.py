"""
模板拼接生成器 - V2.04
基于模板库+参数变量生成回复
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class TemplateSlot:
    slot_name: str
    required: bool = True
    default_value: Optional[str] = None
    description: str = ''


@dataclass
class TemplateDefinition:
    template_id: str
    template_type: str
    slots: List[TemplateSlot]
    templates: List[str]
    priority: int = 1
    description: str = ''


@dataclass
class GeneratedReply:
    content: str
    template_id: str
    template_type: str
    filled_slots: Dict[str, str]
    confidence: float
    generation_method: str = 'template_filling'


class TemplateGenerator:
    TEMPLATE_LIBRARY: Dict[str, TemplateDefinition] = {
        'price_reply': TemplateDefinition(
            template_id='price_reply',
            template_type='price',
            slots=[
                TemplateSlot('课程', True, None, '课程名称'),
                TemplateSlot('价格', True, None, '课程价格'),
                TemplateSlot('课时', False, '未知', '课时数量'),
                TemplateSlot('优惠', False, '', '优惠信息'),
            ],
            templates=[
                '您好，{课程}的费用是{价格}元，包含{课时}课时。{优惠}',
                '{课程}收费{价格}元，课时安排{课时}课时。{优惠}',
                '关于{课程}的价格：标准价{价格}元，课时{课时}课时。{优惠}',
                '我们{课程}定价{价格}元，课时总数{课时}课时。如有优惠{优惠}',
            ],
            priority=1,
            description='价格回复模板',
        ),
        'course_reply': TemplateDefinition(
            template_id='course_reply',
            template_type='course',
            slots=[
                TemplateSlot('课程', True, None, '课程名称'),
                TemplateSlot('内容', True, None, '课程内容'),
                TemplateSlot('时长', False, '', '学习时长'),
                TemplateSlot('方式', False, '', '上课方式'),
            ],
            templates=[
                '{课程}主要学习以下内容：{内容}。学习周期{时长}，上课方式{方式}。',
                '关于{课程}，课程大纲包括：{内容}。{时长}，{方式}。',
                '{课程}教学内容涵盖{内容}，学习时间{时长}，授课形式{方式}。',
            ],
            priority=1,
            description='课程内容回复模板',
        ),
        'teacher_reply': TemplateDefinition(
            template_id='teacher_reply',
            template_type='teacher',
            slots=[
                TemplateSlot('课程', True, None, '课程名称'),
                TemplateSlot('老师', True, None, '老师姓名'),
                TemplateSlot('经验', False, '', '教学经验'),
                TemplateSlot('背景', False, '', '专业背景'),
            ],
            templates=[
                '{课程}主讲老师是{老师}，{经验}{背景}。',
                '我们{课程}由{老师}老师授课，{背景}{经验}。',
                '{课程}师资：{老师}老师，{经验}，{背景}。',
            ],
            priority=1,
            description='师资介绍模板',
        ),
        'schedule_reply': TemplateDefinition(
            template_id='schedule_reply',
            template_type='schedule',
            slots=[
                TemplateSlot('课程', True, None, '课程名称'),
                TemplateSlot('周期', True, None, '学习周期'),
                TemplateSlot('频率', False, '', '上课频率'),
                TemplateSlot('时间', False, '', '具体时间'),
            ],
            templates=[
                '{课程}学习周期{周期}，建议{频率}上课，具体时间{时间}。',
                '关于{课程}时间安排：总时长{周期}，上课频率{频率}，时间{时间}。',
            ],
            priority=1,
            description='时间安排模板',
        ),
        'location_reply': TemplateDefinition(
            template_id='location_reply',
            template_type='location',
            slots=[
                TemplateSlot('校区', True, None, '校区名称'),
                TemplateSlot('地址', True, None, '详细地址'),
                TemplateSlot('交通', False, '', '交通信息'),
            ],
            templates=[
                '{校区}地址：{地址}。交通：{交通}',
                '我们{校区}位于{地址}，交通方式{交通}。',
            ],
            priority=1,
            description='地址位置模板',
        ),
        'enroll_reply': TemplateDefinition(
            template_id='enroll_reply',
            template_type='enroll',
            slots=[
                TemplateSlot('步骤', True, None, '报名步骤'),
                TemplateSlot('资料', False, '', '所需资料'),
                TemplateSlot('联系', False, '', '联系方式'),
            ],
            templates=[
                '报名流程：{步骤}。需准备：{资料}。联系方式：{联系}',
                '报名方式：{步骤}，资料准备{资料}，如有疑问请联系{联系}。',
            ],
            priority=1,
            description='报名流程模板',
        ),
        'contact_reply': TemplateDefinition(
            template_id='contact_reply',
            template_type='contact',
            slots=[
                TemplateSlot('电话', True, None, '联系电话'),
                TemplateSlot('微信', False, '', '客服微信'),
                TemplateSlot('时间', False, '', '工作时间'),
            ],
            templates=[
                '联系方式：电话{电话}，微信{微信}，工作时间{时间}。',
                '如有疑问请致电{电话}或添加微信{微信}，服务时间{时间}。',
            ],
            priority=1,
            description='联系方式模板',
        ),
        'greeting_reply': TemplateDefinition(
            template_id='greeting_reply',
            template_type='greeting',
            slots=[
                TemplateSlot('问候', False, '您好', '问候语'),
            ],
            templates=[
                '{问候}，很高兴为您服务。请问有什么可以帮您？',
                '{问候}，欢迎咨询，请问您想了解什么？',
            ],
            priority=2,
            description='问候回复模板',
        ),
        'thanks_reply': TemplateDefinition(
            template_id='thanks_reply',
            template_type='thanks',
            slots=[
                TemplateSlot('礼貌', False, '感谢', '礼貌用语'),
            ],
            templates=[
                '{礼貌}您的信任，如有其他问题欢迎继续咨询。',
                '非常{礼貌}，随时为您提供帮助。',
            ],
            priority=2,
            description='感谢回复模板',
        ),
    }

    SLOT_ENTITY_MAP: Dict[str, str] = {
        '价格': 'money',
        '课时': 'number',
        '时长': 'duration',
        '周期': 'duration',
        '电话': 'phone',
        '微信': 'wechat',
        '课程': 'course_name',
        '内容': 'course_content',
        '老师': 'teacher_name',
    }

    def __init__(self, custom_templates: Optional[Dict] = None):
        self.templates = self.TEMPLATE_LIBRARY.copy()
        if custom_templates:
            for template_id, template_def in custom_templates.items():
                self.templates[template_id] = template_def

    def generate(
        self,
        intent: str,
        params: Dict[str, str],
        confidence_threshold: float = 0.7
    ) -> GeneratedReply:
        template_def = self._get_template_for_intent(intent)
        
        if not template_def:
            return GeneratedReply(
                content='',
                template_id='',
                template_type=intent,
                filled_slots=params,
                confidence=0.0,
                generation_method='template_filling_failed'
            )
        
        filled_slots = self._fill_slots(template_def, params)
        slot_coverage = self._calc_slot_coverage(template_def, filled_slots)
        
        if slot_coverage < confidence_threshold:
            return GeneratedReply(
                content='',
                template_id=template_def.template_id,
                template_type=template_def.template_type,
                filled_slots=filled_slots,
                confidence=slot_coverage,
                generation_method='template_partial'
            )
        
        selected_template = self._select_template(template_def.templates, filled_slots)
        content = self._apply_template(selected_template, filled_slots)
        
        content = self._clean_empty_slots(content)
        
        return GeneratedReply(
            content=content,
            template_id=template_def.template_id,
            template_type=template_def.template_type,
            filled_slots=filled_slots,
            confidence=slot_coverage,
            generation_method='template_filling'
        )

    def _get_template_for_intent(self, intent: str) -> Optional[TemplateDefinition]:
        intent_template_map = {
            'price': 'price_reply',
            'course': 'course_reply',
            'teacher': 'teacher_reply',
            'schedule': 'schedule_reply',
            'location': 'location_reply',
            'enroll': 'enroll_reply',
            'contact': 'contact_reply',
            'greeting': 'greeting_reply',
            'thanks': 'thanks_reply',
        }
        
        template_id = intent_template_map.get(intent)
        return self.templates.get(template_id)

    def _fill_slots(
        self,
        template_def: TemplateDefinition,
        params: Dict[str, str]
    ) -> Dict[str, str]:
        filled = {}
        
        for slot in template_def.slots:
            if slot.slot_name in params and params[slot.slot_name]:
                filled[slot.slot_name] = params[slot.slot_name]
            elif slot.default_value:
                filled[slot.slot_name] = slot.default_value
            elif slot.required:
                filled[slot.slot_name] = '[缺失]'
        
        return filled

    def _calc_slot_coverage(
        self,
        template_def: TemplateDefinition,
        filled_slots: Dict[str, str]
    ) -> float:
        required_count = len([s for s in template_def.slots if s.required])
        filled_required = 0
        
        for slot in template_def.slots:
            if slot.required:
                if slot.slot_name in filled_slots and filled_slots[slot.slot_name] != '[缺失]':
                    filled_required += 1
        
        return filled_required / required_count if required_count > 0 else 1.0

    def _select_template(
        self,
        templates: List[str],
        filled_slots: Dict[str, str]
    ) -> str:
        best_template = templates[0]
        best_score = 0
        
        for template in templates:
            score = self._score_template(template, filled_slots)
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template

    def _score_template(self, template: str, filled_slots: Dict[str, str]) -> int:
        score = 0
        
        for slot_name, value in filled_slots.items():
            placeholder = f'{{{slot_name}}}'
            if placeholder in template:
                if value and value != '[缺失]':
                    score += 2
                else:
                    score -= 1
        
        return score

    def _apply_template(
        self,
        template: str,
        filled_slots: Dict[str, str]
    ) -> str:
        content = template
        
        for slot_name, value in filled_slots.items():
            placeholder = f'{{{slot_name}}}'
            content = content.replace(placeholder, value)
        
        return content

    def _clean_empty_slots(self, content: str) -> str:
        content = re.sub(r'\{[^}]+\}', '', content)
        
        content = re.sub(r'[，。]\s*[，。]', '。', content)
        content = re.sub(r'[\s]+', ' ', content)
        content = content.strip()
        
        return content

    def generate_with_entity_mapping(
        self,
        intent: str,
        entities: Dict[str, List],
        confidence_threshold: float = 0.7
    ) -> GeneratedReply:
        params = {}
        
        for slot_name, entity_type in self.SLOT_ENTITY_MAP.items():
            if entity_type in entities and entities[entity_type]:
                params[slot_name] = str(entities[entity_type][0])
        
        return self.generate(intent, params, confidence_threshold)

    def generate_batch(
        self,
        intent: str,
        param_list: List[Dict[str, str]]
    ) -> List[GeneratedReply]:
        return [self.generate(intent, params) for params in param_list]

    def add_template(
        self,
        template_id: str,
        template_type: str,
        slots: List[TemplateSlot],
        templates: List[str],
        priority: int = 1
    ):
        self.templates[template_id] = TemplateDefinition(
            template_id=template_id,
            template_type=template_type,
            slots=slots,
            templates=templates,
            priority=priority,
        )

    def get_template_types(self) -> List[str]:
        return [t.template_type for t in self.templates.values()]

    def get_template_info(self, template_id: str) -> Optional[Dict]:
        template_def = self.templates.get(template_id)
        if not template_def:
            return None
        
        return {
            'template_id': template_def.template_id,
            'template_type': template_def.template_type,
            'slots': [{'name': s.slot_name, 'required': s.required, 'default': s.default_value} for s in template_def.slots],
            'template_count': len(template_def.templates),
        }