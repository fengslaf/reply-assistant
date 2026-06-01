"""Public-friendly reply prompt helpers.

This module keeps the small parsing surface used by the desktop client and
tests, without exposing the private server implementation.
"""

from __future__ import annotations

from typing import Dict, List


def _strip_label_prefix(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("【") and "】" in value:
        value = value.split("】", 1)[1].strip()
    return value


def _extract_style_tag(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("（") and value.endswith("）"):
        return value[1:-1].strip()
    if value.startswith("(") and value.endswith(")"):
        return value[1:-1].strip()
    return value


def parse_llm_response(content: str, samples: List[str]) -> List[Dict[str, str]]:
    del samples
    lines = [(line or "").rstrip() for line in (content or "").splitlines()]
    candidates: List[Dict[str, str]] = []
    current_style = ""
    current_content: List[str] = []

    def flush() -> None:
        nonlocal current_style, current_content
        if not current_content:
            return
        candidates.append(
            {
                "content": "\n".join(current_content).strip(),
                "style_tag": current_style or "默认",
            }
        )
        current_style = ""
        current_content = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("【候选"):
            flush()
            header = _strip_label_prefix(line)
            style = header
            if "】" in line:
                style = line.split("】", 1)[1].strip()
            current_style = _extract_style_tag(style)
            continue

        if line.startswith("-----------") or line.startswith("==========="):
            continue

        current_content.append(line)

    flush()
    return candidates[:5]
