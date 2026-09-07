@echo off
REM ============================================================
REM Generate Visual Language Assets
REM Creates color palettes, materials, textures, animations
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\VisualLanguage"
set "REGISTRY=%SCRIPT_DIR%space_whale_visual_language_registry.json"
set "COUNT=150"

echo.
echo ============================================================
echo   Visual Language Asset Generator
echo ============================================================
echo.
echo Generating %COUNT% variations of visual language assets...
echo Output: %OUTPUT_DIR%
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python ollama_visual_variation_generator.py --registry "%REGISTRY%" --output "%OUTPUT_DIR%" --count %COUNT%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Visual Language Generation Complete!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
)

pause
endlocal

