@echo off
REM ============================================================
REM Start Space Whale Monitor Only
REM ============================================================
REM Launches only the Control Room Monitor for watching
REM existing generation processes
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "WATCH_DIR=%SCRIPT_DIR%Output"

echo.
echo ============================================================
echo   Space Whale Asset Generation Monitor
echo ============================================================
echo.
echo This monitor can watch generation in progress.
echo.
echo Watching directory: %WATCH_DIR%
echo.

REM Launch monitor
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "%WATCH_DIR%" -MaxCores 32

endlocal

