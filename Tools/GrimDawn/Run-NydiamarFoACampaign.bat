@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-NydiamarFoACampaign.ps1" -PortalHub asterkarn -DryRunNames %*
echo.
pause
exit /b %ERRORLEVEL%
