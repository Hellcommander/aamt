@echo off
REM ============================================================
REM Generate Textures for Rigging
REM Creates diffuse, emission, normal, roughness, metallic maps
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=%SCRIPT_DIR%Output\Textures"
set "REGISTRY=%SCRIPT_DIR%space_whale_ship_example.json"
set "SHIP_ID=leviathan_alpha"

echo.
echo ============================================================
echo   Texture Generator for Rigging
echo ============================================================
echo.
echo Generating textures for ship: %SHIP_ID%
echo Output: %OUTPUT_DIR%
echo.
echo This creates:
echo   - Diffuse maps
echo   - Emission maps
echo   - Normal maps
echo   - Roughness maps
echo   - Metallic maps
echo.
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

python space_whale_texture_generator.py --ship-registry "%REGISTRY%" --ship-id "%SHIP_ID%" --output-dir "%OUTPUT_DIR%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo   Texture Generation Complete!
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Generation Failed
    echo ============================================================
)

pause
endlocal

