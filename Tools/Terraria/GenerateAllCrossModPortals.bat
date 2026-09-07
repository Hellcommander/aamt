@echo off
REM ============================================================
REM Generate ALL Missing CrossModStabilizer Portal Assets
REM Generates assets for all portals that are missing unique textures
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

echo.
echo ============================================================
echo   Complete CrossModStabilizer Portal Asset Generator
echo   Generating all missing portal spritesheets
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM ============================================================
REM Avalon Biome Portals
REM ============================================================
echo [Avalon] Generating Contagion Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'ContagionBiomePortal' -Description 'A dark green corruption portal with swirling toxic energy, purple particles, and organic corruption patterns' -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [Avalon] Generating Tropics Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'TropicsBiomePortal' -Description 'A vibrant tropical portal with palm leaves, ocean blue, sandy orange, and tropical paradise energy' -Preset Nature -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [Avalon] Generating Cloud Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'CloudBiomePortal' -Description 'A white fluffy cloud portal with sky blue, soft white particles, and airy ethereal energy' -Preset Light -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [Avalon] Generating Ice Caves Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'IceCavesBiomePortal' -Description 'A crystalline ice portal with blue-white crystals, frost particles, and frozen energy' -Preset Ice -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM Rise of Ages Biome Portals
REM ============================================================
echo [RoA] Generating Backwoods Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'BackwoodsBiomePortal' -Description 'A dark forest portal with green-brown organic energy, tree bark patterns, and natural woodland particles' -Preset Nature -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM TheDepths Mod Portal
REM ============================================================
echo [TheDepths] Generating TheDepths Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'TheDepthsPortal' -Description 'A deep purple void portal with dark energy, mysterious particles, and underground depths atmosphere' -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM Copy assets to mod directories
REM ============================================================
echo.
echo ============================================================
echo   Copying assets to mod directories...
echo ============================================================
echo.

set "MOD_ASSETS=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets"
set "MOD_TILES=%MOD_ASSETS%\Tiles"
set "MOD_ITEMS=%MOD_ASSETS%\Items"

if not exist "%MOD_TILES%" mkdir "%MOD_TILES%"
if not exist "%MOD_ITEMS%" mkdir "%MOD_ITEMS%"

REM Copy Avalon portals
if exist "%OUTPUT_DIR%\ContagionBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\ContagionBiomePortal_spritesheet.png" "%MOD_TILES%\contagionbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\ContagionBiomePortal_spritesheet.png" "%MOD_ITEMS%\contagionbiomeportalitem.png" 2>nul
    echo [OK] ContagionBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\TropicsBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\TropicsBiomePortal_spritesheet.png" "%MOD_TILES%\tropicsbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\TropicsBiomePortal_spritesheet.png" "%MOD_ITEMS%\tropicsbiomeportalitem.png" 2>nul
    echo [OK] TropicsBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\CloudBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\CloudBiomePortal_spritesheet.png" "%MOD_TILES%\cloudbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\CloudBiomePortal_spritesheet.png" "%MOD_ITEMS%\cloudbiomeportalitem.png" 2>nul
    echo [OK] CloudBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\IceCavesBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\IceCavesBiomePortal_spritesheet.png" "%MOD_TILES%\icecavesbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\IceCavesBiomePortal_spritesheet.png" "%MOD_ITEMS%\icecavesbiomeportalitem.png" 2>nul
    echo [OK] IceCavesBiomePortal assets copied
)

REM Copy RoA portals
if exist "%OUTPUT_DIR%\BackwoodsBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\BackwoodsBiomePortal_spritesheet.png" "%MOD_TILES%\backwoodsbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\BackwoodsBiomePortal_spritesheet.png" "%MOD_ITEMS%\backwoodsbiomeportalitem.png" 2>nul
    echo [OK] BackwoodsBiomePortal assets copied
)

REM Copy TheDepths portal
if exist "%OUTPUT_DIR%\TheDepthsPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\TheDepthsPortal_spritesheet.png" "%MOD_TILES%\thedepthsportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\TheDepthsPortal_spritesheet.png" "%MOD_ITEMS%\thedepthsportalitem.png" 2>nul
    echo [OK] TheDepthsPortal assets copied
)

echo.
echo ============================================================
echo   Generation Complete!
echo ============================================================
echo.
echo Generated portals:
echo   Avalon: Contagion, Tropics, Cloud, IceCaves
echo   Rise of Ages: Backwoods
echo   TheDepths: Main Portal
echo.
echo Next steps:
echo   1. Verify assets in Assets/Tiles/ and Assets/Items/
echo   2. Build mod in tModLoader
echo   3. Test portal animations in-game
echo.

pause
endlocal
