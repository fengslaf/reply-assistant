"""个人数据系统 GUI 模块。

从 start_gui.py 中提取的 PersonalDataSettingsWindow 和 PersonalDataMainWindow。
"""

import os
import threading
import ctypes
import json
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from gui_utils import (
    reset_ttkbootstrap_style, apply_window_icon, get_personal_icon_path,
    apply_native_ttk_theme,
    apply_plain_ttk_palette, fit_window_to_content, load_app_icon_image,
    GlobalHotkeyManager, hotkey_to_tk_sequence,
    create_labeled_entry_row, restore_view_samples_focus,
    # personal data display helpers
    format_personal_courses, format_personal_course_part,
    get_personal_tree_columns, get_personal_tree_headings,
    personal_record_table_values, personal_record_table_rows,
    format_personal_record_card,
    personal_record_count_text,
    # constants
    HAS_TRAY, HAS_HOTKEY,
    Image, ImageTk, pystray,
    # help
    HelpWindow,
)

from personal_data import (
    PersonalDataManager, parse_personal_record, get_personal_data_format_example,
    get_format_config_line, save_format_config,
)


PERSONAL_ICON_PATH = get_personal_icon_path()


class PersonalDataSettingsWindow:
    """个人数据系统设置窗口。"""

    def __init__(self, parent, data_manager, on_import_data=None, on_view_records=None, on_clear_data=None, on_save=None):
        self.win = tk.Toplevel(parent)
        self.win.title("个人数据系统设置")
        apply_window_icon(self.win, icon_path=PERSONAL_ICON_PATH)
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        self.data_manager = data_manager
        self.on_import_data = on_import_data
        self.on_view_records = on_view_records
        self.on_clear_data = on_clear_data
        self.on_save = on_save
        self.display_mode_var = tk.StringVar(
            value="表格展示" if self.data_manager.get_display_mode() == "table" else "卡片展示"
        )
        self.hotkey_var = tk.StringVar(value=self.data_manager.get_hotkey())
        self.format_line_var = tk.StringVar(value=get_format_config_line())
        self._setup_ui()
        apply_native_ttk_theme(self.win)
        apply_plain_ttk_palette(self.win)
        fit_window_to_content(self.win, default_size=(620, 420))

    def _setup_ui(self):
        storage_frame = ttk.LabelFrame(self.win, text="数据存储", padding=10)
        storage_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(storage_frame, text=f"独立数据目录: {self.data_manager.data_dir}").pack(anchor=tk.W)

        action_row = ttk.Frame(storage_frame)
        action_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(action_row, text="导入数据", command=self._on_import_data).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="清除数据", command=self._on_clear_data).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="查看记录", command=self._on_view_records).pack(side=tk.LEFT)

        display_frame = ttk.LabelFrame(self.win, text="展示设置", padding=10)
        display_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Label(display_frame, text="展示方式:").pack(anchor=tk.W)
        ttk.Combobox(
            display_frame,
            values=["卡片展示", "表格展示"],
            width=18,
            textvariable=self.display_mode_var,
            state="readonly",
        ).pack(anchor=tk.W, pady=(4, 0))

        hotkey_frame = ttk.LabelFrame(self.win, text="快捷键设置", padding=10)
        hotkey_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Label(hotkey_frame, text="全局唤起快捷键:").pack(anchor=tk.W)
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=22).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(hotkey_frame, text="建议格式：ctrl+shift+y", foreground="gray").pack(anchor=tk.W, pady=(4, 0))

        format_frame = ttk.LabelFrame(self.win, text="数据解析格式", padding=10)
        format_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Label(format_frame, text="格式定义（中文逗号分隔，括号内为枚举选项）:").pack(anchor=tk.W)
        ttk.Entry(format_frame, textvariable=self.format_line_var, width=60).pack(fill=tk.X, pady=(4, 0))
        ttk.Label(format_frame, text="示例：姓名，电话，年级，季节（ABCD），科目，班型", foreground="gray").pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(format_frame, text="修改后保存并重启生效。A=寒 B=春 C=暑 D=秋", foreground="gray").pack(anchor=tk.W)

        footer = ttk.Frame(self.win)
        footer.pack(fill=tk.X, padx=10, pady=(0, 12))
        ttk.Button(footer, text="保存并关闭", command=self._on_close).pack(side=tk.RIGHT)

    def _on_import_data(self):
        if self.on_import_data:
            self.on_import_data()

    def _on_view_records(self):
        if self.on_view_records:
            self.on_view_records()

    def _on_clear_data(self):
        if self.on_clear_data:
            self.on_clear_data()

    def _on_close(self):
        self.data_manager.set_display_mode("table" if self.display_mode_var.get() == "表格展示" else "card")
        self.data_manager.set_hotkey(self.hotkey_var.get())
        # 保存解析格式配置
        new_format_line = self.format_line_var.get().strip()
        if new_format_line:
            save_format_config(new_format_line)
        if self.on_save:
            self.on_save(
                "table" if self.display_mode_var.get() == "表格展示" else "card",
                self.hotkey_var.get(),
            )
        self.win.destroy()


class PersonalDataMainWindow:
    """个人数据系统主窗口。"""

    def __init__(self, root, data_manager):
        self.data_manager = data_manager
        reset_ttkbootstrap_style()
        self.root = root
        self.root.title("个人数据系统")
        self.root.geometry("860x660")
        apply_window_icon(self.root, icon_path=PERSONAL_ICON_PATH)
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        style = ttk.Style(self.root)
        style.configure("Personal.Treeview", rowheight=44)
        style.configure("Personal.Treeview.Heading", padding=(10, 9))

        self._next_action = None
        self._last_results = []
        self.summary_var = tk.StringVar(value="请输入姓名、电话、课程或原始文本进行检索")
        self._display_mode = self.data_manager.get_display_mode()
        self._hotkey = self.data_manager.get_hotkey()
        self._hotkey_sequence = None
        self._global_hotkey_manager = None
        self._hotkey_poll_after_id = None
        self._tray_icon = None
        self._tray_thread = None
        self._tray_initialized = False
        self._is_quitting = False

        self._setup_ui()
        apply_native_ttk_theme(self.root)
        apply_plain_ttk_palette(self.root)
        fit_window_to_content(self.root, default_size=(920, 700))
        self._setup_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)

    def _setup_ui(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=14, pady=(8, 6))
        header_frame.columnconfigure(1, weight=1)

        ttk.Label(
            header_frame,
            text="个人数据系统：本地资料检索",
            font=("Microsoft YaHei", 11),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(header_frame, text="👤 local_profile_db").grid(row=0, column=1, sticky="w", padx=20)

        header_actions = ttk.Frame(header_frame)
        header_actions.grid(row=0, column=2, sticky="e")
        ttk.Button(header_actions, text="🏠", width=3, command=self._go_home).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(header_actions, text="❓", width=3, command=self._show_help).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(header_actions, text="⚙", width=3, command=self._show_settings).pack(side=tk.LEFT)

        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=14, pady=5)
        ttk.Label(input_frame, text="检索").pack(side=tk.LEFT, padx=(0, 6))
        self.query_entry = ttk.Entry(input_frame, width=58)
        self.query_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.query_entry.bind("<Return>", self._on_search)
        ttk.Button(input_frame, text="检索", width=8, command=self._on_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="粘贴", width=8, command=self._paste_from_clipboard).pack(side=tk.LEFT, padx=5)

        summary_frame = ttk.Frame(self.root)
        summary_frame.pack(fill=tk.X, padx=14, pady=(2, 5))
        ttk.Label(summary_frame, textvariable=self.summary_var, foreground="gray").pack(anchor=tk.W)

        result_section = ttk.Frame(self.root)
        result_section.pack(fill=tk.BOTH, expand=True, padx=14, pady=5)

        result_header = ttk.Frame(result_section)
        result_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(result_header, text="检索结果", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
        self.result_count_label = ttk.Label(result_header, text="【0】", foreground="gray")
        self.result_count_label.pack(side=tk.LEFT, padx=(6, 0))
        result_actions = ttk.Frame(result_header)
        result_actions.pack(side=tk.RIGHT)
        ttk.Button(result_actions, text="收藏数据", command=self._favorite_record).pack(side=tk.LEFT, padx=(0, 8))

        result_frame = ttk.Frame(result_section)
        result_frame.pack(fill=tk.BOTH, expand=True)
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        self.result_text = tk.Text(result_frame, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        self.result_text.configure(state=tk.DISABLED)
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=get_personal_tree_columns(),
            show="headings",
            height=14,
            style="Personal.Treeview",
        )
        self.result_tree_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree_xscroll = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(
            yscrollcommand=self.result_tree_scroll.set,
            xscrollcommand=self.result_tree_xscroll.set,
        )
        self._configure_personal_result_tree(self.result_tree)
        self._apply_result_display_mode()

        footer = ttk.Frame(self.root)
        footer.pack(fill=tk.X, padx=14, pady=(8, 36))
        self.status_label = ttk.Label(footer, text="")
        self.status_label.pack(side=tk.RIGHT)

    def _update_result_count(self, count):
        self.result_count_label.config(text=f"【{count}】")

    def _show_help(self):
        HelpWindow(self.root)

    def _show_settings(self):
        PersonalDataSettingsWindow(
            self.root,
            self.data_manager,
            on_import_data=self._import_data,
            on_view_records=self._view_records,
            on_clear_data=self._clear_records,
            on_save=self._on_settings_saved,
        )

    def _on_settings_saved(self, display_mode, hotkey):
        self._display_mode = display_mode
        self._hotkey = (hotkey or "").strip() or self.data_manager.get_hotkey()
        self._setup_hotkey()
        self._apply_result_display_mode()
        if self.query_entry.get().strip():
            self._on_search()

    def _configure_personal_result_tree(self, tree):
        """配置驱动的表格列配置。根据 FormatConfig 动态生成表头和列宽。"""
        headings = get_personal_tree_headings()
        for col_id, heading_text in headings:
            tree.heading(col_id, text=heading_text, anchor=tk.CENTER)
            width = 150 if col_id == "name" else 130 if col_id == "phone" else 120
            tree.column(col_id, width=width, minwidth=120, stretch=True, anchor=tk.CENTER)
        tree.tag_configure("group_even", background="white", foreground="black")
        tree.tag_configure("group_odd", background="#f7f7f7", foreground="black")

    def _apply_result_display_mode(self):
        self.result_text.grid_remove()
        self.result_tree.grid_remove()
        self.result_tree_scroll.grid_remove()
        self.result_tree_xscroll.grid_remove()
        if self._display_mode == "table":
            self.result_tree.grid(row=0, column=0, sticky="nsew")
            self.result_tree_scroll.grid(row=0, column=1, sticky="ns")
            self.result_tree_xscroll.grid(row=1, column=0, sticky="ew")
        else:
            self.result_text.grid(row=0, column=0, sticky="nsew")

    def _populate_result_tree(self, results):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        for record_index, record in enumerate(results):
            group_tag = "group_even" if record_index % 2 == 0 else "group_odd"
            for course_index, row_values in enumerate(personal_record_table_rows(record)):
                self.result_tree.insert(
                    "",
                    tk.END,
                    iid=f"{record['id']}::{course_index}",
                    values=row_values,
                    tags=(group_tag,),
                )

    def _show_search_results(self, results, summary_info):
        self._last_results = results
        self._update_result_count(len(results))
        self._apply_result_display_mode()

        if self._display_mode == "table":
            self._populate_result_tree(results)
            return

        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)

        if summary_info and summary_info.get("summary"):
            source_type = summary_info.get("source_type", "personal_structured")
            confidence = summary_info.get("confidence", 0.0) or 0.0
            summary_line = f"摘要: {summary_info['summary']}\n来源: {source_type}（置信{confidence:.0%}）\n\n"
            self.result_text.insert(tk.END, summary_line)

        for index, record in enumerate(results):
            payload = dict(record)
            payload.setdefault("source_type", "personal_structured")
            self.result_text.insert(tk.END, format_personal_record_card(payload, index))
            self.result_text.insert(tk.END, "\n===========\n")

        if not results:
            self.result_text.insert(tk.END, "未找到匹配记录")

        self.result_text.configure(state=tk.DISABLED)

    def _on_search(self, event=None):
        query = self.query_entry.get().strip()
        if not query:
            self.status_label.config(text="请输入检索内容")
            return

        results = self.data_manager.search_records(query, top_k=20)
        summary = self.data_manager.generate_search_summary(query, results)
        self.summary_var.set(summary.get("summary") or "未找到匹配记录")
        self._show_search_results(results, summary)
        self.status_label.config(text=f"完成（{len(results)} 条）")

    def _paste_from_clipboard(self):
        try:
            clipboard = self.root.clipboard_get()
        except tk.TclError:
            self.status_label.config(text="剪贴板无内容")
            return
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, clipboard)
        self._on_search()

    def _favorite_record(self):
        favorite_win = tk.Toplevel(self.root)
        favorite_win.title("收藏数据")
        apply_window_icon(favorite_win, icon_path=PERSONAL_ICON_PATH)
        apply_native_ttk_theme(favorite_win)
        apply_plain_ttk_palette(favorite_win)

        ttk.Label(favorite_win, text=get_personal_data_format_example()).pack(anchor=tk.W, padx=10, pady=(10, 6))
        raw_text = tk.Text(favorite_win, height=8, wrap=tk.WORD)
        raw_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        raw_text.insert(tk.END, "李某某三年级13777778777春秋数学提分A班")

        type_row = ttk.Frame(favorite_win)
        type_row.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(type_row, text="数据类型").pack(side=tk.LEFT, padx=(0, 6))
        record_type_combo = ttk.Combobox(
            type_row,
            values=["student_profile", "custom_profile"],
            width=18,
            state="readonly",
        )
        record_type_combo.pack(side=tk.LEFT)
        record_type_combo.set("student_profile")

        def save_favorite():
            lines = [line for line in raw_text.get("1.0", tk.END).splitlines() if line.strip()]
            if not lines:
                messagebox.showwarning("提示", "请输入要收藏的数据", parent=favorite_win)
                return
            imported = self.data_manager.import_text_lines(lines, record_type=record_type_combo.get())
            self.status_label.config(text=f"已收藏 {len(imported)} 条数据")
            messagebox.showinfo("成功", f"已收藏 {len(imported)} 条数据", parent=favorite_win)
            favorite_win.destroy()

        footer = ttk.Frame(favorite_win)
        footer.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(footer, text="确认保存", command=save_favorite).pack(side=tk.LEFT)
        ttk.Button(footer, text="取消", command=favorite_win.destroy).pack(side=tk.LEFT, padx=(8, 0))
        fit_window_to_content(favorite_win, default_size=(620, 360))

    def _import_data(self):
        file_path = filedialog.askopenfilename(
            title="导入个人资料数据",
            filetypes=[("文本文件", "*.txt"), ("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        lines = []
        try:
            path = Path(file_path)
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, str):
                            lines.append(item)
                        elif isinstance(item, dict):
                            lines.append(item.get("raw_text") or item.get("text") or "")
                elif isinstance(payload, dict):
                    for item in payload.get("records", []):
                        if isinstance(item, str):
                            lines.append(item)
                        elif isinstance(item, dict):
                            lines.append(item.get("raw_text") or item.get("text") or "")
            else:
                lines = path.read_text(encoding="utf-8").splitlines()

            imported = self.data_manager.import_text_lines(lines)
            self.status_label.config(text=f"已导入 {len(imported)} 条资料")
            messagebox.showinfo("导入成功", f"已导入 {len(imported)} 条资料", parent=self.root)
        except Exception as exc:
            messagebox.showerror("错误", f"导入失败: {exc}", parent=self.root)

    def _view_records(self):
        records = self.data_manager.get_all_records()

        view_win = tk.Toplevel(self.root)
        view_win.title("个人资料列表")
        apply_window_icon(view_win, icon_path=PERSONAL_ICON_PATH)
        apply_native_ttk_theme(view_win)
        apply_plain_ttk_palette(view_win)

        style = ttk.Style(view_win)
        style.configure("Personal.Treeview", rowheight=44)
        style.configure("Personal.Treeview.Heading", padding=(10, 9))

        body = ttk.Frame(view_win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            body,
            columns=get_personal_tree_columns(),
            show="headings",
            height=16,
            style="Personal.Treeview",
        )
        yscroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=tree.yview)
        xscroll = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self._configure_personal_result_tree(tree)

        def reload_rows():
            for item in tree.get_children():
                tree.delete(item)
            current_records = self.data_manager.get_all_records()
            for record_index, record in enumerate(current_records):
                group_tag = "group_even" if record_index % 2 == 0 else "group_odd"
                for course_index, row_values in enumerate(personal_record_table_rows(record)):
                    tree.insert(
                        "",
                        tk.END,
                        iid=f"{record['id']}::{course_index}",
                        tags=(record["id"], group_tag),
                        values=row_values,
                    )
            count_label.config(text=personal_record_count_text(len(current_records)))

        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        button_bar = ttk.Frame(view_win)
        button_bar.pack(fill=tk.X, padx=10, pady=(0, 6))
        ttk.Button(button_bar, text="删除选中", command=lambda: on_delete()).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_bar, text="关闭", command=view_win.destroy).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(button_bar, text="双击行可查看/编辑").pack(side=tk.LEFT)
        count_label = ttk.Label(button_bar, text=personal_record_count_text(len(records)))
        count_label.pack(side=tk.RIGHT)

        def open_editor(record_id):
            current_records = {item["id"]: item for item in self.data_manager.get_all_records()}
            record = current_records.get(record_id)
            if not record:
                return

            edit_win = tk.Toplevel(view_win)
            edit_win.title("查看/编辑个人资料")
            apply_window_icon(edit_win, icon_path=PERSONAL_ICON_PATH)

            name_row, name_entry = create_labeled_entry_row(edit_win, "姓名", record.get("name", ""), width=40)
            name_row.pack(fill=tk.X, padx=10, pady=5)
            phone_row, phone_entry = create_labeled_entry_row(edit_win, "电话", record.get("phone", ""), width=40)
            phone_row.pack(fill=tk.X, padx=10, pady=5)
            grade_row, grade_entry = create_labeled_entry_row(edit_win, "记录年级", record.get("recorded_grade", ""), width=40)
            grade_row.pack(fill=tk.X, padx=10, pady=5)
            courses_row, courses_entry = create_labeled_entry_row(
                edit_win,
                "课程/班型",
                format_personal_courses(record.get("courses", [])),
                width=56,
            )
            courses_row.pack(fill=tk.X, padx=10, pady=5)

            ttk.Label(edit_win, text="原始内容:").pack(anchor=tk.W, padx=10, pady=5)
            raw_text = tk.Text(edit_win, height=6, wrap=tk.WORD)
            raw_text.pack(fill=tk.BOTH, expand=True, padx=10)
            raw_text.insert(tk.END, record.get("raw_text", ""))

            def save_record():
                parsed = parse_personal_record(raw_text.get("1.0", tk.END).strip(), recorded_at=record.get("recorded_at"))
                parsed["name"] = name_entry.get().strip() or parsed.get("name", "")
                parsed["phone"] = phone_entry.get().strip() or parsed.get("phone", "")
                parsed["recorded_grade"] = grade_entry.get().strip() or parsed.get("recorded_grade", "")
                parsed["id"] = record["id"]
                parsed["created_at"] = record.get("created_at")
                parsed["updated_at"] = datetime.now().replace(microsecond=0).isoformat()
                self.data_manager.update_record(
                    record["id"],
                    raw_text=raw_text.get("1.0", tk.END).strip(),
                    name=parsed["name"],
                    phone=parsed["phone"],
                    recorded_grade=parsed["recorded_grade"],
                    recorded_at=record.get("recorded_at"),
                    courses=parsed["courses"],
                    parse_status=parsed["parse_status"],
                )
                reload_rows()
                if self.query_entry.get().strip():
                    self._on_search()
                messagebox.showinfo("成功", "资料已更新", parent=edit_win)
                edit_win.destroy()

            footer = ttk.Frame(edit_win)
            footer.pack(fill=tk.X, padx=10, pady=10)
            ttk.Button(footer, text="保存修改", command=save_record).pack(side=tk.LEFT)
            ttk.Button(footer, text="关闭", command=edit_win.destroy).pack(side=tk.LEFT, padx=(8, 0))
            fit_window_to_content(edit_win, default_size=(660, 480))

        def on_double_click(event):
            selection = tree.selection()
            if selection:
                tags = tree.item(selection[0], "tags")
                record_id = tags[0] if tags else selection[0].split("::", 1)[0]
                open_editor(record_id)

        def on_delete():
            selection = list(tree.selection())
            if not selection:
                messagebox.showwarning("提示", "请选择要删除的记录", parent=view_win)
                return
            record_ids = []
            for item_id in selection:
                tags = tree.item(item_id, "tags")
                record_id = tags[0] if tags else item_id.split("::", 1)[0]
                if record_id not in record_ids:
                    record_ids.append(record_id)
            if not messagebox.askyesno("确认删除", f"确定删除 {len(record_ids)} 条记录吗？", parent=view_win):
                return
            deleted = 0
            for record_id in record_ids:
                deleted += 1 if self.data_manager.delete_record(record_id) else 0
            reload_rows()
            if self.query_entry.get().strip():
                self._on_search()
            messagebox.showinfo("成功", f"已删除 {deleted} 条记录", parent=view_win)
            restore_view_samples_focus(view_win, tree)

        tree.bind("<Double-1>", on_double_click)
        reload_rows()
        fit_window_to_content(view_win, default_size=(980, 680))

    def _clear_records(self):
        if not messagebox.askyesno("确认清除", "确定清除个人数据系统中的全部记录吗？", parent=self.root):
            return
        self.data_manager.clear_all_records()
        self.summary_var.set("个人数据已清空")
        self._show_search_results([], {"summary": "", "source_type": "personal_structured", "confidence": 0.0})
        self.status_label.config(text="已清空全部记录")

    def _go_home(self):
        self._is_quitting = True
        self._shutdown_background()
        self._shutdown_hotkey()
        self._next_action = "home"
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

    def _setup_tray(self):
        if not HAS_TRAY or self._tray_initialized:
            return

        icon_image = None
        if PERSONAL_ICON_PATH.exists() and Image is not None:
            try:
                icon_image = Image.open(str(PERSONAL_ICON_PATH)).convert("RGBA")
                icon_image = icon_image.resize((64, 64), Image.LANCZOS)
            except Exception:
                icon_image = None
        if icon_image is None:
            icon_image = load_app_icon_image(size=64)
        if icon_image is None and Image is not None:
            icon_image = Image.new("RGBA", (64, 64), color=(66, 133, 244, 255))
        elif icon_image is None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda *_: self._queue_ui_call(self._show_window), default=True),
            pystray.MenuItem("完全退出", lambda *_: self._queue_ui_call(self._quit_app)),
        )

        self._tray_icon = pystray.Icon("QuickReplyAssistantPersonal", icon_image, "个人数据系统", menu)
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()
        self._tray_initialized = True

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

    def _quit_app(self):
        self._is_quitting = True
        self._next_action = "quit"
        self._shutdown_background()
        self.root.quit()

    def _queue_ui_call(self, callback):
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

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

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.query_entry.focus_set()

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

    def show(self):
        self.root.mainloop()
        return self._next_action
