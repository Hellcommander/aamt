@echo off
setlocal
cd /d "%~dp0"
REM Expand class selection / skillCtrlPane up to 120 + dense scrollable layout
python -u "%~dp0patch_class_ui.py" --max-classes 120 %*
echo.
pause
exit /b %ERRORLEVEL%
