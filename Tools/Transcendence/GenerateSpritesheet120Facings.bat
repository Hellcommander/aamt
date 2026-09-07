@echo off
REM ============================================================
REM Generate 120 Facings Spritesheet
REM Creates rotation spritesheet with Blender
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\Spritesheets"
set "REGISTRY=%SCRIPT_DIR%space_whale_ship_example.json"
set "SHIP_ID=leviathan_alpha"
set "TEXTURE_DIR=%SCRIPT_DIR%Output\Textures"

echo.
echo ============================================================
echo   120 Facings Spritesheet Generator
echo ============================================================
echo.
echo Generating spritesheet for: %SHIP_ID%
echo Output: %OUTPUT_DIR%
echo.
echo NOTE: Requires Blender to be installed and configured
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -File "SpaceWhale120FacingsGenerator.ps1" -RegistryPath "%REGISTRY%" -OutputDir "%OUTPUT_DIR%" -ShipId "%SHIP_ID%" -TextureRegistryPath "%TEXTURE_DIR%\texture_registry.json"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Spritesheet Generation Complete!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
    echo.
    echo Make sure Blender is installed and configured.
)

pause
endlocal

