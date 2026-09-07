@echo off
REM ============================================================
REM Minimal Space Whale Test
REM Quick test (under 1 minute) of core functionality
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Minimal Space Whale Test
echo ============================================================
echo.
echo This test verifies:
echo   - FX Assets multithreading (2 variations)
echo   - GUI window display (WPF with visual elements)
echo.
echo Estimated time: ~15 seconds
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python test_minimal_space_whale.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   All Tests Passed!
    echo ============================================================
    echo.
    echo System is ready for full asset generation.
    echo.
) else (
    echo.
    echo ============================================================
    echo   Some Tests Failed
    echo ============================================================
    echo.
    echo Check the output above for errors.
    echo.
)

pause
endlocal

