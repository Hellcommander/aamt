@echo off
REM ============================================================
REM starbound_asset_quality_checker - Wrapper Script
REM ============================================================
REM
REM Checks quality of generated Starbound assets and keeps only the best ones
REM Similar to terraria_portal_quality_checker.bat
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%starbound_asset_quality_checker.py

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

REM Default assets directory
set DEFAULT_ASSETS_DIR=F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets

REM Check if assets directory provided as argument
if "%~1"=="" (
    set ASSETS_DIR=%DEFAULT_ASSETS_DIR%
) else (
    set ASSETS_DIR=%~1
)

REM Check for dry-run flag
set DRY_RUN=
if /i "%2"=="--dry-run" set DRY_RUN=--dry-run
if /i "%~1"=="--dry-run" set DRY_RUN=--dry-run

REM Run quality checker
%PYTHON_CMD% "%PY_SCRIPT%" "%ASSETS_DIR%" %DRY_RUN% %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)
