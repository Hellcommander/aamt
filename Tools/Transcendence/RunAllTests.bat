@echo off
REM ============================================================
REM Run All Tests
REM Runs all available tests in sequence
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Running All Tests
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM Test 1: Dual Model System
echo [1/2] Testing Dual Model System...
echo.
python test_dual_model_system.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Dual model system test failed!
    pause
    exit /b 1
)
echo.

REM Test 2: Minimal Space Whale
echo [2/2] Testing Minimal Space Whale...
echo.
python test_minimal_space_whale.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Minimal space whale test failed!
    pause
    exit /b 1
)
echo.

echo ============================================================
echo   All Tests Complete!
echo ============================================================
echo.
echo All systems are working correctly.
echo You can now run full asset generation.
echo.
pause
endlocal

