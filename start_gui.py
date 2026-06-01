#!/usr/bin/env python3
"""PC客户端启动脚本 - v1.2 托盘+快捷键版"""

import sys
import os
import threading
import gc
import json
import ctypes
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from gui_utils import (
    reset_ttkbootstrap_style, apply_window_icon, get_personal_icon_path,
    apply_native_ttk_theme,
    apply_plain_ttk_palette, fit_window_to_content, load_app_icon_image,
    GlobalHotkeyManager, hotkey_to_tk_sequence, hotkey_to_windows_registration,
    create_labeled_entry_row, restore_view_samples_focus,
    HelpWindow, SCENE_TAGS, STAGE_TAGS,
    HAS_TRAY, HAS_HOTKEY,
    Image, ImageTk, pystray,
    insert_candidate_display, sample_view_count_text,
    personal_record_count_text,
    COMMERCIAL_FEATURES_AVAILABLE,
    OnlineClient, OnlineAPIError,
    PermanentLicenseManager, get_machine_code,
    generate_device_id, get_device_name,
    get_app_base_dir, get_icon_path, get_tray_icon_path,
    VERSION_LABEL, PUBLIC_SAMPLE_LIMIT, PUBLIC_CUSTOMER_LIMIT,
    is_public_edition,
    DEFAULT_REPLY_HIGHLIGHT_COLOR, DEFAULT_SOURCE_HIGHLIGHT_COLOR,
    candidate_header_segments, HIGHLIGHT_COLOR_OPTIONS,
    extract_reply_content, highlight_color_from_label, highlight_label_from_color,
    normalize_line_breaks, sample_table_values,
    personal_record_table_values, format_personal_record_card,
    format_personal_courses, get_personal_tree_columns, get_personal_tree_headings,
)

from personal_data import PersonalDataManager

# ---------------------------------------------------------------------------
# Backward-compatibility re-exports
# ---------------------------------------------------------------------------
from reply_gui import SettingsWindow, FavoriteDialog, LoginWindow, LocalMainWindow, AccountMainWindow
from personal_gui import PersonalDataSettingsWindow, PersonalDataMainWindow

# ---------------------------------------------------------------------------
# Setup sys.path and environment
# ---------------------------------------------------------------------------
_root = get_app_base_dir()
sys.path.insert(0, str(_root))
os.environ['DATABASE_PATH'] = str(_root / 'data' / 'guest_data.db')
os.environ['VECTOR_STORE_PATH'] = str(_root / 'data' / 'guest_chroma')


HOME_ACCESS_MODES = {"free"} if is_public_edition() else {"free", "local_perpetual", "monthly", "yearly", "plus_monthly", "plus_yearly"}
HOME_STATE_FILE_NAME = "product_home_state.json"
HOME_FREE_SAMPLE_LIMIT = PUBLIC_SAMPLE_LIMIT
HOME_FREE_CUSTOMER_LIMIT = PUBLIC_CUSTOMER_LIMIT


def _home_state_path() -> Path:
    return get_app_base_dir() / "data" / HOME_STATE_FILE_NAME


def _load_home_state() -> Dict[str, str]:
    state: Dict[str, str] = {
        "reply_access_mode": "free",
        "personal_access_mode": "free",
        "display_name": "",
        "nickname": "",
        "server_status_text": "",
        "subscription_plan": "",
        "subscription_status": "",
        "subscription_ends_at": "",
        "device_bound_count": 0,
        "device_limit": 0,
        "sync_status": "",
        "sync_mode": "",
        "plan_type": "",
        "plan_name": "",
        "can_cloud_sync": False,
        "can_multi_device": False,
        "logged_in": False,
        "access_token": "",
        "refresh_token": "",
        "expires_at": "",
        "device_id": "",
        "device_name": "",
        "user_id": "",
        "reply_samples_server_revision": "",
        "personal_record_server_revision": "",
    }
    path = _home_state_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if key == "server_base_url" or value is None:
                        continue
                    state[key] = value
        except Exception:
            pass

    # Migrate old single access_mode to split fields
    old_mode = str(state.pop("access_mode", "")).strip().lower() if "access_mode" in state else ""
    if old_mode and old_mode not in {"", "free"}:
        state.setdefault("reply_access_mode", old_mode)
        state.setdefault("personal_access_mode", old_mode)

    reply_access_mode = str(state.get("reply_access_mode", "free")).strip().lower()
    if reply_access_mode not in HOME_ACCESS_MODES:
        reply_access_mode = "free"
    state["reply_access_mode"] = reply_access_mode

    personal_access_mode = str(state.get("personal_access_mode", "free")).strip().lower()
    if personal_access_mode not in HOME_ACCESS_MODES:
        personal_access_mode = "free"
    state["personal_access_mode"] = personal_access_mode

    if not (state.get("display_name") or "").strip() and (reply_access_mode != "free" or personal_access_mode != "free"):
        state["display_name"] = "张三"
    if not (state.get("nickname") or "").strip():
        state["nickname"] = state.get("display_name", "")

    return state


def _save_home_state(state: Dict[str, str]):
    path = _home_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {}
    for key, value in state.items():
        if key.startswith("_") or key == "server_base_url" or value is None:
            continue
        if isinstance(value, str):
            payload[key] = value.strip()
        else:
            payload[key] = value
    payload["reply_access_mode"] = (state.get("reply_access_mode") or "free").strip().lower()
    payload["personal_access_mode"] = (state.get("personal_access_mode") or "free").strip().lower()
    payload["display_name"] = (state.get("display_name") or "").strip()
    payload["nickname"] = (state.get("nickname") or "").strip()
    payload["last_updated"] = datetime.now().replace(microsecond=0).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_json_items(path: Path, list_key: Optional[str] = None) -> int:
    try:
        if not path.exists():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        if list_key is None:
            return len(payload) if isinstance(payload, list) else 0
        if isinstance(payload, dict):
            items = payload.get(list_key, [])
            return len(items) if isinstance(items, list) else 0
    except Exception:
        return 0
    return 0


def _load_home_metrics() -> Dict[str, int]:
    base_dir = get_app_base_dir() / "data"
    return {
        "reply_samples": _count_json_items(base_dir / "local_data.json", "samples"),
        "personal_records": _count_json_items(base_dir / "personal_data" / "records.json"),
    }


def _format_home_capacity(used: int, limit: int, unit: str) -> str:
    if used > limit:
        return f"{limit}+ / {limit} {unit}"
    return f"{used} / {limit} {unit}"


def _effective_access_mode(state: Dict[str, str]) -> str:
    """Return the best access_mode across reply and personal systems."""
    reply_mode = (state.get("reply_access_mode") or "free").strip().lower()
    personal_mode = (state.get("personal_access_mode") or "free").strip().lower()
    # Priority: plus_yearly/plus_monthly > yearly/monthly > local_perpetual > free
    for candidate in ("plus_yearly", "plus_monthly", "yearly", "monthly", "local_perpetual"):
        if reply_mode == candidate or personal_mode == candidate:
            return candidate
    return "free"


def _build_online_status_text(state: Dict[str, str]) -> str:
    if is_public_edition():
        return ""
    access_mode = _effective_access_mode(state)
    if access_mode == "local_perpetual":
        return "本地授权：已激活"
    has_online_session = _has_online_session(state)
    is_paid_online = _is_paid_subscription_plan(state.get("subscription_plan")) or access_mode in {"monthly", "yearly", "plus_monthly", "plus_yearly"}
    if not has_online_session and not is_paid_online:
        return ""

    parts = []
    server_status = (state.get("server_status_text") or "").strip()
    if server_status:
        parts.append(f"服务器：{server_status}")

    if is_paid_online:
        subscription_plan = (state.get("plan_name") or state.get("subscription_plan") or "").strip() or access_mode
        subscription_status = (state.get("subscription_status") or "").strip()
        if subscription_plan or subscription_status:
            if subscription_status:
                parts.append(f"订阅：{subscription_plan} / {subscription_status}")
            else:
                parts.append(f"订阅：{subscription_plan}")

        bound_count = state.get("device_bound_count")
        device_limit = state.get("device_limit")
        if bound_count is not None and device_limit is not None:
            parts.append(f"设备：{bound_count} / {device_limit}")

        sync_status = (state.get("sync_status") or "").strip()
        if sync_status:
            parts.append(f"云同步：{sync_status}")
        elif (state.get("sync_mode") or "").strip().lower() == "full":
            parts.append("云同步：已启用")
    else:
        parts.insert(0, "账号：免费版")
        sync_mode = (state.get("sync_mode") or "").strip().lower()
        if sync_mode == "upload_only":
            parts.append("云同步：仅上传备份")
        else:
            parts.append("云同步：可上传备份")

    return " · ".join(parts)


def _has_online_session(state: Dict[str, str]) -> bool:
    return bool((state.get("access_token") or "").strip())


def _is_paid_subscription_plan(plan: Optional[str]) -> bool:
    return (plan or "").strip().lower() in {"monthly", "yearly", "plus_monthly", "plus_yearly"}


def _sync_mode_for_state(state: Dict[str, str]) -> str:
    plan = (state.get("subscription_plan") or "").strip().lower()
    access_mode = _effective_access_mode(state)
    if _is_paid_subscription_plan(plan) or access_mode in {"monthly", "yearly", "plus_monthly", "plus_yearly"}:
        return "full"
    if _has_online_session(state):
        return "upload_only"
    return ""


def build_home_view_model(state: Dict[str, str], metrics: Dict[str, int], mode: str = "combined") -> Dict[str, object]:
    if is_public_edition():
        reply_samples = int(metrics.get("reply_samples", 0) or 0)
        personal_records = int(metrics.get("personal_records", 0) or 0)
        # 根据 mode 返回对应的 lines
        if mode == "reply":
            reply_lines = [
                "状态：本地免费版",
                f"样本：{_format_home_capacity(reply_samples, HOME_FREE_SAMPLE_LIMIT, '条')}",
                "云端同步：不可用",
            ]
            personal_lines = []
        elif mode == "personal":
            reply_lines = []
            personal_lines = [
                "状态：本地免费版",
                f"客户：{_format_home_capacity(personal_records, HOME_FREE_CUSTOMER_LIMIT, '人')}",
                "报课套餐：本地管理",
                "云端同步：不可用",
            ]
        else:
            reply_lines = [
                "状态：本地免费版",
                f"样本：{_format_home_capacity(reply_samples, HOME_FREE_SAMPLE_LIMIT, '条')}",
                "云端同步：不可用",
            ]
            personal_lines = [
                "状态：本地免费版",
                f"客户：{_format_home_capacity(personal_records, HOME_FREE_CUSTOMER_LIMIT, '人')}",
                "报课套餐：本地管理",
                "云端同步：不可用",
            ]
        return {
            "headline": "欢迎回来 · 公开版",
            "status_text": "👤 当前：本地免费版",
            "top_primary_text": "本地模式",
            "top_secondary_text": "",
            "show_secondary": False,
            "reply_lines": reply_lines,
            "personal_lines": personal_lines,
            "banner": None,
            "footer_buttons": ["帮助", "关于"],
            "footer_note": "📌 公开版完全免费，不含付费功能。\n🌐 官网：openpaw.top",
            "online_status_text": None,
        }

    reply_mode = (state.get("reply_access_mode") or "free").strip().lower()
    personal_mode = (state.get("personal_access_mode") or "free").strip().lower()
    display_name = (state.get("display_name") or "").strip() or "张三"
    reply_samples = int(metrics.get("reply_samples", 0) or 0)
    personal_records = int(metrics.get("personal_records", 0) or 0)

    # Effective mode for page-level display depends on view mode
    if mode == "reply":
        access_mode = reply_mode
    elif mode == "personal":
        access_mode = personal_mode
    else:  # combined — use best across both
        access_mode = _effective_access_mode(state)

    is_free = access_mode == "free"
    is_local = access_mode == "local_perpetual"
    is_paid_online = access_mode in {"monthly", "yearly", "plus_monthly", "plus_yearly"}
    is_free_online = is_free and _has_online_session(state) and not is_paid_online

    if is_free and not is_free_online:
        # 根据 mode 显示对应的定价
        if mode == "reply":
            headline = "升级回复助手专业版"
            banner = {
                "title": "✨ 回复助手专业版",
                "bullets": [
                    "• 月卡 ¥9.9（不含AI生成）",
                    "• 年卡 ¥79（不含AI生成）",
                    "• Plus月卡 ¥19.9（含500次AI生成）",
                    "• Plus年卡 ¥179（含500次AI生成）",
                ],
                "primary": "立即升级",
                "show_data_dir": True,
            }
        elif mode == "personal":
            headline = "升级客户数据专业版"
            banner = {
                "title": "✨ 客户数据专业版",
                "bullets": [
                    "• 月卡 ¥9.9",
                    "• 年卡 ¥79",
                ],
                "primary": "立即升级",
                "show_data_dir": True,
            }
        else:  # combined
            headline = "一次订阅，解锁对应工具"
            banner = {
                "title": "✨ 升级专业版（每个工具独立购买）",
                "bullets": [
                    "• 回复助手：月卡¥9.9 / 年卡¥79",
                    "• 回复助手Plus：月卡¥19.9 / 年卡¥179（含AI生成）",
                    "• 客户数据：月卡¥9.9 / 年卡¥79",
                ],
                "primary": "立即升级",
                "show_data_dir": True,
            }
        status_text = "👤 当前：未登录（使用本地免费版）"
        top_primary_text = "登录"
        top_secondary_text = "升级 ▼"
        show_secondary = True
        footer_buttons = ["帮助", "关于"]
        footer_note = ""
    elif is_free_online:
        headline = f"欢迎回来，{display_name} · 免费版（云备份）"
        status_text = "👤 已登录 · 免费额度可用"
        top_primary_text = "退出登录"
        top_secondary_text = "升级 ▼"
        show_secondary = True
        footer_buttons = ["管理订阅", "帮助", "设置"]
        footer_note = "📌 当前账号保持免费额度，仅支持云端上传备份，不支持跨设备恢复。"
        banner = None
    elif is_local:
        headline = f"欢迎回来，{display_name} · 专业版（永久）"
        status_text = "👤 已激活 · 本地授权"
        top_primary_text = "退出授权"
        top_secondary_text = ""
        show_secondary = False
        footer_buttons = ["授权管理", "帮助", "设置"]
        footer_note = "📌 本地授权文件已启用，可离线运行，不支持云备份与多设备登录。"
        banner = None
    else:
        plan_label = "月卡" if access_mode == "monthly" else "年卡"
        headline = f"欢迎回来，{display_name} · {plan_label}"
        status_text = "👤 已登录 · 套餐有效"
        top_primary_text = "退出登录"
        top_secondary_text = ""
        show_secondary = False
        footer_buttons = ["管理订阅", "帮助", "设置"]
        footer_note = "📌 您已解锁全部功能。如需团队协作，可升级至团队版。"
        banner = None

    # --- Per-card lines: each card uses its own access_mode independently ---
    _CARD_SYNC_FREE = "云端备份：可上传" if is_free_online else "云端同步：需要订阅"

    if reply_mode == "local_perpetual":
        reply_lines = [
            "状态：完整版（已解锁）",
            f"样本：∞ / {reply_samples} 条",
            "云端同步：不可用",
        ]
    elif reply_mode in {"monthly", "yearly"}:
        reply_lines = [
            "状态：完整版（已解锁）",
            f"样本：∞ / {reply_samples} 条",
            "云端同步：已启用",
        ]
    else:  # free
        reply_lines = [
            "状态：本地免费版",
            f"样本：{_format_home_capacity(reply_samples, HOME_FREE_SAMPLE_LIMIT, '条')}",
            _CARD_SYNC_FREE,
        ]

    if personal_mode == "local_perpetual":
        personal_lines = [
            "状态：完整版（已解锁）",
            f"客户：{personal_records}人",
            "报名套餐：本地授权",
            "云端同步：不可用",
        ]
    elif personal_mode in {"monthly", "yearly"}:
        personal_lines = [
            "状态：完整版（已解锁）",
            f"客户：{personal_records}人",
            "报名套餐：管理",
            "云端同步：已启用",
        ]
    else:  # free
        personal_lines = [
            "状态：本地免费版",
            f"客户：{_format_home_capacity(personal_records, HOME_FREE_CUSTOMER_LIMIT, '人')}",
            "报名套餐：未启用",
            _CARD_SYNC_FREE,
        ]

    online_status_text = _build_online_status_text(state)

    return {
        "headline": headline,
        "status_text": status_text,
        "top_primary_text": top_primary_text,
        "top_secondary_text": top_secondary_text,
        "show_secondary": show_secondary,
        "reply_lines": reply_lines if mode != "personal" else [],
        "personal_lines": personal_lines if mode != "reply" else [],
        "banner": banner,
        "footer_buttons": footer_buttons,
        "footer_note": footer_note,
        "online_status_text": online_status_text,
    }


class ProductHomeWindow:
    """产品首页，总入口。"""

    _MODE_TITLES = {
        "combined": "快捷助手",
        "reply": "快捷回复助手",
        "personal": "客户数据管理系统",
    }

    def __init__(self, root, mode: str = "combined"):
        reset_ttkbootstrap_style()
        self.root = root
        self.mode = mode
        self.root.title(self._MODE_TITLES.get(mode, "快捷助手"))
        self.root.resizable(True, True)
        _icon = get_personal_icon_path() if mode == "personal" else None
        apply_window_icon(self.root, icon_path=_icon)
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        self._state = _load_home_state()
        self._online_client = None if is_public_edition() else OnlineClient()
        self._license_manager = None if is_public_edition() else PermanentLicenseManager(base_dir=get_app_base_dir() / "data")
        self._local_license_payload = None
        self._online_refresh_inflight = False
        self._online_status_callback = self._apply_online_status
        self.selection = None
        self._upgrade_button = None
        self._sync_preview_manager = None
        self._sync_personal_data_manager = None
        self._is_quitting = False
        self._bootstrap_local_permanent_state()
        self._setup_ui()
        self._sync_online_snapshot_from_store()
        self._refresh_online_status_async()
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        fit_window_to_content(self.root, default_size=(1040, 760))
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _setup_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        model = build_home_view_model(self._state, _load_home_metrics(), self.mode)
        # Mode-appropriate access_mode for button logic
        if self.mode == "reply":
            access_mode = (self._state.get("reply_access_mode") or "free").strip().lower()
        elif self.mode == "personal":
            access_mode = (self._state.get("personal_access_mode") or "free").strip().lower()
        else:  # combined — show upgrade if EITHER is free
            _rm = (self._state.get("reply_access_mode") or "free").strip().lower()
            _pm = (self._state.get("personal_access_mode") or "free").strip().lower()
            if _rm == "free" or _pm == "free":
                access_mode = "free"
            else:
                access_mode = _effective_access_mode(self._state)

        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)

        title_row = ttk.Frame(outer)
        title_row.pack(fill=tk.X)
        ttk.Label(title_row, text=self._MODE_TITLES.get(self.mode, "快捷助手"), font=("Microsoft YaHei", 18)).pack(side=tk.LEFT)
        ttk.Label(title_row, text=f"{VERSION_LABEL.lower()}", foreground="gray").pack(side=tk.RIGHT)

        if is_public_edition():
            ttk.Label(outer, text="🌐 官网：openpaw.top", foreground="#2980b9", cursor="hand2").pack(anchor=tk.W, pady=(0, 6))

        ttk.Label(outer, text=model["headline"], font=("Microsoft YaHei", 11)).pack(anchor=tk.W, pady=(4, 10))

        status_row = ttk.Frame(outer)
        status_row.pack(fill=tk.X, pady=(0, 16))
        status_row.columnconfigure(0, weight=1)
        ttk.Label(status_row, text=model["status_text"], foreground="#5a8f5a").grid(row=0, column=0, sticky="w")

        actions = ttk.Frame(status_row)
        actions.grid(row=0, column=1, sticky="e")

        if is_public_edition():
            ttk.Label(actions, text=model["top_primary_text"], foreground="#666").pack(side=tk.LEFT)
            self._upgrade_button = None
        elif access_mode == "free":
            ttk.Button(actions, text=model["top_primary_text"], width=8, command=self._open_online_login_dialog).pack(side=tk.LEFT, padx=(0, 8))
            self._upgrade_button = ttk.Button(actions, text=model["top_secondary_text"], width=14, command=self._show_upgrade_menu)
            self._upgrade_button.pack(side=tk.LEFT)
        elif access_mode == "local_perpetual":
            ttk.Button(actions, text=model["top_primary_text"], width=10, command=self._clear_local_permanent_license).pack(side=tk.LEFT)
            self._upgrade_button = None
        else:
            ttk.Button(actions, text=model["top_primary_text"], width=10, command=self._logout_and_clear_online).pack(side=tk.LEFT)
            self._upgrade_button = None

        online_status_text = model.get("online_status_text")
        if online_status_text:
            ttk.Label(outer, text=online_status_text, foreground="#4f6f8f").pack(anchor="w", pady=(0, 10))

        if self.mode == "combined":
            # Combined mode: two cards side by side, filling width
            modules_frame = ttk.Frame(outer)
            modules_frame.pack(fill=tk.BOTH, expand=True)
            modules_frame.columnconfigure(0, weight=1)
            modules_frame.columnconfigure(1, weight=1)
            modules_frame.rowconfigure(0, weight=1)

            reply_card = ttk.LabelFrame(modules_frame, text="💬 回复助手", padding=16)
            reply_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            reply_card.columnconfigure(0, weight=1)
            self._build_home_card(
                reply_card,
                lines=model["reply_lines"],
                button_text="启动",
                command=lambda: self._select("reply_assistant"),
            )

            personal_card = ttk.LabelFrame(modules_frame, text="📋 客户数据系统", padding=16)
            personal_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            personal_card.columnconfigure(0, weight=1)
            self._build_home_card(
                personal_card,
                lines=model["personal_lines"],
                button_text="启动",
                command=lambda: self._select("personal_data"),
            )
        else:
            # Single mode: centered card with fixed max width
            center_wrapper = ttk.Frame(outer)
            center_wrapper.pack(fill=tk.BOTH, expand=True)
            center_wrapper.columnconfigure(0, weight=1)
            center_wrapper.columnconfigure(1, weight=1)
            center_wrapper.rowconfigure(0, weight=1)

            if self.mode == "reply":
                card = ttk.LabelFrame(center_wrapper, text="💬 回复助手", padding=16)
                card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=120)
                card.columnconfigure(0, weight=1)
                self._build_home_card(
                    card,
                    lines=model["reply_lines"],
                    button_text="启动",
                    command=lambda: self._select("reply_assistant"),
                )
            else:
                card = ttk.LabelFrame(center_wrapper, text="📋 客户数据系统", padding=16)
                card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=120)
                card.columnconfigure(0, weight=1)
                self._build_home_card(
                    card,
                    lines=model["personal_lines"],
                    button_text="启动",
                    command=lambda: self._select("personal_data"),
                )

        if model["banner"]:
            banner = tk.Frame(outer, bg="white", bd=1, relief=tk.SOLID)
            banner.pack(fill=tk.X, pady=(16, 12))
            ttk.Label(banner, text=model["banner"]["title"], font=("Microsoft YaHei", 11)).pack(anchor=tk.W, padx=14, pady=(12, 4))
            for bullet in model["banner"]["bullets"]:
                ttk.Label(banner, text=bullet).pack(anchor=tk.W, padx=22, pady=1)
            banner_buttons = ttk.Frame(banner)
            banner_buttons.pack(anchor=tk.W, padx=14, pady=(10, 12))
            ttk.Button(
                banner_buttons,
                text=model["banner"]["primary"],
                command=self._show_activation_dialog,
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                banner_buttons,
                text=model["banner"]["secondary"],
                command=self._show_membership_purchase_dialog,
            ).pack(side=tk.LEFT)

        if model["footer_note"]:
            ttk.Label(outer, text=model["footer_note"], foreground="gray").pack(anchor=tk.W, pady=(2, 10))

        footer = ttk.Frame(outer)
        footer.pack(fill=tk.X, pady=(0, 4))

        if model["banner"] and model["banner"].get("show_data_dir"):
            ttk.Label(
                footer,
                text=f"📁 数据目录: {get_app_base_dir() / 'data'}",
                foreground="gray",
            ).pack(side=tk.LEFT)
        else:
            ttk.Label(footer, text=" ", foreground="gray").pack(side=tk.LEFT)

        footer_actions = ttk.Frame(footer)
        footer_actions.pack(side=tk.RIGHT)
        for index, label in enumerate(model["footer_buttons"]):
            if label in {"管理订阅", "授权管理"}:
                command = self._show_management
            elif label == "帮助":
                command = self._show_help
            elif label == "设置":
                command = self._show_home_settings
            else:
                command = self._show_about
            ttk.Button(
                footer_actions,
                text=label,
                width=10 if label != "关于" else 8,
                command=command,
            ).pack(side=tk.LEFT, padx=(0, 6 if index < len(model["footer_buttons"]) - 1 else 0))

        self._refresh_window_geometry()

    def _build_home_card(self, card, lines, button_text, command):
        display_lines = list(lines)
        while len(display_lines) < 4:
            display_lines.append("")
        for row, line in enumerate(display_lines):
            ttk.Label(
                card,
                text=line or " ",
                foreground=("gray" if row == 0 else "black"),
                anchor="center",
            ).grid(row=row, column=0, sticky="ew", pady=(0, 4))
        ttk.Frame(card).grid(row=len(display_lines), column=0, sticky="nsew", pady=(4, 10))
        btn_frame = ttk.Frame(card)
        btn_frame.grid(row=len(display_lines) + 1, column=0, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        ttk.Button(btn_frame, text=button_text, command=command, width=16).grid(row=0, column=0)

    def _sync_online_snapshot_from_store(self):
        if is_public_edition() or self._online_client is None:
            return
        try:
            snapshot = self._online_client.load_session()
        except Exception:
            snapshot = {}
        if snapshot:
            self._merge_online_snapshot(snapshot, persist=False)

    def _bootstrap_local_permanent_state(self):
        if is_public_edition():
            self._local_license_payload = None
            _rm = (self._state.get("reply_access_mode") or "").strip().lower()
            _pm = (self._state.get("personal_access_mode") or "").strip().lower()
            if _rm == "local_perpetual" or _pm == "local_perpetual":
                self._state["reply_access_mode"] = "free"
                self._state["personal_access_mode"] = "free"
                for key in (
                    "license_id",
                    "license_machine_code",
                    "license_activated_at",
                    "license_expires_at",
                    "license_plan",
                ):
                    self._state[key] = ""
                _save_home_state(self._state)
            return

        try:
            status = self._license_manager.get_status(machine_code=get_machine_code())
        except Exception:
            status = None
        self._local_license_payload = status.payload if status and status.active else None
        if not self._local_license_payload:
            _rm = (self._state.get("reply_access_mode") or "").strip().lower()
            _pm = (self._state.get("personal_access_mode") or "").strip().lower()
            if _rm == "local_perpetual" or _pm == "local_perpetual":
                self._state["reply_access_mode"] = "free"
                self._state["personal_access_mode"] = "free"
                for key in (
                    "license_id",
                    "license_machine_code",
                    "license_activated_at",
                    "license_expires_at",
                    "license_plan",
                ):
                    self._state[key] = ""
                _save_home_state(self._state)
            return

        license_payload = dict(self._local_license_payload)
        display_name = (self._state.get("display_name") or self._state.get("nickname") or "张三").strip() or "张三"
        self._state.update(
            {
                "reply_access_mode": "local_perpetual",
                "personal_access_mode": "local_perpetual",
                "display_name": display_name,
                "nickname": display_name,
                "server_status_text": "已激活",
                "subscription_plan": "local_perpetual",
                "subscription_status": "active",
                "subscription_ends_at": license_payload.get("expires_at") or "",
                "plan_type": "permanent",
                "plan_name": "本地永久版",
                "can_cloud_sync": False,
                "can_multi_device": False,
                "logged_in": False,
                "sync_mode": "",
                "sync_status": "不可用",
            }
        )
        self._state["license_id"] = license_payload.get("license_id") or ""
        self._state["license_machine_code"] = license_payload.get("machine_code") or ""
        self._state["license_activated_at"] = license_payload.get("activated_at") or ""
        self._state["license_expires_at"] = license_payload.get("expires_at") or ""
        self._state["license_plan"] = license_payload.get("plan") or "permanent"
        _save_home_state(self._state)

    def _merge_online_snapshot(self, snapshot: Dict[str, object], persist: bool = True):
        if is_public_edition():
            self._state["reply_access_mode"] = "free"
            self._state["personal_access_mode"] = "free"
            self._state["sync_mode"] = ""
            self._state["server_status_text"] = ""
            self._state["subscription_plan"] = ""
            self._state["subscription_status"] = ""
            self._state["subscription_ends_at"] = ""
            self._state["can_cloud_sync"] = False
            self._state["can_multi_device"] = False
            self._state["logged_in"] = False
            if persist:
                _save_home_state(self._state)
                self._setup_ui()
            return
        if not snapshot:
            return

        for key in (
            "server_status_text",
            "subscription_plan",
            "subscription_status",
            "subscription_ends_at",
            "device_bound_count",
            "device_limit",
            "sync_status",
            "sync_mode",
            "plan_type",
            "plan_name",
            "can_cloud_sync",
            "can_multi_device",
            "logged_in",
            "access_token",
            "refresh_token",
            "expires_at",
            "device_id",
            "device_name",
            "user_id",
            "reply_samples_server_revision",
            "personal_record_server_revision",
        ):
            if key in snapshot and snapshot.get(key) is not None:
                self._state[key] = snapshot.get(key)

        if snapshot.get("username") and not self._state.get("display_name"):
            self._state["display_name"] = snapshot.get("username")
            self._state["nickname"] = snapshot.get("username")

        subscription_plan = str(snapshot.get("subscription_plan") or snapshot.get("plan_type") or "").strip().lower()
        if self._local_license_payload:
            self._state["reply_access_mode"] = "local_perpetual"
            self._state["personal_access_mode"] = "local_perpetual"
            self._state["sync_mode"] = ""
        elif subscription_plan in {"monthly", "yearly"}:
            self._state["reply_access_mode"] = subscription_plan
            self._state["personal_access_mode"] = subscription_plan
            self._state["sync_mode"] = "full"
        elif subscription_plan in {"plus_monthly", "plus_yearly"}:
            self._state["reply_access_mode"] = subscription_plan
            if self._state.get("personal_access_mode") not in {"monthly", "yearly", "plus_monthly", "plus_yearly"}:
                self._state["personal_access_mode"] = "free"
            self._state["sync_mode"] = "full"
        elif self._state.get("access_token"):
            self._state["reply_access_mode"] = "free"
            self._state["personal_access_mode"] = "free"
            self._state["sync_mode"] = "upload_only"
        else:
            self._state["sync_mode"] = ""

        if persist:
            _save_home_state(self._state)
            self._setup_ui()

    def _refresh_online_status_async(self):
        if is_public_edition():
            return
        if self._online_refresh_inflight:
            return
        if self._local_license_payload:
            return
        access_mode = _effective_access_mode(self._state)
        if access_mode not in {"monthly", "yearly", "plus_monthly", "plus_yearly"} and not self._online_client.has_session():
            return

        self._online_refresh_inflight = True

        def worker():
            try:
                payload = self._online_client.update_home_summary()
                snapshot = self._online_client.load_session()
                if payload:
                    snapshot = dict(snapshot)
                    snapshot.setdefault("server_home_status", payload)
                    snapshot.setdefault("server_status_text", "已连接")
                try:
                    self.root.after(0, lambda snapshot=snapshot: self._apply_online_status(snapshot))
                except tk.TclError:
                    return
            except Exception as exc:
                try:
                    self.root.after(0, lambda error=exc: self._apply_online_status_error(error))
                except tk.TclError:
                    return
            finally:
                self._online_refresh_inflight = False

        threading.Thread(target=worker, daemon=True).start()

    def _apply_online_status(self, snapshot: Dict[str, object]):
        if snapshot:
            self._merge_online_snapshot(snapshot, persist=True)

    def _apply_online_status_error(self, error):
        if isinstance(error, OnlineAPIError):
            self._state["server_status_text"] = error.message
        else:
            self._state["server_status_text"] = "离线"
        self._setup_ui()

    def _get_preview_manager_for_sync(self):
        if self._sync_preview_manager is None:
            from preview_mode import PreviewModeManager

            self._sync_preview_manager = PreviewModeManager()
        return self._sync_preview_manager

    def _get_personal_data_manager_for_sync(self):
        if self._sync_personal_data_manager is None:
            self._sync_personal_data_manager = PersonalDataManager(base_dir=get_app_base_dir() / "data")
        return self._sync_personal_data_manager

    def _build_sync_payloads(self) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        session = self._online_client.load_session()

        try:
            preview_manager = self._get_preview_manager_for_sync()
            samples = preview_manager.get_all_samples() if preview_manager else []
        except Exception:
            samples = []
        if samples:
            payloads.append(
                {
                    "data_type": "reply_samples",
                    "schema_version": 1,
                    "sync_mode": "full",
                    "client_revision": session.get("reply_samples_server_revision") or "",
                    "items": [
                        {
                            "id": sample.get("id") or f"reply-sample-{index + 1}",
                            "operation": "create",
                            "payload": sample,
                        }
                        for index, sample in enumerate(samples)
                    ],
                }
            )

        try:
            personal_manager = self._get_personal_data_manager_for_sync()
            records = personal_manager.get_all_records() if personal_manager else []
        except Exception:
            records = []
        if records:
            payloads.append(
                {
                    "data_type": "personal_record",
                    "schema_version": 1,
                    "sync_mode": "full",
                    "client_revision": session.get("personal_record_server_revision") or "",
                    "items": [
                        {
                            "id": record.get("id") or f"personal-record-{index + 1}",
                            "operation": "create",
                            "payload": record,
                        }
                        for index, record in enumerate(records)
                    ],
                }
            )

        return payloads

    def _remember_sync_revision(self, data_type: str, server_revision: str):
        if not server_revision:
            return
        snapshot = self._online_client.load_session()
        if data_type == "reply_samples":
            snapshot["reply_samples_server_revision"] = server_revision
        elif data_type == "personal_record":
            snapshot["personal_record_server_revision"] = server_revision
        self._online_client.save_session(snapshot)

    def _upload_cloud_backup(self, result_label, refresh_callback=None):
        payloads = self._build_sync_payloads()
        if not payloads:
            result_label.config(text="当前没有可上传的数据", foreground="gray")
            return

        result_label.config(text="正在上传云端备份...", foreground="orange")

        def worker():
            try:
                details = []
                for payload in payloads:
                    response = self._online_client.sync_upload(payload)
                    self._remember_sync_revision(payload["data_type"], response.get("server_revision") or "")
                    accepted_count = response.get("accepted_count")
                    if accepted_count is None:
                        accepted_count = len(payload.get("items", []))
                    details.append(f"{payload['data_type']} × {accepted_count}")

                message = "上传完成"
                if details:
                    message = f"上传完成（{'；'.join(details)}）"

                def finish_success():
                    result_label.config(text=message, foreground="green")
                    if refresh_callback:
                        refresh_callback()

                try:
                    self.root.after(0, finish_success)
                except tk.TclError:
                    return
            except Exception as exc:
                try:
                    self.root.after(0, lambda error=exc: result_label.config(text=str(error), foreground="red"))
                except tk.TclError:
                    return

        threading.Thread(target=worker, daemon=True).start()

    def _open_online_login_dialog(self):
        if is_public_edition():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("在线登录 / 注册")
        apply_window_icon(dialog)
        apply_native_ttk_theme(dialog)
        apply_plain_ttk_palette(dialog)

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        username_var = tk.StringVar(value=self._state.get("display_name") or "")
        password_var = tk.StringVar(value="")
        email_var = tk.StringVar(value="")

        for label_text, var, show in [
            ("用户名 *", username_var, ""),
            ("密码 *", password_var, "*"),
            ("邮箱", email_var, ""),
        ]:
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=5)
            ttk.Label(row, text=label_text, width=14).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=38, show=show).pack(side=tk.LEFT, fill=tk.X, expand=True)
        result_label = ttk.Label(body, text="", foreground="gray")
        result_label.pack(anchor=tk.W, pady=(0, 8))

        button_row = ttk.Frame(body)
        button_row.pack(fill=tk.X)

        def run_action(action: str):
            username = (username_var.get() or "").strip()
            password = password_var.get()
            email = (email_var.get() or "").strip() or None
            device_name = get_device_name()
            if not username or not password:
                result_label.config(text="请填写用户名和密码", foreground="red")
                return

            result_label.config(text="正在处理...", foreground="orange")

            def worker():
                try:
                    if action == "register":
                        payload = self._online_client.register(
                            username=username,
                            password=password,
                            email=email,
                            device_id=self._state.get("device_id") or generate_device_id(),
                            device_name=device_name,
                        )
                    else:
                        payload = self._online_client.login(
                            username=username,
                            password=password,
                            device_id=self._state.get("device_id") or generate_device_id(),
                            device_name=device_name,
                        )
                    payload["device_name"] = device_name
                    payload["device_id"] = self._state.get("device_id") or generate_device_id()
                    if email:
                        payload["email"] = email
                    payload.setdefault("subscription_plan", payload.get("subscription_plan") or "free")
                    try:
                        self.root.after(0, lambda payload=payload: finish_success(payload))
                    except tk.TclError:
                        return
                except Exception as exc:
                    try:
                        self.root.after(0, lambda error=exc: result_label.config(text=str(error), foreground="red"))
                    except tk.TclError:
                        return

            threading.Thread(target=worker, daemon=True).start()

        def finish_success(payload: Dict[str, object]):
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except tk.TclError:
                pass
            self._after_online_login(payload)

        ttk.Button(button_row, text="登录并保存", command=lambda: run_action("login")).pack(side=tk.LEFT)
        ttk.Button(button_row, text="注册账号", command=lambda: run_action("register")).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=(8, 0))

        dialog.transient(self.root)
        dialog.grab_set()
        fit_window_to_content(dialog, default_size=(460, 300))

    def _after_online_login(self, payload: Dict[str, object]):
        if is_public_edition():
            return
        subscription_plan = str(payload.get("subscription_plan") or "free").strip().lower()
        is_paid_plan = subscription_plan in {"monthly", "yearly"}
        self._state["reply_access_mode"] = subscription_plan if is_paid_plan else "free"
        self._state["personal_access_mode"] = subscription_plan if is_paid_plan else "free"
        self._state["server_status_text"] = "已连接"
        self._state["subscription_plan"] = subscription_plan if subscription_plan else ("monthly" if is_paid_plan else "free")
        subscription_status = str(payload.get("subscription_status") or "").strip()
        if not subscription_status and payload.get("trial_ends_at"):
            subscription_status = "trial"
        self._state["subscription_status"] = subscription_status or ("active" if is_paid_plan else "free")
        self._state["subscription_ends_at"] = payload.get("subscription_ends_at") or ""
        self._state["device_id"] = payload.get("device_id") or self._state.get("device_id") or generate_device_id()
        self._state["device_name"] = payload.get("device_name") or self._state.get("device_name") or get_device_name()
        self._state["access_token"] = payload.get("access_token") or ""
        self._state["refresh_token"] = payload.get("refresh_token") or ""
        self._state["expires_at"] = payload.get("expires_at") or ""
        self._state["user_id"] = payload.get("user_id") or ""
        self._state["sync_mode"] = "full" if is_paid_plan else "upload_only"
        self._state["sync_status"] = "已启用" if is_paid_plan else "仅上传备份"
        if not self._state.get("display_name"):
            self._state["display_name"] = payload.get("username") or "张三"
        if not self._state.get("nickname"):
            self._state["nickname"] = self._state["display_name"]
        _save_home_state(self._state)
        self._setup_ui()
        self._refresh_online_status_async()

    def _logout_and_clear_online(self):
        if is_public_edition() or self._online_client is None:
            return
        try:
            self._online_client.clear_session()
        except Exception:
            pass
        for key in (
            "server_status_text",
            "subscription_plan",
            "subscription_status",
            "subscription_ends_at",
            "device_bound_count",
            "device_limit",
            "sync_status",
            "sync_mode",
            "plan_type",
            "plan_name",
            "can_cloud_sync",
            "can_multi_device",
            "logged_in",
            "access_token",
            "refresh_token",
            "expires_at",
            "device_id",
            "device_name",
            "user_id",
            "reply_samples_server_revision",
            "personal_record_server_revision",
        ):
            self._state[key] = "" if isinstance(self._state.get(key), str) else 0
        self._set_access_mode("free")

    def _clear_local_permanent_license(self):
        if is_public_edition() or self._license_manager is None:
            return
        try:
            self._license_manager.clear_license()
        except Exception:
            pass
        self._local_license_payload = None
        for key in (
            "license_id",
            "license_machine_code",
            "license_activated_at",
            "license_expires_at",
            "license_plan",
        ):
            self._state[key] = ""
        self._set_access_mode("free")

    def _refresh_window_geometry(self):
        fit_window_to_content(self.root, default_size=(1040, 760))

    def _set_access_mode(self, mode: str, system: str = "both"):
        """Set access mode for the specified system(s).

        Args:
            mode: The access mode value (e.g. "free", "monthly", "yearly", "local_perpetual").
            system: Which system to update - "reply", "personal", or "both" (default).
        """
        if is_public_edition():
            mode = "free"
        mode = (mode or "free").strip().lower()
        if mode not in HOME_ACCESS_MODES:
            mode = "free"
        if mode == "free":
            self._state["display_name"] = ""
            self._state["nickname"] = ""
        else:
            self._state["display_name"] = self._state.get("display_name") or "张三"
            self._state["nickname"] = self._state.get("nickname") or self._state["display_name"]
        if system in ("reply", "both"):
            self._state["reply_access_mode"] = mode
        if system in ("personal", "both"):
            self._state["personal_access_mode"] = mode
        _save_home_state(self._state)
        self._setup_ui()

    def _login_preview(self):
        self._state["display_name"] = self._state.get("display_name") or "张三"
        self._state["nickname"] = self._state["display_name"]
        self._set_access_mode("monthly")

    def _logout_to_free(self):
        self._set_access_mode("free")

    def _show_upgrade_menu(self):
        if is_public_edition():
            return
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="开通会员（月卡/年卡）", command=self._show_membership_purchase_dialog)
        menu.add_command(label="输入激活码（本地永久版）", command=self._show_activation_dialog)
        menu.add_command(label="会员状态", command=self._show_membership_status_dialog)
        try:
            if self._upgrade_button is not None:
                x = self._upgrade_button.winfo_rootx()
                y = self._upgrade_button.winfo_rooty() + self._upgrade_button.winfo_height()
            else:
                x = self.root.winfo_rootx() + 120
                y = self.root.winfo_rooty() + 120
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _show_membership_purchase_dialog(self):
        if is_public_edition():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("开通会员")
        apply_window_icon(dialog)
        apply_native_ttk_theme(dialog)
        apply_plain_ttk_palette(dialog)

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        # 根据 mode 显示不同的标题和选项
        if self.mode == "reply":
            ttk.Label(body, text="开通回复助手专业版", font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(body, text="选择套餐并选择支付方式。Plus包含500次/月AI生成。", foreground="gray").pack(anchor=tk.W, pady=(4, 10))
        elif self.mode == "personal":
            ttk.Label(body, text="开通客户数据专业版", font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(body, text="选择套餐并选择支付方式。", foreground="gray").pack(anchor=tk.W, pady=(4, 10))
        else:
            ttk.Label(body, text="开通专业版", font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
            ttk.Label(body, text="每个工具独立购买，选择对应的套餐。", foreground="gray").pack(anchor=tk.W, pady=(4, 10))

        plan_var = tk.StringVar(value="yearly")
        payment_method_var = tk.StringVar(value="wechat")
        order_info_var = tk.StringVar(value="请选择套餐后点击创建订单。")

        plan_frame = ttk.LabelFrame(body, text="套餐")
        plan_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 根据 mode 显示不同的套餐选项
        if self.mode == "reply":
            # 回复助手：月卡/年卡/Plus月卡/Plus年卡
            plans = [
                ("月卡 ¥9.9/月（不含AI）", "monthly", "基础功能"),
                ("年卡 ¥79/年（不含AI）", "yearly", "基础功能，更划算"),
                ("Plus月卡 ¥19.9/月（含AI）", "plus_monthly", "含500次AI生成/月"),
                ("Plus年卡 ¥179/年（含AI）", "plus_yearly", "含500次AI生成/月，最划算"),
            ]
        elif self.mode == "personal":
            # 客户数据：月卡/年卡（无Plus）
            plans = [
                ("月卡 ¥9.9/月", "monthly", "适合短期使用"),
                ("年卡 ¥79/年（推荐）", "yearly", "适合长期使用"),
            ]
        else:
            # combined：显示所有选项
            plans = [
                ("回复助手月卡 ¥9.9/月", "reply_monthly", "基础功能"),
                ("回复助手年卡 ¥79/年", "reply_yearly", "基础功能"),
                ("回复助手Plus月卡 ¥19.9/月", "reply_plus_monthly", "含AI生成"),
                ("回复助手Plus年卡 ¥179/年", "reply_plus_yearly", "含AI生成"),
                ("客户数据月卡 ¥9.9/月", "personal_monthly", "基础功能"),
                ("客户数据年卡 ¥79/年", "personal_yearly", "基础功能"),
            ]
        
        for label, value, hint in plans:
            row = ttk.Frame(plan_frame)
            row.pack(fill=tk.X, padx=8, pady=3)
            ttk.Radiobutton(row, text=label, variable=plan_var, value=value).pack(side=tk.LEFT)
            ttk.Label(row, text=hint, foreground="gray").pack(side=tk.LEFT, padx=(8, 0))

        payment_frame = ttk.LabelFrame(body, text="支付方式")
        payment_frame.pack(fill=tk.X, pady=(0, 8))
        for label, value in [("微信支付", "wechat"), ("支付宝", "alipay")]:
            ttk.Radiobutton(payment_frame, text=label, variable=payment_method_var, value=value).pack(anchor=tk.W, padx=8, pady=2)

        ttk.Label(body, textvariable=order_info_var, foreground="gray", wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 8))

        button_row = ttk.Frame(body)
        button_row.pack(fill=tk.X)

        def create_order():
            plan = plan_var.get().strip()
            payment_method = payment_method_var.get().strip()
            order_info_var.set("正在创建订单...")

            def worker():
                try:
                    data = self._online_client.create_payment_order(
                        plan=plan,
                        payment_method=payment_method,
                        payment_info={
                            "client_version": VERSION_LABEL.lower(),
                            "source": "home_purchase_dialog",
                        },
                    )

                    def finish():
                        order_no = data.get("order_no") or data.get("order_id") or "—"
                        payment_params = data.get("payment_params") or {}
                        message = f"订单已创建：{order_no}"
                        if payment_params:
                            message += f"；支付参数：{json.dumps(payment_params, ensure_ascii=False)}"
                        order_info_var.set(message)

                    self.root.after(0, finish)
                except Exception as exc:
                    try:
                        self.root.after(0, lambda error=exc: order_info_var.set(f"创建订单失败：{error}"))
                    except tk.TclError:
                        return

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(button_row, text="创建订单", command=create_order).pack(side=tk.LEFT)
        ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=(8, 0))

        dialog.transient(self.root)
        dialog.grab_set()
        fit_window_to_content(dialog, default_size=(560, 360))

    def _show_activation_dialog(self):
        if is_public_edition():
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("输入激活码")
        apply_window_icon(dialog)
        apply_native_ttk_theme(dialog)
        apply_plain_ttk_palette(dialog)

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        ttk.Label(body, text="输入激活码", font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(body, text="本地永久版使用机器码 + 激活码完成本机授权。", foreground="gray").pack(anchor=tk.W, pady=(4, 10))

        machine_code = get_machine_code()
        machine_code_var = tk.StringVar(value=machine_code)
        activation_code_var = tk.StringVar(value="")
        result_var = tk.StringVar(value="请输入管理员提供的激活码。")

        machine_row = ttk.Frame(body)
        machine_row.pack(fill=tk.X, pady=4)
        ttk.Label(machine_row, text="机器码", width=12).pack(side=tk.LEFT)
        machine_entry = ttk.Entry(machine_row, textvariable=machine_code_var, width=42, state="readonly")
        machine_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        activation_row = ttk.Frame(body)
        activation_row.pack(fill=tk.X, pady=4)
        ttk.Label(activation_row, text="激活码", width=12).pack(side=tk.LEFT)
        activation_entry = ttk.Entry(activation_row, textvariable=activation_code_var, width=42)
        activation_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(body, textvariable=result_var, foreground="gray", wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 8))

        button_row = ttk.Frame(body)
        button_row.pack(fill=tk.X)

        def copy_machine_code():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(machine_code_var.get().strip())
                result_var.set("机器码已复制到剪贴板。")
            except Exception as exc:
                result_var.set(f"复制失败：{exc}")

        def activate():
            activation_code = activation_code_var.get().strip()
            if not activation_code:
                result_var.set("请先输入激活码。")
                return
            result_var.set("正在验证激活码...")
            try:
                payload = self._license_manager.activate(activation_code, machine_code=machine_code)
                self._local_license_payload = dict(payload)
                self._bootstrap_local_permanent_state()
                result_var.set("激活成功，已保存本机授权。")
                try:
                    dialog.destroy()
                except Exception:
                    pass
                self._setup_ui()
            except Exception as exc:
                result_var.set(f"激活失败：{exc}")

        ttk.Button(button_row, text="复制机器码", command=copy_machine_code).pack(side=tk.LEFT)
        ttk.Button(button_row, text="激活", command=activate).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=(8, 0))

        dialog.transient(self.root)
        dialog.grab_set()
        fit_window_to_content(dialog, default_size=(560, 320))

    def _show_membership_status_dialog(self):
        if is_public_edition():
            return
        self._show_management()

    def _show_help(self):
        HelpWindow(self.root)

    def _show_management(self):
        if is_public_edition():
            return
        # Use effective access_mode for management view
        if self.mode == "reply":
            mode = (self._state.get("reply_access_mode") or "free").strip().lower()
        elif self.mode == "personal":
            mode = (self._state.get("personal_access_mode") or "free").strip().lower()
        else:
            mode = _effective_access_mode(self._state)
        is_paid_online = mode in {"monthly", "yearly", "plus_monthly", "plus_yearly"}
        dialog = tk.Toplevel(self.root)
        dialog.title("授权管理" if mode == "local_perpetual" else "管理订阅")
        apply_window_icon(dialog)
        apply_native_ttk_theme(dialog)
        apply_plain_ttk_palette(dialog)

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        title_text = "本地永久版授权管理" if mode == "local_perpetual" else ("在线订阅中心" if is_paid_online else "在线备份中心")
        ttk.Label(body, text=title_text, font=("Microsoft YaHei", 12, "bold")).pack(anchor=tk.W)

        summary_var = tk.StringVar(
            value="本地永久版通过本机授权文件离线可用，不支持云备份与多设备登录。" if mode == "local_perpetual" else ("当前账号可进行完整云同步与微信绑定。" if is_paid_online else "当前账号仅支持上传云端备份。")
        )
        ttk.Label(body, textvariable=summary_var, foreground="gray").pack(anchor=tk.W, pady=(4, 10))

        fields: Dict[str, tk.StringVar] = {}

        def add_field(label_text: str, key: str, default: str = ""):
            row = ttk.Frame(body)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label_text, width=12).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=default)
            ttk.Label(row, textvariable=value_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            fields[key] = value_var

        if mode == "local_perpetual":
            license_payload = self._local_license_payload or {}
            add_field("机器码", "device_id", license_payload.get("machine_code") or get_machine_code())
            add_field("授权状态", "status", "已激活")
            add_field("激活时间", "activated_at", license_payload.get("activated_at") or "—")
            add_field("授权计划", "plan", license_payload.get("plan") or "permanent")
            add_field("云同步", "sync", "不可用")
            add_field("容量", "quota", "本地容量全开")

            note = ttk.Label(
                body,
                text="本地永久版通过机器码 + 激活码完成本机授权，激活后可离线使用，不支持云备份与多设备登录。",
                foreground="gray",
                wraplength=480,
                justify=tk.LEFT,
            )
            note.pack(anchor=tk.W, pady=(6, 10))

            button_row = ttk.Frame(body)
            button_row.pack(fill=tk.X, pady=(2, 0))

            def copy_machine_id():
                value = fields["device_id"].get().strip()
                if not value:
                    return
                try:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(value)
                    messagebox.showinfo("已复制", "机器码已复制到剪贴板", parent=dialog)
                except Exception as exc:
                    messagebox.showerror("错误", f"复制失败: {exc}", parent=dialog)

            ttk.Button(button_row, text="复制机器码", command=copy_machine_id).pack(side=tk.LEFT)
            ttk.Button(button_row, text="输入激活码", command=lambda: self._show_activation_dialog()).pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=(8, 0))
        else:
            online_sync_mode = _sync_mode_for_state(self._state)
            add_field("账号", "username", self._state.get("display_name") or self._state.get("nickname") or "未登录")
            add_field("套餐", "plan", self._state.get("plan_name") or ("免费版" if mode == "free" else self._state.get("subscription_plan") or mode))
            add_field("状态", "subscription_status", self._state.get("subscription_status") or "unknown")
            add_field("到期时间", "ends_at", self._state.get("subscription_ends_at") or "—")
            add_field(
                "设备",
                "device_count",
                f"{self._state.get('device_bound_count', 0)} / {self._state.get('device_limit', 0)}",
            )
            add_field("云同步", "sync", self._state.get("sync_status") or "未启用")
            add_field("服务器状态", "server_status", self._state.get("server_status_text") or "离线")
            add_field(
                "云同步模式",
                "sync_mode",
                "完整同步" if online_sync_mode == "full" else "仅上传备份" if online_sync_mode == "upload_only" else "未启用",
            )

            result_label = ttk.Label(body, text="", foreground="gray")
            result_label.pack(anchor=tk.W, pady=(6, 8))

            def render_from_state():
                fields["username"].set(self._state.get("display_name") or self._state.get("nickname") or "未登录")
                fields["plan"].set(self._state.get("plan_name") or ("免费版" if mode == "free" else self._state.get("subscription_plan") or mode))
                fields["subscription_status"].set(self._state.get("subscription_status") or "unknown")
                fields["ends_at"].set(self._state.get("subscription_ends_at") or "—")
                fields["device_count"].set(
                    f"{self._state.get('device_bound_count', 0)} / {self._state.get('device_limit', 0)}"
                )
                fields["sync"].set(self._state.get("sync_status") or "未启用")
                fields["server_status"].set(self._state.get("server_status_text") or "离线")
                fields["sync_mode"].set(
                    "完整同步"
                    if (self._state.get("sync_mode") or "").strip().lower() == "full"
                    else "仅上传备份"
                    if (self._state.get("sync_mode") or "").strip().lower() == "upload_only"
                    else "未启用"
                )
                summary_var.set(self._build_online_status_text(self._state) or "在线状态正常")

            sync_frame = ttk.LabelFrame(body, text="云同步")
            sync_frame.pack(fill=tk.X, pady=(4, 8))

            sync_note = ttk.Label(
                sync_frame,
                text="当前账号仅支持上传云端备份，不支持跨设备恢复。" if not is_paid_online else "当前账号可进行完整云同步。",
                foreground="gray",
                wraplength=500,
                justify=tk.LEFT,
            )
            sync_note.pack(anchor=tk.W, padx=8, pady=(6, 4))

            sync_button_row = ttk.Frame(sync_frame)
            sync_button_row.pack(fill=tk.X, padx=8, pady=(0, 8))

            def upload_backup():
                self._upload_cloud_backup(result_label, refresh_callback=render_from_state)

            ttk.Button(sync_button_row, text="上传备份", command=upload_backup).pack(side=tk.LEFT)

            wechat_frame = ttk.LabelFrame(body, text="微信绑定")
            wechat_frame.pack(fill=tk.X, pady=(4, 8))

            wechat_status_var = tk.StringVar(value="未查询")
            wechat_openid_var = tk.StringVar(value="-")
            wechat_time_var = tk.StringVar(value="-")
            wechat_code_var = tk.StringVar(value="-")
            wechat_hint_var = tk.StringVar(value="点击获取验证码后，在公众号发送绑定码。")

            for label_text, value_var in [
                ("绑定状态", wechat_status_var),
                ("OpenID", wechat_openid_var),
                ("绑定时间", wechat_time_var),
                ("验证码", wechat_code_var),
            ]:
                row = ttk.Frame(wechat_frame)
                row.pack(fill=tk.X, padx=8, pady=2)
                ttk.Label(row, text=label_text, width=10).pack(side=tk.LEFT)
                ttk.Label(row, textvariable=value_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

            ttk.Label(
                wechat_frame,
                textvariable=wechat_hint_var,
                foreground="gray",
                wraplength=500,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=8, pady=(2, 6))

            wechat_button_row = ttk.Frame(wechat_frame)
            wechat_button_row.pack(fill=tk.X, padx=8, pady=(0, 8))

            def refresh_wechat_status():
                result_label.config(text="正在查询微信绑定状态...", foreground="orange")

                def worker():
                    try:
                        data = self._online_client.get_wechat_status()

                        def finish():
                            bound = bool(data.get("bound"))
                            wechat_status_var.set("已绑定" if bound else "未绑定")
                            wechat_openid_var.set(data.get("openid") or "-")
                            wechat_time_var.set(data.get("bound_at") or "-")
                            wechat_code_var.set("-")
                            wechat_hint_var.set("已绑定微信，可直接发送消息；未绑定时请先获取验证码。")
                            result_label.config(text="微信状态已更新", foreground="green")

                        self.root.after(0, finish)
                    except Exception as exc:
                        try:
                            self.root.after(0, lambda error=exc: result_label.config(text=str(error), foreground="red"))
                        except tk.TclError:
                            return

                threading.Thread(target=worker, daemon=True).start()

            def request_wechat_code():
                result_label.config(text="正在获取微信验证码...", foreground="orange")

                def worker():
                    try:
                        data = self._online_client.get_wechat_bind_code()

                        def finish():
                            wechat_status_var.set("未绑定")
                            wechat_code_var.set(data.get("bind_code") or "-")
                            wechat_hint_var.set(data.get("instructions") or "请在公众号发送绑定码完成绑定。")
                            result_label.config(text="验证码已生成", foreground="green")

                        self.root.after(0, finish)
                    except Exception as exc:
                        try:
                            self.root.after(0, lambda error=exc: result_label.config(text=str(error), foreground="red"))
                        except tk.TclError:
                            return

                threading.Thread(target=worker, daemon=True).start()

            def unbind_wechat():
                if not messagebox.askyesno("确认解绑", "确定要解除微信绑定吗？", parent=dialog):
                    return
                result_label.config(text="正在解绑微信...", foreground="orange")

                def worker():
                    try:
                        self._online_client.unbind_wechat()

                        def finish():
                            wechat_status_var.set("未绑定")
                            wechat_openid_var.set("-")
                            wechat_time_var.set("-")
                            wechat_code_var.set("-")
                            wechat_hint_var.set("微信已解除绑定。")
                            result_label.config(text="微信解绑成功", foreground="green")

                        self.root.after(0, finish)
                    except Exception as exc:
                        try:
                            self.root.after(0, lambda error=exc: result_label.config(text=str(error), foreground="red"))
                        except tk.TclError:
                            return

                threading.Thread(target=worker, daemon=True).start()

            ttk.Button(wechat_button_row, text="刷新状态", command=refresh_wechat_status).pack(side=tk.LEFT)
            ttk.Button(wechat_button_row, text="获取验证码", command=request_wechat_code).pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(wechat_button_row, text="解绑微信", command=unbind_wechat).pack(side=tk.LEFT, padx=(8, 0))

            button_row = ttk.Frame(body)
            button_row.pack(fill=tk.X, pady=(2, 0))

            def refresh_online():
                result_label.config(text="正在刷新在线状态...", foreground="orange")

                def worker():
                    try:
                        data = self._online_client.update_home_summary()
                        snapshot = self._online_client.load_session()
                        if data:
                            snapshot = dict(snapshot)
                            snapshot.setdefault("server_home_status", data)
                            snapshot.setdefault("server_status_text", "已连接")
                        try:
                            self.root.after(0, lambda snapshot=snapshot: _apply_refresh(snapshot))
                        except tk.TclError:
                            return
                    except Exception as exc:
                        try:
                            self.root.after(0, lambda error=exc: _apply_refresh_error(error))
                        except tk.TclError:
                            return

                threading.Thread(target=worker, daemon=True).start()

            def _apply_refresh(snapshot: Dict[str, object]):
                if snapshot:
                    self._merge_online_snapshot(snapshot, persist=True)
                render_from_state()
                result_label.config(text="已刷新", foreground="green")

            def _apply_refresh_error(error):
                if isinstance(error, OnlineAPIError):
                    self._state["server_status_text"] = error.message
                    message = error.message
                else:
                    self._state["server_status_text"] = "离线"
                    message = str(error)
                _save_home_state(self._state)
                render_from_state()
                result_label.config(text=message, foreground="red")

            def logout_online():
                dialog.destroy()
                self._logout_and_clear_online()

            ttk.Button(button_row, text="刷新状态", command=refresh_online).pack(side=tk.LEFT)
            ttk.Button(button_row, text="退出登录", command=logout_online).pack(side=tk.LEFT, padx=(8, 0))
            ttk.Button(button_row, text="关闭", command=dialog.destroy).pack(side=tk.LEFT, padx=(8, 0))
            render_from_state()
            refresh_online()
            refresh_wechat_status()

        dialog.transient(self.root)
        dialog.grab_set()
        fit_window_to_content(dialog, default_size=(540, 360))

    def _show_home_settings(self):
        messagebox.showinfo("设置", "全局设置后续接入。")

    def _show_about(self):
        if is_public_edition():
            messagebox.showinfo("关于", 
                f"快捷助手 {VERSION_LABEL.lower()}\n"
                f"当前版本：公开版（免费）\n"
                f"官网：openpaw.top"
            )
        else:
            if self.mode == "reply":
                mode = (self._state.get("reply_access_mode") or "free").strip().lower()
            elif self.mode == "personal":
                mode = (self._state.get("personal_access_mode") or "free").strip().lower()
            else:
                mode = _effective_access_mode(self._state)
            mode_text = {
                "free": "本地免费版",
                "local_perpetual": "本地永久版",
                "monthly": "月卡",
                "yearly": "年卡",
                "plus_monthly": "Plus月卡",
                "plus_yearly": "Plus年卡",
            }.get(mode, "本地免费版")
            messagebox.showinfo("关于", f"快捷助手 {VERSION_LABEL.lower()}\n当前状态：{mode_text}")

    def _shutdown_background(self):
        """ProductHomeWindow 无 tray/hotkey，仅做占位以统一退出路径。"""
        pass

    def _select(self, selection):
        self.selection = selection
        self._is_quitting = True
        self._shutdown_background()
        self.root.quit()

    def _close(self):
        self.selection = None
        self._is_quitting = True
        self._shutdown_background()
        self.root.quit()

    def show(self):
        self.root.mainloop()
        return self.selection




def main():
    return run_app()


def run_app():
    preview_api_client = None
    personal_data_manager = None
    # 使用单一 tk.Tk() root，整个生命周期不销毁重建，
    # 避免 Tcl_AsyncDelete: async handler deleted by the wrong thread
    root = tk.Tk()
    root.withdraw()  # 启动时隐藏，构建完再显示
    try:
        while True:
            for child in root.winfo_children():
                child.destroy()
            root.update()  # 强制同步销毁

            home = ProductHomeWindow(root)
            root.deiconify()  # 构建完成，显示窗口
            module_name = home.show()
            if not module_name:
                return

            root.withdraw()  # mainloop 退出后立即隐藏
            root.update()  # 强制同步

            if module_name == "reply_assistant":
                from preview_mode import PreviewAPIClient, PreviewModeManager
                user_id = "local_user"
                if preview_api_client is None:
                    pm = PreviewModeManager()
                    preview_api_client = PreviewAPIClient(pm, user_id)
                api = preview_api_client

                for child in root.winfo_children():
                    child.destroy()
                root.update()  # 强制同步销毁

                win = LocalMainWindow(root, api, user_id)
                root.deiconify()  # 构建完成，显示窗口
                action = win.show()
                if action == "home":
                    root.withdraw()  # 返回首页前隐藏
                    root.update()
                    continue
                return

            if module_name == "personal_data":
                if personal_data_manager is None:
                    personal_data_manager = PersonalDataManager(base_dir=get_app_base_dir() / "data")

                for child in root.winfo_children():
                    child.destroy()
                root.update()  # 强制同步销毁

                win = PersonalDataMainWindow(root, personal_data_manager)
                root.deiconify()  # 构建完成，显示窗口
                action = win.show()
                if action == "home":
                    root.withdraw()  # 返回首页前隐藏
                    root.update()
                    continue
                return
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == '__main__':
    run_app()
