@echo off
echo 正在清除Windows图标缓存...
echo.

taskkill /f /im explorer.exe 2>nul

cd /d %userprofile%\AppData\Local
attrib -h IconCache.db
del IconCache.db /f /q 2>nul

cd /d %userprofile%\AppData\Local\Microsoft\Windows\Explorer
del iconcache_*.db /f /q 2>nul

start explorer.exe

echo.
echo 图标缓存已清除，请重新运行程序
echo 任务栏图标应该会显示新图标了
pause