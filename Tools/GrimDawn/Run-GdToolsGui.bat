@echo off
setlocal
cd /d "%~dp0"
start "GD Mod Tools" pythonw "%~dp0gd_tools_gui.py" 2>nul
if errorlevel 1 (
  python "%~dp0gd_tools_gui.py"
  echo.
  pause
)
exit /b %ERRORLEVEL%
