@echo off
REM ============================================================
REM Fix Space Time Vortex Mod with codellama:34b
REM ============================================================
REM
REM This script runs the Qud mod fixer on the Space Time Vortex mod
REM using codellama:34b for better complex code understanding.
REM ============================================================

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%qud_mod_fixer.py

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

REM Set paths
set MOD_NAME=Improved and Rebalanced Space Time Vortex
set SAVE_PATH=C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud
set PLAYER_LOG=%SAVE_PATH%\Player.log
set GAME_LOG=%SAVE_PATH%\game_log.txt
set ERRORS_LOG=%SAVE_PATH%\errors found.txt
set HARMONY_LOG=%SAVE_PATH%\harmony.log.txt

echo ============================================================
echo Running Qud Mod Fixer
echo ============================================================
echo Mod: %MOD_NAME%
echo Model: codellama:34b
echo Error Logs: 
echo   - %PLAYER_LOG%
echo   - %GAME_LOG%
echo   - %ERRORS_LOG%
echo   - %HARMONY_LOG%
echo ============================================================
echo.

REM Run the fixer (foreground - you'll see all output)
%PYTHON_CMD% "%PY_SCRIPT%" "%MOD_NAME%" --model "codellama:34b" --error-logs "%PLAYER_LOG%" "%GAME_LOG%" "%ERRORS_LOG%" "%HARMONY_LOG%" --save-path "%SAVE_PATH%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    pause
)

