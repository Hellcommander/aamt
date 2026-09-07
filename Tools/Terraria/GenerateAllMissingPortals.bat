@echo off
REM ============================================================
REM Generate ALL Missing Portal Spritesheets
REM Generates assets for all portals that are missing unique textures
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

echo.
echo ============================================================
echo   Complete Portal Asset Generator
echo   Generating all missing portal spritesheets
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

REM ============================================================
REM OrchidMod Biome Portals
REM ============================================================
echo [OrchidMod] Generating Jungle Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'OrchidJungleBiomePortal' -Description 'A vibrant green jungle portal with organic vines, leaves, and natural energy swirling inward' -Preset Nature -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [OrchidMod] Generating Desert Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'OrchidDesertBiomePortal' -Description 'A sandy orange desert portal with swirling sand particles and heat distortion waves' -Preset Fire -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [OrchidMod] Generating Ocean Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'OrchidOceanBiomePortal' -Description 'A cyan blue ocean portal with water ripples, bubbles, and flowing aquatic energy' -Preset Ice -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [OrchidMod] Generating Snow Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'OrchidSnowBiomePortal' -Description 'A white frosty snow portal with ice crystals, snowflakes, and cold mist swirling' -Preset Ice -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM CalamityFables Biome Portals
REM ============================================================
echo [CalamityFables] Generating Burnt Desert Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'BurntDesertBiomePortal' -Description 'A scorching orange-red burnt desert portal with embers, ash particles, and intense heat waves' -Preset Fire -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [CalamityFables] Generating Wulfrum Scrapyard Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'WulfrumScrapyardBiomePortal' -Description 'A cyan electric mechanical portal with gears, sparks, and technological energy pulses' -Preset Electric -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM SpiritMod Biome Portals
REM ============================================================
echo [SpiritMod] Generating Spirit Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'SpiritBiomePortal' -Description 'A mystical purple spirit portal with ethereal particles, ghostly wisps, and magical energy' -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [SpiritMod] Generating SpiritMod Main Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'SpiritModPortal' -Description 'A powerful purple mystical portal with swirling spirit energy and magical distortion' -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [SpiritMod] Generating Savanna Biome Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'SavannaBiomePortal' -Description 'A warm golden savanna portal with grass particles, earth tones, and natural organic energy' -Preset Nature -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

REM ============================================================
REM Mod Realm Portals
REM ============================================================
echo [Redemption] Generating Redemption Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'RedemptionPortal' -Description 'A crimson red redemption portal with dark energy, corruption particles, and intense red glow' -Preset Fire -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [Aequus] Generating Aequus Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'AequusPortal' -Description 'A turquoise ocean portal with water ripples, bubbles, and flowing aquatic energy' -Preset Ice -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [EndPrelude] Generating EndPrelude Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'EndPreludePortal' -Description 'A deep purple end portal with void particles, dark energy, and mysterious distortion' -Preset Shadow -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [StarsAndFire] Generating Stars And Fire Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'StarsAndFirePortal' -Description 'An orange fire portal with star particles, flames, and cosmic energy swirling outward' -Preset Fire -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [PokeMod] Generating PokeMod Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'PokeModPortal' -Description 'A bright yellow Pokemon portal with star particles, electric sparks, and cheerful energy' -Preset Electric -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

echo [RandomResource] Generating Random Resource Portal...
powershell -ExecutionPolicy Bypass -Command "& {& '.\TerrariaPortalOllamaGenerator.ps1' -PortalName 'RandomResourcePortal' -Description 'A golden resource portal with treasure particles, coins, gems, and valuable energy' -Preset Light -TileSize 16 -FrameCount 8 -OutputDir '%OUTPUT_DIR%'}"

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

REM Copy each portal individually
if exist "%OUTPUT_DIR%\OrchidJungleBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\OrchidJungleBiomePortal_spritesheet.png" "%MOD_TILES%\orchidjunglebiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\OrchidJungleBiomePortal_spritesheet.png" "%MOD_ITEMS%\orchidjunglebiomeportalitem.png" 2>nul
    echo [OK] OrchidJungleBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\OrchidDesertBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\OrchidDesertBiomePortal_spritesheet.png" "%MOD_TILES%\orchiddesertbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\OrchidDesertBiomePortal_spritesheet.png" "%MOD_ITEMS%\orchiddesertbiomeportalitem.png" 2>nul
    echo [OK] OrchidDesertBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\OrchidOceanBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\OrchidOceanBiomePortal_spritesheet.png" "%MOD_TILES%\orchidoceanbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\OrchidOceanBiomePortal_spritesheet.png" "%MOD_ITEMS%\orchidoceanbiomeportalitem.png" 2>nul
    echo [OK] OrchidOceanBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\OrchidSnowBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\OrchidSnowBiomePortal_spritesheet.png" "%MOD_TILES%\orchidsnowbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\OrchidSnowBiomePortal_spritesheet.png" "%MOD_ITEMS%\orchidsnowbiomeportalitem.png" 2>nul
    echo [OK] OrchidSnowBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\BurntDesertBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\BurntDesertBiomePortal_spritesheet.png" "%MOD_TILES%\burntdesertbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\BurntDesertBiomePortal_spritesheet.png" "%MOD_ITEMS%\burntdesertbiomeportalitem.png" 2>nul
    echo [OK] BurntDesertBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\WulfrumScrapyardBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\WulfrumScrapyardBiomePortal_spritesheet.png" "%MOD_TILES%\wulfrumscrapyardbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\WulfrumScrapyardBiomePortal_spritesheet.png" "%MOD_ITEMS%\wulfrumscrapyardbiomeportalitem.png" 2>nul
    echo [OK] WulfrumScrapyardBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\SpiritBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\SpiritBiomePortal_spritesheet.png" "%MOD_TILES%\spiritbiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\SpiritBiomePortal_spritesheet.png" "%MOD_ITEMS%\spiritbiomeportalitem.png" 2>nul
    echo [OK] SpiritBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\SpiritModPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\SpiritModPortal_spritesheet.png" "%MOD_TILES%\spiritmodportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\SpiritModPortal_spritesheet.png" "%MOD_ITEMS%\spiritmodportalitem.png" 2>nul
    echo [OK] SpiritModPortal assets copied
)

if exist "%OUTPUT_DIR%\SavannaBiomePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\SavannaBiomePortal_spritesheet.png" "%MOD_TILES%\savannabiomeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\SavannaBiomePortal_spritesheet.png" "%MOD_ITEMS%\savannabiomeportalitem.png" 2>nul
    echo [OK] SavannaBiomePortal assets copied
)

if exist "%OUTPUT_DIR%\RedemptionPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\RedemptionPortal_spritesheet.png" "%MOD_TILES%\redemptionportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\RedemptionPortal_spritesheet.png" "%MOD_ITEMS%\redemptionportalitem.png" 2>nul
    echo [OK] RedemptionPortal assets copied
)

if exist "%OUTPUT_DIR%\AequusPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\AequusPortal_spritesheet.png" "%MOD_TILES%\aequusportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\AequusPortal_spritesheet.png" "%MOD_ITEMS%\aequusportalitem.png" 2>nul
    echo [OK] AequusPortal assets copied
)

if exist "%OUTPUT_DIR%\EndPreludePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\EndPreludePortal_spritesheet.png" "%MOD_TILES%\endpreludeportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\EndPreludePortal_spritesheet.png" "%MOD_ITEMS%\endpreludeportalitem.png" 2>nul
    echo [OK] EndPreludePortal assets copied
)

if exist "%OUTPUT_DIR%\StarsAndFirePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\StarsAndFirePortal_spritesheet.png" "%MOD_TILES%\starsandfireportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\StarsAndFirePortal_spritesheet.png" "%MOD_ITEMS%\starsandfireportalitem.png" 2>nul
    echo [OK] StarsAndFirePortal assets copied
)

if exist "%OUTPUT_DIR%\PokeModPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\PokeModPortal_spritesheet.png" "%MOD_TILES%\pokemodportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\PokeModPortal_spritesheet.png" "%MOD_ITEMS%\pokemodportalitem.png" 2>nul
    echo [OK] PokeModPortal assets copied
)

if exist "%OUTPUT_DIR%\RandomResourcePortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\RandomResourcePortal_spritesheet.png" "%MOD_TILES%\randomresourceportal_spritesheet.png" >nul
    python "%SCRIPT_DIR%\extract_portal_item.py" "%OUTPUT_DIR%\RandomResourcePortal_spritesheet.png" "%MOD_ITEMS%\randomresourceportalitem.png" 2>nul
    echo [OK] RandomResourcePortal assets copied
)

echo.
echo ============================================================
echo   Generation Complete!
echo ============================================================
echo.
echo Generated portals:
echo   OrchidMod: Jungle, Desert, Ocean, Snow
echo   CalamityFables: Burnt Desert, Wulfrum Scrapyard
echo   SpiritMod: Spirit, Main Portal, Savanna
echo   Mod Realms: Redemption, Aequus, EndPrelude, StarsAndFire, PokeMod, RandomResource
echo.
echo Next steps:
echo   1. Update portal tile classes to use correct texture paths
echo   2. Build mod in tModLoader
echo   3. Test portal animations in-game
echo.

pause
endlocal
