@echo off
REM ============================================================
REM elin_spell_assets - Wrapper Script
REM ============================================================
REM
REM Launches the Python script directly
REM NOTE: This is a low-level wrapper. For easier usage, use:
REM   ElinSpellAssetGenerator.bat or ElinSpellAssetGenerator.ps1
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%elin_spell_assets.py

if not exist "%PY_SCRIPT%" (
    echo ERROR: Python script not found at:
    echo   %PY_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check for Python
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

REM If no arguments provided, show usage
if "%~1"=="" (
    echo.
    echo Usage: %~nx0 --spec SPEC_FILE --output OUTPUT_DIR --name SPELL_NAME [options]
    echo.
    echo Required arguments:
    echo   --spec SPEC_FILE      JSON specification file
    echo   --output OUTPUT_DIR   Output directory
    echo   --name SPELL_NAME     Spell name (safe format)
    echo.
    echo Optional flags:
    echo   --icon                Generate icon
    echo   --fx                  Generate FX animation
    echo   --fx-frames N         Number of FX frames (default: 4)
    echo   --projectile          Generate projectile
    echo   --proj-frames N       Number of projectile frames (default: 2)
    echo   --buff                Generate buff icon
    echo.
    echo For easier usage, use ElinSpellAssetGenerator.bat instead.
    echo.
    pause
    exit /b 0
)

%PYTHON_CMD% "%PY_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
