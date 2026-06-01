@echo off
chcp 65001 >nul 2>&1
REM build reply assistant EXE (standalone)
cd /d "%~dp0"
python build_exe.py --name QuickReplyAssistant --entry start_reply.py --mode onedir
pause
