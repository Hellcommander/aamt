@echo off
REM ============================================================
REM Generate SpiritMod Biome Portal Spritesheets
REM Generates Synthwave, Asteroid, and Briar biome portals
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

echo.
echo ============================================================
echo   SpiritMod Biome Portal Generator
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

echo Generating Synthwave Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" `
    -PortalName "SynthwaveBiomePortal" `
    -Description "A vibrant purple-pink synthwave portal with retro neon glow and pulsing energy waves" `
    -Preset Shadow `
    -TileSize 16 `
    -FrameCount 8 `
    -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Synthwave Portal generation failed
    pause
    exit /b 1
)

echo.
echo Generating Asteroid Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" `
    -PortalName "AsteroidBiomePortal" `
    -Description "A gray stone asteroid portal with floating rock particles and cosmic dust" `
    -Preset Void `
    -TileSize 16 `
    -FrameCount 8 `
    -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Asteroid Portal generation failed
    pause
    exit /b 1
)

echo.
echo Generating Briar Biome Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" `
    -PortalName "BriarBiomePortal" `
    -Description "A green nature portal with vines, thorns, and organic swirling energy" `
    -Preset Nature `
    -TileSize 16 `
    -FrameCount 8 `
    -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Briar Portal generation failed
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

REM Copy Synthwave portal
if exist "%OUTPUT_DIR%\SynthwaveBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\SynthwaveBiomePortal_spritesheet.png" "%MOD_TILES%\synthwavebiomeportal_spritesheet.png" >nul
    REM Extract first frame for item (16x16 from 128x16 spritesheet)
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\SynthwaveBiomePortal_spritesheet.png" "%MOD_ITEMS%\synthwavebiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Synthwave Portal assets copied
    ) else (
        echo [WARN] Synthwave Portal tile copied, but item extraction failed
    )
)

REM Copy Asteroid portal
if exist "%OUTPUT_DIR%\AsteroidBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\AsteroidBiomePortal_spritesheet.png" "%MOD_TILES%\asteroidbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\AsteroidBiomePortal_spritesheet.png" "%MOD_ITEMS%\asteroidbiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Asteroid Portal assets copied
    ) else (
        echo [WARN] Asteroid Portal tile copied, but item extraction failed
    )
)

REM Copy Briar portal
if exist "%OUTPUT_DIR%\BriarBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\BriarBiomePortal_spritesheet.png" "%MOD_TILES%\briarbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\BriarBiomePortal_spritesheet.png" "%MOD_ITEMS%\briarbiomeportalitem.png" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Briar Portal assets copied
    ) else (
        echo [WARN] Briar Portal tile copied, but item extraction failed
    )
)

echo.
echo ============================================================
echo   Generation Complete!
echo ============================================================
echo.
echo Generated portals:
echo   - SynthwaveBiomePortal (purple-pink synthwave theme)
echo   - AsteroidBiomePortal (gray stone asteroid theme)
echo   - BriarBiomePortal (green nature theme)
echo.
echo Next steps:
echo   1. Update portal tile classes to use correct texture paths
echo   2. Generate item textures from first frame of spritesheets
echo   3. Build mod in tModLoader
echo   4. Test portal animations in-game
echo.

pause
endlocal
