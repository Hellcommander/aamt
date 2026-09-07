@echo off
REM ============================================================
REM Generate Terraria Portal Spritesheets
REM Uses Ollama to generate animated portal assets
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"
set "OUTPUT_DIR=d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

echo.
echo ============================================================
echo   Terraria Portal Spritesheet Generator
echo ============================================================
echo.

cd /d "%SCRIPT_DIR%"

echo Generating Corruption Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" `
    -PortalName "CorruptionPortal" `
    -Description "A dark purple corruption portal with swirling energy and distortion waves" `
    -Preset Shadow `
    -TileSize 16 `
    -FrameCount 8 `
    -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Corruption Portal generation failed
    pause
    exit /b 1
)

echo.
echo Generating Story of Red Cloud Portal...
powershell -ExecutionPolicy Bypass -File "TerrariaPortalOllamaGenerator.ps1" `
    -PortalName "StoryOfRedCloudPortal" `
    -Description "A fiery orange-red portal with outward flowing energy particles and heat distortion" `
    -Preset Fire `
    -TileSize 16 `
    -FrameCount 8 `
    -OutputDir "%OUTPUT_DIR%"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Story of Red Cloud Portal generation failed
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

if exist "%OUTPUT_DIR%\CorruptionPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\CorruptionPortal_spritesheet.png" "%MOD_ASSETS%\Tiles\CorruptionPortalTile.png" >nul
    copy /Y "%OUTPUT_DIR%\CorruptionPortal_spritesheet.png" "%MOD_ASSETS%\Items\CorruptionPortalItem.png" >nul
    echo [OK] Corruption Portal assets copied
)

if exist "%OUTPUT_DIR%\StoryOfRedCloudPortal_spritesheet.png" (
    copy /Y "%OUTPUT_DIR%\StoryOfRedCloudPortal_spritesheet.png" "%MOD_ASSETS%\Tiles\StoryOfRedCloudPortalTile.png" >nul
    copy /Y "%OUTPUT_DIR%\StoryOfRedCloudPortal_spritesheet.png" "%MOD_ASSETS%\Items\StoryOfRedCloudPortalItem.png" >nul
    echo [OK] Story of Red Cloud Portal assets copied
)

echo.
echo ============================================================
echo   Generation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Build mod in tModLoader
echo   2. Test portal animations in-game
echo   3. Adjust animation speed if needed (in tile classes)
echo.

pause
endlocal


