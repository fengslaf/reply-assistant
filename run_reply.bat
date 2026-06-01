@echo off
chcp 65001 >nul 2>&1
REM run reply assistant (source mode)
cd /d "%~dp0"
python start_reply.py
