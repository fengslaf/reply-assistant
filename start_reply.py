#!/usr/bin/env python3
"""回复助手独立入口 - 启动回复助手系统"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path
_root = Path(__file__).parent
sys.path.insert(0, str(_root))

import gui_utils  # noqa: F401 — 触发 DPI awareness + tkinter 初始化


def run_reply_app():
    """回复助手主循环：首页 → 回复助手 → 首页 ..."""
    import tkinter as tk

    # 从 start_gui 导入回复助手相关的类
    from start_gui import ProductHomeWindow, LocalMainWindow, _effective_access_mode, _load_home_state
    from preview_mode import PreviewAPIClient, PreviewModeManager

    preview_api_client = None
    root = tk.Tk()
    root.withdraw()
    try:
        while True:
            for child in root.winfo_children():
                child.destroy()
            root.update()

            home = ProductHomeWindow(root, mode="reply")
            root.deiconify()
            module_name = home.show()
            if not module_name:
                return

            root.withdraw()
            root.update()

            if module_name == "reply_assistant":
                user_id = "local_user"
                if preview_api_client is None:
                    pm = PreviewModeManager()
                    preview_api_client = PreviewAPIClient(pm, user_id)
                api = preview_api_client

                for child in root.winfo_children():
                    child.destroy()
                root.update()

                win = LocalMainWindow(root, api, user_id, access_mode=_effective_access_mode(_load_home_state()))
                root.deiconify()
                action = win.show()
                if action == "home":
                    root.withdraw()
                    root.update()
                    continue
                return
            # 如果首页选择了 personal_data，忽略（本入口只处理回复助手）
            # 返回首页继续循环
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


def main():
    return run_reply_app()


if __name__ == '__main__':
    main()
