@echo off
REM ============================================================
REM New-QudSpringUI - Wrapper Script (AAMT, Caves of Qud Spring Molting UI windows)
REM ============================================================
REM Launches the PowerShell pipeline with proper execution policy
REM   New-QudSpringUI.bat -Spec specs\springmenu.springui.json -Build -Install
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%New-QudSpringUI.ps1

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
