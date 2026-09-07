@echo off
REM ============================================================
REM Fix Portal Asset Names
REM Renames generated portal assets to match what portal classes expect
REM ============================================================

setlocal enabledelayedexpansion

set "MOD_ASSETS=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets"
set "MOD_TILES=%MOD_ASSETS%\Tiles"
set "MOD_ITEMS=%MOD_ASSETS%\Items"

echo.
echo ============================================================
echo   Fixing Portal Asset Names
echo ============================================================
echo.

REM Rename spritesheets from PascalCase to lowercase
if exist "%MOD_TILES%\OrchidJungleBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\orchidjunglebiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\OrchidJungleBiomePortal_spritesheet.png" "orchidjunglebiomeportal_spritesheet.png"
        echo [OK] Renamed OrchidJungleBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\OrchidDesertBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\orchiddesertbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\OrchidDesertBiomePortal_spritesheet.png" "orchiddesertbiomeportal_spritesheet.png"
        echo [OK] Renamed OrchidDesertBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\OrchidOceanBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\orchidoceanbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\OrchidOceanBiomePortal_spritesheet.png" "orchidoceanbiomeportal_spritesheet.png"
        echo [OK] Renamed OrchidOceanBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\OrchidSnowBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\orchidsnowbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\OrchidSnowBiomePortal_spritesheet.png" "orchidsnowbiomeportal_spritesheet.png"
        echo [OK] Renamed OrchidSnowBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\BurntDesertBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\burntdesertbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\BurntDesertBiomePortal_spritesheet.png" "burntdesertbiomeportal_spritesheet.png"
        echo [OK] Renamed BurntDesertBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\WulfrumScrapyardBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\wulfrumscrapyardbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\WulfrumScrapyardBiomePortal_spritesheet.png" "wulfrumscrapyardbiomeportal_spritesheet.png"
        echo [OK] Renamed WulfrumScrapyardBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\SpiritBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\spiritbiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\SpiritBiomePortal_spritesheet.png" "spiritbiomeportal_spritesheet.png"
        echo [OK] Renamed SpiritBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\SpiritModPortal_spritesheet.png" (
    if not exist "%MOD_TILES%\spiritmodportal_spritesheet.png" (
        ren "%MOD_TILES%\SpiritModPortal_spritesheet.png" "spiritmodportal_spritesheet.png"
        echo [OK] Renamed SpiritModPortal spritesheet
    )
)

if exist "%MOD_TILES%\SavannaBiomePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\savannabiomeportal_spritesheet.png" (
        ren "%MOD_TILES%\SavannaBiomePortal_spritesheet.png" "savannabiomeportal_spritesheet.png"
        echo [OK] Renamed SavannaBiomePortal spritesheet
    )
)

if exist "%MOD_TILES%\RedemptionPortal_spritesheet.png" (
    if not exist "%MOD_TILES%\redemptionportal_spritesheet.png" (
        ren "%MOD_TILES%\RedemptionPortal_spritesheet.png" "redemptionportal_spritesheet.png"
        echo [OK] Renamed RedemptionPortal spritesheet
    )
)

if exist "%MOD_TILES%\AequusPortal_spritesheet.png" (
    if not exist "%MOD_TILES%\aequusportal_spritesheet.png" (
        ren "%MOD_TILES%\AequusPortal_spritesheet.png" "aequusportal_spritesheet.png"
        echo [OK] Renamed AequusPortal spritesheet
    )
)

if exist "%MOD_TILES%\EndPreludePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\endpreludeportal_spritesheet.png" (
        ren "%MOD_TILES%\EndPreludePortal_spritesheet.png" "endpreludeportal_spritesheet.png"
        echo [OK] Renamed EndPreludePortal spritesheet
    )
)

if exist "%MOD_TILES%\StarsAndFirePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\starsandfireportal_spritesheet.png" (
        ren "%MOD_TILES%\StarsAndFirePortal_spritesheet.png" "starsandfireportal_spritesheet.png"
        echo [OK] Renamed StarsAndFirePortal spritesheet
    )
)

if exist "%MOD_TILES%\PokeModPortal_spritesheet.png" (
    if not exist "%MOD_TILES%\pokemodportal_spritesheet.png" (
        ren "%MOD_TILES%\PokeModPortal_spritesheet.png" "pokemodportal_spritesheet.png"
        echo [OK] Renamed PokeModPortal spritesheet
    )
)

if exist "%MOD_TILES%\RandomResourcePortal_spritesheet.png" (
    if not exist "%MOD_TILES%\randomresourceportal_spritesheet.png" (
        ren "%MOD_TILES%\RandomResourcePortal_spritesheet.png" "randomresourceportal_spritesheet.png"
        echo [OK] Renamed RandomResourcePortal spritesheet
    )
)

echo.
echo ============================================================
echo   Renaming Complete!
echo ============================================================
echo.
echo All portal spritesheets have been renamed to lowercase
echo to match what the portal tile classes expect.
echo.
echo Item textures are already in the correct format.
echo.

pause
endlocal
