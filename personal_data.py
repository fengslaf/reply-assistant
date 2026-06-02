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

    配置格式：姓名，电话，年级，季节（ABCD），科目，班型
    - 每个字段用中文逗号分隔
    - 括号内的内容是类型提示：
      - （ABCD）→ 枚举类型，字母可映射为汉字
      - 其他 → 暂不处理，视为普通文本
    """

    FIELD_PATTERNS = {
        "电话": (r"1\d{10}", "text"),
        "年级": (r"(?:[1-6]年级|[一二三四五六]年级|初[一二三]|高[一二三])", "text"),
        "姓名": (r"[\u4e00-\u9fff]{2,6}", "text"),
        "科目": (None, "text"),  # 使用 SUBJECT_PATTERN 动态生成
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

        # 检查是否有括号提示：季节（ABCD）
        paren_match = re.match(r"^(.+?)（(.+?)）$", part)
        if paren_match:
            label = paren_match.group(1)
            hint = paren_match.group(2)
            # 判断是枚举（全大写字母）还是其他
            if hint.isalpha() and hint.isupper():
                field_type = "enum"
                values = list(hint)
                aliases = {c: self.DEFAULT_ALIASES.get(c, c) for c in hint}

        # 生成 snake_case key
        key = self._label_to_key(label)

        # 根据字段名选择正则模式
        pattern = ""
        if label in self.FIELD_PATTERNS:
            pattern, _ = self.FIELD_PATTERNS[label]
        if not pattern and label == "科目":
            pattern = "|".join(sorted((re.escape(s) for s in SUBJECTS), key=len, reverse=True))

        # 枚举类型：匹配一个或多个连续的枚举值字符（如"春秋"、"暑秋"、"CD"等）
        if field_type == "enum" and aliases:
            # 收集所有值的字符（中文+字母）+ 全部季节字符（确保冬等未配置的也能匹配）
            all_chars = set()
            for v in aliases.values():
                all_chars.update(v)
            all_chars.update(aliases.keys())  # 也包含字母缩写
            all_chars.update(COURSE_STAGE_TOKENS)  # 确保所有季节字都能匹配
            pattern = "[" + "".join(sorted(all_chars)) + "]{1,4}"

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
    """配置驱动的通用解析器。根据 FormatConfig 定义的字段自动提取数据。"""
    recorded_at = _ensure_iso(recorded_at)
    expanded_text = _expand_season_letters(raw_text)
    compact_text = _compact_text(expanded_text)
    config = get_format_config()

    # 按配置逐字段匹配（优先匹配有明确模式的字段，再匹配姓名）
    matched: Dict[str, str] = {}
    remaining = compact_text

    # 第一轮：匹配有明确模式的字段（电话、年级、科目、季节等）
    for field_def in config.fields:
        if field_def.pattern and field_def.key != "name":
            raw_value = field_def.match(remaining)
            if raw_value:
                matched[field_def.key] = field_def.expand_value(raw_value)
                remaining = remaining.replace(raw_value, "", 1)

    # 第二轮：匹配姓名（从剩余文本开头提取，姓名通常在最前面）
    # 姓名可能是2或3个汉字，需要判断边界
    # 启发式：班型通常以 提/思/基/精/冲/培 等字开头
    _CLASS_TYPE_STARTERS = set("提思基精冲培辅训奥新强优")
    for field_def in config.fields:
        if field_def.key == "name" and remaining:
            # 尝试3字名和2字名，选择更合理的分割
            name_3 = re.match(r'[\u4e00-\u9fff]{3}', remaining)
            name_2 = re.match(r'[\u4e00-\u9fff]{2}', remaining)
            chosen_name = ""
            if name_3 and name_2:
                # 第3个字是否像班型开头？
                third_char = remaining[2]
                if third_char in _CLASS_TYPE_STARTERS:
                    chosen_name = name_2.group(0)  # 2字名更合理
                else:
                    chosen_name = name_3.group(0)  # 3字名更合理
            elif name_3:
                chosen_name = name_3.group(0)
            elif name_2:
                chosen_name = name_2.group(0)
            if chosen_name:
                matched["name"] = chosen_name
                remaining = remaining[len(chosen_name):]

    # 第三轮：匹配无模式的字段（班型等，从剩余文本中提取）
    for field_def in config.fields:
        if not field_def.pattern and field_def.key not in matched:
            if remaining.strip():
                matched[field_def.key] = remaining.strip()
                remaining = ""

    # 处理特殊字段
    phone = matched.get("phone", "")
    grade = _normalize_grade(matched.get("grade", ""))
    name = matched.get("name", "")
    season = matched.get("season", "")
    subject = matched.get("subject", "")
    class_type = matched.get("class_type", "")

    # 如果没匹配到姓名，从剩余文本中提取
    if not name:
        name_match = CHINESE_NAME_PATTERN.search(remaining)
        name = name_match.group(0) if name_match else ""

    # 构建课程信息（兼容旧格式）
    courses = []
    if subject:
        courses.append({
            "subject": subject,
            "stage": season,
            "class_type": class_type,
            "raw_text": f"{season}{subject}{class_type}".strip(),
        })

    now = _iso_now()
    return {
        "id": f"person_{uuid.uuid4().hex[:12]}",
        "record_type": record_type,
        "raw_text": raw_text.strip(),
        "name": name,
        "phone": phone,
        "recorded_grade": grade,
        "recorded_at": recorded_at,
        "courses": courses,
        # 动态字段：存储所有配置中的字段值
        "dynamic_fields": {k: v for k, v in matched.items() if k not in ("name", "phone", "grade")},
        "created_at": now,
        "updated_at": now,
        "parse_status": "complete" if name and phone else "partial",
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
        """配置驱动的搜索文本生成。根据 FormatConfig 动态生成搜索 blob。"""
        config = get_format_config()
        parts = []
        for field_def in config.fields:
            if field_def.key == "name":
                parts.append(record.get("name", ""))
            elif field_def.key == "phone":
                parts.append(record.get("phone", ""))
            elif field_def.key == "grade":
                parts.append(record.get("recorded_grade", ""))
                parts.append(compute_display_grade(record.get("recorded_grade", ""), record.get("recorded_at", ""), as_of))
            elif field_def.key == "subject":
                for course in record.get("courses", []):
                    parts.append(course.get("subject", ""))
            elif field_def.key == "stage" or field_def.key == "season":
                for course in record.get("courses", []):
                    parts.append(course.get("stage", ""))
            elif field_def.key == "class_type":
                for course in record.get("courses", []):
                    parts.append(course.get("class_type", ""))
            else:
                # 动态字段
                dynamic = record.get("dynamic_fields", {})
                parts.append(dynamic.get(field_def.key, ""))
        parts.append(record.get("raw_text", ""))
        return " ".join(part for part in parts if part)

    def _search_score(self, query: str, record: Dict, as_of: Optional[str] = None) -> float:
        """配置驱动的搜索评分。根据 FormatConfig 动态评分。"""
        config = get_format_config()
        query_norm = _compact_text(query).lower()
        if not query_norm:
            return 0.0

        score = 0.0
        blob_norm = _compact_text(self._search_blob(record, as_of)).lower()

        # 按配置字段评分
        for field_def in config.fields:
            if field_def.key == "name":
                name_norm = _compact_text(record.get("name", "")).lower()
                if query_norm and query_norm in name_norm:
                    score += 100
            elif field_def.key == "phone":
                phone_norm = _compact_text(record.get("phone", "")).lower()
                if query_norm and query_norm == phone_norm:
                    score += 95
                elif query_norm and query_norm in phone_norm:
                    score += 80
            elif field_def.key == "grade":
                recorded_grade_norm = _compact_text(record.get("recorded_grade", "")).lower()
                display_grade_norm = _compact_text(
                    compute_display_grade(record.get("recorded_grade", ""), record.get("recorded_at", ""), as_of)
                ).lower()
                if query_norm and query_norm in recorded_grade_norm:
                    score += 70
                if query_norm and query_norm in display_grade_norm:
                    score += 68
            elif field_def.key == "subject":
                for course in record.get("courses", []):
                    if query_norm in _compact_text(course.get("subject", "")).lower():
                        score += 85
            elif field_def.key == "stage" or field_def.key == "season":
                for course in record.get("courses", []):
                    if query_norm in _compact_text(course.get("stage", "")).lower():
                        score += 74
            elif field_def.key == "class_type":
                for course in record.get("courses", []):
                    if query_norm in _compact_text(course.get("class_type", "")).lower():
                        score += 72
            else:
                # 动态字段
                dynamic = record.get("dynamic_fields", {})
                field_val = _compact_text(dynamic.get(field_def.key, "")).lower()
                if query_norm and query_norm in field_val:
                    score += 60

        # 通用 blob 匹配
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
