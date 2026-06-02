"""
回复助手 GUI 类模块

从 start_gui.py 提取的回复系统相关类:
- SettingsWindow: 设置窗口
- FavoriteDialog: 收藏样本弹窗
- LoginWindow: 登录窗口
- LocalMainWindow: 本地模式主窗口
- AccountMainWindow: 账号模式主窗口
"""

import sys
import os
import threading
import json
import time
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path

from gui_utils import (
    reset_ttkbootstrap_style, apply_window_icon, apply_native_ttk_theme,
    apply_plain_ttk_palette, fit_window_to_content, load_app_icon_image,
    GlobalHotkeyManager, create_labeled_entry_row, restore_view_samples_focus,
    insert_candidate_display, sample_view_count_text,
    SCENE_TAGS, STAGE_TAGS, HAS_TRAY, HAS_HOTKEY,
    Image, ImageTk, pystray,
    # reply display helpers
    DEFAULT_REPLY_HIGHLIGHT_COLOR, DEFAULT_SOURCE_HIGHLIGHT_COLOR,
    candidate_header_segments, HIGHLIGHT_COLOR_OPTIONS,
    extract_reply_content, highlight_color_from_label, highlight_label_from_color,
    normalize_line_breaks, sample_table_values,
    # help
    HelpWindow,
)


class SettingsWindow:
    """设置窗口"""
    
    def __init__(
        self,
        parent,
        preview_manager,
        on_save=None,
        on_clear_data=None,
        on_import_data=None,
        on_view_samples=None,
    ):
        self.win = tk.Toplevel(parent)
        self.win.title("设置")
        apply_window_icon(self.win)
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        self.preview_manager = preview_manager
        self.on_save = on_save
        self.on_clear_data = on_clear_data
        self.on_import_data = on_import_data
        self.on_view_samples = on_view_samples
        self._setup_ui()
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        fit_window_to_content(self.win, default_size=(580, 440))
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_ui(self):
        data_frame = ttk.LabelFrame(self.win, text="数据存储", padding=10)
        data_frame.pack(fill=tk.X, padx=10, pady=10)
        
        data_dir = self.preview_manager.data_dir
        self.data_dir_label = ttk.Label(data_frame, text=f"数据目录: {data_dir}")
        self.data_dir_label.pack(anchor=tk.W)
        
        path_action_frame = ttk.Frame(data_frame)
        path_action_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(path_action_frame, text="更改路径", command=self._change_data_dir).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(path_action_frame, text="导入数据", command=self._on_import_data).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(path_action_frame, text="清除数据", command=self._on_clear_data).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(path_action_frame, text="查看样本", command=self._on_view_samples).pack(side=tk.LEFT)
        
        hotkey_frame = ttk.LabelFrame(self.win, text="快捷键设置", padding=10)
        hotkey_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(hotkey_frame, text="全局唤起快捷键:").pack(anchor=tk.W)
        self.hotkey_entry = ttk.Entry(hotkey_frame, width=20)
        self.hotkey_entry.pack(anchor=tk.W, pady=5)
        self.hotkey_entry.insert(0, self.preview_manager.get_hotkey())
        ttk.Label(hotkey_frame, text="建议格式：ctrl+shift+y", foreground="gray").pack(anchor=tk.W)
        
        search_frame = ttk.LabelFrame(self.win, text="检索参数", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="返回候选数量 (top_k):").pack(anchor=tk.W)
        self.topk_spin = ttk.Spinbox(search_frame, from_=1, to=10, width=10)
        self.topk_spin.pack(anchor=tk.W, pady=5)
        self.topk_spin.set(5)

        ttk.Label(search_frame, text="命中词颜色:").pack(anchor=tk.W, pady=(8, 0))
        self.source_highlight_combo = ttk.Combobox(
            search_frame,
            values=[label for label, _ in HIGHLIGHT_COLOR_OPTIONS],
            width=18,
            state="readonly",
        )
        self.source_highlight_combo.pack(anchor=tk.W, pady=5)
        self.source_highlight_combo.set(
            highlight_label_from_color(self.preview_manager.get_source_highlight_color())
        )

        ttk.Label(search_frame, text="正文颜色:").pack(anchor=tk.W, pady=(8, 0))
        self.reply_highlight_combo = ttk.Combobox(
            search_frame,
            values=[label for label, _ in HIGHLIGHT_COLOR_OPTIONS],
            width=18,
            state="readonly",
        )
        self.reply_highlight_combo.pack(anchor=tk.W, pady=5)
        self.reply_highlight_combo.set(
            highlight_label_from_color(self.preview_manager.get_reply_highlight_color())
        )

        self.v204_generation_var = tk.BooleanVar(value=self.preview_manager.get_v204_generation_enabled())
        ttk.Checkbutton(
            search_frame,
            text="启用智能生成增强（V2.04）",
            variable=self.v204_generation_var,
        ).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(
            search_frame,
            text="开启后将使用自动 hybrid 模式增强候选生成与排序",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(4, 0))
        
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        ttk.Button(btn_frame, text="保存并关闭", command=self._on_close).pack(side=tk.RIGHT, padx=5)
    
    def _on_close(self):
        if self.on_save:
            top_k = int(self.topk_spin.get())
            source_highlight_color = highlight_color_from_label(self.source_highlight_combo.get())
            reply_highlight_color = highlight_color_from_label(self.reply_highlight_combo.get())
            hotkey = (self.hotkey_entry.get() or "").strip() or self.preview_manager.get_hotkey()
            self.on_save(
                top_k=top_k,
                source_highlight_color=source_highlight_color,
                reply_highlight_color=reply_highlight_color,
                v204_generation_enabled=self.v204_generation_var.get(),
                hotkey=hotkey,
            )
        self.win.destroy()

    def _on_clear_data(self):
        if self.on_clear_data:
            self.on_clear_data()

    def _on_import_data(self):
        if self.on_import_data:
            self.on_import_data()

    def _on_view_samples(self):
        if self.on_view_samples:
            self.on_view_samples()
    
    def _change_data_dir(self):
        new_dir = filedialog.askdirectory(title="选择数据存储目录")
        if new_dir:
            self.preview_manager.data_dir = Path(new_dir)
            self.data_dir_label.config(text=f"数据目录: {new_dir}")
            messagebox.showinfo("成功", f"数据目录已更改: {new_dir}")


class FavoriteDialog:
    """收藏样本弹窗"""
    
    def __init__(self, parent, query, reply, scenes, on_save, preview_manager=None):
        self.win = tk.Toplevel(parent)
        self.win.title("收藏样本")
        self.win.geometry("400x350")
        apply_window_icon(self.win)
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        self.query = query
        self.reply = reply
        self.scenes = scenes
        self.on_save = on_save
        self.preview_manager = preview_manager
        self._setup_ui()
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        fit_window_to_content(self.win, default_size=(560, 420))
    
    def _setup_ui(self):
        query_row, query_entry = create_labeled_entry_row(
            self.win,
            "问题",
            self.query,
            width=60,
            readonly=True,
        )
        query_row.pack(fill=tk.X, padx=10, pady=5)
        self.query_entry = query_entry
        
        ttk.Label(self.win, text="回复内容:").pack(anchor=tk.W, padx=10, pady=5)
        reply_text = tk.Text(self.win, height=5, wrap=tk.WORD)
        reply_text.pack(fill=tk.X, padx=10)
        reply_text.insert(tk.END, self.reply)
        self.reply_text = reply_text
        
        ttk.Label(self.win, text="场景标签:").pack(anchor=tk.W, padx=10, pady=5)
        self.scene_combo = ttk.Combobox(self.win, values=self.scenes, width=30)
        self.scene_combo.pack(anchor=tk.W, padx=10)
        self.scene_combo.set("")
        
        ttk.Label(self.win, text="备注（可选）:").pack(anchor=tk.W, padx=10, pady=5)
        self.note_entry = ttk.Entry(self.win, width=40)
        self.note_entry.pack(anchor=tk.W, padx=10)
        
        # 覆盖选项
        overwrite_frame = ttk.Frame(self.win)
        overwrite_frame.pack(fill=tk.X, padx=10, pady=5)
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(overwrite_frame, text="覆盖（检索到完全一样的问题时，替换原样本）", 
                       variable=self.overwrite_var).pack(anchor=tk.W)
        
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.win.destroy).pack(side=tk.LEFT, padx=10)
    
    def _save(self):
        reply = self.reply_text.get("1.0", "end-1c")
        scene = self.scene_combo.get()
        note = self.note_entry.get().strip()
        overwrite = self.overwrite_var.get()
        self.on_save(self.query, reply, scene, note, overwrite)
        self.win.destroy()


class LoginWindow:
    """登录窗口"""
    
    def __init__(self):
        reset_ttkbootstrap_style()
        self.root = tk.Tk()
        self.root.title("快捷回复助手")
        self.root.resizable(True, True)
        apply_window_icon(self.root)
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        
        self._setup_ui()
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        fit_window_to_content(self.root, default_size=(520, 380))
        self.user_id = None
        self.mode = None
    
    def _setup_ui(self):
        ttk.Label(self.root, text="回复助手", font=("Microsoft YaHei", 16)).pack(pady=15)

        local_frame = ttk.LabelFrame(self.root, text="本地模式", padding=10)
        local_frame.pack(fill=tk.X, padx=30, pady=8)
        ttk.Label(local_frame, text="离线运行，本地数据匹配").pack(anchor=tk.CENTER)
        ttk.Button(local_frame, text="进入本地模式", command=self._on_local, width=25).pack(pady=8)

        account_frame = ttk.LabelFrame(self.root, text="账号登录模式", padding=10)
        account_frame.pack(fill=tk.X, padx=30, pady=8)
        ttk.Label(account_frame, text="连接服务器，使用 AI 生成").pack(anchor=tk.CENTER)

        login_frame = ttk.Frame(account_frame)
        login_frame.pack(pady=8)

        ttk.Label(login_frame, text="账号:").pack(side=tk.TOP, pady=2)
        self.user_entry = ttk.Entry(login_frame, width=25)
        self.user_entry.pack(side=tk.TOP, pady=2)
        self.user_entry.insert(0, "advisor_001")

        ttk.Label(login_frame, text="密码:").pack(side=tk.TOP, pady=2)
        self.pwd_entry = ttk.Entry(login_frame, width=25, show="*")
        self.pwd_entry.pack(side=tk.TOP, pady=2)

        ttk.Button(account_frame, text="账号登录", command=self._on_account, width=25).pack(pady=8)
    
    def _on_local(self):
        self.user_id = "local_user"
        self.mode = "local"
        reset_ttkbootstrap_style()
        self.root.quit()
    
    def _on_account(self):
        user_id = self.user_entry.get().strip()
        pwd = self.pwd_entry.get().strip()
        if not user_id:
            messagebox.showwarning("提示", "请输入账号")
            return
        self.user_id = user_id
        self.mode = "account"
        reset_ttkbootstrap_style()
        self.root.quit()

    def show(self):
        self.root.mainloop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        return self.user_id, self.mode


class LocalMainWindow:
    """本地模式主窗口 - v1.2 托盘+快捷键版"""
    
    def __init__(self, root, api_client, user_id, access_mode="free"):
        self.api_client = api_client
        self.preview_manager = api_client.preview_manager
        self.user_id = user_id
        self.access_mode = access_mode
        
        reset_ttkbootstrap_style()
        self.root = root
        # 根据 access_mode 动态显示窗口标题
        _am = access_mode
        if _am in ('plus_monthly', 'plus_yearly'):
            _mode_label = "Plus专业版"
        elif _am in ('monthly', 'yearly'):
            _mode_label = "专业版"
        elif _am == 'local_perpetual':
            _mode_label = "本地永久版"
        else:
            _mode_label = "本地免费版"
        self.root.title(f"快捷回复助手 - {_mode_label} ({user_id})")
        self.root.geometry("750x650")
        apply_window_icon(self.root)
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        
        self._candidates = []
        self._is_from_match = False
        self._top_k = 5
        self._source_highlight_color = self.preview_manager.get_source_highlight_color()
        self._reply_highlight_color = self.preview_manager.get_reply_highlight_color()
        self._hotkey = self.preview_manager.get_hotkey()
        self._hotkey_sequence = None
        self._global_hotkey_manager = None
        self._hotkey_poll_after_id = None
        self._tray_icon = None
        self._tray_thread = None
        self._tray_initialized = False
        self._is_quitting = False
        self._next_action = None
        self._search_in_progress = False
        
        self._setup_ui()
        self._update_status_bar()
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        fit_window_to_content(self.root, default_size=(900, 650))
        self._setup_hotkey()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)
    
    def _setup_ui(self):
        style = ttk.Style(self.root)
        style.configure("Personal.Treeview", rowheight=44)
        style.configure("Personal.Treeview.Heading", padding=(10, 9))

        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=14, pady=(8, 6))
        header_frame.columnconfigure(1, weight=1)
        
        # 根据 access_mode 动态显示状态
        access_mode = self.access_mode
        if access_mode in ('plus_monthly', 'plus_yearly'):
            mode_text = "Plus专业版"
        elif access_mode in ('monthly', 'yearly'):
            mode_text = "专业版"
        elif access_mode == 'local_perpetual':
            mode_text = "本地永久版"
        else:
            mode_text = "本地免费版"

        ttk.Label(
            header_frame,
            text=f"{mode_text}：在线状态",
            font=("Arial", 11),
        ).grid(row=0, column=0, sticky="w")

        self.user_label = ttk.Label(header_frame, text=f"👤 {self.user_id}")
        self.user_label.grid(row=0, column=1, sticky="w", padx=20)

        header_button_frame = ttk.Frame(header_frame)
        header_button_frame.grid(row=0, column=2, sticky="e")
        ttk.Button(header_button_frame, text="🏠", width=3, command=self._go_home).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(header_button_frame, text="❓", width=3, command=self._show_help).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(header_button_frame, text="⚙", width=3, command=self._show_settings).pack(side=tk.LEFT)
        
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=14, pady=5)
        
        input_row = ttk.Frame(input_frame)
        input_row.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_row, text="问题").pack(side=tk.LEFT, padx=(0, 5))
        self.query_entry = ttk.Entry(input_row, width=50)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.query_entry.bind('<Return>', self._on_search)
        
        self.search_button = ttk.Button(input_row, text="检索", command=self._on_search, width=8)
        self.search_button.pack(side=tk.LEFT, padx=5)
        self.paste_button = ttk.Button(input_row, text="粘贴", command=self._paste_from_clipboard, width=8)
        self.paste_button.pack(side=tk.LEFT, padx=5)
        
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=14, pady=5)
        
        ttk.Label(filter_frame, text="场景:").pack(side=tk.LEFT)
        self.scene_combo = ttk.Combobox(filter_frame, values=SCENE_TAGS, width=15, state="readonly")
        self.scene_combo.pack(side=tk.LEFT, padx=5)
        self.scene_combo.set("")
        
        ttk.Label(filter_frame, text="阶段:").pack(side=tk.LEFT, padx=10)
        self.stage_combo = ttk.Combobox(filter_frame, values=STAGE_TAGS, width=15, state="readonly")
        self.stage_combo.pack(side=tk.LEFT, padx=5)
        self.stage_combo.set("")
        
        # Plus AI 生成勾选框（仅私有版且有Plus权限时可用）
        self.plus_var = tk.BooleanVar(value=False)
        self.plus_check = ttk.Checkbutton(
            filter_frame, 
            text="AI生成（Plus）", 
            variable=self.plus_var,
        )
        self.plus_check.pack(side=tk.LEFT, padx=10)
        
        # 检查是否有Plus权限，没有则禁用
        if not self._is_plus_user():
            self.plus_check.config(state="disabled")
            self.plus_var.set(False)
        
        self.match_type_label = ttk.Label(self.root, text="", foreground="gray")
        
        candidate_section = ttk.Frame(self.root)
        candidate_section.pack(fill=tk.BOTH, expand=True, padx=14, pady=5)

        candidate_header = ttk.Frame(candidate_section)
        candidate_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(candidate_header, text="候选回复", font=("Arial", 10)).pack(side=tk.LEFT)
        self.candidate_count_label = ttk.Label(candidate_header, text="【0】", foreground="gray")
        self.candidate_count_label.pack(side=tk.LEFT, padx=(6, 0))

        candidate_actions = ttk.Frame(candidate_header)
        candidate_actions.pack(side=tk.RIGHT)
        ttk.Button(candidate_actions, text="收藏样本", command=self._on_favorite).pack(side=tk.LEFT)

        result_frame = ttk.Frame(candidate_section)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(result_frame, height=15, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.bind('<Key>', self._on_text_edit)
        
        actions_row = ttk.Frame(self.root)
        actions_row.pack(fill=tk.X, padx=14, pady=(8, 36))

        quick_copy_frame = ttk.Frame(actions_row)
        quick_copy_frame.pack(side=tk.LEFT)
        ttk.Button(quick_copy_frame, text="复制第一条", command=self._copy_first).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_copy_frame, text="复制第二条", command=self._copy_second).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_copy_frame, text="复制第三条", command=self._copy_third).pack(side=tk.LEFT, padx=5)

        right_actions = ttk.Frame(actions_row)
        right_actions.pack(side=tk.RIGHT)

        copy_index_frame = ttk.Frame(right_actions)
        copy_index_frame.pack(side=tk.LEFT, padx=(0, 14))
        ttk.Label(copy_index_frame, text="第").pack(side=tk.LEFT, padx=(0, 5))
        self.copy_index_spin = ttk.Spinbox(copy_index_frame, from_=1, to=99, width=5)
        self.copy_index_spin.pack(side=tk.LEFT)
        self.copy_index_spin.set(1)
        ttk.Label(copy_index_frame, text="条").pack(side=tk.LEFT, padx=2)
        ttk.Button(copy_index_frame, text="【复制】", command=self._copy_by_index).pack(side=tk.LEFT, padx=(5, 0))

        delete_index_frame = ttk.Frame(right_actions)
        delete_index_frame.pack(side=tk.LEFT, padx=(0, 14))
        ttk.Label(delete_index_frame, text="删除第").pack(side=tk.LEFT, padx=(0, 5))
        self.delete_index_spin = ttk.Spinbox(delete_index_frame, from_=1, to=99, width=5)
        self.delete_index_spin.pack(side=tk.LEFT)
        self.delete_index_spin.set(1)
        ttk.Label(delete_index_frame, text="条样本").pack(side=tk.LEFT, padx=2)
        ttk.Button(delete_index_frame, text="【删除】", command=self._delete_by_index).pack(side=tk.LEFT, padx=(5, 0))

        self.status_label = ttk.Label(right_actions, text="")
        self.status_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        self._update_sample_count()
        self._update_candidate_count_label(0)
    
    def _update_status_bar(self):
        if hasattr(self, "user_label"):
            self.user_label.config(text=f"👤 {self.user_id}")

    def _update_candidate_count_label(self, count):
        if hasattr(self, "candidate_count_label"):
            self.candidate_count_label.config(text=f"【{count}】")
    
    def _show_settings(self):
        def on_settings_save(top_k, source_highlight_color, reply_highlight_color, v204_generation_enabled, hotkey):
            self._top_k = top_k
            self._source_highlight_color = source_highlight_color
            self._reply_highlight_color = reply_highlight_color
            self._hotkey = (hotkey or "").strip() or self.preview_manager.get_hotkey()
            self.preview_manager.set_source_highlight_color(source_highlight_color)
            self.preview_manager.set_reply_highlight_color(reply_highlight_color)
            self.preview_manager.set_v204_generation_enabled(v204_generation_enabled)
            self.preview_manager.set_hotkey(self._hotkey)
            self._setup_hotkey()
            self._update_status_bar()
            if self._candidates:
                self._render_candidates()
        SettingsWindow(
            self.root,
            self.preview_manager,
            on_save=on_settings_save,
            on_clear_data=self._reset_data,
            on_import_data=self._import_data,
            on_view_samples=self._view_samples,
        )
    
    def _show_help(self):
        HelpWindow(self.root)
    
    def _is_plus_user(self):
        """判断当前用户是否有Plus权限（仅回复助手）"""
        from gui_utils import is_public_edition
        if is_public_edition():
            return False
        # 从 preview_manager 的 state 中读取 reply_access_mode
        try:
            state = self.preview_manager.data.get('state', {})
            access_mode = state.get('reply_access_mode', 'free')
            return access_mode in ('plus_monthly', 'plus_yearly')
        except Exception:
            return False

    def _paste_from_clipboard(self):
        try:
            clipboard = self.root.clipboard_get()
            self.query_entry.delete(0, tk.END)
            self.query_entry.insert(0, clipboard)
            self._on_search()
        except tk.TclError:
            self.status_label.config(text="剪贴板无内容")
    
    def _on_text_edit(self, event=None):
        self._is_from_match = False
    
    def _update_sample_count(self):
        self._sample_count = self.preview_manager.get_sample_count()
        self._update_status_bar()

    def _refresh_result_highlight(self):
        source_color = self._source_highlight_color or self.result_text.cget("background")
        reply_color = self._reply_highlight_color or self.result_text.cget("background")
        self.result_text.tag_configure("source_text", background=source_color)
        self.result_text.tag_configure("reply_text", background=reply_color)

    def _render_candidates(self):
        self._refresh_result_highlight()
        self.result_text.delete("1.0", tk.END)
        self._update_candidate_count_label(len(self._candidates))

        for i, candidate in enumerate(self._candidates):
            insert_candidate_display(
                self.result_text,
                i,
                candidate,
                source_highlight_tag="source_text",
                reply_highlight_tag="reply_text",
            )

    def _set_search_busy(self, busy: bool):
        self._search_in_progress = busy
        state = tk.DISABLED if busy else tk.NORMAL
        if hasattr(self, "search_button"):
            self.search_button.config(state=state)
        if hasattr(self, "paste_button"):
            self.paste_button.config(state=state)
    
    def _on_search(self, event=None):
        query = self.query_entry.get().strip()
        if not query:
            self.status_label.config(text="请输入问题")
            return

        if self._search_in_progress:
            return

        self.status_label.config(text="检索中...")
        self.match_type_label.config(text="检索中...", foreground="orange")
        scene_hint = self.scene_combo.get()
        use_ai = self.plus_var.get() if hasattr(self, 'plus_var') else False
        self._set_search_busy(True)

        def worker():
            try:
                result = self.api_client.generate_reply(
                    query=query,
                    scene_hint=scene_hint if scene_hint else None,
                    top_k=self._top_k,
                    use_ai_generation=use_ai
                )
                try:
                    self.root.after(0, lambda result=result, scene_hint=scene_hint: self._finish_search_success(result, scene_hint))
                except tk.TclError:
                    return
            except Exception as exc:
                try:
                    self.root.after(0, lambda error=exc: self._finish_search_error(error))
                except tk.TclError:
                    return

        threading.Thread(target=worker, daemon=True).start()

    def _finish_search_success(self, result, scene_hint):
        self._set_search_busy(False)
        self._candidates = result.get('candidates', [])
        self._is_from_match = True

        mt = result.get('match_type', 'none')
        self.match_type_label.config(
            text=f"{mt}" + (f" ({scene_hint})" if scene_hint else ""),
            foreground="green" if mt == "exact" else "blue" if mt == "similar" else "gray"
        )
        self._render_candidates()
        self.status_label.config(text=f"完成 ({len(self._candidates)} 条候选)")

    def _finish_search_error(self, error):
        self._set_search_busy(False)
        self.status_label.config(text=f"错误: {error}")
        self._update_candidate_count_label(len(self._candidates))
        self.match_type_label.config(text="失败", foreground="red")
    
    def _copy_candidate(self, index):
        if index < len(self._candidates):
            content = self._candidates[index].get('content', '')
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_label.config(text=f"已复制候选{index + 1}")
        else:
            self.status_label.config(text="无该候选")
    
    def _copy_by_index(self):
        index = int(self.copy_index_spin.get()) - 1
        self._copy_candidate(index)
    
    def _copy_first(self): self._copy_candidate(0)
    def _copy_second(self): self._copy_candidate(1)
    def _copy_third(self): self._copy_candidate(2)
    
    def _on_favorite(self):
        query = self.query_entry.get().strip()
        if not query:
            self.status_label.config(text="请输入问题")
            return
        
        reply_text = self.result_text.get("1.0", tk.END)
        reply_text = extract_reply_content(reply_text)
        if not reply_text.strip():
            self.status_label.config(text="请先检索或输入回复")
            return
        
        def save_callback(query, reply, scene, note, overwrite=False):
            try:
                if overwrite:
                    samples = self.preview_manager.get_all_samples()
                    found_idx = None
                    for i, s in enumerate(samples):
                        if self.preview_manager._normalize_text(s.get('parent_message', '')) == \
                           self.preview_manager._normalize_text(query):
                            found_idx = i
                            break
                    
                    if found_idx is not None:
                        self.preview_manager.update_sample(found_idx, parent_message=query, 
                                                           replies=[reply], scene_tag=scene)
                        self._update_sample_count()
                        self.status_label.config(text=f"已覆盖第{found_idx + 1}条样本")
                    else:
                        self.api_client.create_sample(
                            parent_message=query,
                            advisor_reply=reply,
                            scene_tag=scene if scene else None
                        )
                        self._update_sample_count()
                        self.status_label.config(text=f"已收藏（未找到相同问题，新增）")
                else:
                    result = self.api_client.create_sample(
                        parent_message=query,
                        advisor_reply=reply,
                        scene_tag=scene if scene else None
                    )
                    self._update_sample_count()
                    self.status_label.config(text="已收藏")
            except Exception as e:
                messagebox.showerror("错误", f"收藏失败: {e}")
        
        FavoriteDialog(self.root, query, reply_text, SCENE_TAGS, save_callback, 
                       preview_manager=self.preview_manager)
    
    def _import_data(self):
        file_path = filedialog.askopenfilename(
            title="导入对话数据",
            filetypes=[("JSON文件", "*.json"), ("CSV文件", "*.csv")]
        )
        if not file_path:
            return
        
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                convs = []
                if isinstance(data, list):
                    convs = data
                elif isinstance(data, dict):
                    convs = data.get('samples', data.get('conversations', [data]))
                
                valid = [c for c in convs if 'parent_message' in c and 'advisor_reply' in c]
            else:
                messagebox.showwarning("提示", "暂不支持 CSV 格式，请使用 JSON")
                return
            
            if not valid:
                messagebox.showwarning("提示", "未找到有效数据\n格式: parent_message + advisor_reply")
                return
            
            result = self.api_client.import_samples(valid)
            self._update_sample_count()
            messagebox.showinfo("导入成功",
                                f"导入 {result['imported_count']} 条")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {e}")
    
    def _view_samples(self):
        samples = self.preview_manager.get_all_samples()

        view_win = tk.Toplevel(self.root)
        view_win.title("本地样本列表")
        view_win.resizable(True, True)
        apply_window_icon(view_win)

        style = ttk.Style(view_win)
        style.configure("Sample.Treeview", rowheight=30)
        style.configure("Sample.Treeview.Heading", padding=(8, 6))

        body = ttk.Frame(view_win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            body,
            columns=("idx", "parent", "reply", "scene", "time"),
            show="headings",
            height=16,
            style="Sample.Treeview",
        )

        yscroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=tree.yview)
        xscroll = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        tree.heading("idx", text="#", anchor=tk.W)
        tree.heading("parent", text="问题摘要", anchor=tk.W)
        tree.heading("reply", text="回复摘要", anchor=tk.W)
        tree.heading("scene", text="场景", anchor=tk.W)
        tree.heading("time", text="时间", anchor=tk.W)

        tree.column("idx", width=48, minwidth=40, stretch=False, anchor=tk.W)
        tree.column("parent", width=320, minwidth=220, stretch=True, anchor=tk.W)
        tree.column("reply", width=380, minwidth=260, stretch=True, anchor=tk.W)
        tree.column("scene", width=110, minwidth=90, stretch=False, anchor=tk.W)
        tree.column("time", width=110, minwidth=90, stretch=False, anchor=tk.W)

        def reload_rows():
            for item in tree.get_children():
                tree.delete(item)
            current_samples = self.preview_manager.get_all_samples()
            row_num = 0
            for si, sample in enumerate(current_samples):
                replies = sample.get("replies", [])
                if not replies:
                    # sample with no replies — still show one row
                    replies = [""]
                for ri, reply in enumerate(replies):
                    row_num += 1
                    iid = f"{si}_{ri}"
                    tree.insert("", tk.END, iid=iid,
                                values=sample_table_values(sample, row_num, reply))
            count_label.config(text=sample_view_count_text(row_num))

        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        btn_frame = ttk.Frame(view_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        count_label = ttk.Label(btn_frame, text=sample_view_count_text(len(samples)))
        count_label.pack(side=tk.RIGHT)

        reload_rows()

        def refresh_list():
            reload_rows()

        def open_cluster_analysis():
            try:
                report = self.api_client.cluster_saved_samples(method="greedy", text_field="parent_message")
            except Exception as e:
                messagebox.showerror("错误", f"聚类分析失败: {e}", parent=view_win)
                return

            if not report or not getattr(report, "clusters", None):
                messagebox.showinfo("提示", "当前没有可用于聚类分析的样本", parent=view_win)
                return

            analysis_win = tk.Toplevel(view_win)
            analysis_win.title("样本聚类分析")
            analysis_win.resizable(True, True)
            apply_window_icon(analysis_win)

            outer = ttk.Frame(analysis_win, padding=10)
            outer.pack(fill=tk.BOTH, expand=True)
            outer.rowconfigure(1, weight=1)
            outer.columnconfigure(0, weight=1)

            summary_frame = ttk.LabelFrame(outer, text="分析概览", padding=10)
            summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

            summary_text = (
                f"样本总数: {getattr(report, 'total_texts', 0)}    "
                f"聚类总数: {getattr(report, 'total_clusters', 0)}    "
                f"方法: {getattr(report, 'method', 'greedy')}    "
                f"阈值: {getattr(report, 'threshold', 0):.2f}"
            )
            ttk.Label(summary_frame, text=summary_text).pack(anchor=tk.W)

            stats = getattr(report, "statistics", {}) or {}
            stats_text = (
                f"平均簇大小: {stats.get('avg_cluster_size', 0):.2f}    "
                f"平均簇内相似度: {stats.get('avg_intra_similarity', 0):.3f}    "
                f"最大簇大小: {stats.get('max_cluster_size', 0)}    "
                f"单样本簇: {stats.get('singleton_count', 0)}"
            )
            ttk.Label(summary_frame, text=stats_text, foreground="gray").pack(anchor=tk.W, pady=(5, 0))

            text_frame = ttk.LabelFrame(outer, text="聚类详情", padding=10)
            text_frame.grid(row=1, column=0, sticky="nsew")
            text_frame.rowconfigure(0, weight=1)
            text_frame.columnconfigure(0, weight=1)

            analysis_text = tk.Text(text_frame, wrap=tk.WORD)
            analysis_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=analysis_text.yview)
            analysis_text.configure(yscrollcommand=analysis_scroll.set)

            lines = []
            for idx, cluster in enumerate(report.clusters, start=1):
                keywords = "、".join(cluster.centroid_keywords[:8]) if getattr(cluster, "centroid_keywords", None) else ""
                lines.append(f"【簇{idx}】{cluster.member_count}条")
                lines.append(f"关键词: {keywords or '无'}")
                lines.append(f"簇内相似度: {cluster.intra_similarity:.3f}")
                for sample_text in cluster.texts[:3]:
                    preview = sample_text[:60]
                    if len(sample_text) > 60:
                        preview += "..."
                    lines.append(f"- {preview}")
                lines.append("")

            analysis_text.insert("1.0", "\n".join(lines).strip())
            analysis_text.configure(state=tk.DISABLED)
            analysis_text.grid(row=0, column=0, sticky="nsew")
            analysis_scroll.grid(row=0, column=1, sticky="ns")

            fit_window_to_content(analysis_win, default_size=(760, 560))

        def on_double_click(event):
            sel = tree.selection()
            if not sel:
                return
            # iid format: "{sample_idx}_{reply_idx}"
            parts = sel[0].split("_")
            idx = int(parts[0])
            current_samples = self.preview_manager.get_all_samples()
            if idx < 0 or idx >= len(current_samples):
                return
            sample = current_samples[idx]

            edit_win = tk.Toplevel(view_win)
            edit_win.title(f"查看/编辑样本 #{idx + 1}")
            edit_win.geometry("500x400")
            apply_window_icon(edit_win)

            parent_row, parent_entry = create_labeled_entry_row(
                edit_win,
                "问题",
                sample.get('parent_message', ''),
                width=60,
            )
            parent_row.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(edit_win, text="回复内容:").pack(anchor=tk.W, padx=10, pady=5)
            reply_text = tk.Text(edit_win, height=8, wrap=tk.WORD)
            reply_text.pack(fill=tk.X, padx=10)
            reply_text.insert(tk.END, sample.get('replies', [''])[0])

            ttk.Label(edit_win, text="场景标签:").pack(anchor=tk.W, padx=10, pady=5)
            scene_combo = ttk.Combobox(edit_win, values=SCENE_TAGS, width=30)
            scene_combo.pack(anchor=tk.W, padx=10)
            scene_combo.set(sample.get('scene_tag', '') or "")

            def save_changes():
                new_parent = parent_entry.get().strip()
                new_reply = reply_text.get("1.0", tk.END).strip()
                new_scene = scene_combo.get()

                if new_parent and new_reply:
                    self.preview_manager.update_sample(
                        idx,
                        parent_message=new_parent,
                        replies=[new_reply],
                        scene_tag=new_scene
                    )
                    refresh_list()
                    self._update_sample_count()
                    messagebox.showinfo("成功", f"样本 #{idx + 1} 已更新", parent=edit_win)
                    edit_win.destroy()
                else:
                    messagebox.showwarning("提示", "问题和回复不能为空", parent=edit_win)

            edit_btn_frame = ttk.Frame(edit_win)
            edit_btn_frame.pack(fill=tk.X, pady=10)
            ttk.Button(edit_btn_frame, text="保存修改", command=save_changes).pack(side=tk.LEFT, padx=10)
            ttk.Button(edit_btn_frame, text="关闭", command=edit_win.destroy).pack(side=tk.LEFT, padx=10)
            fit_window_to_content(edit_win, default_size=(640, 480))

        tree.bind('<Double-1>', on_double_click)

        def on_delete():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("提示", "请选择要删除的样本", parent=view_win)
                return

            # iid format: "{sample_idx}_{reply_idx}" — deduplicate by sample_idx
            sample_indices = sorted(set(int(s.split("_")[0]) for s in sel), reverse=True)

            count = len(sample_indices)
            current_samples = self.preview_manager.get_all_samples()
            preview = current_samples[sample_indices[-1]].get('parent_message', '')[:20] if current_samples else ""

            msg = f"确定删除 {count} 条样本？\n\n"
            if count == 1:
                msg = f"确定删除第{sample_indices[-1] + 1}条样本？\n\n问题: {preview}..."

            if messagebox.askyesno("确认删除", msg, parent=view_win):
                success_count = 0
                for idx in sample_indices:
                    result = self.api_client.delete_sample(idx)
                    if result['success']:
                        success_count += 1

                refresh_list()
                self._update_sample_count()
                messagebox.showinfo("成功", f"已删除 {success_count} 条样本", parent=view_win)
                restore_view_samples_focus(view_win, tree)

        ttk.Button(btn_frame, text="聚类分析", command=open_cluster_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中", command=on_delete).pack(side=tk.LEFT, padx=5)
        ttk.Label(btn_frame, text="双击行可查看/编辑").pack(side=tk.LEFT, padx=20)
        ttk.Button(btn_frame, text="关闭", command=view_win.destroy).pack(side=tk.LEFT, padx=20)
        fit_window_to_content(view_win, default_size=(980, 680))

    def _delete_by_index(self):
        total_samples = self.preview_manager.get_sample_count()
        if total_samples == 0:
            messagebox.showwarning("提示", "当前无样本可删除")
            return

        index = int(self.delete_index_spin.get()) - 1
        if index < 0 or index >= total_samples:
            messagebox.showwarning("提示", f"无效索引，当前样本范围: 1-{total_samples}")
            return

        samples = self.preview_manager.get_all_samples()
        preview = samples[index].get('parent_message', '')[:30]

        msg1 = f"第一步确认：删除第 {index + 1} 条样本？\n\n问题: {preview}..."
        if not messagebox.askyesno("删除确认", msg1):
            return

        msg2 = f"第二步确认：再次确认删除第 {index + 1} 条样本？\n\n此操作不可撤销！"
        if not messagebox.askyesno("删除确认", msg2):
            return

        result = self.api_client.delete_sample(index)
        if result['success']:
            self._update_sample_count()
            self.status_label.config(text=f"已删除第 {index + 1} 条样本")
            messagebox.showinfo("成功", f"已删除第 {index + 1} 条样本")
        else:
            messagebox.showerror("错误", "删除失败")
    
    def _reset_data(self):
        if not messagebox.askyesno("第一步确认", "确定要重置为默认数据？\n\n当前所有样本将被清除！"):
            return
        
        if not messagebox.askyesno("第二步确认",
                                    "再次确认：是否重置？\n\n此操作不可撤销！"):
            return
        
        if not messagebox.askyesno("最终确认",
                                    "最后一次确认：重置数据？\n\n点击'是'将执行重置。"):
            return
        
        self.preview_manager.reset_to_default()
        self._update_sample_count()
        self.status_label.config(text="已重置为默认数据")
        messagebox.showinfo("完成", "数据已重置为默认样本")
    
    def _queue_ui_call(self, callback):
        try:
            self.root.after(0, callback)
        except tk.TclError:
            return
    
    def _setup_tray(self):
        if not HAS_TRAY or self._tray_initialized:
            return
        
        icon_image = load_app_icon_image(size=64)
        if icon_image is None and Image is not None:
            icon_image = Image.new('RGBA', (64, 64), color=(66, 133, 244, 255))
        elif icon_image is None:
            return
        
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda *_: self._queue_ui_call(self._show_window), default=True),
            pystray.MenuItem("完全退出", lambda *_: self._queue_ui_call(self._quit_app))
        )

        self._tray_icon = pystray.Icon("QuickReplyAssistant", icon_image, "快捷回复助手", menu)
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()
        self._tray_initialized = True
    
    def _setup_hotkey(self):
        self._shutdown_hotkey()
        if not HAS_HOTKEY:
            return
        hotkey = (self._hotkey or "").strip()
        if not hotkey:
            return
        self._global_hotkey_manager = GlobalHotkeyManager(hotkey)
        if not self._global_hotkey_manager.start():
            self.status_label.config(text="快捷键设置无效")
            return
        self._poll_hotkey_signal()

    def _shutdown_hotkey(self):
        try:
            if self._hotkey_poll_after_id:
                self.root.after_cancel(self._hotkey_poll_after_id)
        except tk.TclError:
            pass
        self._hotkey_poll_after_id = None
        if self._global_hotkey_manager:
            self._global_hotkey_manager.stop()
        self._global_hotkey_manager = None
        self._hotkey_sequence = None

    def _poll_hotkey_signal(self):
        if self._is_quitting:
            self._hotkey_poll_after_id = None
            return
        if self._global_hotkey_manager and self._global_hotkey_manager.triggered.is_set():
            self._global_hotkey_manager.triggered.clear()
            self._show_window()
        try:
            self._hotkey_poll_after_id = self.root.after(120, self._poll_hotkey_signal)
        except tk.TclError:
            self._hotkey_poll_after_id = None
    
    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.query_entry.focus_set()
        if self._tray_icon:
            try:
                self._tray_icon.visible = False
            except Exception:
                pass
        
        try:
            self.root.update_idletasks()
            
            root_hwnd = ctypes.windll.user32.FindWindowW(None, self.root.title())
            if root_hwnd:
                ctypes.windll.user32.ShowWindow(root_hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(root_hwnd)
                ctypes.windll.user32.BringWindowToTop(root_hwnd)
        except Exception:
            pass

    def _shutdown_background(self):
        self._shutdown_hotkey()
        if self._tray_icon:
            try:
                self._tray_icon.visible = False
            except Exception:
                pass
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        self._tray_thread = None
        self._tray_initialized = False

    def _go_home(self):
        if self._is_quitting:
            return
        self._is_quitting = True
        self._next_action = "home"
        self._shutdown_background()
        self.root.quit()
    
    def _on_close_window(self):
        if self._is_quitting:
            return
        self._setup_tray()
        self.root.withdraw()
        if self._tray_icon:
            try:
                self._tray_icon.visible = True
            except Exception:
                pass
    
    def _quit_app(self):
        self._is_quitting = True
        self._next_action = "quit"
        self._shutdown_background()
        self.root.quit()

    def show(self):
        self.root.mainloop()
        return self._next_action


class AccountMainWindow:
    """账号模式主窗口"""
    
    def __init__(self, root, api_client, user_id):
        self.api_client = api_client
        self.user_id = user_id
        
        reset_ttkbootstrap_style()
        self.root = root
        self.root.title(f"快捷回复助手 - {user_id}")
        self.root.geometry("650x550")
        apply_window_icon(self.root)
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        
        self._candidates = []
        self._source_highlight_color = DEFAULT_SOURCE_HIGHLIGHT_COLOR
        self._reply_highlight_color = DEFAULT_REPLY_HIGHLIGHT_COLOR
        self._next_action = None
        self._setup_ui()
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        fit_window_to_content(self.root, default_size=(780, 580))
    
    def _setup_ui(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"账号模式: {self.user_id}",
                  foreground="green").pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="❓ 帮助", width=8,
                   command=lambda: HelpWindow(self.root)).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(header_frame, text="🏠", width=3, command=self._go_home).pack(side=tk.RIGHT, padx=(0, 5))

        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        query_row = ttk.Frame(input_frame)
        query_row.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(query_row, text="问题").pack(side=tk.LEFT, padx=(0, 5))
        self.query_entry = ttk.Entry(query_row, width=50)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.query_entry.bind('<Return>', self._on_search)
        
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="场景:").pack(side=tk.LEFT)
        self.scene_combo = ttk.Combobox(filter_frame, values=SCENE_TAGS, width=12, state="readonly")
        self.scene_combo.pack(side=tk.LEFT, padx=5)
        self.scene_combo.set("")
        
        ttk.Label(filter_frame, text="阶段:").pack(side=tk.LEFT, padx=10)
        self.stage_combo = ttk.Combobox(filter_frame, values=STAGE_TAGS, width=12, state="readonly")
        self.stage_combo.pack(side=tk.LEFT, padx=5)
        self.stage_combo.set("")
        
        ttk.Button(filter_frame, text="生成回复",
                   command=self._on_search).pack(side=tk.LEFT, padx=10)
        
        result_frame = ttk.LabelFrame(self.root, text="候选回复")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.result_text = tk.Text(result_frame, height=12, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 28))
        
        ttk.Button(btn_frame, text="复制第一条",
                   command=self._copy_first).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="复制第二条",
                   command=self._copy_second).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="复制第三条",
                   command=self._copy_third).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(btn_frame, text="")
        self.status_label.pack(side=tk.RIGHT, padx=5)

    def _go_home(self):
        self._next_action = "home"
        self.root.quit()

    def _refresh_result_highlight(self):
        self.result_text.tag_configure("source_text", background=self._source_highlight_color)
        self.result_text.tag_configure("reply_text", background=self._reply_highlight_color)

    def _render_candidates(self):
        self._refresh_result_highlight()
        self.result_text.delete("1.0", tk.END)

        for i, candidate in enumerate(self._candidates):
            insert_candidate_display(
                self.result_text,
                i,
                candidate,
                source_highlight_tag="source_text",
                reply_highlight_tag="reply_text",
            )
    
    def _on_search(self, event=None):
        query = self.query_entry.get().strip()
        if not query:
            self.status_label.config(text="请输入问题")
            return
        
        self.status_label.config(text="生成中...")
        
        try:
            result = self.api_client.generate_reply(
                query=query,
                scene_hint=self.scene_combo.get() if self.scene_combo.get() else None
            )
            self._candidates = result.get('candidates', [])
            self._render_candidates()
            
            self.status_label.config(text=f"完成 ({result.get('model_used', '')})")
        except Exception as e:
            self.status_label.config(text=f"错误: {e}")
    
    def _copy_candidate(self, idx):
        if idx < len(self._candidates):
            self.root.clipboard_clear()
            self.root.clipboard_append(self._candidates[idx].get('content', ''))
            self.status_label.config(text=f"已复制候选{idx + 1}")
    
    def _copy_first(self): self._copy_candidate(0)
    def _copy_second(self): self._copy_candidate(1)
    def _copy_third(self): self._copy_candidate(2)
    
    def show(self):
        self.root.mainloop()
        return self._next_action
