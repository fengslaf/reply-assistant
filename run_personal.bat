@echo off
chcp 65001 >nul 2>&1
REM run customer data (source mode)
cd /d "%~dp0"
python start_personal.py
