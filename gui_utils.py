#!/usr/bin/env python3
"""共享GUI工具函数 - 回复助手和客户系统共用

从 start_gui.py 提取的共享工具函数、常量和商业版stub。
两个系统（回复助手、客户系统）都 import 本模块。
"""

import sys
import os
import threading
import ctypes
from pathlib import Path

# ---------------------------------------------------------------------------
# DPI awareness — must run before any Tk import
# ---------------------------------------------------------------------------
APP_ID = "ZLG.QuickReplyAssistant.v1.2"

def set_app_user_model_id():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

set_app_user_model_id()
enable_dpi_awareness()

# ---------------------------------------------------------------------------
# ttkbootstrap shim (avoid importing the package at top level)
# ---------------------------------------------------------------------------
class _BootstrapStyleShim:
    instance = None

class _BootstrapShim:
    Style = _BootstrapStyleShim

tb = _BootstrapShim()
HAS_TTKBOOTSTRAP = False

def reset_ttkbootstrap_style():
    """Clear any lingering ttkbootstrap singleton state without importing it."""
    tb.Style.instance = None
    bootstrap_module = sys.modules.get("ttkbootstrap")
    if bootstrap_module and hasattr(bootstrap_module, "Style"):
        try:
            bootstrap_module.Style.instance = None
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------
def get_app_base_dir():
    """获取应用基础目录（兼容打包和源码模式）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def get_icon_path():
    """获取图标路径（兼容打包和源码模式）"""
    if getattr(sys, 'frozen', False):
        icon_env = os.environ.get('APP_ICON_PATH')
        if icon_env and Path(icon_env).exists():
            return Path(icon_env)
        icon_in_exe_dir = Path(sys.executable).parent / 'app.ico'
        if icon_in_exe_dir.exists():
            return icon_in_exe_dir
        icon_in_internal = Path(sys.executable).parent / '_internal' / 'app.ico'
        if icon_in_internal.exists():
            return icon_in_internal
        icon_in_meipass = Path(sys._MEIPASS) / 'app.ico'
        if icon_in_meipass.exists():
            return icon_in_meipass
    return get_app_base_dir() / 'app.ico'

def get_tray_icon_path():
    """Prefer the colorful JPG for the tray icon, then fall back to ICO."""
    candidates = []
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        candidates.extend([
            exe_dir / 'app.jpg',
            exe_dir / 'app.ico',
            exe_dir / '_internal' / 'app.jpg',
            exe_dir / '_internal' / 'app.ico',
        ])
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.extend([
                Path(meipass) / 'app.jpg',
                Path(meipass) / 'app.ico',
            ])
    candidates.extend([
        get_app_base_dir() / 'app.jpg',
        get_app_base_dir() / 'app.ico',
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return get_app_base_dir() / 'app.jpg'

# ---------------------------------------------------------------------------
# PIL / pystray imports
# ---------------------------------------------------------------------------
try:
    import pystray
    from PIL import Image, ImageTk
    HAS_TRAY = True
except ImportError:
    Image = None
    ImageTk = None
    HAS_TRAY = False

HAS_HOTKEY = os.name == "nt"

# ---------------------------------------------------------------------------
# Image loading helpers
# ---------------------------------------------------------------------------
def load_app_icon_image(size: int = 64):
    """Load and normalize the app icon image for Tk and tray usage."""
    if Image is None:
        return None
    icon_path = get_tray_icon_path()
    if not icon_path.exists():
        return None
    try:
        icon_image = Image.open(icon_path).convert("RGBA")
    except Exception:
        return None
    if icon_image.width != icon_image.height:
        square_side = max(icon_image.width, icon_image.height)
        square_image = Image.new("RGBA", (square_side, square_side), (0, 0, 0, 0))
        paste_x = (square_side - icon_image.width) // 2
        paste_y = (square_side - icon_image.height) // 2
        square_image.paste(icon_image, (paste_x, paste_y))
        icon_image = square_image
    if size:
        icon_image = icon_image.resize((size, size), Image.LANCZOS)
    return icon_image

# ---------------------------------------------------------------------------
# Tk import + path setup
# ---------------------------------------------------------------------------
_root = get_app_base_dir()
sys.path.insert(0, str(_root))
os.environ['DATABASE_PATH'] = str(_root / 'data' / 'guest_data.db')
os.environ['VECTOR_STORE_PATH'] = str(_root / 'data' / 'guest_chroma')

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ---------------------------------------------------------------------------
# Window utilities
# ---------------------------------------------------------------------------
def get_personal_icon_path():
    """获取个人数据系统图标路径"""
    candidates = []
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        candidates.extend([
            exe_dir / 'personal_icon.png',
            exe_dir / '_internal' / 'personal_icon.png',
        ])
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(Path(meipass) / 'personal_icon.png')
    candidates.append(get_app_base_dir() / 'personal_icon.png')
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return get_app_base_dir() / 'personal_icon.png'


def apply_window_icon(window, icon_path=None):
    """Apply the app icon to a Tk window.

    Args:
        window: The Tk window to apply the icon to.
        icon_path: Optional custom icon path (PNG). If None, uses the default app icon.
    """
    if icon_path is not None and Path(icon_path).exists() and Image is not None:
        try:
            icon_image = Image.open(str(icon_path)).convert("RGBA")
            if icon_image.width != icon_image.height:
                square_side = max(icon_image.width, icon_image.height)
                square_image = Image.new("RGBA", (square_side, square_side), (0, 0, 0, 0))
                paste_x = (square_side - icon_image.width) // 2
                paste_y = (square_side - icon_image.height) // 2
                square_image.paste(icon_image, (paste_x, paste_y))
                icon_image = square_image
            icon_image = icon_image.resize((64, 64), Image.LANCZOS)
            if ImageTk is not None:
                icon_photo = ImageTk.PhotoImage(icon_image)
                window._app_icon_photo = icon_photo
                window.iconphoto(True, icon_photo)
                return
        except Exception:
            pass
    icon_image = load_app_icon_image(size=64)
    if icon_image is not None and ImageTk is not None:
        try:
            icon_photo = ImageTk.PhotoImage(icon_image)
            window._app_icon_photo = icon_photo
            window.iconphoto(True, icon_photo)
            return
        except Exception:
            pass
    fallback_path = get_icon_path()
    if fallback_path.exists():
        try:
            window.iconbitmap(str(fallback_path))
        except Exception:
            pass

def fit_window_to_content(window, default_size=None, max_size_ratio=(0.95, 0.92)):
    """Resize a window to its requested size, with a sensible fallback."""
    window.update_idletasks()
    req_width = window.winfo_reqwidth()
    req_height = window.winfo_reqheight()
    if default_size:
        req_width = max(req_width, default_size[0])
        req_height = max(req_height, default_size[1])
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    max_width = max(320, int(screen_width * max_size_ratio[0]))
    max_height = max(240, int(screen_height * max_size_ratio[1]))
    width = min(req_width, max_width)
    height = min(req_height, max_height)
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")

def apply_native_ttk_theme(window):
    """Prefer a native/light ttk theme so buttons do not look overly heavy."""
    try:
        style = ttk.Style(window)
        theme_names = set(style.theme_names())
        for theme_name in ("winnative", "xpnative", "vista", "default", "clam"):
            if theme_name in theme_names:
                style.theme_use(theme_name)
                return
    except Exception:
        return

def apply_plain_ttk_palette(window):
    """Force a plain white/black ttk palette for predictable first-launch colors."""
    try:
        window.configure(bg="white")
        window.option_add("*Foreground", "black")
        window.option_add("*Background", "white")
        window.option_add("*Text.foreground", "black")
        window.option_add("*Text.background", "white")
        window.option_add("*Text.selectBackground", "#d9ecff")
        window.option_add("*Text.selectForeground", "black")
        window.option_add("*Entry.foreground", "black")
        window.option_add("*Entry.background", "white")
        window.option_add("*Listbox.foreground", "black")
        window.option_add("*Listbox.background", "white")

        style = ttk.Style(window)
        for style_name in ("TFrame", "TLabelframe", "TLabelframe.Label", "TLabel", "TCheckbutton", "TRadiobutton"):
            style.configure(style_name, background="white", foreground="black")

        style.configure("TButton", foreground="black", background="white", padding=4)
        style.map(
            "TButton",
            foreground=[("disabled", "#808080"), ("pressed", "black"), ("active", "black")],
            background=[("pressed", "#f2f2f2"), ("active", "#f7f7f7"), ("!disabled", "white")],
        )

        style.configure("TEntry", foreground="black", fieldbackground="white")
        style.map(
            "TEntry",
            foreground=[("disabled", "#808080"), ("!disabled", "black")],
            fieldbackground=[("readonly", "white"), ("disabled", "#f4f4f4"), ("!disabled", "white")],
        )

        style.configure("TCombobox", foreground="black", fieldbackground="white", background="white")
        style.map(
            "TCombobox",
            foreground=[("disabled", "#808080"), ("readonly", "black"), ("!disabled", "black")],
            fieldbackground=[("readonly", "white"), ("disabled", "#f4f4f4"), ("!disabled", "white")],
            selectforeground=[("readonly", "black"), ("!disabled", "black")],
            selectbackground=[("readonly", "white"), ("!disabled", "white")],
            background=[("active", "#f7f7f7"), ("!disabled", "white")],
        )

        style.configure("Treeview", foreground="black", fieldbackground="white", background="white")
        style.map(
            "Treeview",
            foreground=[("selected", "black")],
            background=[("selected", "#d9ecff")],
        )
    except Exception:
        return

# ---------------------------------------------------------------------------
# Hotkey utilities
# ---------------------------------------------------------------------------
def hotkey_to_tk_sequence(hotkey: str):
    """Convert a ctrl+shift+y style hotkey string into a Tk bind sequence."""
    hotkey = (hotkey or "").strip().lower()
    if not hotkey:
        return None
    key_aliases = {
        "ctrl": "Control", "control": "Control",
        "shift": "Shift", "alt": "Alt",
    }
    parts = [part.strip() for part in hotkey.split("+") if part.strip()]
    if not parts:
        return None
    key = parts[-1]
    modifiers = []
    for part in parts[:-1]:
        normalized = key_aliases.get(part)
        if not normalized:
            return None
        if normalized not in modifiers:
            modifiers.append(normalized)
    if len(key) == 1 and key.isalnum():
        key_name = key.lower()
    elif key.startswith("f") and key[1:].isdigit():
        key_name = key.upper()
    else:
        special_keys = {
            "space": "space", "enter": "Return", "return": "Return",
            "tab": "Tab", "esc": "Escape", "escape": "Escape",
        }
        key_name = special_keys.get(key)
        if not key_name:
            return None
    return "<" + "-".join(modifiers + [key_name]) + ">"

def hotkey_to_windows_registration(hotkey: str):
    """Convert ctrl+shift+y style hotkey text into Windows RegisterHotKey values."""
    hotkey = (hotkey or "").strip().lower()
    if not hotkey:
        return None
    modifier_flags = {
        "alt": 0x0001, "ctrl": 0x0002, "control": 0x0002,
        "shift": 0x0004, "win": 0x0008, "windows": 0x0008,
    }
    parts = [part.strip() for part in hotkey.split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    for part in parts[:-1]:
        flag = modifier_flags.get(part)
        if flag is None:
            return None
        modifiers |= flag
    key = parts[-1]
    if len(key) == 1 and key.isalpha():
        virtual_key = ord(key.upper())
    elif len(key) == 1 and key.isdigit():
        virtual_key = ord(key)
    elif key.startswith("f") and key[1:].isdigit():
        number = int(key[1:])
        if number < 1 or number > 24:
            return None
        virtual_key = 0x70 + number - 1
    else:
        special_keys = {
            "space": 0x20, "enter": 0x0D, "return": 0x0D,
            "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
        }
        virtual_key = special_keys.get(key)
        if virtual_key is None:
            return None
    return modifiers, virtual_key

# ---------------------------------------------------------------------------
# Global hotkey manager (Windows)
# ---------------------------------------------------------------------------
class GlobalHotkeyManager:
    """Register a Windows global hotkey and expose presses through a threading.Event."""

    def __init__(self, hotkey: str):
        self.hotkey = (hotkey or "").strip()
        self.triggered = threading.Event()
        self.error = None
        self._thread = None
        self._thread_id = None
        self._registered = threading.Event()
        self._registration = hotkey_to_windows_registration(self.hotkey)
        self._hotkey_id = (id(self) & 0x7FFF) or 1

    def start(self) -> bool:
        if os.name != "nt":
            self.error = "global hotkeys are only supported on Windows"
            return False
        if not self._registration:
            self.error = "invalid hotkey"
            return False
        if self._thread and self._thread.is_alive():
            return True
        self.error = None
        self.triggered.clear()
        self._registered.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        self._registered.wait(timeout=1.0)
        return self.error is None

    def _message_loop(self):
        if os.name != "nt":
            self.error = "global hotkeys are only supported on Windows"
            self._registered.set()
            return
        from ctypes import wintypes
        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND), ("message", wintypes.UINT),
                ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
                ("time", wintypes.DWORD), ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long),
            ]
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        modifiers, virtual_key = self._registration
        self._thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, self._hotkey_id, modifiers, virtual_key):
            self.error = "register failed"
            self._registered.set()
            return
        self._registered.set()
        msg = MSG()
        try:
            while True:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:
                    break
                if msg.message == 0x0312 and msg.wParam == self._hotkey_id:
                    self.triggered.set()
        finally:
            try:
                user32.UnregisterHotKey(None, self._hotkey_id)
            except Exception:
                pass

    def stop(self):
        if os.name == "nt" and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None
        self._registered.clear()
        self.triggered.clear()

# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------
def create_labeled_entry_row(parent, label_text, value="", width=60, readonly=False):
    """Create a one-line label + entry row for question-style fields."""
    row = ttk.Frame(parent)
    ttk.Label(row, text=label_text).pack(side=tk.LEFT, padx=(0, 5))
    entry = ttk.Entry(row, width=width)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    if value:
        entry.insert(0, value)
    if readonly:
        entry.configure(state="readonly")
    return row, entry

def restore_view_samples_focus(view_win, tree):
    try:
        view_win.deiconify()
        view_win.lift()
        view_win.focus_force()
        tree.focus_set()
    except tk.TclError:
        pass

# ---------------------------------------------------------------------------
# Personal data display helpers
# ---------------------------------------------------------------------------
def format_personal_courses(courses):
    items = []
    for course in courses or []:
        subject = (course or {}).get("subject", "")
        class_type = (course or {}).get("class_type", "")
        if subject and class_type:
            items.append(f"{subject}{class_type}")
        elif subject:
            items.append(subject)
        elif class_type:
            items.append(class_type)
    return " / ".join(items)

def format_personal_course_part(courses, field_name, separator=" / "):
    items = []
    for course in courses or []:
        value = (course or {}).get(field_name, "")
        if value:
            items.append(value)
    return separator.join(items)

def get_personal_tree_columns():
    from personal_data import get_format_config
    config = get_format_config()
    columns = [f.key for f in config.fields]
    columns.append("recorded_time")
    return tuple(columns)

def get_personal_tree_headings():
    from personal_data import get_format_config
    config = get_format_config()
    headings = [(f.key, f.label) for f in config.fields]
    headings.append(("recorded_time", "报班时间"))
    return headings

def personal_record_table_values(record, multiline=False):
    from personal_data import get_format_config
    config = get_format_config()
    values = []
    for field_def in config.fields:
        if field_def.key == "name":
            values.append(record.get("name", "") or "未识别")
        elif field_def.key == "phone":
            values.append(record.get("phone", "") or "未识别")
        elif field_def.key == "grade":
            values.append(record.get("display_grade", "") or record.get("recorded_grade", "") or "未识别")
        elif field_def.key == "subject":
            sep = "\n" if multiline else " / "
            values.append(format_personal_course_part(record.get("courses", []), "subject", separator=sep) or "未识别")
        elif field_def.key in ("stage", "season"):
            sep = "\n" if multiline else " / "
            values.append(format_personal_course_part(record.get("courses", []), "stage", separator=sep) or "未识别")
        elif field_def.key == "class_type":
            sep = "\n" if multiline else " / "
            values.append(format_personal_course_part(record.get("courses", []), "class_type", separator=sep) or "未识别")
        else:
            dynamic = record.get("dynamic_fields", {})
            values.append(dynamic.get(field_def.key, "") or record.get(field_def.key, "") or "未识别")
    values.append(record.get("recorded_at", "")[:10])
    return tuple(values)

def personal_record_table_rows(record):
    from personal_data import get_format_config
    config = get_format_config()
    courses = record.get("courses") or [{}]
    rows = []
    for index, course in enumerate(courses):
        show = index == 0
        rv = []
        for fd in config.fields:
            if fd.key == "name":
                rv.append((record.get("name", "") or "未识别") if show else "")
            elif fd.key == "phone":
                rv.append((record.get("phone", "") or "未识别") if show else "")
            elif fd.key == "grade":
                dg = record.get("display_grade", "") or record.get("recorded_grade", "") or "未识别"
                rv.append(dg if show else "")
            elif fd.key == "subject":
                rv.append((course or {}).get("subject", "") or "未识别")
            elif fd.key in ("stage", "season"):
                rv.append((course or {}).get("stage", "") or "未识别")
            elif fd.key == "class_type":
                rv.append((course or {}).get("class_type", "") or "未识别")
            else:
                dynamic = record.get("dynamic_fields", {})
                rv.append(dynamic.get(fd.key, "") if show else "")
        rm = (record.get("recorded_at", "") or "")[:7] or "未记录"
        rv.append(rm if show else "")
        rows.append(tuple(rv))
    return rows

def format_personal_record_card(record, index):
    courses = format_personal_courses(record.get("courses", [])) or "未识别"
    stages = format_personal_course_part(record.get("courses", []), "stage") or "未识别"
    class_types = format_personal_course_part(record.get("courses", []), "class_type") or "未识别"
    dg = record.get("display_grade", "") or record.get("recorded_grade", "") or "未识别"
    rg = record.get("recorded_grade", "") or "未识别"
    st = record.get("source_type", "personal_structured")
    conf = record.get("confidence")
    extra = f"来源: {st}"
    if conf is not None:
        extra += f"（置信{conf:.0%}）"
    return "\n".join([
        f"【记录{index + 1}】 {record.get('name', '') or '未识别姓名'}",
        extra,
        f"电话: {record.get('phone', '') or '未识别'}",
        f"当前年级: {dg}    报班年级: {rg}",
        f"课程: {courses}",
        f"阶段: {stages}    班型: {class_types}",
        f"报班时间: {record.get('recorded_at', '') or '未记录'}",
        f"原始内容: {record.get('raw_text', '') or '无'}",
    ])

# ---------------------------------------------------------------------------
# Reply display helpers
# ---------------------------------------------------------------------------
from reply_display import (
    DEFAULT_REPLY_HIGHLIGHT_COLOR,
    DEFAULT_SOURCE_HIGHLIGHT_COLOR,
    candidate_header_segments,
    HIGHLIGHT_COLOR_OPTIONS,
    extract_reply_content,
    highlight_color_from_label,
    highlight_label_from_color,
    normalize_line_breaks,
    sample_table_values,
)

def insert_candidate_display(
    text_widget, index, candidate,
    source_highlight_tag=None, reply_highlight_tag=None, highlight_tag=None,
):
    """Insert one compact candidate block."""
    content = normalize_line_breaks(candidate.get("content", ""))
    if source_highlight_tag is None and highlight_tag is not None:
        source_highlight_tag = highlight_tag
    for segment_text, should_highlight in candidate_header_segments(candidate, index):
        start = text_widget.index("end-1c")
        text_widget.insert(tk.END, segment_text)
        end = text_widget.index("end-1c")
        if should_highlight and source_highlight_tag:
            text_widget.tag_add(source_highlight_tag, start, end)
    text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, "-----------\n")
    content_start = text_widget.index("end-1c")
    text_widget.insert(tk.END, content)
    content_end = text_widget.index("end-1c")
    if reply_highlight_tag and content_start != content_end:
        text_widget.tag_add(reply_highlight_tag, content_start, content_end)
    if not content.endswith("\n"):
        text_widget.insert(tk.END, "\n")
    text_widget.insert(tk.END, "===========\n")

# ---------------------------------------------------------------------------
# Help window (used by both reply and personal systems)
# ---------------------------------------------------------------------------
class HelpWindow:
    """帮助文档窗口"""
    
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("使用指南")
        self.win.geometry("550x500")
        apply_window_icon(self.win)
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        self._setup_ui()
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        fit_window_to_content(self.win, default_size=(720, 520))
    
    def _setup_ui(self):
        text = tk.Text(self.win, wrap=tk.WORD, padx=10, pady=10, font=("Microsoft YaHei", 10))
        text.pack(fill=tk.BOTH, expand=True)
        
        help_content = load_user_readme()
        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)
        
        ttk.Button(self.win, text="关闭", command=self.win.destroy).pack(pady=5)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCENE_TAGS = [
    "", "问价格", "回去考虑", "试听后犹豫", "孩子兴趣一般",
    "已读不回", "沉默唤醒", "约试听", "约复聊", "问课程",
    "问师资", "问时间"
]

STAGE_TAGS = [
    "", "新咨询", "初次接触", "问价阶段", "试听前",
    "试听后", "报名前", "上课中", "沉默后再唤醒"
]

# ---------------------------------------------------------------------------
# Commercial stubs (public edition)
# ---------------------------------------------------------------------------
from edition_limits import PUBLIC_CUSTOMER_LIMIT, PUBLIC_SAMPLE_LIMIT, is_public_edition
from version import VERSION_LABEL

COMMERCIAL_FEATURES_AVAILABLE = not is_public_edition()
if COMMERCIAL_FEATURES_AVAILABLE:
    try:
        from membership_license import PermanentLicenseManager, get_machine_code
        from online_client import (
            OnlineAPIError, OnlineClient, generate_device_id, get_device_name,
        )
    except ImportError:
        COMMERCIAL_FEATURES_AVAILABLE = False

if not COMMERCIAL_FEATURES_AVAILABLE:
    class OnlineAPIError(Exception):
        pass

    class PermanentLicenseManager:
        def __init__(self, *args, **kwargs):
            self.base_dir = kwargs.get("base_dir")
        def get_status(self, *args, **kwargs):
            return type("LicenseStatus", (), {"active": False, "message": "未激活", "payload": None})()
        def clear_license(self):
            return None
        def activate(self, activation_code: str, machine_code: str = ""):
            return {
                "license_id": "", "machine_code": machine_code or get_machine_code(),
                "plan": "permanent", "activated_at": "", "expires_at": "", "signature": "",
            }

    def get_machine_code() -> str:
        return "PUBLIC-ONLY"
    def generate_device_id() -> str:
        return "PUBLIC-ONLY"
    def get_device_name() -> str:
        return os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "Unknown"

    class OnlineClient:
        def __init__(self, *args, **kwargs):
            self._session_snapshot = {}
        def has_session(self) -> bool:
            return False
        def load_session(self):
            return dict(self._session_snapshot)
        def save_session(self, snapshot=None):
            self._session_snapshot = dict(snapshot or {})
        def clear_session(self):
            self._session_snapshot = {}
        def update_home_summary(self, *a, **kw):
            return {"success": False, "data": {}}
        def sync_upload(self, *a, **kw):
            return {"success": False, "message": "公开版不支持在线同步"}
        def register(self, *a, **kw):
            return {"success": False, "message": "公开版不支持注册"}
        def login(self, *a, **kw):
            return {"success": False, "message": "公开版不支持登录"}
        def create_payment_order(self, *a, **kw):
            return {"success": False, "message": "公开版不支持支付"}
        def get_subscription_status(self, *a, **kw):
            return {"success": False, "message": "公开版不支持订阅"}
        def renew_subscription(self, *a, **kw):
            return {"success": False, "message": "公开版不支持订阅"}
        def get_wechat_status(self, *a, **kw):
            return {"success": False, "data": {}}
        def get_wechat_bind_code(self, *a, **kw):
            return {"success": False, "data": {}}
        def unbind_wechat(self, *a, **kw):
            return {"success": False, "message": "公开版不支持微信绑定"}

# ---------------------------------------------------------------------------
# Help content
# ---------------------------------------------------------------------------
HELP_CONTENT = ""

def load_user_readme():
    readme_path = get_app_base_dir() / 'data' / 'USER_README.md'
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return """
快捷回复助手 - 使用指南

【快速上手】
1. 输入问题，或点击"粘贴"把剪贴板内容放入输入框。
2. 点击"检索"，或按 Enter。
3. 从候选中挑选并复制需要的回复。

【设置】
- 数据目录：在设置页中修改数据存储位置
- 导入数据：在设置页中导入样本数据
- 清除数据：在设置页中恢复默认样本数据
- 查看样本：在设置页中查看、编辑或删除本地样本
- 搜索参数：可调整返回候选数量（top_k）和高亮颜色

【快捷键】
- Ctrl+Shift+Y：全局唤起窗口

【托盘运行】
- 点击关闭按钮最小化到托盘
"""

def sample_view_count_text(count: int) -> str:
    return f"样本数: {count}"

def personal_record_count_text(count: int) -> str:
    return f"资料数: {count}"
