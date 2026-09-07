@echo off
REM ============================================================
REM Minimal Space Whale Test - Under 1 Minute
REM ============================================================
REM Quick test to verify multithreading AND GUI work
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Minimal Space Whale Test
echo ============================================================
echo.
echo This will test:
echo   - Multithreading (FX generator)
echo   - GUI window display
echo.
echo Expected time: Under 1 minute
echo.
echo NOTE: GUI window will open briefly - you can close it
echo.

python "%SCRIPT_DIR%test_minimal_space_whale.py"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   All Tests Passed!
    echo ============================================================
    echo.
    echo Multithreading and GUI are working correctly.
    echo You can now run the full generation.
) else (
    echo.
    echo ============================================================
    echo   Some Tests Failed
    echo ============================================================
    echo.
    echo Check the errors above for details.
)

echo.
pause

endlocal
