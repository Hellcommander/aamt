@echo off
REM ============================================================
REM Test GUI Window
REM Launches the Control Room Monitor GUI to verify
REM it displays images and XML content (not just progress bars)
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleAssets"

echo.
echo ============================================================
echo   GUI Test - Control Room Monitor
echo ============================================================
echo.
echo This will launch the Control Room Monitor GUI.
echo.
echo You should see:
echo   - Left panel: Grid of image previews (when files exist)
echo   - Right top: XML file list with content
echo   - Right bottom: Progress bars and tasks
echo   - Bottom: Log output
echo.
echo If you only see progress bars, the GUI needs fixing.
echo.
echo ============================================================
echo.

REM Create output directory if it doesn't exist
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

REM Generate test samples first
echo.
echo Generating test sample images...
call GenerateTestSamples.bat
echo.

REM Launch the monitor GUI
cd /d "%SCRIPT_DIR%"
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "%OUTPUT_DIR%" -MaxCores 32

echo.
echo GUI window closed.
echo.
pause
endlocal

