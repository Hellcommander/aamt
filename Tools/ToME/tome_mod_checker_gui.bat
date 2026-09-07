@echo off
REM ============================================================
REM tome_mod_checker_gui - Wrapper Script
REM ============================================================
REM
REM ToME Mod Checker GUI with Drag and Drop
REM Features:
REM   - Interactive model selection
REM   - Error log loading
REM   - AI-assisted fixing
REM   - Enhanced status indicators
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%tome_mod_checker_gui.py

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

%PYTHON_CMD% "%PY_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
