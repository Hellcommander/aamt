@echo off
REM ============================================================
REM Transcendence TLisp/XML Checker - GUI Launcher
REM ============================================================
REM
REM INSTRUCTIONS:
REM   1. Edit the MOD_PATH variable below (optional - GUI will let you browse)
REM   2. Save this file
REM   3. Double-click to run (opens GUI window)
REM
REM ============================================================

REM ============================================================
REM OPTIONAL: Set default path (leave empty to browse in GUI)
REM ============================================================
set MOD_PATH=

REM ============================================================
REM DO NOT EDIT BELOW THIS LINE
REM ============================================================

set SCRIPT_DIR=%~dp0
set CHECKER_SCRIPT=%SCRIPT_DIR%TranscendenceTlispXmlChecker.ps1

REM Check if the checker script exists
if not exist "%CHECKER_SCRIPT%" (
    echo ERROR: Checker script not found at:
    echo   %CHECKER_SCRIPT%
    echo.
    echo Please make sure this batch file is in the Tools folder.
    pause
    exit /b 1
)

echo ============================================================
echo Transcendence TLisp/XML Checker - GUI Mode
echo ============================================================
echo.
echo Opening GUI window...
echo.

REM Run the checker with GUI
if "%MOD_PATH%"=="" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CHECKER_SCRIPT%"
) else (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CHECKER_SCRIPT%" -Path "%MOD_PATH%"
)

REM Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo Checker exited with errors (exit code: %ERRORLEVEL%)
    echo ============================================================
    pause
)

