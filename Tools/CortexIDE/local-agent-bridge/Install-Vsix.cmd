@echo off
rem Install the newest local-agent-bridge-*.vsix into CortexIDE (runs Install-Vsix.ps1).
rem Close CortexIDE first. Arguments are passed through, e.g.:
rem   Install-Vsix.cmd -Build
rem   Install-Vsix.cmd -Vsix local-agent-bridge-2.11.0.vsix
rem   Install-Vsix.cmd -ExtensionsDir "%TEMP%\ext-test"
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Vsix.ps1" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (echo Install finished.) else (echo Install FAILED with exit code %RC%.)

rem Keep the window open when started by double-click from Explorer.
echo %CMDCMDLINE% | find /i "/c" >nul && pause
endlocal & exit /b %RC%
