@echo off
setlocal
cd /d "%~dp0"
REM SurvivalPlayground from profiles\survivalmode.json (DB overlay, skip resources)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-GdSurvivalClasses.ps1" -DryRunNames -SkipResources %*
echo.
pause
exit /b %ERRORLEVEL%
