@echo off
REM ============================================================
REM Transcendence Mod Tools - Integrated XML Checker & Error Helper
REM ============================================================
REM
REM Usage:
REM   TranscendenceModTools.bat [path] [-scan]
REM
REM Examples:
REM   TranscendenceModTools.bat
REM   TranscendenceModTools.bat "..\ZZZ_CrossModCompatibility"
REM   TranscendenceModTools.bat "..\ZZZ_CrossModCompatibility" -scan
REM
REM ============================================================

set SCRIPT_DIR=%~dp0
set TOOL_SCRIPT=%SCRIPT_DIR%TranscendenceModTools.ps1

if not exist "%TOOL_SCRIPT%" (
    echo ERROR: Tool script not found at:
    echo   %TOOL_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check for -scan flag
set SCAN_MODE=0
if /i "%~2"=="-scan" set SCAN_MODE=1
if /i "%~1"=="-scan" (
    set SCAN_MODE=1
    set MOD_PATH=%~2
) else (
    set MOD_PATH=%~1
)

REM Check if a path argument was provided
if "%MOD_PATH%"=="" (
    REM No arguments - launch normally
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TOOL_SCRIPT%"
) else (
    REM Pass the path argument to PowerShell
    REM Resolve relative paths relative to Extensions directory
    cd /d "%SCRIPT_DIR%.."
    if %SCAN_MODE%==1 (
        REM Auto-scan mode: scan and exit
        pwsh -NoProfile -ExecutionPolicy Bypass -File "%TOOL_SCRIPT%" -AutoScan -Path "%MOD_PATH%"
    ) else (
        REM Normal mode: open GUI with path
        pwsh -NoProfile -ExecutionPolicy Bypass -File "%TOOL_SCRIPT%" -Path "%MOD_PATH%"
    )
)
