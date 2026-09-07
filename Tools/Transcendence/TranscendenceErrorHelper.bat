@echo off
REM ============================================================
REM Transcendence Error Helper - Diagnose Error Messages
REM ============================================================
REM
REM Paste your Transcendence error messages and get help fixing them!
REM
REM Usage:
REM   Double-click to run in GUI mode
REM   Or run with -NoGui for command-line mode
REM ============================================================

set SCRIPT_DIR=%~dp0
set HELPER_SCRIPT=%SCRIPT_DIR%TranscendenceErrorHelper.ps1

if not exist "%HELPER_SCRIPT%" (
    echo ERROR: Helper script not found at:
    echo   %HELPER_SCRIPT%
    echo.
    echo Please make sure this batch file is in the Tools folder.
    pause
    exit /b 1
)

echo ============================================================
echo Transcendence Error Helper
echo ============================================================
echo.

pwsh -NoProfile -ExecutionPolicy Bypass -File "%HELPER_SCRIPT%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error running helper (exit code: %ERRORLEVEL%)
    pause
)

