@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not defined APP_EDITION set "APP_EDITION=public"

py -3 run.py
pause
