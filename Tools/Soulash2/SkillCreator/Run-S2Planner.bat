@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
  start "Soulash 2 Planner" pythonw "%~dp0s2_planner_gui.py"
  exit /b 0
)
python "%~dp0s2_planner_gui.py"
echo.
pause
exit /b %ERRORLEVEL%
