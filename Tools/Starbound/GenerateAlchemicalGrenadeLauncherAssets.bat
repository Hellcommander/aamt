@echo off
REM Generate assets for Enhanced Alchemical Grenade Launcher system
cd /d "%~dp0"
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateAlchemicalGrenadeLauncherAssets.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
)
pause
