from __future__ import annotations

import os
import sys
from pathlib import Path

PUBLIC_SAMPLE_LIMIT = 50
PUBLIC_CUSTOMER_LIMIT = 50


def _get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _read_edition_marker() -> str:
    env_edition = os.environ.get("APP_EDITION", "").strip().lower()
    if env_edition in {"public", "private"}:
        return env_edition

    candidates = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.extend(
            [
                exe_dir / "app_edition.txt",
                exe_dir / "_internal" / "app_edition.txt",
                Path(getattr(sys, "_MEIPASS", "")) / "app_edition.txt",
                Path(getattr(sys, "_MEIPASS", "")) / "_internal" / "app_edition.txt",
            ]
        )
    candidates.append(_get_app_base_dir() / "app_edition.txt")
    candidates.append(_get_app_base_dir() / "_internal" / "app_edition.txt")

    for candidate in candidates:
        try:
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8").strip().lower()
                if text in {"public", "private"}:
                    return text
        except Exception:
            continue
    return "public"


def is_public_edition() -> bool:
    return _read_edition_marker() == "public"


def get_sample_limit() -> int | None:
    return PUBLIC_SAMPLE_LIMIT if is_public_edition() else None


def get_customer_limit() -> int | None:
    return PUBLIC_CUSTOMER_LIMIT if is_public_edition() else None
