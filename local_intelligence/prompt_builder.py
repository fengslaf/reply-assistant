"""
动态提示词构建器 - 根据场景自动生成prompt
无外部模型依赖，基于意图+实体+上下文构建针对性prompt
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class PromptConfig:
    system_prompt: str
    user_prompt_template: str
    context_enrichment: List[str]
    constraints: List[str]
    style_guide: str
    max_tokens_hint: int = 500


class PromptBuilder:
    INTENT_PROMPTS: Dict[str, PromptConfig] = {
        'price': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长解答价格相关问题。回答要简洁、具体、准确。',
            user_prompt_template='用户咨询价格问题：{query}\n请给出简洁的价格说明，包含具体金额和课时信息。',
            context_enrichment=['价格范围', '课时数量', '是否包含优惠'],
            constraints=['回答不超过100字', '必须包含具体金额', '避免模糊表述'],
            style_guide='专业、简洁、数据化',
            max_tokens_hint=300,
        ),
        'course': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长介绍课程内容。回答要详细但不冗长，突出核心价值。',
            user_prompt_template='用户咨询课程内容：{query}\n请介绍课程的主要内容和核心模块，突出学习价值。',
            context_enrichment=['课程大纲', '学习模块', '实践项目'],
            constraints=['回答不超过200字', '列出关键模块', '突出实用价值'],
            style_guide='详细、结构化、价值导向',
            max_tokens_hint=400,
        ),
        'teacher': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长介绍师资情况。回答要突出老师的专业背景和教学经验。',
            user_prompt_template='用户咨询老师情况：{query}\n请介绍主讲老师的背景和教学经验。',
            context_enrichment=['老师姓名', '专业背景', '教学经验', '学生评价'],
            constraints=['回答不超过150字', '突出专业背景', '提到教学经验'],
            style_guide='专业、信任导向、有说服力',
            max_tokens_hint=350,
        ),
        'schedule': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长解答时间安排问题。回答要具体、灵活、考虑用户需求。',
            user_prompt_template='用户咨询时间安排：{query}\n请给出课程的时间安排和周期信息。',
            context_enrichment=['总课时', '学习周期', '上课频率', '时间灵活性'],
            constraints=['回答不超过100字', '包含具体时间', '体现灵活性'],
            style_guide='具体、灵活、用户友好',
            max_tokens_hint=300,
        ),
        'location': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长解答地点位置问题。回答要清晰、准确、方便导航。',
            user_prompt_template='用户咨询上课地点：{query}\n请给出详细的地址和交通信息。',
            context_enrichment=['详细地址', '交通方式', '校区名称'],
            constraints=['回答不超过100字', '地址准确', '提到交通方式'],
            style_guide='清晰、准确、实用',
            max_tokens_hint=300,
        ),
        'enroll': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长指导报名流程。回答要简洁、步骤清晰、引导行动。',
            user_prompt_template='用户咨询报名方式：{query}\n请给出清晰的报名流程和联系方式。',
            context_enrichment=['报名步骤', '联系方式', '所需资料'],
            constraints=['回答不超过150字', '步骤清晰', '提供联系方式'],
            style_guide='简洁、行动导向、引导性强',
            max_tokens_hint=350,
        ),
        'material': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长解答学习资料问题。回答要具体、全面、突出资源丰富。',
            user_prompt_template='用户咨询学习资料：{query}\n请介绍课程提供的资料和学习资源。',
            context_enrichment=['教材清单', '课件资源', '在线资源'],
            constraints=['回答不超过150字', '列出关键资料', '突出资源丰富'],
            style_guide='具体、全面、资源导向',
            max_tokens_hint=350,
        ),
        'certificate': PromptConfig(
            system_prompt='你是一位专业的课程顾问，擅长解答证书认证问题。回答要权威、具体、突出价值。',
            user_prompt_template='用户咨询证书认证：{query}\n请介绍课程相关的证书和认证情况。',
            context_enrichment=['证书类型', '认证机构', '证书价值'],
            constraints=['回答不超过100字', '证书名称准确', '突出认证价值'],
            style_guide='权威、专业、价值导向',
            max_tokens_hint=300,
        ),
        'refund': PromptConfig(
            system_prompt='你是一位专业的课程顾问，耐心解答退款政策问题。回答要清晰、友好、体现保障。',
            user_prompt_template='用户咨询退款政策：{query}\n请清晰说明退款条件和流程。',
            context_enrichment=['退款条件', '退款流程', '退款时效'],
            constraints=['回答不超过150字', '条件清晰', '态度友好'],
            style_guide='清晰、友好、保障导向',
            max_tokens_hint=350,
        ),
        'contact': PromptConfig(
            system_prompt='你是一位专业的客服，擅长提供联系方式。回答要简洁、准确、方便用户。',
            user_prompt_template='用户咨询联系方式：{query}\n请提供准确的联系渠道。',
            context_enrichment=['客服电话', '微信', '工作时间'],
            constraints=['回答不超过50字', '联系方式准确', '格式清晰'],
            style_guide='简洁、准确、格式化',
            max_tokens_hint=200,
        ),
        'greeting': PromptConfig(
            system_prompt='你是一位友好的课程顾问，热情回应用户的问候。',
            user_prompt_template='用户发送问候：{query}\n请友好回应并询问需求。',
            context_enrichment=['服务介绍', '引导咨询'],
            constraints=['回答不超过50字', '态度热情', '引导下一步'],
            style_guide='热情、友好、引导性',
            max_tokens_hint=200,
        ),
        'thanks': PromptConfig(
            system_prompt='你是一位友好的课程顾问，礼貌回应感谢。',
            user_prompt_template='用户表示感谢：{query}\n请礼貌回应并表示随时服务。',
            context_enrichment=['服务承诺', '联系方式'],
            constraints=['回答不超过30字', '态度友好', '表示随时服务'],
            style_guide='礼貌、友好、服务导向',
            max_tokens_hint=150,
        ),
        'complaint': PromptConfig(
            system_prompt='你是一位耐心、专业的客服，认真处理投诉问题。态度诚恳、重视用户反馈。',
            user_prompt_template='用户投诉：{query}\n请诚恳表示重视，并给出处理方案或反馈渠道。',
            context_enrichment=['处理承诺', '反馈渠道', '改进措施'],
            constraints=['态度诚恳', '给出处理方案', '不超过100字'],
            style_guide='诚恳、重视、解决方案导向',
            max_tokens_hint=300,
        ),
    }

    DEFAULT_PROMPT: PromptConfig = PromptConfig(
        system_prompt='你是一位专业的课程顾问，帮助用户解答关于课程培训的问题。',
        user_prompt_template='用户问题：{query}\n请给出专业、简洁的回答。',
        context_enrichment=['相关信息'],
        constraints=['回答不超过200字'],
        style_guide='专业、简洁',
        max_tokens_hint=400,
    )

    STYLE_MODIFIERS: Dict[str, str] = {
        'formal': '使用正式用语，专业严谨。',
        'casual': '使用轻松用语，亲切自然。',
        'detailed': '详细解释，包含背景信息。',
        'brief': '简洁回答，只说关键信息。',
        'sales': '引导报名，突出课程价值。',
        'support': '耐心解答，强调服务质量。',
    }

    CONTEXT_PREFIXES: Dict[str, str] = {
        'price': '价格信息：',
        'course': '课程内容：',
        'teacher': '师资介绍：',
        'schedule': '时间安排：',
        'location': '地址信息：',
        'contact': '联系方式：',
    }

    def __init__(self, custom_prompts: Optional[Dict] = None):
        self.intent_prompts = self.INTENT_PROMPTS.copy()
        if custom_prompts:
            self.intent_prompts.update(custom_prompts)

    def build(self, intent: str, query: str, entities: Optional[Dict] = None, context: Optional[List] = None, style_modifier: Optional[str] = None) -> Dict[str, str]:
        config = self.intent_prompts.get(intent, self.DEFAULT_PROMPT)
        
        system_prompt = config.system_prompt
        if style_modifier and style_modifier in self.STYLE_MODIFIERS:
            system_prompt += '\n' + self.STYLE_MODIFIERS[style_modifier]
        
        user_prompt = config.user_prompt_template.replace('{query}', query)
        
        if entities:
            entity_context = self._build_entity_context(intent, entities)
            if entity_context:
                user_prompt += '\n相关信息：' + entity_context
        
        if context:
            normalized_context = []
            for item in context[:3]:
                if isinstance(item, dict):
                    role = item.get('role', '')
                    content = item.get('content', '')
                    if role and content:
                        normalized_context.append(f"{role}: {content}")
                    elif content:
                        normalized_context.append(str(content))
                else:
                    normalized_context.append(str(item))
            context_str = '\n'.join([item for item in normalized_context if item])
            user_prompt += '\n上下文：' + context_str
        
        constraints_str = '\n注意：' + '; '.join(config.constraints[:3])
        user_prompt += constraints_str
        
        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'max_tokens': config.max_tokens_hint,
            'intent': intent,
            'style_guide': config.style_guide,
        }

    def _build_entity_context(self, intent: str, entities: Dict) -> str:
        context_parts = []
        
        prefix = self.CONTEXT_PREFIXES.get(intent, '')
        
        for entity_type, entity_values in entities.items():
            if entity_values:
                values_str = ', '.join([str(v) for v in entity_values[:3]])
                context_parts.append(f'{entity_type}: {values_str}')
        
        if context_parts:
            return prefix + '; '.join(context_parts)
        return ''

    def build_with_sample(self, intent: str, query: str, sample_reply: str, confidence: float) -> Dict[str, str]:
        config = self.intent_prompts.get(intent, self.DEFAULT_PROMPT)
        
        system_prompt = config.system_prompt
        
        user_prompt = f'''用户问题：{query}

参考回答（相似度{confidence:.2f}）：
{sample_reply}

请根据参考回答，生成一个更合适的回复。可以调整语气、补充信息，但要保持专业性。'''

        if confidence < 0.6:
            user_prompt += '\n注意：参考回答相似度较低，请谨慎参考。'

        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'max_tokens': config.max_tokens_hint,
            'intent': intent,
            'reference_confidence': confidence,
        }

    def build_multi_intent(self, intents: List[str], query: str) -> Dict[str, str]:
        primary_intent = intents[0] if intents else 'unknown'
        config = self.intent_prompts.get(primary_intent, self.DEFAULT_PROMPT)
        
        intent_str = ', '.join(intents[:3])
        
        system_prompt = f'''你是一位专业的课程顾问。用户问题涉及多个方面：{intent_str}。
请综合考虑，给出全面但简洁的回答。'''

        user_prompt = f'用户问题：{query}\n请针对以上多个方面给出简洁的回复。'

        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'max_tokens': min(config.max_tokens_hint + 100, 600),
            'intents': intents,
        }

    def get_quick_prompt(self, intent: str) -> str:
        config = self.intent_prompts.get(intent, self.DEFAULT_PROMPT)
        return config.system_prompt

    def get_prompt_constraints(self, intent: str) -> List[str]:
        config = self.intent_prompts.get(intent, self.DEFAULT_PROMPT)
        return config.constraints

    def get_all_intent_types(self) -> List[str]:
        return list(self.intent_prompts.keys())

    def add_intent_prompt(self, intent: str, config: PromptConfig):
        self.intent_prompts[intent] = config

    def customize_style(self, intent: str, style: str):
        if intent in self.intent_prompts:
            current = self.intent_prompts[intent]
            if style in self.STYLE_MODIFIERS:
                current.system_prompt += '\n' + self.STYLE_MODIFIERS[style]
