@echo off
chcp 65001 >nul 2>&1
REM build customer data EXE (standalone)
cd /d "%~dp0"
python build_exe.py --name CustomerDataManager --entry start_personal.py --mode onedir --ico personal_icon.ico
pause
