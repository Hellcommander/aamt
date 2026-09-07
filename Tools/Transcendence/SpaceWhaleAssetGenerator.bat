@echo off
REM ============================================================
REM SpaceWhaleAssetGenerator.bat - Launch Space Whale Asset Generator
REM ============================================================
REM Generates all assets for Space Whale ship with GUI progress tracking

setlocal EnableDelayedExpansion

REM Get the directory of the batch file
set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Space Whale Asset Generator
echo ============================================================
echo.

REM Check if PowerShell script exists
set "PS_SCRIPT=%SCRIPT_DIR%SpaceWhaleAssetGenerator.ps1"
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check if Python is available (for model router)
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: Python not found in PATH
    echo Some features may not work without Python
    echo.
    timeout /t 2 >nul
)

REM Launch PowerShell generator with Control Room GUI
echo Launching Space Whale Asset Generator...
echo.

REM Only pass additional arguments if they exist
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -UseControlRoom 2>&1
    set "EXIT_CODE=%ERRORLEVEL%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -UseControlRoom %* 2>&1
    set "EXIT_CODE=%ERRORLEVEL%"
)

echo.
echo ============================================================
if !EXIT_CODE! equ 0 (
    echo   Generation Complete!
    echo ============================================================
) else (
    echo   Generation Failed (Exit Code: !EXIT_CODE!)
    echo ============================================================
    echo.
    echo Check the error messages above for details.
    echo.
)

REM Always keep window open so user can see what happened
echo.
echo Press any key to exit...
pause >nul

endlocal

