@echo off
REM ============================================================
REM CDDABeeSwarmGenerator - Wrapper Script
REM AI-Assisted Modding Tools (AAMT) - CDDA Toolset
REM ============================================================
REM
REM Launches the PowerShell script with proper execution policy
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%CDDABeeSwarmGenerator.ps1

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
