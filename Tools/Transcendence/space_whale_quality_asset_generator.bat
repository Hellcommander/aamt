@echo off
REM ============================================================
REM Space Whale Quality Asset Generator - Batch Wrapper
REM Multi-stage quality-first pipeline
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%space_whale_quality_asset_generator.py"

echo ============================================================
echo Space Whale High-Quality Asset Generator
echo Multi-Stage Quality-First Pipeline
echo ============================================================
echo.

REM Check if Python script exists
if not exist "%PY_SCRIPT%" (
    echo ERROR: Python script not found at:
    echo   %PY_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Check for Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Python not found in PATH
        echo Please install Python 3.7+ or add it to your PATH
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

REM Display configuration
echo Configuration:
echo   - Draft Count: 6 variations per asset type
echo   - Refinement: Enabled (top 3 candidates)
echo   - Final Selection: Best 2 per type
echo   - Quality Thresholds: 13 (draft), 17 (production), 19 (target)
echo   - Retry Logic: 3 retries per stage with exponential backoff
echo   - Resume Support: --resume to continue interrupted generation
echo   - Skip Flags: --skip-draft, --skip-assess, etc. to skip stages
echo   - Ship Filtering: --ship-id to target specific ships
echo.
echo Asset Generation Pipeline:
echo   [1] Textures (PNG/TGA for Blender models)
echo   [2] Rigging (bone-driven animation system)
echo   [3] Visual Language (color palettes)
echo   [4] FX Assets (particles + effects)
echo   [5] Audio (WAV + OGG formats)
echo   [6] Spritesheets (MANDATORY - 120 facings using Blender)
echo   [7] Items (Weapons, Devices, Armor for Transcendence)
echo.
echo Usage Examples:
echo   %~n0 --quick                    Quick mode (4 drafts, no refinement)
echo   %~n0 --resume --skip-completed  Resume and skip completed stages
echo   %~n0 --ship-id leviathan_alpha  Generate for specific ship only
echo   %~n0 --skip-spritesheet         Skip spritesheet generation
echo   %~n0 --use-sd3                  Use SD3 for creative textures + design drafts
echo   %~n0 --use-sd3 --sd3-fast       Use SD3 FAST mode (skip design drafts)
echo   %~n0 --use-sd3 --sd3-texture-type design_draft  Generate design drafts only
echo.

REM Parse command line arguments for quick mode
set "ARGS="
set "QUICK_MODE="

:parse_args
if "%~1"=="" goto end_parse_args
if /i "%~1"=="--quick" (
    set "QUICK_MODE=1"
    echo Quick Mode: 4 drafts, no refinement
    echo.
)
set "ARGS=%ARGS% %~1"
shift
goto parse_args
:end_parse_args

REM Run Python script
echo Starting asset generation pipeline...
echo.

%PYTHON_CMD% "%PY_SCRIPT%" %ARGS%

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE%==0 (
    echo ============================================================
    echo Asset Generation Complete!
    echo ============================================================
    echo.
    echo Output directory: Output\SpaceWhaleAssets_HQ
    echo.
    echo Assets Generated:
    echo   - Textures (PNG/TGA for Blender models)
    echo   - Rigging (bone-driven spine animation)
    echo   - Visual Language variations (JSON)
    echo   - FX assets with particles (JSON)
    echo   - Audio files (WAV + OGG formats)
    echo   - 120 facings spritesheets for all ships (PNG + BMP masks)
    echo   - Game items (Weapons, Devices, Armor, Reactors XML)
    echo.
    echo Next steps:
    echo   1. Review quality report: QUALITY_REPORT.md
    echo   2. Check Stage4_Final for best assets
    echo   3. Check Stage6_Spritesheets for rendered spritesheets
    echo   4. Check Stage7_Items for game item XML files
    echo   5. Import into Transcendence XML
    echo.
) else (
    echo ============================================================
    echo Asset Generation Failed
    echo ============================================================
    echo.
    echo Exit code: %EXIT_CODE%
    echo Check log files for details
    echo.
)

pause
exit /b %EXIT_CODE%
