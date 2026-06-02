from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from edition_limits import get_customer_limit

try:
    from local_intelligence import IntelligenceManagerV204
except ImportError:  # pragma: no cover
    IntelligenceManagerV204 = None


SUBJECTS = [
    "Python",
    "英语",
    "数学",
    "语文",
    "物理",
    "化学",
    "生物",
    "历史",
    "地理",
    "政治",
    "道法",
    "科学",
    "编程",
    "奥数",
    "美术",
    "音乐",
]
SUBJECT_PATTERN = re.compile("|".join(sorted((re.escape(item) for item in SUBJECTS), key=len, reverse=True)))
PHONE_PATTERN = re.compile(r"1\d{10}")
GRADE_PATTERN = re.compile(r"(?:[1-6]年级|[一二三四五六]年级|初[一二三]|高[一二三])")
CHINESE_NAME_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,3}?")
COURSE_STAGE_TOKENS = ("春", "暑", "夏", "秋", "寒", "冬")
COURSE_STAGE_CHAR_SET = set("".join(COURSE_STAGE_TOKENS))
SEASON_LETTER_MAP = {"A": "寒", "B": "春", "C": "暑", "D": "秋"}
GRADE_ALIASES = {
    "1年级": "一年级",
    "2年级": "二年级",
    "3年级": "三年级",
    "4年级": "四年级",
    "5年级": "五年级",
    "6年级": "六年级",
}
GRADE_SEQUENCE = [
    "一年级",
    "二年级",
    "三年级",
    "四年级",
    "五年级",
    "六年级",
    "初一",
    "初二",
    "初三",
    "高一",
    "高二",
    "高三",
]
DEFAULT_PERSONAL_RESULT_COLOR = "#fff59d"
DEFAULT_PERSONAL_SAMPLE_VERSION = 2
DEFAULT_PERSONAL_SAMPLE_LINES = [
    "李萌萌，13789877876，五年级，英语集训A，物理燎原B",
    "李明轩，13677778888，四年级，暑秋数学燎原A，冬英语提升班",
]


class FieldDef:
    """单个字段定义"""

    def __init__(self, key: str, label: str, field_type: str = "text",
                 pattern: str = "", values: Optional[List[str]] = None,
                 aliases: Optional[Dict[str, str]] = None):
        self.key = key
        self.label = label
        self.type = field_type
        self.pattern = pattern
        self.values = values or []
        self.aliases = aliases or {}
        self._compiled: Optional[re.Pattern] = re.compile(pattern) if pattern else None

    def match(self, text: str) -> Optional[str]:
        """在文本中匹配此字段，返回原始匹配文本或 None"""
        if self._compiled:
            m = self._compiled.search(text)
            if m:
                return m.group(0)
        return None

    def expand_value(self, raw: str) -> str:
        """将匹配的原始文本展开为显示值（枚举字母→中文）"""
        if self.type == "enum" and self.aliases:
            expanded = []
            for c in raw:
                if c in self.aliases:
                    expanded.append(self.aliases[c])
                else:
                    expanded.append(c)
            return "".join(expanded)
        return raw


class FormatConfig:
    """
    解析一行格式配置，生成字段定义。

    配置格式：姓名，电话，性别（男/女/未知），年龄区间（18-25/26-35/36-45/45+）
    - 每个字段用中文逗号分隔
    - 括号内的内容是类型提示：
      - （ABCD）→ 枚举类型，字母可映射为汉字
      - （男/女/未知）→ 枚举类型，斜杠分隔的选项
      - （18-25/26-35）→ 枚举类型，区间选项
      - 其他 → 视为普通文本
    """

    FIELD_PATTERNS = {
        "电话": (r"1\d{10}", "text"),
        "手机": (r"1\d{10}", "text"),
        "年级": (r"(?:[1-6]年级|[一二三四五六]年级|初[一二三]|高[一二三])", "text"),
        "姓名": (r"[\u4e00-\u9fff]{2,6}", "text"),
        "客户姓名": (r"[\u4e00-\u9fff]{2,6}", "text"),
        "日期": (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date"),
        "首次接触日期": (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date"),
        "最近联系日期": (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date"),
        "下次跟进日期": (r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date"),
        "购车预算": (r"\d+(\.\d+)?", "number"),
        "预算总价": (r"\d+(\.\d+)?", "number"),
        "预算区间": (r"\d+[-/]\d+", "text"),  # range like "500-1000" is text, not number
        "驾照年限": (r"\d+年?", "number"),
        "面积需求": (r"\d+[-~]?\d*(㎡)?", "text"),  # "95-110" is text
        "年龄区间": (r"\d+[-/]\d+", "text"),  # "26-35" is text
    }

    DEFAULT_ALIASES = {"A": "寒", "B": "春", "C": "暑", "D": "秋"}

    def __init__(self, format_line: str):
        self.raw_line = format_line.strip()
        self.fields: List[FieldDef] = []
        self._parse(self.raw_line)

    def _parse(self, line: str) -> None:
        parts = [p.strip() for p in line.split("，") if p.strip()]
        for part in parts:
            field = self._parse_field(part)
            self.fields.append(field)

    def _parse_field(self, part: str) -> FieldDef:
        label = part
        field_type = "text"
        values: List[str] = []
        aliases: Dict[str, str] = {}

        # 检查是否有括号提示：季节（ABCD）或 性别（男/女/未知）
        paren_match = re.match(r"^(.+?)（(.+?)）$", part)
        if paren_match:
            label = paren_match.group(1)
            hint = paren_match.group(2)
            # 判断是枚举（全大写字母ABCD）还是斜杠分隔的选项
            if hint.isalpha() and hint.isupper():
                # 字母枚举：ABCD → A=寒, B=春, C=暑, D=秋
                field_type = "enum"
                values = list(hint)
                aliases = {c: self.DEFAULT_ALIASES.get(c, c) for c in hint}
            elif "/" in hint:
                # 斜杠分隔的选项：男/女/未知
                field_type = "enum"
                values = [v.strip() for v in hint.split("/") if v.strip()]
                aliases = {v: v for v in values}

        # Check label against FIELD_PATTERNS for type hints (e.g. date, number)
        if label in self.FIELD_PATTERNS:
            pattern, field_type_from_name = self.FIELD_PATTERNS[label]
            if not paren_match:  # only override if no parenthetical hint
                field_type = field_type_from_name
        else:
            pattern = ""

        # 生成 snake_case key
        key = self._label_to_key(label)

        # 枚举类型：构建匹配模式
        if field_type == "enum" and aliases:
            # 判断是单字符枚举（ABCD）还是多字符枚举（男/女/未知、18-25/26-35等）
            all_values = list(aliases.keys()) + list(aliases.values())
            if all(len(v) == 1 for v in all_values):
                # 单字符枚举：用字符类 [ABCD春夏秋冬寒]
                all_chars = set(all_values)
                pattern = "[" + "".join(sorted(all_chars)) + "]{1,4}"
            else:
                # 多字符枚举：用交替匹配 (?:男|女|未知)
                escaped = [re.escape(v) for v in values]
                pattern = "(?:" + "|".join(escaped) + ")"

        return FieldDef(key=key, label=label, field_type=field_type,
                        pattern=pattern, values=values, aliases=aliases)

    @staticmethod
    def _label_to_key(label: str) -> str:
        mapping = {
            "姓名": "name",
            "电话": "phone",
            "年级": "grade",
            "季节": "season",
            "科目": "subject",
            "班型": "class_type",
        }
        return mapping.get(label, label)

    def get_field_keys(self) -> List[str]:
        return [f.key for f in self.fields]

    def get_field_labels(self) -> List[str]:
        return [f.label for f in self.fields]

    def get_field_by_key(self, key: str) -> Optional[FieldDef]:
        for f in self.fields:
            if f.key == key:
                return f
        return None


# 全局配置实例（运行时加载）
_FORMAT_CONFIG: Optional[FormatConfig] = None


def get_format_config() -> FormatConfig:
    """获取全局格式配置，优先从文件加载，否则使用默认"""
    global _FORMAT_CONFIG
    if _FORMAT_CONFIG is not None:
        return _FORMAT_CONFIG
    config_path = Path(__file__).resolve().parent / "data" / "personal_data" / "format.txt"
    if config_path.exists():
        line = config_path.read_text(encoding="utf-8").strip()
        if line:
            _FORMAT_CONFIG = FormatConfig(line)
            return _FORMAT_CONFIG
    # 默认配置
    _FORMAT_CONFIG = FormatConfig("姓名，电话，年级，季节（ABCD），科目，班型")
    return _FORMAT_CONFIG


def reload_format_config() -> FormatConfig:
    """强制重新加载格式配置"""
    global _FORMAT_CONFIG
    _FORMAT_CONFIG = None
    return get_format_config()


def get_format_config_line() -> str:
    """获取当前格式配置的原始文本行"""
    config = get_format_config()
    return config.raw_line


def save_format_config(format_line: str) -> FormatConfig:
    """保存格式配置到文件并重新加载"""
    global _FORMAT_CONFIG
    config_path = Path(__file__).resolve().parent / "data" / "personal_data" / "format.txt"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(format_line.strip(), encoding="utf-8")
    _FORMAT_CONFIG = None
    return get_format_config()


def get_personal_data_format_example() -> str:
    """根据当前解析规则生成数据格式示例。修改解析规则时自动同步。"""
    example_parts = []
    example_parts.append("姓名")
    example_parts.append("电话")
    example_parts.append("年级")
    example_parts.append("季节")
    example_parts.append("科目")
    example_parts.append("班型")
    return "格式：" + "，".join(example_parts)


def _iso_now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _ensure_iso(value: Optional[str]) -> str:
    if not value:
        return _iso_now()
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def _parse_datetime(value: Optional[str]) -> datetime:
    text = _ensure_iso(value)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")


def _compact_text(raw_text: str) -> str:
    return re.sub(r"[，,;；、|/\\\s]+", "", raw_text or "")


def _expand_season_letters(text: str) -> str:
    """将季节字母简写展开为汉字，如 CD→暑秋，AB→寒春。

    只展开独立的季节字母序列（1-4个大写字母 A-D），
    不展开夹在中文之间的单个字母（如"提分A班"中的 A 不展开）。
    """
    # 匹配连续的季节字母序列（1-4个），但不展开后面紧跟中文字符的序列
    def _replace_match(m: re.Match) -> str:
        seq = m.group(0)
        # 检查后面是否紧跟中文字符（如果是，说明是"提分A班"这种，不展开）
        end_pos = m.end()
        if end_pos < len(text) and '\u4e00' <= text[end_pos] <= '\u9fff':
            return seq  # 保留原字母
        return "".join(SEASON_LETTER_MAP.get(c, c) for c in seq)

    # 匹配 1-4 个连续大写字母 ABCD
    return re.sub(r'[ABCD]{1,4}', _replace_match, text)


def _normalize_grade(value: str) -> str:
    return GRADE_ALIASES.get((value or "").strip(), (value or "").strip())


def academic_year_index(value: Optional[str]) -> int:
    dt = _parse_datetime(value)
    return dt.year if (dt.month, dt.day) >= (9, 1) else dt.year - 1


def compute_display_grade(recorded_grade: str, recorded_at: str, as_of: Optional[str] = None) -> str:
    grade = _normalize_grade(recorded_grade)
    if not grade:
        return ""

    plus_match = re.fullmatch(r"高三\+(\d+)", grade)
    steps = max(academic_year_index(as_of or recorded_at) - academic_year_index(recorded_at), 0)
    if plus_match:
        return f"高三+{int(plus_match.group(1)) + steps}"
    if grade not in GRADE_SEQUENCE:
        return grade

    target_index = GRADE_SEQUENCE.index(grade) + steps
    if target_index < len(GRADE_SEQUENCE):
        return GRADE_SEQUENCE[target_index]
    return f"高三+{target_index - (len(GRADE_SEQUENCE) - 1)}"


def parse_personal_record(raw_text: str, recorded_at: Optional[str] = None, record_type: str = "student_profile") -> Dict:
    """配置驱动的智能解析器。根据 FormatConfig 定义的字段自动提取数据。
    
    解析策略（支持跳过字段 + 混合格式）：
    1. 按中文逗号切分输入
    2. 第一轮：按位置匹配，但文本字段会检查是否更匹配后续枚举字段
    3. 第二轮：剩余未匹配的段，按类型特征智能分配
    4. 第三轮：剩余的文本段按顺序填入未匹配的文本字段
    5. 无逗号输入：回退到正则模式匹配
    """
    recorded_at = _ensure_iso(recorded_at)
    expanded_text = _expand_season_letters(raw_text)
    config = get_format_config()

    # 按中文逗号切分输入
    segments = [s.strip() for s in re.split(r'[，,]', expanded_text) if s.strip()]

    # 如果没有逗号分隔（如教育领域的连写格式），回退到正则模式匹配
    if len(segments) <= 1:
        return _parse_concatenated(raw_text, expanded_text, config, recorded_at, record_type)

    matched: Dict[str, str] = {}
    used: set = set()  # 已使用的段索引
    skipped_by_enum: set = set()  # 在第一轮因枚举值冲突而被跳过的文本字段key
    fields = config.fields

    # 收集所有枚举值，用于判断文本段是否更匹配枚举字段
    all_enum_values: set = set()
    for f in fields:
        if f.type == "enum":
            all_enum_values.update(f.values or [])
            all_enum_values.update((f.aliases or {}).values())

    # ── 第一轮：按位置匹配 ──
    for i, field_def in enumerate(fields):
        if i < len(segments):
            raw = segments[i]
            if field_def.type == "enum":
                # 枚举字段：值匹配 / 别名匹配 / 多字符组合匹配（如"春秋"、"寒春"）
                alias_vals = set((field_def.aliases or {}).values())
                if (raw in field_def.values
                        or raw in alias_vals
                        or (len(raw) > 1 and all(c in field_def.values or c in alias_vals for c in raw))):
                    matched[field_def.key] = field_def.expand_value(raw)
                    used.add(i)
                # 不匹配 → 不填充，留给后面的智能分配
            else:
                # 文本字段：如果该值明显匹配某个枚举字段，则跳过，留给第二轮
                if raw and raw not in all_enum_values:
                    matched[field_def.key] = raw
                    used.add(i)
                elif raw and raw in all_enum_values:
                    # 该文本字段因枚举值冲突被跳过
                    skipped_by_enum.add(field_def.key)

    # ── 第二轮：剩余段按类型特征智能分配 ──
    for i, seg in enumerate(segments):
        if i in used or not seg:
            continue

        assigned = False

        # 手机号特征：1开头11位数字
        if re.fullmatch(r"1\d{10}", seg):
            for f in fields:
                if f.key not in matched and f.key in ("phone", "手机", "电话"):
                    matched[f.key] = seg
                    used.add(i)
                    assigned = True
                    break

        if assigned:
            continue

        # 日期特征：YYYY-MM-DD 或 YYYY/MM/DD，优先 date-type 字段
        if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", seg):
            for f in fields:
                if f.key not in matched and f.type == "date":
                    matched[f.key] = seg
                    used.add(i)
                    assigned = True
                    break
            if not assigned:
                for f in fields:
                    if f.key not in matched and "日期" in f.label:
                        matched[f.key] = seg
                        used.add(i)
                        assigned = True
                        break

        if assigned:
            continue

        # 枚举值特征：检查是否匹配某个未填充的枚举字段的值
        for f in fields:
            if f.key not in matched and f.type == "enum":
                alias_vals = set((f.aliases or {}).values())
                if (seg in (f.values or [])
                        or seg in alias_vals
                        or (len(seg) > 1 and all(c in (f.values or []) or c in alias_vals for c in seg))):
                    matched[f.key] = f.expand_value(seg)
                    used.add(i)
                    assigned = True
                    break

        if assigned:
            continue

        # 数字特征：纯数字或小数，优先匹配数值类字段
        if re.fullmatch(r"\d+(\.\d+)?", seg):
            for f in fields:
                if f.key not in matched and f.type == "number":
                    matched[f.key] = seg
                    used.add(i)
                    assigned = True
                    break
            if not assigned:
                for f in fields:
                    if f.key not in matched and f.type == "text":
                        matched[f.key] = seg
                        used.add(i)
                        assigned = True
                        break

    # ── 第三轮：剩余文本段填入未匹配的文本字段 ──
    # 优先填入未被跳过的文本字段，再填入被跳过的
    available_text = [f for f in fields if f.key not in matched and f.type == "text" and f.key not in skipped_by_enum]
    deferred_text = [f for f in fields if f.key not in matched and f.type == "text" and f.key in skipped_by_enum]
    ordered_text_fields = available_text + deferred_text

    for i, seg in enumerate(segments):
        if i in used or not seg:
            continue
        for f in ordered_text_fields:
            if f.key not in matched:
                matched[f.key] = seg
                used.add(i)
                break

    # 确保所有字段都有值（空字符串）
    for f in fields:
        if f.key not in matched:
            matched[f.key] = ""

    # 提取常用字段（兼容旧格式）
    name = matched.get("name", matched.get("客户姓名", ""))
    phone = matched.get("phone", matched.get("手机", matched.get("电话", "")))
    grade = _normalize_grade(matched.get("grade", ""))

    now = _iso_now()
    return {
        "id": f"person_{uuid.uuid4().hex[:12]}",
        "record_type": record_type,
        "raw_text": raw_text.strip(),
        "name": name,
        "phone": phone,
        "recorded_grade": grade,
        "recorded_at": recorded_at,
        "courses": [],
        "dynamic_fields": matched,
        "created_at": now,
        "updated_at": now,
        "parse_status": "complete" if name else "partial",
    }


def _parse_concatenated(raw_text: str, expanded_text: str, config, recorded_at: str, record_type: str) -> Dict:
    """回退解析器：处理无逗号的连写格式（如教育领域的连写输入）。
    
    策略（针对 education 连写格式优化）：
    1. 提取手机号（11位数字，最明确的模式）
    2. 提取年级（X年级/初X/高X）
    3. 提取科目（已知科目列表匹配）
    4. 提取姓名（智能2/3字判断）
    5. 从剩余文本中提取季节（连续季节字符序列）
    6. 剩余归入 class_type
    """
    compact_text = _compact_text(expanded_text)
    matched: Dict[str, str] = {}
    remaining = compact_text

    # ── 第一轮：提取手机号 ──
    phone_match = re.search(r"1\d{10}", remaining)
    if phone_match:
        matched["phone"] = phone_match.group(0)
        remaining = remaining[:phone_match.start()] + remaining[phone_match.end():]

    # ── 第二轮：提取年级 ──
    grade_match = re.search(r"(?:[1-6]年级|[一二三四五六]年级|初[一二三]|高[一二三])", remaining)
    if grade_match:
        matched["grade"] = grade_match.group(0)
        remaining = remaining[:grade_match.start()] + remaining[grade_match.end():]

    # ── 第三轮：提取科目（已知科目列表，最长匹配优先）──
    if any(f.key == "subject" for f in config.fields):
        subject_match = SUBJECT_PATTERN.search(remaining)
        if subject_match:
            matched["subject"] = subject_match.group(0)
            remaining = remaining[:subject_match.start()] + remaining[subject_match.end():]

    # ── 第四轮：提取姓名（智能 2/3 字判断）──
    if remaining:
        name_3 = re.match(r'[\u4e00-\u9fff]{3}', remaining)
        name_2 = re.match(r'[\u4e00-\u9fff]{2}', remaining)
        chosen_name = ""
        _CLASS_TYPE_STARTERS = set("提思基精冲培辅训奥新强优")
        if name_3 and name_2:
            third_char = remaining[2]
            if third_char in _CLASS_TYPE_STARTERS:
                chosen_name = name_2.group(0)
            else:
                chosen_name = name_3.group(0)
        elif name_3:
            chosen_name = name_3.group(0)
        elif name_2:
            chosen_name = name_2.group(0)
        if chosen_name:
            matched["name"] = chosen_name
            remaining = remaining[len(chosen_name):]

    # ── 第五轮：提取季节（连续季节字符序列，1-4个）──
    if remaining and any(f.key == "season" for f in config.fields):
        season_match = re.match(r'[ABCD春夏秋冬寒]{1,4}', remaining)
        if season_match:
            matched["season"] = season_match.group(0)
            remaining = remaining[season_match.end():]

    # ── 第六轮：剩余文本归入 class_type ──
    for field_def in config.fields:
        if field_def.key not in matched and remaining.strip():
            matched[field_def.key] = remaining.strip()
            remaining = ""
            break

    # 确保所有字段都有值
    for f in config.fields:
        if f.key not in matched:
            matched[f.key] = ""

    name = matched.get("name", "")
    phone = matched.get("phone", matched.get("手机", matched.get("电话", "")))
    grade = _normalize_grade(matched.get("grade", ""))

    now = _iso_now()
    return {
        "id": f"person_{uuid.uuid4().hex[:12]}",
        "record_type": record_type,
        "raw_text": raw_text.strip(),
        "name": name,
        "phone": phone,
        "recorded_grade": grade,
        "recorded_at": recorded_at,
        "courses": [],
        "dynamic_fields": matched,
        "created_at": now,
        "updated_at": now,
        "parse_status": "complete" if name else "partial",
    }


@dataclass
class PersonalSearchResult:
    record: Dict
    score: float


class PersonalDataManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent / "data"
        self.data_dir = self.base_dir / "personal_data"
        self.records_path = self.data_dir / "records.json"
        self.config_path = self.data_dir / "config.json"
        self.imports_dir = self.data_dir / "imports"
        self._records_file_created = not self.records_path.exists()
        self._ensure_storage()
        self.records = self._load_json(self.records_path, [])
        self.config = self._load_json(self.config_path, {})
        self._ensure_config_defaults()
        if not self.config.get("defaults_seeded", False) and not self.records:
            self.records = self._build_default_records()
            self._save_records()
            self.config["defaults_seeded"] = True
            self.config["default_sample_version"] = DEFAULT_PERSONAL_SAMPLE_VERSION
            self._save_config()
        else:
            self._apply_default_sample_updates()
            if not self.config.get("display_mode_migrated", False):
                self.config["display_mode"] = "table"
                self.config["display_mode_migrated"] = True
            self._save_config()
        self.intelligence_manager = self._create_intelligence_manager()

    def _ensure_storage(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.imports_dir.mkdir(parents=True, exist_ok=True)
        if not self.records_path.exists():
            self.records_path.write_text("[]", encoding="utf-8")
        if not self.config_path.exists():
            self.config_path.write_text(
                json.dumps(
                    {
                        "enable_v204_generation": False,
                        "result_highlight_color": DEFAULT_PERSONAL_RESULT_COLOR,
                        "display_mode": "table",
                        "hotkey": "ctrl+shift+y",
                        "last_updated": _iso_now(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _build_default_records(self) -> List[Dict]:
        recorded_at = _iso_now()
        return [
            parse_personal_record(text, recorded_at=recorded_at, record_type="student_profile")
            for text in DEFAULT_PERSONAL_SAMPLE_LINES
        ]

    def _load_json(self, path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _ensure_config_defaults(self):
        defaults = {
            "enable_v204_generation": False,
            "result_highlight_color": DEFAULT_PERSONAL_RESULT_COLOR,
            "display_mode": "table",
            "hotkey": "ctrl+shift+y",
            "defaults_seeded": False,
            "default_sample_version": 0,
            "display_mode_migrated": False,
            "last_updated": _iso_now(),
        }
        config = self.config if isinstance(self.config, dict) else {}
        for key, value in defaults.items():
            config.setdefault(key, value)
        self.config = config

    def _apply_default_sample_updates(self):
        current_version = int(self.config.get("default_sample_version", 0) or 0)
        if current_version >= DEFAULT_PERSONAL_SAMPLE_VERSION:
            return

        if current_version < 2 and self.records:
            existing_raw = {_compact_text(record.get("raw_text", "")) for record in self.records}
            sample_text = DEFAULT_PERSONAL_SAMPLE_LINES[1]
            if _compact_text(sample_text) not in existing_raw:
                self.records.append(
                    parse_personal_record(sample_text, recorded_at=_iso_now(), record_type="student_profile")
                )
                self._save_records()

        self.config["default_sample_version"] = DEFAULT_PERSONAL_SAMPLE_VERSION

    def _save_records(self):
        self.records_path.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")

    def _save_config(self):
        self.config["last_updated"] = _iso_now()
        self.config_path.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _create_intelligence_manager(self):
        if IntelligenceManagerV204 is None:
            return None
        try:
            return IntelligenceManagerV204(enable_all_generators=True)
        except Exception:
            return None

    def get_v204_generation_enabled(self) -> bool:
        return bool(self.config.get("enable_v204_generation", False))

    def set_v204_generation_enabled(self, enabled: bool):
        self.config["enable_v204_generation"] = bool(enabled)
        self._save_config()

    def get_result_highlight_color(self) -> str:
        return (self.config.get("result_highlight_color") or DEFAULT_PERSONAL_RESULT_COLOR).strip() or DEFAULT_PERSONAL_RESULT_COLOR

    def set_result_highlight_color(self, color: str):
        self.config["result_highlight_color"] = (color or DEFAULT_PERSONAL_RESULT_COLOR).strip() or DEFAULT_PERSONAL_RESULT_COLOR
        self._save_config()

    def get_display_mode(self) -> str:
        value = (self.config.get("display_mode") or "card").strip().lower()
        return value if value in {"card", "table"} else "table"

    def set_display_mode(self, mode: str):
        value = (mode or "card").strip().lower()
        self.config["display_mode"] = value if value in {"card", "table"} else "table"
        self.config["display_mode_migrated"] = True
        self._save_config()

    def get_hotkey(self) -> str:
        return (self.config.get("hotkey") or "ctrl+shift+y").strip() or "ctrl+shift+y"

    def set_hotkey(self, hotkey: str):
        value = (hotkey or "").strip() or "ctrl+shift+y"
        self.config["hotkey"] = value
        self._save_config()

    def _ensure_customer_capacity(self, additional_count: int = 1):
        customer_limit = get_customer_limit()
        if customer_limit is None:
            return
        current_count = len(self.records)
        if current_count + max(additional_count, 0) > customer_limit:
            raise ValueError(f"公开版最多保存 {customer_limit} 条客户记录")

    def add_record_from_text(self, raw_text: str, recorded_at: Optional[str] = None, record_type: str = "student_profile") -> Optional[Dict]:
        text = (raw_text or "").strip()
        if not text:
            return None
        self._ensure_customer_capacity(1)
        record = parse_personal_record(text, recorded_at=recorded_at, record_type=record_type)
        self.records.append(record)
        self._save_records()
        return record

    def import_text_lines(self, lines: List[str], recorded_at: Optional[str] = None, record_type: str = "student_profile") -> List[Dict]:
        recorded_at = _ensure_iso(recorded_at)
        imported: List[Dict] = []
        importable_lines = [line for line in lines if line and line.strip()]
        self._ensure_customer_capacity(len(importable_lines))
        for line in importable_lines:
            text = (line or "").strip()
            if not text:
                continue
            record = parse_personal_record(text, recorded_at=recorded_at, record_type=record_type)
            self.records.append(record)
            imported.append(record)
        self._save_records()
        import_log_path = self.imports_dir / f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import_log_path.write_text(
            json.dumps(
                {
                    "recorded_at": recorded_at,
                    "record_type": record_type,
                    "count": len(imported),
                    "lines": importable_lines,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return imported

    def _decorate_record(self, record: Dict, as_of: Optional[str] = None) -> Dict:
        payload = dict(record)
        payload["display_grade"] = compute_display_grade(record.get("recorded_grade", ""), record.get("recorded_at", ""), as_of)
        return payload

    def get_all_records(self, as_of: Optional[str] = None) -> List[Dict]:
        return [self._decorate_record(record, as_of) for record in self.records]

    def update_record(self, record_id: str, **updates) -> bool:
        for record in self.records:
            if record.get("id") != record_id:
                continue
            for key in ["raw_text", "name", "phone", "recorded_grade", "recorded_at", "courses", "record_type", "parse_status"]:
                if key in updates:
                    record[key] = updates[key]
            record["updated_at"] = _iso_now()
            self._save_records()
            return True
        return False

    def delete_record(self, record_id: str) -> bool:
        before = len(self.records)
        self.records = [record for record in self.records if record.get("id") != record_id]
        if len(self.records) == before:
            return False
        self._save_records()
        return True

    def clear_all_records(self):
        self.records = []
        self.config["defaults_seeded"] = True
        self.config["default_sample_version"] = DEFAULT_PERSONAL_SAMPLE_VERSION
        self._save_config()
        self._save_records()

    def _search_blob(self, record: Dict, as_of: Optional[str] = None) -> str:
        """Config-driven search text generation."""
        config = get_format_config()
        parts = []
        dynamic = record.get("dynamic_fields", {})
        for field_def in config.fields:
            if field_def.key == "name":
                parts.append(record.get("name", ""))
            elif field_def.key == "phone":
                parts.append(record.get("phone", ""))
            else:
                # All other fields (including grade, subject, etc.) come from dynamic_fields
                parts.append(dynamic.get(field_def.key, ""))
        parts.append(record.get("raw_text", ""))
        return " ".join(part for part in parts if part)

    def _search_score(self, query: str, record: Dict, as_of: Optional[str] = None) -> float:
        """Config-driven search scoring."""
        config = get_format_config()
        query_norm = _compact_text(query).lower()
        if not query_norm:
            return 0.0

        score = 0.0
        dynamic = record.get("dynamic_fields", {})

        # Score each configured field
        for field_def in config.fields:
            if field_def.key == "name":
                name_val = _compact_text(record.get("name", "")).lower()
                if query_norm and query_norm in name_val:
                    score += 100
            elif field_def.key == "phone":
                phone_val = _compact_text(record.get("phone", "")).lower()
                if query_norm and query_norm == phone_val:
                    score += 95
                elif query_norm and query_norm in phone_val:
                    score += 80
            else:
                # All other fields from dynamic_fields
                val = _compact_text(dynamic.get(field_def.key, "")).lower()
                if query_norm and query_norm in val:
                    score += 60

        # Generic blob match as fallback
        blob_norm = _compact_text(self._search_blob(record, as_of)).lower()
        if query_norm and query_norm in blob_norm:
            score += 40
        return score

    def search_records(self, query: str, as_of: Optional[str] = None, top_k: int = 20) -> List[Dict]:
        ranked: List[PersonalSearchResult] = []
        for record in self.records:
            score = self._search_score(query, record, as_of)
            if score > 0:
                ranked.append(PersonalSearchResult(record=record, score=score))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return [self._decorate_record(item.record, as_of) for item in ranked[:top_k]]

    def generate_search_summary(self, query: str, records: List[Dict]) -> Dict:
        if not records:
            return {"summary": "", "source_type": "personal_structured", "confidence": 0.0}

        if not self.get_v204_generation_enabled() or self.intelligence_manager is None:
            names = "、".join(record.get("name", "") for record in records[:3] if record.get("name"))
            return {
                "summary": f"共匹配到 {len(records)} 条记录" + (f"，优先结果：{names}" if names else ""),
                "source_type": "personal_structured",
                "confidence": 0.0,
            }

        matched_samples = []
        for record in records[:3]:
            course_text = "；".join(
                f"{course.get('stage', '')}{course.get('subject', '')}{course.get('class_type', '')}" for course in record.get("courses", [])
            )
            matched_samples.append(
                {
                    "content": f"{record.get('name', '')} {record.get('phone', '')} {record.get('display_grade', '')} {course_text}".strip(),
                    "confidence": 0.8,
                    "source_type": "personal_structured",
                }
            )

        generated = self.intelligence_manager.generate_reply(
            query=query,
            matched_samples=matched_samples,
            generation_mode="hybrid",
            context_messages=None,
        ).get("generated_replies", [])
        if generated:
            best = generated[0]
            return {
                "summary": best.get("content", ""),
                "source_type": best.get("source_type", "personal_structured"),
                "confidence": best.get("confidence", 0.0),
            }

        return {"summary": f"共匹配到 {len(records)} 条记录", "source_type": "personal_structured", "confidence": 0.0}
