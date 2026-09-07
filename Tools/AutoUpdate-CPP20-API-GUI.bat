@echo off
REM ============================================================
REM AutoUpdate-CPP20-API-GUI - Launcher with STA mode
REM Supports drag and drop: drag files/folders onto this batch file
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

REM Check if files/folders were dropped (drag and drop)
set "DROPPED_PATH="
if not "%~1"=="" (
    REM Check if first argument is a valid path
    if exist "%~1" (
        set "DROPPED_PATH=%~1"
        REM If it's a file, get its parent directory
        if exist "%~1\" (
            REM It's a folder
            set "DROPPED_PATH=%~1"
        ) else (
            REM It's a file - get parent directory
            for %%F in ("%~1") do set "DROPPED_PATH=%%~dpF"
            REM Remove trailing backslash
            set "DROPPED_PATH=!DROPPED_PATH:~0,-1!"
        )
    )
)

echo.
echo ========================================
echo  Auto C++20 Migration Tool - GUI
echo ========================================
echo.

if not "!DROPPED_PATH!"=="" (
    echo Drag and drop detected: !DROPPED_PATH!
    echo.
    echo Launching GUI with dropped path...
    echo.
    REM Launch in STA mode with -Path parameter
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AutoUpdate-CPP20-API-GUI.ps1" -Path "!DROPPED_PATH!"
) else (
echo Launching GUI window in STA mode...
echo.
    echo Tip: You can drag and drop files or folders onto this batch file!
    echo.
REM Launch in STA mode (required for Windows Forms)
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AutoUpdate-CPP20-API-GUI.ps1" %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo Error occurred. Press any key to exit...
    pause >nul
)

endlocal

