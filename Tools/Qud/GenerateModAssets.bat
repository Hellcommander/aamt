@echo off
REM Generate visual assets for Caves of Qud mods
REM Creates tiles, icons, and visual effects for mutations, creatures, and equipment

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python

if "%1"=="" (
    echo Usage: GenerateModAssets.bat "Mod Name"
    echo.
    echo Examples:
    echo   GenerateModAssets.bat "Broodmother Mutation"
    echo   GenerateModAssets.bat "Improved and Rebalanced Space Time Vortex"
    echo.
    echo This will generate:
    echo   - Mutation icons and ability markers
    echo   - Creature sprites/tiles
    echo   - Equipment tiles and icons (sack, etc.)
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo Caves of Qud Mod Asset Generator
echo ============================================================
echo.

"%PYTHON_CMD%" "%SCRIPT_DIR%generate_mod_assets.py" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Script exited with error code: %ERRORLEVEL%
    echo.
    echo Make sure Pillow is installed:
    echo   pip install Pillow
    echo.
    pause
)

