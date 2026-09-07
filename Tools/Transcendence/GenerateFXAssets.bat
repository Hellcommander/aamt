@echo off
REM ============================================================
REM Generate FX Assets
REM Creates variations of all Space Whale FX effects
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "REGISTRY=%SCRIPT_DIR%space_whale_fx_registry.json"
set "VARIATIONS=150"
set "TOP_N=10"

echo.
echo ============================================================
echo   FX Asset Generator
echo ============================================================
echo.
echo Generating %VARIATIONS% variations per effect...
echo Selecting top %TOP_N% variations for placeholders...
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python space_whale_fx_variation_generator.py "%REGISTRY%" %VARIATIONS% %TOP_N%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   FX Generation Complete!
    echo ============================================================
    echo.
    echo Files created:
    echo   - space_whale_fx_registry_best.json
    echo   - space_whale_fx_registry_placeholders.json
    echo   - SPACE_WHALE_FX_QUALITY_ASSESSMENT.md
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
)

pause
endlocal

