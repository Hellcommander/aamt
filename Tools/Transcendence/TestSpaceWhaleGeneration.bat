@echo off
REM ============================================================
REM Test Space Whale Generation - Quick Test
REM ============================================================
REM Creates a simple tiny space whale with minimal variations
REM to verify all systems work correctly
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Space Whale Generation Test
echo ============================================================
echo.
echo This will create a simple tiny space whale with:
echo   - 5 variations per asset type (instead of 150)
echo   - All core systems tested
echo   - Quick verification (~1-2 minutes)
echo.
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Run test
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%TestSpaceWhaleGeneration.ps1" -Variations 5

echo.
echo ============================================================
echo   Test Complete!
echo ============================================================
echo.
echo Check the output directory for generated files.
echo If all tests passed, you can run the full generation.
echo.
pause

endlocal

