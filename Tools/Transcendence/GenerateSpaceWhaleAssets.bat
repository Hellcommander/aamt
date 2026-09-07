@echo off
REM ============================================================
REM Generate Space Whale Comprehensive Assets
REM Generates 150 variations with quality checking
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

echo.
echo ========================================
echo  Space Whale Comprehensive Asset Generator
echo ========================================
echo.
echo This will generate 150 variations of each asset type:
echo   - Visual Language
echo   - FX Assets
echo   - Audio Assets
echo   - Quality checking and reporting
echo.
echo This may take a while...
echo.

REM Launch with GUI option
if "%1"=="--gui" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateSpaceWhaleAssets.ps1" -UseGUI
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateSpaceWhaleAssets.ps1"
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo Error occurred. Press any key to exit...
    pause >nul
)

endlocal

