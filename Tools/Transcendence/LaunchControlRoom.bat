@echo off
REM ============================================================
REM Launch Control Room Monitor
REM Optional GUI to monitor asset generation in real-time
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleAssets"
set "MAX_CORES=32"

echo.
echo ============================================================
echo   Control Room Monitor
echo ============================================================
echo.
echo Launching GUI monitor...
echo Watching: %OUTPUT_DIR%
echo.
echo The GUI will show:
echo   - All generated images in a grid
echo   - XML files with content preview
echo   - Progress bars and task status
echo   - Real-time log output
echo.
echo ============================================================
echo.

REM Create output directory if it doesn't exist
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

cd /d "%SCRIPT_DIR%"

powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "%OUTPUT_DIR%" -MaxCores %MAX_CORES%

echo.
echo Control Room Monitor closed.
echo.
pause
endlocal
