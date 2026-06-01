#!/usr/bin/env python3
"""客户数据系统独立入口 - 启动客户数据系统"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path
_root = Path(__file__).parent
sys.path.insert(0, str(_root))

import gui_utils  # noqa: F401 — 触发 DPI awareness + tkinter 初始化


def run_personal_app():
    """客户数据系统主循环：首页 → 客户数据 → 首页 ..."""
    import tkinter as tk

    from gui_utils import get_app_base_dir
    from personal_data import PersonalDataManager
    from start_gui import ProductHomeWindow, PersonalDataMainWindow

    personal_data_manager = None
    root = tk.Tk()
    root.withdraw()
    try:
        while True:
            for child in root.winfo_children():
                child.destroy()
            root.update()

            home = ProductHomeWindow(root, mode="personal")
            root.deiconify()
            module_name = home.show()
            if not module_name:
                return

            root.withdraw()
            root.update()

            if module_name == "personal_data":
                if personal_data_manager is None:
                    personal_data_manager = PersonalDataManager(base_dir=get_app_base_dir() / "data")

                for child in root.winfo_children():
                    child.destroy()
                root.update()

                win = PersonalDataMainWindow(root, personal_data_manager)
                root.deiconify()
                action = win.show()
                if action == "home":
                    root.withdraw()
                    root.update()
                    continue
                return
            # 如果首页选择了 reply_assistant，忽略（本入口只处理客户数据）
            # 返回首页继续循环
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def main():
    return run_personal_app()


if __name__ == '__main__':
    main()
