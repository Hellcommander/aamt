@echo off
REM ============================================================
REM Test GUI With Sample Images
REM Generates sample images then launches GUI to display them
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\TestSamples"

echo.
echo ============================================================
echo   Test GUI With Sample Images
echo ============================================================
echo.
echo This will:
echo   1. Generate sample test images
echo   2. Launch GUI to display them
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Step 1: Generate samples
echo [1/2] Generating test sample images...
call GenerateTestSamples.bat
if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Sample generation had issues, but continuing...
    echo.
)

REM Step 2: Launch GUI
echo.
echo [2/2] Launching GUI to display samples...
echo.
echo The GUI should show:
echo   - Sample images in the left panel (grid)
echo   - Any XML files in the right panel
echo   - Progress bars and status
echo.
echo If you only see progress bars, the image loading needs fixing.
echo.

powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "%OUTPUT_DIR%" -MaxCores 32

echo.
echo GUI test complete.
echo.
pause
endlocal

