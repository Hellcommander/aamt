@echo off
REM SoulashAssetGenerator.bat - Drag-and-Drop Wrapper
REM AI-Assisted Modding Tools (AAMT) - Soulash Toolset
REM Generates Soulash mod asset files
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1" neq "" (
    REM File/folder dropped - use as asset name
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%SoulashAssetGenerator.ps1" -AssetName "%~n1" -AssetType Creature -Preset Default -OutputDir "%~dp1" -GeneratePlaceholder
) else (
    REM No file dropped, show usage
    echo.
    echo ============================================
    echo   Soulash Asset Generator
    echo ============================================
    echo.
    echo Usage: Drag a file onto this batch file to use its name as the asset name
    echo.
    echo Or run directly with PowerShell:
    echo   .\SoulashAssetGenerator.ps1 -AssetName "demon" -AssetType Creature -Preset Demon
    echo.
    echo Asset Types:
    echo   Creature   - Monsters, NPCs with spritesheets
    echo   Portrait   - Character face icons
    echo   Item       - Equipment, consumables
    echo   Ability    - Skill/spell icons
    echo   Tile       - Ground, wall tiles
    echo   Building   - Structures
    echo   Effect     - Animated effects
    echo   Spritesheet - Full spritesheet definitions
    echo.
    echo Creature Presets:
    echo   Demon, Undead, Beast, Humanoid, Elemental, Construct
    echo.
    echo Item Presets:
    echo   Weapon, Armor, Potion, Book, Gem, Food, Tool
    echo.
    echo Ability Presets:
    echo   Attack, Magic, Buff, Debuff, Passive
    echo.
    pause
)

if %ERRORLEVEL% neq 0 pause
endlocal

