@echo off
REM ============================================================
REM Test Dual Model System
REM Verifies that CodeLlama-34B and WizardLM-uncensored are
REM correctly detected and assigned to appropriate tasks
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo   Dual Model System Test
echo ============================================================
echo.
echo This test verifies:
echo   - Model detection (CodeLlama-34B, WizardLM-uncensored)
echo   - Task-based routing (code vs visual tasks)
echo   - Dual model configuration
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python test_dual_model_system.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Test Passed!
    echo ============================================================
    echo.
    echo Dual model system is working correctly.
    echo Code tasks will use: CodeLlama-34B
    echo Visual tasks will use: WizardLM-uncensored
    echo.
) else (
    echo.
    echo ============================================================
    echo   Test Failed
    echo ============================================================
    echo.
    echo Check the output above for errors.
    echo.
)

pause
endlocal

