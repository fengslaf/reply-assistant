#!/usr/bin/env python3
"""Build script for onefile mode - force correct tkinter binaries."""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

PYTHON_BASE = Path(r"C:\Users\fengshuiliang\AppData\Roaming\uv\python\cpython-3.13.5-windows-x86_64-none")
TCL_PATH = PYTHON_BASE / "tcl"
DLLS_PATH = PYTHON_BASE / "DLLs"

def clean_build():
    for dir_name in ['build', 'dist']:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
    
    for spec in PROJECT_ROOT.glob('*.spec'):
        spec.unlink()

def build_onefile():
    clean_build()
    
    tcl86 = TCL_PATH / "tcl8.6"
    tk86 = TCL_PATH / "tk8.6"
    tkinter_dll = DLLS_PATH / "_tkinter.pyd"
    python_dll = PYTHON_BASE / "python313.dll"
    
    if not tkinter_dll.exists():
        raise RuntimeError(f"_tkinter.pyd not found: {tkinter_dll}")
    if not tcl86.exists():
        raise RuntimeError(f"TCL not found: {tcl86}")
    if not tk86.exists():
        raise RuntimeError(f"TK not found: {tk86}")
    
    runtime_hook = PROJECT_ROOT / "hook_runtime_tk.py"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=QuickReplyAssistant",
        "--clean",
        "--noconfirm",
        "--runtime-hook=" + str(runtime_hook),
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=_tkinter",
        "--hidden-import=preview_mode",
        "--hidden-import=json",
        "--hidden-import=datetime",
        "--hidden-import=re",
        "--hidden-import=sqlite3",
        "--add-binary=" + str(tkinter_dll) + ";.",
        "--add-data=" + str(tcl86) + ";tcl8.6",
        "--add-data=" + str(tk86) + ";tk8.6",
    ]
    
    data_dir = PROJECT_ROOT / "data"
    if data_dir.exists():
        cmd.append("--add-data=" + str(data_dir) + ";data")
    
    preview_mode = PROJECT_ROOT / "preview_mode.py"
    if preview_mode.exists():
        cmd.append("--add-data=" + str(preview_mode) + ";.")
    
    start_gui = PROJECT_ROOT / "start_gui.py"
    if start_gui.exists():
        cmd.append("--add-data=" + str(start_gui) + ";.")
    
    cmd.append(str(PROJECT_ROOT / "run_exe.py"))
    
    print("Building onefile executable...")
    print("_tkinter.pyd:", tkinter_dll)
    print("TCL:", tcl86)
    print("TK:", tk86)
    
    env = os.environ.copy()
    env["PYINSTALLER_SUPPRESS_WARNINGS"] = "1"
    
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    
    exe_path = PROJECT_ROOT / "dist" / "QuickReplyAssistant.exe"
    
    if result.returncode == 0 and exe_path.exists():
        print(f"\nBuild SUCCESS: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
        return True
    
    print("\nBuild FAILED")
    warn_file = PROJECT_ROOT / "build" / "QuickReplyAssistant" / "warn-QuickReplyAssistant.txt"
    if warn_file.exists():
        print("\nWarnings:")
        with open(warn_file, "r", encoding="utf-8") as f:
            print(f.read())
    
    return False

if __name__ == "__main__":
    build_onefile()