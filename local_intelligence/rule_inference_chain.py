"""
规则推理链 - V2.04
基于预定义规则链进行逻辑推理生成回复
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import re


@dataclass
class RuleCondition:
    condition_type: str
    condition_value: Any
    negate: bool = False
    description: str = ''


@dataclass
class RuleAction:
    action_type: str
    action_value: str
    priority: int = 1
    description: str = ''


@dataclass
class InferenceRule:
    rule_id: str
    rule_name: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    confidence: float = 0.8
    enabled: bool = True
    priority: int = 1


@dataclass
class InferenceStep:
    rule_id: str
    rule_name: str
    matched: bool
    confidence: float
    action_taken: str
    reasoning: str


@dataclass
class InferenceResult:
    content: str
    inference_chain: List[InferenceStep]
    final_confidence: float
    matched_rules: List[str]
    generation_method: str = 'rule_inference'


class RuleInferenceChain:
    DEFAULT_RULES: List[InferenceRule] = [
        InferenceRule(
            rule_id='price_complaint_1',
            rule_name='价格抱怨处理规则',
            conditions=[
                RuleCondition('intent', 'price', False, '意图为价格'),
                RuleCondition('keyword', '贵', False, '包含"贵"关键词'),
                RuleCondition('keyword', '太', False, '包含"太"强调词'),
            ],
            actions=[
                RuleAction('reply', '关于价格问题，我们提供多种优惠方案：早鸟优惠、团购优惠、分期付款等，具体可以根据您的需求选择。', 1, '提供优惠方案'),
                RuleAction('suggest', '了解优惠方案', 2, '建议了解优惠'),
            ],
            confidence=0.85,
            priority=1
        ),
        InferenceRule(
            rule_id='price_complaint_2',
            rule_name='价格抱怨缓和规则',
            conditions=[
                RuleCondition('intent', 'price', False, '意图为价格'),
                RuleCondition('keyword', '贵', False, '包含"贵"关键词'),
                RuleCondition('entity', 'money', True, '无明确价格实体'),
            ],
            actions=[
                RuleAction('reply', '我理解您对价格的关注。我们的课程定价综合考虑了师资、课时、教学资源等因素，确保学习效果。您可以先了解课程内容再做决定。', 1, '价格合理性说明'),
            ],
            confidence=0.75,
            priority=2
        ),
        InferenceRule(
            rule_id='price_specific_1',
            rule_name='价格询问精确回复规则',
            conditions=[
                RuleCondition('intent', 'price', False, '意图为价格'),
                RuleCondition('entity', 'money', False, '包含价格实体'),
                RuleCondition('entity', 'course_name', False, '包含课程实体'),
            ],
            actions=[
                RuleAction('template', 'price_reply', 1, '使用价格模板'),
                RuleAction('fallback', 'local_search', 2, '降级检索'),
            ],
            confidence=0.90,
            priority=1
        ),
        InferenceRule(
            rule_id='enroll_intent_1',
            rule_name='报名意向引导规则',
            conditions=[
                RuleCondition('intent', 'enroll', False, '意图为报名'),
                RuleCondition('keyword', '想', False, '包含"想"关键词'),
                RuleCondition('keyword', '报名', False, '包含"报名"关键词'),
            ],
            actions=[
                RuleAction('reply', '好的，报名流程很简单：1.选择课程 2.填写信息 3.支付费用。您可以现在就开始报名，或者先了解更多课程信息。', 1, '报名流程引导'),
                RuleAction('suggest', '开始报名', 2, '建议开始报名'),
            ],
            confidence=0.80,
            priority=1
        ),
        InferenceRule(
            rule_id='enroll_intent_2',
            rule_name='报名犹豫处理规则',
            conditions=[
                RuleCondition('intent', 'enroll', False, '意图为报名'),
                RuleCondition('keyword', '考虑', False, '包含"考虑"关键词'),
            ],
            actions=[
                RuleAction('reply', '理解您的考虑。您可以先了解更多课程详情、师资情况、学员评价等信息，有任何问题随时咨询我们。', 1, '考虑阶段支持'),
                RuleAction('suggest', '了解更多', 2, '建议了解更多'),
            ],
            confidence=0.70,
            priority=2
        ),
        InferenceRule(
            rule_id='course_inquiry_1',
            rule_name='课程内容询问规则',
            conditions=[
                RuleCondition('intent', 'course', False, '意图为课程'),
                RuleCondition('keyword', '学', False, '包含"学"关键词'),
                RuleCondition('keyword', '什么', False, '包含"什么"关键词'),
            ],
            actions=[
                RuleAction('template', 'course_reply', 1, '使用课程模板'),
            ],
            confidence=0.85,
            priority=1
        ),
        InferenceRule(
            rule_id='course_inquiry_2',
            rule_name='课程详情询问规则',
            conditions=[
                RuleCondition('intent', 'course', False, '意图为课程'),
                RuleCondition('keyword', '详细', False, '包含"详细"关键词'),
            ],
            actions=[
                RuleAction('reply', '课程详细内容包括：理论基础、实践操作、案例分析、项目实战等模块。您可以预约试听课程，亲身体验教学方式。', 1, '课程详情介绍'),
            ],
            confidence=0.80,
            priority=2
        ),
        InferenceRule(
            rule_id='teacher_inquiry_1',
            rule_name='师资询问规则',
            conditions=[
                RuleCondition('intent', 'teacher', False, '意图为师资'),
                RuleCondition('keyword', '老师', False, '包含"老师"关键词'),
            ],
            actions=[
                RuleAction('template', 'teacher_reply', 1, '使用师资模板'),
            ],
            confidence=0.85,
            priority=1
        ),
        InferenceRule(
            rule_id='schedule_inquiry_1',
            rule_name='时间询问规则',
            conditions=[
                RuleCondition('intent', 'schedule', False, '意图为时间'),
                RuleCondition('keyword', '多久', False, '包含"多久"关键词'),
            ],
            actions=[
                RuleAction('template', 'schedule_reply', 1, '使用时间模板'),
            ],
            confidence=0.85,
            priority=1
        ),
        InferenceRule(
            rule_id='greeting_1',
            rule_name='问候响应规则',
            conditions=[
                RuleCondition('intent', 'greeting', False, '意图为问候'),
            ],
            actions=[
                RuleAction('reply', '您好，很高兴为您服务！请问您想了解哪方面信息：课程内容、价格、师资、还是时间安排？', 1, '问候响应+引导'),
            ],
            confidence=0.95,
            priority=1
        ),
        InferenceRule(
            rule_id='thanks_1',
            rule_name='感谢响应规则',
            conditions=[
                RuleCondition('intent', 'thanks', False, '意图为感谢'),
            ],
            actions=[
                RuleAction('reply', '感谢您的信任！如有其他问题，欢迎随时咨询。祝您学习顺利！', 1, '感谢响应'),
            ],
            confidence=0.95,
            priority=1
        ),
        InferenceRule(
            rule_id='refund_request_1',
            rule_name='退款请求处理规则',
            conditions=[
                RuleCondition('intent', 'refund', False, '意图为退款'),
                RuleCondition('keyword', '退', False, '包含"退"关键词'),
            ],
            actions=[
                RuleAction('reply', '关于退款政策：课程开始前可全额退款，开始后按实际课时扣除费用。具体情况请联系客服处理。', 1, '退款政策说明'),
            ],
            confidence=0.80,
            priority=1
        ),
        InferenceRule(
            rule_id='complaint_1',
            rule_name='投诉处理规则',
            conditions=[
                RuleCondition('intent', 'complaint', False, '意图为投诉'),
                RuleCondition('keyword', '不好', False, '包含负面词'),
            ],
            actions=[
                RuleAction('reply', '非常抱歉给您带来不好的体验。我们会认真对待您的反馈，请详细说明问题，我们会尽快处理和改进。', 1, '投诉响应'),
            ],
            confidence=0.85,
            priority=1
        ),
    ]

    CONDITION_CHECKERS: Dict[str, callable] = {}

    def __init__(
        self,
        custom_rules: Optional[List[InferenceRule]] = None,
        custom_conditions: Optional[Dict] = None
    ):
        self.rules = self.DEFAULT_RULES.copy()
        
        if custom_rules:
            self.rules.extend(custom_rules)
        
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        
        self.condition_checkers = {
            'intent': self._check_intent_condition,
            'keyword': self._check_keyword_condition,
            'entity': self._check_entity_condition,
            'context': self._check_context_condition,
        }
        
        if custom_conditions:
            self.condition_checkers.update(custom_conditions)

    def infer(
        self,
        query: str,
        intent: str,
        entities: Dict[str, List],
        context: Optional[List[str]] = None
    ) -> InferenceResult:
        inference_chain = []
        matched_rules = []
        final_confidence = 0.0
        content = ''
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            matched, step = self._evaluate_rule(
                rule,
                query,
                intent,
                entities,
                context
            )
            
            inference_chain.append(step)
            
            if matched:
                matched_rules.append(rule.rule_id)
                
                action_result = self._execute_action(rule.actions[0], entities)
                
                if action_result:
                    content = action_result
                    final_confidence = rule.confidence
                    
                    break
        
        if not content:
            fallback_result = self._fallback_inference(query, intent)
            content = fallback_result['content']
            final_confidence = fallback_result['confidence']
        
        return InferenceResult(
            content=content,
            inference_chain=inference_chain,
            final_confidence=final_confidence,
            matched_rules=matched_rules,
            generation_method='rule_inference'
        )

    def _evaluate_rule(
        self,
        rule: InferenceRule,
        query: str,
        intent: str,
        entities: Dict[str, List],
        context: Optional[List[str]]
    ) -> Tuple[bool, InferenceStep]:
        matched_conditions = 0
        total_conditions = len(rule.conditions)
        
        for condition in rule.conditions:
            checker = self.condition_checkers.get(condition.condition_type)
            
            if checker:
                is_matched = checker(
                    condition.condition_value,
                    query,
                    intent,
                    entities,
                    context
                )
                
                if condition.negate:
                    is_matched = not is_matched
                
                if is_matched:
                    matched_conditions += 1
        
        all_matched = matched_conditions == total_conditions
        
        step = InferenceStep(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            matched=all_matched,
            confidence=rule.confidence if all_matched else 0.0,
            action_taken=rule.actions[0].action_value if all_matched else '',
            reasoning=f'匹配条件数: {matched_conditions}/{total_conditions}'
        )
        
        return (all_matched, step)

    def _check_intent_condition(
        self,
        expected_intent: str,
        query: str,
        intent: str,
        entities: Dict,
        context: Optional[List]
    ) -> bool:
        return intent == expected_intent

    def _check_keyword_condition(
        self,
        keyword: str,
        query: str,
        intent: str,
        entities: Dict,
        context: Optional[List]
    ) -> bool:
        return keyword in query

    def _check_entity_condition(
        self,
        entity_type: str,
        query: str,
        intent: str,
        entities: Dict,
        context: Optional[List]
    ) -> bool:
        return entity_type in entities and len(entities[entity_type]) > 0

    def _check_context_condition(
        self,
        context_keyword: str,
        query: str,
        intent: str,
        entities: Dict,
        context: Optional[List]
    ) -> bool:
        if not context:
            return False
        
        context_str = ' '.join(context)
        return context_keyword in context_str

    def _execute_action(
        self,
        action: RuleAction,
        entities: Dict[str, List]
    ) -> str:
        if action.action_type == 'reply':
            return action.action_value
        
        elif action.action_type == 'template':
            return self._fill_template(action.action_value, entities)
        
        elif action.action_type == 'suggest':
            return f'建议：{action.action_value}'
        
        return action.action_value

    def _fill_template(
        self,
        template_id: str,
        entities: Dict[str, List]
    ) -> str:
        templates = {
            'price_reply': '课程费用为{价格}元，包含{课时}课时。',
            'course_reply': '课程内容包括{内容}等模块。',
            'teacher_reply': '主讲老师{老师}，经验丰富。',
            'schedule_reply': '学习周期{周期}，建议每周学习{频率}。',
        }
        
        template = templates.get(template_id, '')
        
        slot_entity_map = {
            '{价格}': 'money',
            '{课时}': 'number',
            '{内容}': 'course_name',
            '{老师}': 'teacher',
            '{周期}': 'duration',
        }
        
        for slot, entity_type in slot_entity_map.items():
            if entity_type in entities and entities[entity_type]:
                template = template.replace(slot, str(entities[entity_type][0]))
            else:
                template = template.replace(slot, '具体咨询')
        
        return template

    def _fallback_inference(
        self,
        query: str,
        intent: str
    ) -> Dict[str, Any]:
        fallback_replies = {
            'price': '关于价格问题，请咨询客服获取具体报价。',
            'course': '关于课程内容，我们提供多种课程选择，请咨询客服了解详情。',
            'teacher': '我们的师资团队经验丰富，请咨询客服获取具体介绍。',
            'schedule': '关于时间安排，我们可以灵活调整，请咨询客服了解详情。',
            'location': '地址信息请咨询客服获取详细导航。',
            'enroll': '报名流程简单快捷，请咨询客服开始报名。',
            'contact': '联系方式请咨询客服。',
            'greeting': '您好，有什么可以帮您？',
            'thanks': '感谢您的信任！',
            'unknown': '请详细说明您的需求，我们会尽力帮助您。',
        }
        
        return {
            'content': fallback_replies.get(intent, fallback_replies['unknown']),
            'confidence': 0.3
        }

    def infer_with_context(
        self,
        query: str,
        intent: str,
        entities: Dict[str, List],
        context_messages: List[str]
    ) -> InferenceResult:
        return self.infer(query, intent, entities, context_messages)

    def add_rule(
        self,
        rule: InferenceRule
    ):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str):
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

    def enable_rule(self, rule_id: str, enabled: bool = True):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = enabled

    def get_rule(self, rule_id: str) -> Optional[InferenceRule]:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_rules_by_intent(self, intent: str) -> List[InferenceRule]:
        matching_rules = []
        for rule in self.rules:
            for condition in rule.conditions:
                if condition.condition_type == 'intent' and condition.condition_value == intent:
                    matching_rules.append(rule)
                    break
        return matching_rules

    def get_inference_chain_summary(
        self,
        result: InferenceResult
    ) -> str:
        steps = []
        for step in result.inference_chain:
            status = '✓' if step.matched else '×'
            steps.append(f'{status} {step.rule_name}: {step.reasoning}')
        
        return '\n'.join(steps)

    def get_stats(self) -> Dict:
        return {
            'total_rules': len(self.rules),
            'enabled_rules': len([r for r in self.rules if r.enabled]),
            'intent_coverage': len(set(
                c.condition_value
                for r in self.rules
                for c in r.conditions
                if c.condition_type == 'intent'
            )),
            'priority_distribution': {
                p: len([r for r in self.rules if r.priority == p])
                for p in [1, 2, 3]
            }
        }