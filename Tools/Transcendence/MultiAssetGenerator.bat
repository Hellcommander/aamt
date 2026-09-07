@echo off
REM ============================================================
REM MultiAssetGenerator.bat - Drag-and-Drop Wrapper
REM ============================================================
REM 
REM Usage:
REM   1. Double-click to run with default settings
REM   2. Drag a JSON config file onto this script
REM   3. Drag a folder to use as output directory
REM
REM Config JSON format:
REM   {
REM     "AssetName": "MyAsset",
REM     "AssetTypes": ["Tile", "Particle", "Icon"],
REM     "GameTypes": ["Terraria", "Elin"],
REM     "Description": "A magical portal effect"
REM   }
REM
REM ============================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%MultiAssetGenerator.ps1"

REM Check if PowerShell 7 (pwsh) is available
where pwsh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "POWERSHELL=pwsh"
) else (
    set "POWERSHELL=powershell"
)

echo ================================================================
echo   Multi-Asset Generator
echo ================================================================
echo.

REM Check if a file/folder was dropped
if "%~1"=="" (
    REM No file dropped - run interactively
    echo No file dropped. Running with interactive mode...
    echo.
    
    REM Prompt for asset name
    set /p "ASSET_NAME=Enter asset name: "
    if "!ASSET_NAME!"=="" (
        echo Error: Asset name is required.
        goto :error
    )
    
    REM Prompt for asset types
    echo.
    echo Available asset types:
    echo   1. Tile
    echo   2. Particle
    echo   3. Icon
    echo   4. FX
    echo   5. Projectile
    echo   6. Texture
    echo   7. Model
    echo   8. Spritesheet
    echo.
    set /p "ASSET_TYPES=Enter asset types (comma-separated, e.g., Tile,Particle): "
    if "!ASSET_TYPES!"=="" set "ASSET_TYPES=Tile"
    
    REM Prompt for game types
    echo.
    echo Available game types:
    echo   1. Terraria
    echo   2. Elin
    echo   3. Qud
    echo   4. Starbound
    echo   5. CDDA
    echo   6. Transcendence
    echo   7. All
    echo.
    set /p "GAME_TYPES=Enter game types (comma-separated, e.g., Terraria,Elin): "
    if "!GAME_TYPES!"=="" set "GAME_TYPES=All"
    
    REM Prompt for description
    echo.
    set /p "DESCRIPTION=Enter asset description (optional): "
    if "!DESCRIPTION!"=="" set "DESCRIPTION=Generated asset"
    
    echo.
    echo Generating assets...
    echo   Name: !ASSET_NAME!
    echo   Types: !ASSET_TYPES!
    echo   Games: !GAME_TYPES!
    echo   Description: !DESCRIPTION!
    echo.
    
    REM Convert comma-separated to PowerShell array format
    set "ASSET_TYPES_PS=!ASSET_TYPES:,=','!"
    set "GAME_TYPES_PS=!GAME_TYPES:,=','!"
    
    %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AssetTypes @('!ASSET_TYPES_PS!') -GameTypes @('!GAME_TYPES_PS!') -AssetName "!ASSET_NAME!" -AssetDescription "!DESCRIPTION!"
    
) else (
    REM File/folder was dropped
    set "DROPPED=%~1"
    set "DROPPED_EXT=%~x1"
    
    if /i "!DROPPED_EXT!"==".json" (
        REM JSON config file was dropped
        echo Processing config file: %~nx1
        echo.
        
        REM Parse JSON and run
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -Command ^
            "$config = Get-Content -Raw '%~1' | ConvertFrom-Json; ^
            $assetTypes = if ($config.AssetTypes) { $config.AssetTypes } else { @('Tile') }; ^
            $gameTypes = if ($config.GameTypes) { $config.GameTypes } else { @('All') }; ^
            $assetName = if ($config.AssetName) { $config.AssetName } else { 'DroppedAsset' }; ^
            $description = if ($config.Description) { $config.Description } else { 'Generated asset' }; ^
            $outputDir = if ($config.OutputDir) { $config.OutputDir } else { 'GeneratedAssets' }; ^
            & '%PS_SCRIPT%' -AssetTypes $assetTypes -GameTypes $gameTypes -AssetName $assetName -AssetDescription $description -OutputDir $outputDir"
    ) else if exist "%~1\" (
        REM Folder was dropped - use as output directory
        echo Using dropped folder as output directory: %~1
        echo.
        
        set /p "ASSET_NAME=Enter asset name: "
        if "!ASSET_NAME!"=="" set "ASSET_NAME=GeneratedAsset"
        
        %POWERSHELL% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -AssetTypes @('Tile','Texture') -GameTypes @('All') -AssetName "!ASSET_NAME!" -OutputDir "%~1"
    ) else (
        echo Unknown file type: %~nx1
        echo.
        echo Supported inputs:
        echo   - JSON config file (.json)
        echo   - Folder (for output directory)
        echo.
        goto :error
    )
)

if %ERRORLEVEL% neq 0 goto :error

echo.
echo ================================================================
echo   Generation Complete!
echo ================================================================
echo.
goto :end

:error
echo.
echo ================================================================
echo   An error occurred. Check the output above for details.
echo ================================================================
echo.

:end
echo Press any key to exit...
pause >nul
endlocal

