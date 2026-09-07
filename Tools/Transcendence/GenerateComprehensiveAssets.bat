@echo off
REM ============================================================
REM Generate Comprehensive Space Whale Assets
REM Main entry point for generating all asset types
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\SpaceWhaleComprehensive"
set "SHIP_ID=leviathan_alpha"
set "VARIATIONS=150"

echo.
echo ============================================================
echo   Comprehensive Space Whale Asset Generator
echo ============================================================
echo.
echo This will generate:
echo   - Visual Language Assets (%VARIATIONS% variations)
echo   - FX Assets (%VARIATIONS% variations)
echo   - Audio Assets (%VARIATIONS% variations)
echo   - Textures for Rigging
echo   - 120 Facings Spritesheet
echo   - Quality Reports
echo.
echo Output: %OUTPUT_DIR%
echo Ship ID: %SHIP_ID%
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python space_whale_comprehensive_asset_generator.py --output-dir "%OUTPUT_DIR%" --ship-id "%SHIP_ID%" --variations %VARIATIONS%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Generation Complete!
    echo ============================================================
    echo.
    echo All assets saved to: %OUTPUT_DIR%
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
    echo.
    echo Check the errors above.
)

pause
endlocal

