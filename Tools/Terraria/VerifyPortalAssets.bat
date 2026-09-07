@echo off
REM ============================================================
REM Verify Portal Assets
REM Checks that all generated portal assets are in the correct locations
REM ============================================================

setlocal enabledelayedexpansion

set "MOD_ASSETS=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets"
set "MOD_TILES=%MOD_ASSETS%\Tiles"
set "MOD_ITEMS=%MOD_ASSETS%\Items"
set "OUTPUT_DIR=%MOD_TILES%"

echo.
echo ============================================================
echo   Portal Asset Verification
echo ============================================================
echo.

set "MISSING=0"
set "FOUND=0"

REM List of expected portals
set "PORTALS=OrchidJungleBiomePortal OrchidDesertBiomePortal OrchidOceanBiomePortal OrchidSnowBiomePortal BurntDesertBiomePortal WulfrumScrapyardBiomePortal SpiritBiomePortal SpiritModPortal SavannaBiomePortal RedemptionPortal AequusPortal EndPreludePortal StarsAndFirePortal PokeModPortal RandomResourcePortal SynthwaveBiomePortal AsteroidBiomePortal BriarBiomePortal"

echo Checking portal spritesheets...
echo.

for %%P in (%PORTALS%) do (
    set "FOUND_FILE=0"
    
    REM Check for various possible naming conventions
    if exist "%OUTPUT_DIR%\%%P_spritesheet.png" (
        echo [OK] %%P_spritesheet.png found
        set /a FOUND+=1
        set "FOUND_FILE=1
    )
    
    REM Check lowercase versions
    set "LOWER=%%P"
    set "LOWER=!LOWER:OrchidJungleBiomePortal=orchidjunglebiomeportal!"
    set "LOWER=!LOWER:OrchidDesertBiomePortal=orchiddesertbiomeportal!"
    set "LOWER=!LOWER:OrchidOceanBiomePortal=orchidoceanbiomeportal!"
    set "LOWER=!LOWER:OrchidSnowBiomePortal=orchidsnowbiomeportal!"
    set "LOWER=!LOWER:BurntDesertBiomePortal=burntdesertbiomeportal!"
    set "LOWER=!LOWER:WulfrumScrapyardBiomePortal=wulfrumscrapyardbiomeportal!"
    set "LOWER=!LOWER:SpiritBiomePortal=spiritbiomeportal!"
    set "LOWER=!LOWER:SpiritModPortal=spiritmodportal!"
    set "LOWER=!LOWER:SavannaBiomePortal=savannabiomeportal!"
    set "LOWER=!LOWER:RedemptionPortal=redemptionportal!"
    set "LOWER=!LOWER:AequusPortal=aequusportal!"
    set "LOWER=!LOWER:EndPreludePortal=endpreludeportal!"
    set "LOWER=!LOWER:StarsAndFirePortal=starsandfireportal!"
    set "LOWER=!LOWER:PokeModPortal=pokemodportal!"
    set "LOWER=!LOWER:RandomResourcePortal=randomresourceportal!"
    set "LOWER=!LOWER:SynthwaveBiomePortal=synthwavebiomeportal!"
    set "LOWER=!LOWER:AsteroidBiomePortal=asteroidbiomeportal!"
    set "LOWER=!LOWER:BriarBiomePortal=briarbiomeportal!"
    
    if !FOUND_FILE! equ 0 (
        if exist "%MOD_TILES%\!LOWER!_spritesheet.png" (
            echo [OK] !LOWER!_spritesheet.png found
            set /a FOUND+=1
            set "FOUND_FILE=1
        )
    )
    
    if !FOUND_FILE! equ 0 (
        echo [MISSING] %%P spritesheet not found
        set /a MISSING+=1
    )
)

echo.
echo Checking portal item textures...
echo.

set "MISSING_ITEMS=0"
set "FOUND_ITEMS=0"

for %%P in (%PORTALS%) do (
    set "FOUND_ITEM=0"
    
    REM Check for various possible naming conventions
    if exist "%MOD_ITEMS%\%%Pitem.png" (
        echo [OK] %%Pitem.png found
        set /a FOUND_ITEMS+=1
        set "FOUND_ITEM=1
    )
    
    REM Check lowercase versions
    set "LOWER=%%P"
    set "LOWER=!LOWER:OrchidJungleBiomePortal=orchidjunglebiomeportal!"
    set "LOWER=!LOWER:OrchidDesertBiomePortal=orchiddesertbiomeportal!"
    set "LOWER=!LOWER:OrchidOceanBiomePortal=orchidoceanbiomeportal!"
    set "LOWER=!LOWER:OrchidSnowBiomePortal=orchidsnowbiomeportal!"
    set "LOWER=!LOWER:BurntDesertBiomePortal=burntdesertbiomeportal!"
    set "LOWER=!LOWER:WulfrumScrapyardBiomePortal=wulfrumscrapyardbiomeportal!"
    set "LOWER=!LOWER:SpiritBiomePortal=spiritbiomeportal!"
    set "LOWER=!LOWER:SpiritModPortal=spiritmodportal!"
    set "LOWER=!LOWER:SavannaBiomePortal=savannabiomeportal!"
    set "LOWER=!LOWER:RedemptionPortal=redemptionportal!"
    set "LOWER=!LOWER:AequusPortal=aequusportal!"
    set "LOWER=!LOWER:EndPreludePortal=endpreludeportal!"
    set "LOWER=!LOWER:StarsAndFirePortal=starsandfireportal!"
    set "LOWER=!LOWER:PokeModPortal=pokemodportal!"
    set "LOWER=!LOWER:RandomResourcePortal=randomresourceportal!"
    set "LOWER=!LOWER:SynthwaveBiomePortal=synthwavebiomeportal!"
    set "LOWER=!LOWER:AsteroidBiomePortal=asteroidbiomeportal!"
    set "LOWER=!LOWER:BriarBiomePortal=briarbiomeportal!"
    
    if !FOUND_ITEM! equ 0 (
        if exist "%MOD_ITEMS%\!LOWER!item.png" (
            echo [OK] !LOWER!item.png found
            set /a FOUND_ITEMS+=1
            set "FOUND_ITEM=1
        )
    )
    
    if !FOUND_ITEM! equ 0 (
        echo [MISSING] %%P item texture not found
        set /a MISSING_ITEMS+=1
    )
)

echo.
echo ============================================================
echo   Summary
echo ============================================================
echo.
echo Spritesheets: !FOUND! found, !MISSING! missing
echo Item Textures: !FOUND_ITEMS! found, !MISSING_ITEMS! missing
echo.

if !MISSING! equ 0 (
    echo [SUCCESS] All portal spritesheets are present!
) else (
    echo [WARNING] Some portal spritesheets are missing.
    echo           You may need to regenerate them or check file names.
)

if !MISSING_ITEMS! equ 0 (
    echo [SUCCESS] All portal item textures are present!
) else (
    echo [WARNING] Some portal item textures are missing.
    echo           Run extract_portal_item.py to generate them.
)

echo.
pause
endlocal
