@echo off
REM ============================================================
REM Generate AAMod (Ancients Awakened) Biome Portal Spritesheets
REM Generates Mire, Inferno, and Mushroom Blight biome portals
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

echo.
echo ============================================================
echo   AAMod Biome Portal Generator
echo   Generating portals for: Mire, Inferno, Mushroom Blight
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

echo Generating Mire Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" -PortalName "MireBiomePortal" -Description "A poisonous swampy green mire portal with toxic bubbles, mud particles, and sickly green energy swirling inward" -Preset Nature -TileSize 16 -FrameCount 8 -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Mire Portal generation failed
    pause
    exit /b 1
)

echo.
echo Generating Inferno Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" -PortalName "InfernoBiomePortal" -Description "A scorching fiery orange-red inferno portal with flames, embers, lava particles, and intense heat waves swirling outward" -Preset Fire -TileSize 16 -FrameCount 8 -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Inferno Portal generation failed
    pause
    exit /b 1
)

echo.
echo Generating Mushroom Blight Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" -PortalName "MushroomBlightBiomePortal" -Description "A cancerous purple-pink mushroom blight portal with fungal spores, mycelium particles, and corrupted organic energy pulsing" -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Mushroom Blight Portal generation failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Copying assets to mod directories...
echo ============================================================
echo.

REM Copy spritesheets to proper locations
set "MOD_ASSETS=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets"
set "MOD_TILES=%MOD_ASSETS%\Tiles"
set "MOD_ITEMS=%MOD_ASSETS%\Items"

REM Create directories if they don't exist
if not exist "%MOD_TILES%" mkdir "%MOD_TILES%"
if not exist "%MOD_ITEMS%" mkdir "%MOD_ITEMS%"

REM Copy Mire portal
if exist "%OUTPUT_DIR%\MireBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\MireBiomePortal_spritesheet.png" "%MOD_TILES%\mirebiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\MireBiomePortal_spritesheet.png" "%MOD_ITEMS%\mirebiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Mire Portal assets copied
    ) else (
        echo [WARN] Mire Portal tile copied, but item extraction failed
    )
)

REM Copy Inferno portal
if exist "%OUTPUT_DIR%\InfernoBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\InfernoBiomePortal_spritesheet.png" "%MOD_TILES%\infernobiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\InfernoBiomePortal_spritesheet.png" "%MOD_ITEMS%\infernobiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Inferno Portal assets copied
    ) else (
        echo [WARN] Inferno Portal tile copied, but item extraction failed
    )
)

REM Copy Mushroom Blight portal
if exist "%OUTPUT_DIR%\MushroomBlightBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\MushroomBlightBiomePortal_spritesheet.png" "%MOD_TILES%\mushroomblightbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\MushroomBlightBiomePortal_spritesheet.png" "%MOD_ITEMS%\mushroomblightbiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Mushroom Blight Portal assets copied
    ) else (
        echo [WARN] Mushroom Blight Portal tile copied, but item extraction failed
    )
)

echo.
echo ============================================================
echo   Generation Complete!
echo ============================================================
echo.
echo Generated portals:
echo   - MireBiomePortal (poisonous swampy green theme)
echo   - InfernoBiomePortal (fiery orange-red theme)
echo   - MushroomBlightBiomePortal (cancerous purple-pink theme)
echo.
echo Next steps:
echo   1. Update AAModBiomeIsolation.cs to use portal tile types
echo   2. Create portal tile classes (MireBiomePortalTile, etc.)
echo   3. Create portal item classes (MireBiomePortalItem, etc.)
echo   4. Build mod in tModLoader
echo   5. Test portal animations in-game
echo.

pause
endlocal
