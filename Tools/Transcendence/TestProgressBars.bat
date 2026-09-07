@echo off
REM ============================================================
REM Test Progress Bars in Monitor GUI
REM Verifies that progress bars are visible and functional
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Test Progress Bars Visibility
echo ============================================================
echo.
echo This will launch the monitor GUI and simulate progress
echo to verify that progress bars are visible and updating.
echo.
echo You should see:
echo   - Progress bars with cyan fill (#FF66ccff)
echo   - Progress bars with dark background (#FF1a2a3a)
echo   - Progress percentage text below each bar
echo   - Progress bars updating as files are detected
echo.
echo If you only see text, the WPF rendering is broken.
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Generate test samples first
echo Generating test samples...
python CreateQuickTestSamples.py --output "Output\TestSamples" --count 3
echo.

REM Launch monitor
echo Launching monitor with progress bars...
echo.
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "AssetGeneratorControlRoom_Monitor.ps1" -WatchDirectory "Output\TestSamples" -MaxCores 32

echo.
echo Test complete.
pause
endlocal

