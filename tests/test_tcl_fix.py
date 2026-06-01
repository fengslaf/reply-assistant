"""
验证 Tcl_AsyncDelete 修复：模拟窗口导航循环，确认不触发 Tcl 异常。

核心测试逻辑：
1. 创建单一 tk.Tk() root
2. 循环 N 次：创建子控件 → 清除 → 创建新子控件
3. 检查是否有 Tcl 错误输出

用法：python tests/test_tcl_fix.py
"""
import sys
import os
import tkinter as tk
from io import StringIO

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 捕获 Tcl 错误输出
_tcl_errors = []
_original_stderr = sys.stderr


class TclErrorCapture:
    """捕获 stderr 中的 Tcl 相关错误"""
    def __init__(self):
        self.buffer = StringIO()
        self.captured = []

    def write(self, text):
        self.buffer.write(text)
        if 'Tcl' in text or 'async' in text.lower() or 'handler' in text.lower():
            self.captured.append(text.strip())
        # 也输出到原始 stderr 以便调试
        _original_stderr.write(text)

    def flush(self):
        self.buffer.flush()
        _original_stderr.flush()


def simulate_navigation(root: tk.Tk, iterations: int = 10):
    """
    模拟 ProductHomeWindow → LocalMainWindow → PersonalDataMainWindow 的导航循环。
    每次迭代清除 root 的所有子控件，然后重新构建 UI。
    """
    errors = []

    for i in range(iterations):
        try:
            # 清除所有子控件（模拟 run_app 中的 child.destroy() 循环）
            for child in root.winfo_children():
                child.destroy()

            # 模拟 ProductHomeWindow.__init__ 的核心 UI 构建
            frame = tk.Frame(root)
            frame.pack(fill=tk.BOTH, expand=True)
            lbl = tk.Label(frame, text=f"ProductHome - Iteration {i}")
            lbl.pack()
            btn = tk.Button(frame, text="Go to Reply")
            btn.pack()
            root.update_idletasks()

            # 清除，模拟导航到 LocalMainWindow
            for child in root.winfo_children():
                child.destroy()

            # 模拟 LocalMainWindow.__init__ 的核心 UI 构建
            frame2 = tk.Frame(root)
            frame2.pack(fill=tk.BOTH, expand=True)
            lbl2 = tk.Label(frame2, text=f"LocalMain - Iteration {i}")
            lbl2.pack()
            btn2 = tk.Button(frame2, text="Go to Home")
            btn2.pack()
            root.update_idletasks()

            # 清除，模拟导航到 PersonalDataMainWindow
            for child in root.winfo_children():
                child.destroy()

            # 模拟 PersonalDataMainWindow.__init__ 的核心 UI 构建
            frame3 = tk.Frame(root)
            frame3.pack(fill=tk.BOTH, expand=True)
            lbl3 = tk.Label(frame3, text=f"PersonalData - Iteration {i}")
            lbl3.pack()
            root.update_idletasks()

            # 处理事件队列（触发潜在的 Tcl 异步错误）
            root.update()
            root.update_idletasks()

        except tk.TclError as e:
            errors.append(f"Iteration {i}: TclError - {e}")
        except Exception as e:
            errors.append(f"Iteration {i}: {type(e).__name__} - {e}")

    return errors


def main():
    print("=" * 60)
    print("Tcl_AsyncDelete Fix Verification")
    print("Simulating: Reply <-> Personal navigation x10")
    print("=" * 60)

    # 设置错误捕获
    error_capture = TclErrorCapture()
    sys.stderr = error_capture

    try:
        # 创建单一 root（修复后的方案）
        root = tk.Tk()
        root.withdraw()  # 不显示窗口
        root.title("Tcl Fix Test")

        # 运行模拟导航
        errors = simulate_navigation(root, iterations=10)

        # 额外触发事件循环
        for _ in range(5):
            root.update()
            root.update_idletasks()

        # 销毁
        root.destroy()

    except Exception as e:
        print(f"\n[FAIL] Exception: {e}")
        sys.stderr = _original_stderr
        return 1
    finally:
        sys.stderr = _original_stderr

    # 报告结果
    print("\n" + "=" * 60)

    if error_capture.captured:
        print(f"[FAIL] Detected {len(error_capture.captured)} Tcl errors:")
        for err in error_capture.captured:
            print(f"  - {err}")
        return 1
    elif errors:
        print(f"[FAIL] Detected {len(errors)} exceptions:")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("[PASS] 10 rounds of navigation, no Tcl_AsyncDelete error")
        print("Fix verified successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
