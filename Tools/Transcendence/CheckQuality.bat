@echo off
REM ============================================================
REM Quality Checker
REM Checks generated assets and reports low-quality items
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleComprehensive"
set "THRESHOLD=8.0"

echo.
echo ============================================================
echo   Asset Quality Checker
echo ============================================================
echo.
echo Checking assets in: %OUTPUT_DIR%
echo Threshold: Scores < %THRESHOLD% will be detailed
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python space_whale_quality_checker.py --output-dir "%OUTPUT_DIR%" --threshold %THRESHOLD%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Quality Check Complete!
    echo ============================================================
    echo.
    echo Report saved to: %OUTPUT_DIR%\SPACE_WHALE_QUALITY_REPORT.md
) else (
    echo.
    echo ============================================================
    echo   Quality Check Failed
    echo ============================================================
)

pause
endlocal

