#!/usr/bin/env python3
"""Build script - Auto-detect Python environment for PyInstaller onefile"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PRESERVED_DATA_BACKUP = PROJECT_ROOT / ".build_preserved_data"
BUILD_EDITION_MARKER = PROJECT_ROOT / "app_edition.txt"


def get_build_edition() -> str:
    edition = os.environ.get("APP_EDITION", "public").strip().lower()
    return edition if edition in {"public", "private"} else "public"


def write_build_edition_marker() -> Path:
    BUILD_EDITION_MARKER.write_text(get_build_edition(), encoding="utf-8")
    return BUILD_EDITION_MARKER


def cleanup_build_edition_marker() -> None:
    try:
        BUILD_EDITION_MARKER.unlink()
    except FileNotFoundError:
        pass


def detect_python_base():
    """Auto-detect Python installation base directory based on current Python."""
    executable = Path(sys.executable)
    
    # If running from venv, find the base Python
    if 'venv' in str(executable).lower() or 'Scripts' in str(executable):
        # Try pyvenv.cfg to find the base Python
        venv_cfg = executable.parent.parent / 'pyvenv.cfg'
        if venv_cfg.exists():
            with open(venv_cfg, 'r') as f:
                for line in f:
                    if line.startswith('home ='):
                        home = Path(line.split('=')[1].strip())
                        if (home / 'tcl').exists():
                            return home
        
        # Check for uv managed Python
        uv_python = Path(os.environ.get('UV_PYTHON_INSTALL_DIR', 
            r"C:\Users\fengshuiliang\AppData\Roaming\uv\python"))
        
        # Try to match Python version
        version = sys.version_info
        version_str = f"cpython-{version.major}.{version.minor}.{version.micro}-windows-x86_64-none"
        uv_path = uv_python / version_str
        
        if uv_path.exists():
            return uv_path
        
        # Fallback: look for any cpython in uv directory
        for p in uv_python.glob("cpython-*"):
            if p.is_dir():
                return p
        
        # Fallback: look for local Python installations
        local_python = Path(os.environ.get('LOCALAPPDATA', 
            r"C:\Users\fengshuiliang\AppData\Local")) / "Programs" / "Python"
        
        version_str = f"Python{version.major}{version.minor}"
        local_path = local_python / version_str
        if local_path.exists() and (local_path / 'tcl').exists():
            return local_path
    
    # If running from base Python installation
    parent = executable.parent
    if (parent / "tcl").exists():
        return parent
    
    # Check parent's parent (e.g., C:\Python312)
    grandparent = parent.parent
    if (grandparent / "tcl").exists():
        return grandparent
    
    raise RuntimeError(f"Cannot find Python base installation from: {executable}")


def clean_build(exe_name='QuickReplyAssistant', mode='onedir'):
    """Clean only the current build's output, preserve other EXEs."""
    # Clean build directory (PyInstaller intermediate files)
    build_dir = PROJECT_ROOT / 'build'
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Clean only this EXE's output, not the entire dist directory
    dist_dir = PROJECT_ROOT / 'dist'
    if dist_dir.exists():
        if mode == 'onedir':
            # onedir: dist/QuickReplyAssistant/ folder
            exe_folder = dist_dir / exe_name
            if exe_folder.exists():
                shutil.rmtree(exe_folder)
        else:
            # onefile: dist/QuickReplyAssistant.exe file
            exe_file = dist_dir / f'{exe_name}.exe'
            if exe_file.exists():
                exe_file.unlink()

    for spec in PROJECT_ROOT.glob('*.spec'):
        spec.unlink()


def backup_existing_runtime_data(exe_name='QuickReplyAssistant', mode='onedir'):
    if PRESERVED_DATA_BACKUP.exists():
        shutil.rmtree(PRESERVED_DATA_BACKUP)

    if mode == 'onedir':
        source_data_dir = PROJECT_ROOT / 'dist' / exe_name / 'data'
    else:
        source_data_dir = PROJECT_ROOT / 'dist' / 'data'

    if source_data_dir.exists():
        shutil.copytree(source_data_dir, PRESERVED_DATA_BACKUP)
        return PRESERVED_DATA_BACKUP
    return None


def restore_preserved_runtime_data(exe_name='QuickReplyAssistant', mode='onedir'):
    if not PRESERVED_DATA_BACKUP.exists():
        return

    if mode == 'onedir':
        target_data_dir = PROJECT_ROOT / 'dist' / exe_name / 'data'
    else:
        target_data_dir = PROJECT_ROOT / 'dist' / 'data'

    target_data_dir.mkdir(parents=True, exist_ok=True)

    for item in PRESERVED_DATA_BACKUP.iterdir():
        target_path = target_data_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target_path, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target_path)

    shutil.rmtree(PRESERVED_DATA_BACKUP, ignore_errors=True)


def build_exe(mode='onefile', exe_name='QuickReplyAssistant', entry_script=None, icon_file=None):
    backup_existing_runtime_data(exe_name=exe_name, mode=mode)
    clean_build(exe_name=exe_name, mode=mode)
    write_build_edition_marker()

    if entry_script is None:
        entry_script = PROJECT_ROOT / 'run_exe.py'
    else:
        entry_script = Path(entry_script)

    try:
        python_base = detect_python_base()
        tcl_path = python_base / "tcl"
        dlls_path = python_base / "DLLs"

        tcl86 = tcl_path / 'tcl8.6'
        tk86 = tcl_path / 'tk8.6'
        tkinter_dll = dlls_path / "_tkinter.pyd"

        if not tkinter_dll.exists():
            raise RuntimeError(f"_tkinter.pyd not found: {tkinter_dll}")
        if not tcl86.exists():
            raise RuntimeError(f"TCL not found: {tcl86}")
        if not tk86.exists():
            raise RuntimeError(f"TK not found: {tk86}")

        runtime_hook = PROJECT_ROOT / "hook_runtime_tk.py"
        edition_marker = write_build_edition_marker()

        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--{}'.format(mode),
            '--windowed',
            '--log-level=ERROR',
            '--name={}'.format(exe_name),
            '--icon={}'.format(str(icon_file or PROJECT_ROOT / 'app.ico')),
            '--add-data={};.'.format(str(PROJECT_ROOT / 'app.ico')),
            '--clean',
            '--noconfirm',
            '--runtime-hook=' + str(runtime_hook),
            '--hidden-import=tkinter',
            '--hidden-import=tkinter.ttk',
            '--hidden-import=tkinter.messagebox',
            '--hidden-import=tkinter.filedialog',
            '--hidden-import=_tkinter',
            '--hidden-import=preview_mode',
            '--hidden-import=preview_adapter',
            '--hidden-import=personal_data',
            '--hidden-import=local_intelligence',
            '--hidden-import=local_intelligence.intelligence_manager_v204',
            '--hidden-import=local_search.search_engine_v204',
            '--hidden-import=requests',
            '--hidden-import=urllib3',
            '--hidden-import=certifi',
            '--hidden-import=charset_normalizer',
            '--hidden-import=idna',
            '--hidden-import=json',
            '--hidden-import=datetime',
            '--hidden-import=re',
            '--hidden-import=sqlite3',
            '--hidden-import=keyboard',
            '--hidden-import=pystray',
            '--hidden-import=PIL',
            '--hidden-import=PIL.Image',
            '--hidden-import=PIL.ImageTk',
            '--hidden-import=threading',
            '--hidden-import=gui_utils',
            '--hidden-import=reply_gui',
            '--hidden-import=personal_gui',
            # 排除公开版不需要的大型依赖（可选依赖，代码中已有 try/except）
            '--exclude-module=torch',
            '--exclude-module=torch.*',
            '--exclude-module=cv2',
            '--exclude-module=pandas',
            '--exclude-module=pandas.*',
            '--exclude-module=matplotlib',
            '--exclude-module=matplotlib.*',
            '--exclude-module=transformers',
            '--exclude-module=transformers.*',
            '--exclude-module=onnxruntime',
            '--exclude-module=onnxruntime.*',
            '--exclude-module=sklearn',
            '--exclude-module=sklearn.*',
            '--exclude-module=scikit-learn',
            '--exclude-module=sentence_transformers',
            '--exclude-module=chromadb',
            '--exclude-module=chromadb.*',
            '--exclude-module=chromadb_client',
            '--exclude-module=grpc',
            '--exclude-module=grpcio',
            '--exclude-module=hf_xet',
            '--add-binary={};.'.format(tkinter_dll),
            '--add-data={};tcl8.6'.format(tcl86),
            '--add-data={};tk8.6'.format(tk86),
            '--add-data={};.'.format(edition_marker),
        ]

        icon_file = PROJECT_ROOT / 'app.ico'
        if icon_file.exists():
            cmd.append('--add-data={};.'.format(icon_file))

        tray_image_file = PROJECT_ROOT / 'app.jpg'
        if tray_image_file.exists():
            cmd.append('--add-data={};.'.format(tray_image_file))

        personal_icon_file = PROJECT_ROOT / 'personal_icon.png'
        if personal_icon_file.exists():
            cmd.append('--add-data={};.'.format(personal_icon_file))

        personal_ico_file = PROJECT_ROOT / 'personal_icon.ico'
        if personal_ico_file.exists():
            cmd.append('--add-data={};.'.format(personal_ico_file))

        data_dir = PROJECT_ROOT / 'data'
        if data_dir.exists():
            cmd.append('--add-data={};data'.format(data_dir))

        preview_mode = PROJECT_ROOT / 'preview_mode.py'
        if preview_mode.exists():
            cmd.append('--add-data={};.'.format(preview_mode))

        start_gui = PROJECT_ROOT / 'start_gui.py'
        if start_gui.exists():
            cmd.append('--add-data={};.'.format(start_gui))

        gui_utils = PROJECT_ROOT / 'gui_utils.py'
        if gui_utils.exists():
            cmd.append('--add-data={};.'.format(gui_utils))

        cmd.append(str(entry_script))

        print("Building {} executable...".format(mode))
        print("Edition:", get_build_edition())
        print("Python base:", python_base)
        print("_tkinter.pyd:", tkinter_dll)
        print("TCL:", tcl86)
        print("TK:", tk86)

        env = os.environ.copy()
        env["PYINSTALLER_SUPPRESS_WARNINGS"] = "1"
        env["PYTHONWARNINGS"] = "ignore"

        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)

        if mode == 'onefile':
            exe_path = PROJECT_ROOT / 'dist' / '{}.exe'.format(exe_name)
        else:
            exe_path = PROJECT_ROOT / 'dist' / exe_name / '{}.exe'.format(exe_name)

        if result.returncode == 0 and exe_path.exists():
            restore_preserved_runtime_data(exe_name=exe_name, mode=mode)
            print("\nBuild SUCCESS: {}".format(exe_path))
            if exe_path.stat().st_size:
                print("Size: {:.2f} MB".format(exe_path.stat().st_size / 1024 / 1024))
            return True

        print("\nBuild FAILED")
        warn_file = PROJECT_ROOT / 'build' / exe_name / 'warn-{}.txt'.format(exe_name)
        if warn_file.exists():
            print("\nWarnings:")
            with open(warn_file, 'r', encoding='utf-8') as f:
                print(f.read())

        return False
    finally:
        cleanup_build_edition_marker()


if __name__ == '__main__':
    import argparse
    import sys as _sys
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['onefile', 'onedir'], default='onedir',
                        help='Build mode: onefile (single exe) or onedir (folder)')
    parser.add_argument('--name', default='QuickReplyAssistant',
                        help='EXE name (default: QuickReplyAssistant)')
    parser.add_argument('--entry', default=None,
                        help='Entry script (default: run_exe.py)')
    parser.add_argument('--ico', default=None,
                        help='Custom icon file (ICO format, default: app.ico)')
    parser.add_argument('--project-root', default=None,
                        help='Project root directory (default: script parent dir)')
    args = parser.parse_args()
    if args.project_root:
        _root = Path(args.project_root)
        _mod = _sys.modules[__name__]
        setattr(_mod, 'PROJECT_ROOT', _root)
        setattr(_mod, 'PRESERVED_DATA_BACKUP', _root / ".build_preserved_data")
        setattr(_mod, 'BUILD_EDITION_MARKER', _root / "app_edition.txt")
    _ico = Path(args.ico) if args.ico else None
    build_exe(mode=args.mode, exe_name=args.name, entry_script=args.entry, icon_file=_ico)
