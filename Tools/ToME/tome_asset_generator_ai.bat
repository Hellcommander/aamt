@echo off
REM ============================================================
REM tome_asset_generator_ai - Wrapper Script
REM AI-Assisted Modding Tools (AAMT) - ToME Toolset
REM ============================================================
REM
REM Launches the AI-enhanced Python script with tool detection
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%tome_asset_generator_ai.py

if not exist "%PY_SCRIPT%" (
    echo ERROR: Python script not found at:
    echo   %PY_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check tools using AAMT unified detection (Ollama is required for AI features)
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%InitializeToMETools.ps1" -RequiredTools @("Python", "Ollama") -OptionalTools @("ImageMagick") >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Checking required tools for AI asset generation...
    powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%InitializeToMETools.ps1" -RequiredTools @("Python", "Ollama") -OptionalTools @("ImageMagick")
    echo.
    pause
    exit /b 1
)

REM Get Python path from tool detection
for /f "delims=" %%i in ('powershell -Command "(Import-Module '%SCRIPT_DIR%..\Shared\ToolDetection.psm1' -ErrorAction SilentlyContinue; Get-PythonPath)"') do set PYTHON_PATH=%%i

if defined PYTHON_PATH (
    set "PYTHON_CMD=%PYTHON_PATH%"
) else (
    REM Fallback to PATH detection
    where python >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        where py >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            echo ERROR: Python not found in PATH
            echo Please install Python or add it to your PATH
            pause
            exit /b 1
        )
        set "PYTHON_CMD=py"
    ) else (
        set "PYTHON_CMD=python"
    )
)

%PYTHON_CMD% "%PY_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
