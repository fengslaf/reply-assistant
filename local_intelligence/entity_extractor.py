"""
实体抽取器 - 基于规则+词典
无外部模型依赖，提取数字、时间、课程名等实体
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Entity:
    type: str
    value: Any
    text: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class EntityResult:
    entities: Dict[str, List[Entity]]
    raw_text: str
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        return self.entities.get(entity_type, [])
    
    def get_all_values(self, entity_type: str) -> List[Any]:
        return [e.value for e in self.get_entities_by_type(entity_type)]
    
    def has_entity(self, entity_type: str) -> bool:
        return entity_type in self.entities and len(self.entities[entity_type]) > 0


class EntityExtractor:
    ENTITY_PATTERNS: Dict[str, List[str]] = {
        'money': [
            r'\d+元',
            r'\d+块',
            r'\d+万',
            r'\d+千元',
            r'\d+\.?\d*元',
            r'\d+,\d+元',
            r'(\d+)块',
            r'(\d+)块钱',
        ],
        'number': [
            r'\d+课时',
            r'\d+节课',
            r'\d+个',
            r'\d+人',
            r'\d+次',
            r'\d+期',
            r'\d+周',
            r'\d+天',
            r'\d+月',
            r'\d+年',
        ],
        'time': [
            r'\d+点',
            r'\d+:\d+',
            r'\d+时\d+分',
            r'早上|上午|中午|下午|晚上|晚间',
            r'周一|周二|周三|周四|周五|周六|周日',
            r'星期一|星期二|星期三|星期四|星期五|星期六|星期七',
            r'工作日|周末|双休',
        ],
        'duration': [
            r'\d+小时',
            r'\d+分钟',
            r'\d+天',
            r'\d+周',
            r'\d+个月',
            r'\d+季度',
        ],
        'phone': [
            r'1[3-9]\d{9}',
            r'\d{3,4}-\d{7,8}',
            r'\d{7,8}',
        ],
        'wechat': [
            r'[a-zA-Z][a-zA-Z0-9_-]{5,19}',
        ],
        'email': [
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        ],
        'url': [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
        ],
    }

    DICT_ENTITIES: Dict[str, List[str]] = {
        'course_name': [
            'Python课程', 'Java课程', '前端课程', 'UI设计课程',
            '数据分析课程', '人工智能课程', '机器学习课程',
            '基础课程', '进阶课程', '高级课程', '专业课程',
            '入门班', '提高班', '精品班', 'VIP班', '一对一',
            '周末班', '晚班', '全日制班', '寒暑假班',
        ],
        'course_type': [
            '线上课', '线下课', '直播课', '录播课', '混合课',
            '面授', '网课', '一对一', '小班', '大班',
        ],
        'teacher_role': [
            '主讲老师', '助教', '班主任', '导师', '讲师',
            '资深讲师', '金牌讲师', '首席讲师',
        ],
        'certificate': [
            '结业证书', '技能证书', '职业资格证', '等级证书',
            '认证证书', '培训证书', '专业证书',
        ],
        'material_type': [
            '教材', '课件', '视频', '题库', '练习册', '作业',
            '案例', '素材', '源码', '文档',
        ],
        'location_keyword': [
            '校区', '总部', '分部', '教学楼', '教室',
            '线上', '线下', '直播平台',
        ],
    }

    def __init__(self, custom_patterns: Optional[Dict] = None, custom_dict: Optional[Dict] = None):
        self.patterns = self.ENTITY_PATTERNS.copy()
        self.dict_entities = self.DICT_ENTITIES.copy()
        
        if custom_patterns:
            for entity_type, patterns in custom_patterns.items():
                if entity_type in self.patterns:
                    self.patterns[entity_type].extend(patterns)
                else:
                    self.patterns[entity_type] = patterns
        
        if custom_dict:
            for entity_type, words in custom_dict.items():
                if entity_type in self.dict_entities:
                    self.dict_entities[entity_type].extend(words)
                else:
                    self.dict_entities[entity_type] = words
        
        self._compile_patterns()

    def _compile_patterns(self):
        self.compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for entity_type, patterns in self.patterns.items():
            self.compiled_patterns[entity_type] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def extract(self, text: str) -> EntityResult:
        text_lower = text.lower()
        entities: Dict[str, List[Entity]] = {}

        for entity_type, patterns in self.compiled_patterns.items():
            matched_entities = []
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = Entity(
                        type=entity_type,
                        value=self._parse_value(entity_type, match.group()),
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                    matched_entities.append(entity)
            if matched_entities:
                entities[entity_type] = matched_entities

        for entity_type, words in self.dict_entities.items():
            matched_entities = []
            for word in words:
                pos = text.find(word)
                while pos != -1:
                    entity = Entity(
                        type=entity_type,
                        value=word,
                        text=word,
                        start=pos,
                        end=pos + len(word),
                    )
                    matched_entities.append(entity)
                    pos = text.find(word, pos + 1)
            if matched_entities:
                entities[entity_type] = matched_entities

        return EntityResult(entities=entities, raw_text=text)

    def _parse_value(self, entity_type: str, text: str) -> Any:
        parsers = {
            'money': self._parse_money,
            'number': self._parse_number,
            'time': self._parse_time,
            'duration': self._parse_duration,
            'phone': lambda t: t,
            'wechat': lambda t: t,
            'email': lambda t: t,
            'url': lambda t: t,
        }
        parser = parsers.get(entity_type, lambda t: t)
        return parser(text)

    def _parse_money(self, text: str) -> float:
        text = text.replace(',', '').replace('块钱', '元').replace('块', '元')
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            return float(numbers[0])
        return 0.0

    def _parse_number(self, text: str) -> int:
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0

    def _parse_time(self, text: str) -> str:
        return text

    def _parse_duration(self, text: str) -> Dict[str, int]:
        numbers = re.findall(r'\d+', text)
        unit = ''
        if '小时' in text:
            unit = 'hours'
        elif '分钟' in text:
            unit = 'minutes'
        elif '天' in text:
            unit = 'days'
        elif '周' in text:
            unit = 'weeks'
        elif '个月' in text:
            unit = 'months'
        return {'value': int(numbers[0]) if numbers else 0, 'unit': unit}

    def extract_by_type(self, text: str, entity_type: str) -> List[Entity]:
        result = self.extract(text)
        return result.get_entities_by_type(entity_type)

    def get_all_entity_types(self) -> List[str]:
        return list(self.patterns.keys()) + list(self.dict_entities.keys())

    def add_entity_type(self, entity_type: str, patterns: Optional[List[str]] = None, words: Optional[List[str]] = None):
        if patterns:
            if entity_type in self.patterns:
                self.patterns[entity_type].extend(patterns)
            else:
                self.patterns[entity_type] = patterns
            self.compiled_patterns[entity_type] = [re.compile(p, re.IGNORECASE) for p in self.patterns[entity_type]]
        
        if words:
            if entity_type in self.dict_entities:
                self.dict_entities[entity_type].extend(words)
            else:
                self.dict_entities[entity_type] = words