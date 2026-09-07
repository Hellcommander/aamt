@echo off
REM ============================================================
REM mod_fixer - Wrapper Script
REM ============================================================
REM
REM AI-assisted mod fixing with Ollama integration
REM Features:
REM   - Interactive model selection
REM   - Status UI with progress indicators
REM   - Model switching capability
REM   - Enhanced error handling
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%mod_fixer.py

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

REM Launch Python script and pass through all arguments
REM The Python script will handle displaying detailed status information
REM and interactive model selection
%PYTHON_CMD% "%PY_SCRIPT%" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
