@echo off
REM ============================================================
REM Verify Image Display in Monitor GUI
REM Checks that test samples exist and launches monitor
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\TestSamples"

echo.
echo ============================================================
echo   Verify Image Display in Monitor GUI
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Check if test samples exist
if not exist "%OUTPUT_DIR%" (
    echo Creating test samples...
    python CreateQuickTestSamples.py --output "%OUTPUT_DIR%" --count 5
)

REM List existing images
echo.
echo Existing images in %OUTPUT_DIR%:
dir /b "%OUTPUT_DIR%\*.png" 2>nul
if %ERRORLEVEL% neq 0 (
    echo No PNG files found! Generating samples...
    python CreateQuickTestSamples.py --output "%OUTPUT_DIR%" --count 5
)

echo.
echo ============================================================
echo   Launching Monitor GUI
echo ============================================================
echo.
echo The GUI should show:
echo   - A job card for "Test Samples"
echo   - An IMAGE in the left panel (200x200px preview)
echo   - Progress bar and status
echo   - Logs in the right panel
echo.
echo If you see the image, the live preview system works!
echo.

powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "Output\TestSamples" -MaxCores 32

echo.
echo Monitor closed.
echo.
pause
endlocal

