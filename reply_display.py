"""Helpers for formatting and parsing candidate reply text."""

from __future__ import annotations

import re
from typing import Dict

HIGHLIGHT_COLOR_OPTIONS = (
    ("黄色高亮", "#fff59d"),
    ("浅黄高亮", "#fff9c4"),
    ("橙色高亮", "#ffe0b2"),
    ("绿色高亮", "#c8e6c9"),
    ("蓝色高亮", "#bbdefb"),
    ("无高亮", ""),
)

DEFAULT_SOURCE_HIGHLIGHT_COLOR = "#bbdefb"
DEFAULT_REPLY_HIGHLIGHT_COLOR = "#fff59d"
DEFAULT_HIGHLIGHT_COLOR = DEFAULT_REPLY_HIGHLIGHT_COLOR

MATCH_TYPE_LABELS = {
    "exact": "精准匹配",
    "contains": "包含匹配",
    "contains_query": "包含匹配",
    "contains_parent": "被包含匹配",
    "contained": "被包含匹配",
    "partial": "模糊匹配",
    "keyword": "关键词匹配",
    "similar": "相似匹配",
}

SOURCE_SEGMENT_SPLIT_RE = re.compile(r"\s*(?:——|--)\s*")

MATCH_LABEL_ALIASES = {
    "精准匹配": "精准匹配",
    "精确匹配": "精准匹配",
    "包含匹配": "包含匹配",
    "被包含匹配": "被包含匹配",
    "模糊匹配": "模糊匹配",
    "关键词匹配": "关键词匹配",
    "相似匹配": "相似匹配",
}


def normalize_line_breaks(text: str | None) -> str:
    """Normalize Windows/Mac newlines to ``\n`` without stripping internal blank lines."""
    if text is None:
        return ""
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def compact_preview_text(text: str | None, limit: int = 42) -> str:
    """Return a one-line preview suitable for table rows and list items."""
    normalized = normalize_line_breaks(text).replace("\n", " / ").strip()
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return normalized[: limit - 3].rstrip() + "..."


def format_candidate_block(candidate: Dict, index: int) -> str:
    """Render one candidate block with the compact layout used in the UI."""
    content = normalize_line_breaks(candidate.get("content", ""))
    return "\n".join(
        [
            format_candidate_header(candidate, index),
            "-----------",
            content,
            "===========",
        ]
    )


def _normalize_match_label(label: str | None) -> str | None:
    """Normalize a match label to the display wording used in the UI."""
    if label is None:
        return None

    normalized = normalize_line_breaks(label).strip()
    if not normalized:
        return None

    compact = normalized.replace(" ", "")
    for alias, canonical in MATCH_LABEL_ALIASES.items():
        if alias.replace(" ", "") == compact:
            return canonical

    if "精确匹配" in compact or "精准匹配" in compact:
        return "精准匹配"
    if "被包含匹配" in compact:
        return "被包含匹配"
    if "包含匹配" in compact:
        return "包含匹配"
    if "模糊匹配" in compact:
        return "模糊匹配"
    if "关键词匹配" in compact:
        return "关键词匹配"
    if "相似匹配" in compact:
        return "相似匹配"
    return None


def _format_confidence(confidence: float) -> str:
    return f"（置信{confidence:.0%}）"


def _source_display_parts(source: str | None, match_type: str | None = None) -> tuple[str, list[str], str | None]:
    """Split a quoted source into its text, extra qualifiers, and match label."""
    normalized = normalize_line_breaks(source).strip()
    if not normalized:
        return "", [], None

    quoted_text, suffix = split_quoted_source_text(normalized)
    if not quoted_text:
        return "", [], None

    segments = [segment for segment in SOURCE_SEGMENT_SPLIT_RE.split(suffix) if segment]
    extras = [segment for segment in segments if _normalize_match_label(segment) is None]

    match_label = MATCH_TYPE_LABELS.get(match_type or "")
    if not match_label:
        for segment in reversed(segments):
            match_label = _normalize_match_label(segment)
            if match_label:
                break

    return quoted_text, extras, match_label


def format_candidate_header(candidate: Dict, index: int) -> str:
    """Render the first line for a candidate block."""
    confidence = candidate.get("confidence", 0) or 0
    source = candidate.get("source", "")
    quoted_text, extras, match_label = _source_display_parts(source, candidate.get("match_type"))

    if quoted_text:
        parts = [f"【候选{index + 1}】 来源:\"{quoted_text}\""]
        for extra in extras:
            parts.append(f"——{extra}")
        if match_label:
            parts.append(f"——{match_label}")
        return "".join(parts) + _format_confidence(confidence)

    if source:
        return f"【候选{index + 1}】 来源:{source}{_format_confidence(confidence)}"

    return f"【候选{index + 1}】{_format_confidence(confidence)}"


def candidate_header_segments(candidate: Dict, index: int) -> list[tuple[str, bool]]:
    """Return header text segments and whether each segment should be highlighted."""
    confidence = candidate.get("confidence", 0) or 0
    source = candidate.get("source", "")
    quoted_text, extras, match_label = _source_display_parts(source, candidate.get("match_type"))

    if quoted_text:
        segments: list[tuple[str, bool]] = [(f"【候选{index + 1}】 来源:\"", False)]
        segments.append((quoted_text, True))
        segments.append(("\"", False))
        for extra in extras:
            segments.append((f"——{extra}", False))
        if match_label:
            segments.append((f"——{match_label}", False))
        segments.append((_format_confidence(confidence), False))
        return segments

    if source:
        return [(f"【候选{index + 1}】 来源:{source}{_format_confidence(confidence)}", False)]

    return [(f"【候选{index + 1}】{_format_confidence(confidence)}", False)]


def split_quoted_source_text(source: str | None) -> tuple[str, str]:
    """Split a source string like ``"您好" —— 精确匹配`` into match text and suffix."""
    normalized = normalize_line_breaks(source).strip()
    if len(normalized) >= 2 and normalized.startswith('"'):
        closing_quote = normalized.find('"', 1)
        if closing_quote > 1:
            return normalized[1:closing_quote], normalized[closing_quote + 1 :]
    return "", normalized


def sample_table_values(
    sample: Dict, index: int, reply_text: str | None = None
) -> tuple[str, str, str, str, str]:
    """Build compact values for the sample viewer table.

    Args:
        sample: The sample dict.
        index: Display row number (1-based shown in first column).
        reply_text: Specific reply to show. If None, shows replies[0] (legacy).
    """
    parent_preview = compact_preview_text(sample.get("parent_message", ""), 36)
    if reply_text is None:
        replies = sample.get("replies", [])
        reply_text = replies[0] if replies else ""
    reply_preview = compact_preview_text(reply_text, 52)
    scene = sample.get("scene_tag", "") or "无"
    created_at = sample.get("created_at", "")
    created_day = created_at[:10] if created_at else ""
    return (str(index + 1), parent_preview, reply_preview, scene, created_day)


def extract_reply_content(display_text: str) -> str:
    """Extract the editable reply body from a formatted candidate block."""
    text = normalize_line_breaks(display_text).strip("\n")
    lines = text.split("\n")

    try:
        content_start = next(i for i, line in enumerate(lines) if line.strip() == "-----------") + 1
    except StopIteration:
        return text[:-1] if text.endswith("\n") else text

    content_end = len(lines)
    for i in range(content_start, len(lines)):
        if lines[i].strip() == "===========":
            content_end = i
            break

    return "\n".join(lines[content_start:content_end])


def highlight_color_from_label(label: str) -> str:
    """Convert a preset label to the stored highlight color value."""
    for option_label, color in HIGHLIGHT_COLOR_OPTIONS:
        if option_label == label:
            return color
    return DEFAULT_HIGHLIGHT_COLOR


def highlight_label_from_color(color: str | None) -> str:
    """Convert a stored highlight color back to the preset label."""
    normalized = (color or "").strip().lower()
    for option_label, option_color in HIGHLIGHT_COLOR_OPTIONS:
        if option_color.lower() == normalized:
            return option_label
    if not normalized:
        return "无高亮"
    return "黄色高亮"
