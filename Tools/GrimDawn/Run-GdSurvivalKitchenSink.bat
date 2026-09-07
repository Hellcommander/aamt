@echo off
setlocal
cd /d "%~dp0"
REM SurvivalPlayground kitchen-sink including resource ARCs (slow)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-GdSurvivalClasses.ps1" -DryRunNames %*
echo.
pause
exit /b %ERRORLEVEL%
