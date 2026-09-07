@echo off
REM ============================================================
REM Test Monitor GUI With Sample Images
REM Generates samples then launches the new monitor GUI
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\TestSamples"

echo.
echo ============================================================
echo   Test Monitor GUI With Live Previews
echo ============================================================
echo.
echo This will:
echo   1. Generate sample test images
echo   2. Launch the new monitor GUI with per-job cards
echo.
echo The GUI should show:
echo   - Per-job cards (Visual, FX, Audio, Textures, Spritesheet)
echo   - Live spritesheet previews in left panel
echo   - Progress bars and status
echo   - Real-time logs in right panel
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Step 1: Generate samples
echo [1/2] Generating test sample images...
python CreateQuickTestSamples.py --output "%OUTPUT_DIR%" --count 5
if %ERRORLEVEL% neq 0 (
    echo WARNING: Sample generation had issues, but continuing...
)

REM Step 2: Launch GUI
echo.
echo [2/2] Launching Control Room Monitor...
echo.
echo The GUI should show job cards with live previews.
echo If you see images in the left panel, it's working!
echo.

powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "Output\TestSamples" -MaxCores 32

echo.
echo Monitor test complete.
echo.
pause
endlocal

