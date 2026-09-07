@echo off
REM ============================================================
REM Asset Generator Control Room Monitor - Optional Launcher
REM ============================================================
REM Launches monitoring GUI that can watch generation in progress

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ========================================
echo  Asset Generator Control Room Monitor
echo ========================================
echo.
echo This is an optional monitoring tool.
echo Launch it while generation is running to see real-time progress.
echo.

REM Launch in STA mode (required for WPF)
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AssetGeneratorControlRoom_Monitor.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Error occurred. Press any key to exit...
    pause >nul
)

endlocal

