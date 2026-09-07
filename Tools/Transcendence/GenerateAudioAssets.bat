@echo off
REM ============================================================
REM Generate Audio Assets
REM Creates procedural audio for Space Whale communication
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\Audio"
set "REGISTRY=%SCRIPT_DIR%space_whale_audio_registry.json"
set "VARIATIONS=150"

echo.
echo ============================================================
echo   Audio Asset Generator
echo ============================================================
echo.
echo Generating %VARIATIONS% variations per sound...
echo Output: %OUTPUT_DIR%
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python space_whale_audio_generator.py --registry "%REGISTRY%" --output "%OUTPUT_DIR%" --variations %VARIATIONS%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Audio Generation Complete!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
)

pause
endlocal

