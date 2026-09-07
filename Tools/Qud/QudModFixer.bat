@echo off
REM ============================================================
REM QudModFixer - Caves of Qud Mod Fixing Tool
REM ============================================================
REM
REM Automatically fixes mods to work with newer API versions
REM and corrects Harmony patch asset references using AI models.
REM
REM Features:
REM   - Interactive model selection
REM   - Status UI with progress indicators
REM   - Model switching capability
REM   - Enhanced error handling
REM
REM Launches the PowerShell script with proper execution policy
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%QudModFixer.ps1

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Launch PowerShell script and pass through all arguments
REM The PowerShell script will handle displaying detailed file processing information
REM and interactive model selection
pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
