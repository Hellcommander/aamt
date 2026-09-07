@echo off
REM ============================================================
REM StarboundOllamaAssetGenerator - Wrapper Script
REM ============================================================
REM
REM Launches the PowerShell script with proper execution policy
REM Uses Ollama AI to generate creative Starbound assets
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%StarboundOllamaAssetGenerator.ps1

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
