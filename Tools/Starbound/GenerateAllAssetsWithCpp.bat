@echo off
REM ============================================================
REM GenerateAllAssetsWithCpp - Asset Generation with C++ Backend
REM ============================================================
REM
REM Generates all assets using the C++ backend for better quality
REM ============================================================

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%GenerateAllModSprites.ps1
set MOD_PATH=F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery
set OLLAMA_MODEL=codellama:7b-instruct

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Magi-Tech Asset Generation - C++ Backend Mode
echo ============================================================
echo.
echo Generating all assets with C++ backend for better quality...
echo Mod Path: %MOD_PATH%
echo Ollama Model: %OLLAMA_MODEL%
echo.

REM Run the main asset generation script with C++ backend
pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend

set MAIN_EXIT=%ERRORLEVEL%

REM Also generate placeholder replacement assets with C++ backend
echo.
echo Generating placeholder replacement assets with C++ backend...
echo.

set PLACEHOLDER_SCRIPT=%SCRIPT_DIR%GeneratePlaceholderAssets.ps1
if exist "%PLACEHOLDER_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PLACEHOLDER_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend
    set PLACEHOLDER_EXIT=%ERRORLEVEL%
) else (
    echo WARNING: Placeholder asset generator script not found
    set PLACEHOLDER_EXIT=0
)

REM Generate animation spritesheets with C++ backend
echo.
echo Generating animation spritesheets with C++ backend...
echo.

set ANIMATION_SCRIPT=%SCRIPT_DIR%GenerateAnimationSprites.ps1
if exist "%ANIMATION_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ANIMATION_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend
    set ANIMATION_EXIT=%ERRORLEVEL%
) else (
    echo WARNING: Animation sprite generator script not found
    set ANIMATION_EXIT=0
)

REM Generate Alchemical Grenade Launcher assets
set ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateAlchemicalGrenadeLauncherAssets.ps1
if exist "%ALCHEMICAL_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set ALCHEMICAL_EXIT=%ERRORLEVEL%
) else (
    set ALCHEMICAL_EXIT=0
)

REM Generate Floating Dungeon assets
set DUNGEON_SCRIPT=%SCRIPT_DIR%GenerateFloatingDungeonAssets.ps1
if exist "%DUNGEON_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%DUNGEON_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set DUNGEON_EXIT=%ERRORLEVEL%
) else (
    set DUNGEON_EXIT=0
)

REM Generate Mech Weapon & Magic Animations
set MECH_ANIM_SCRIPT=%SCRIPT_DIR%GenerateMechWeaponMagicAnimations.ps1
if exist "%MECH_ANIM_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECH_ANIM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set MECH_ANIM_EXIT=%ERRORLEVEL%
) else (
    set MECH_ANIM_EXIT=0
)

REM Generate Enhanced Alchemical Launcher Assets
set ENHANCED_ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateEnhancedAlchemicalLauncherAssets.ps1
if exist "%ENHANCED_ALCHEMICAL_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ENHANCED_ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set ENHANCED_ALCHEMICAL_EXIT=%ERRORLEVEL%
) else (
    set ENHANCED_ALCHEMICAL_EXIT=0
)

REM Generate Magic Orb Assets
set MAGIC_ORB_SCRIPT=%SCRIPT_DIR%GenerateMagicOrbAssets.ps1
if exist "%MAGIC_ORB_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MAGIC_ORB_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set MAGIC_ORB_EXIT=%ERRORLEVEL%
) else (
    set MAGIC_ORB_EXIT=0
)

REM Generate Centipede Form Assets
set CENTIPEDE_FORM_SCRIPT=%SCRIPT_DIR%GenerateCentipedeFormAssets.ps1
if exist "%CENTIPEDE_FORM_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CENTIPEDE_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -UseCppBackend
    set CENTIPEDE_FORM_EXIT=%ERRORLEVEL%
) else (
    set CENTIPEDE_FORM_EXIT=0
)

REM Generate specialized assets with C++ backend
echo.
echo Generating specialized assets with C++ backend...
echo.

set SPECIALIZED_EXIT=0
set OLLAMA_GENERATOR=%SCRIPT_DIR%StarboundOllamaAssetGenerator.ps1

if exist "%OLLAMA_GENERATOR%" (
    echo Generating particle effects...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "magicportal" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "spellcast" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "magicaura" -OllamaModel "%OLLAMA_MODEL%" -UseCppBackend -OutputDir "%MOD_PATH%\assets" 2>nul
)

set BEHAVIOR_SCRIPT=%SCRIPT_DIR%StarboundBehaviorGenerator.ps1
if exist "%BEHAVIOR_SCRIPT%" (
    echo Generating AI behaviors...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BEHAVIOR_SCRIPT%" -BehaviorName "magitech_monster" -Preset Default -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BEHAVIOR_SCRIPT%" -BehaviorName "magitech_boss" -Preset Boss -HealthStages 3 -OutputDir "%MOD_PATH%\assets" 2>nul
)

set CURSOR_SCRIPT=%SCRIPT_DIR%StarboundCursorGenerator.ps1
if exist "%CURSOR_SCRIPT%" (
    echo Generating cursors...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CURSOR_SCRIPT%" -CursorName "magitech_cursor" -Preset Default -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CURSOR_SCRIPT%" -CursorName "magitech_pointer" -Preset Pointer -OutputDir "%MOD_PATH%\assets" 2>nul
)

set TILE_SCRIPT=%SCRIPT_DIR%StarboundTileGenerator.ps1
if exist "%TILE_SCRIPT%" (
    echo Generating tiles...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TILE_SCRIPT%" -TileName "magitech_block" -Preset Basic -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TILE_SCRIPT%" -TileName "magitech_protection" -Preset Protection -OutputDir "%MOD_PATH%\assets" 2>nul
)

set SHIP_SCRIPT=%SCRIPT_DIR%StarboundShipGenerator.ps1
if exist "%SHIP_SCRIPT%" (
    echo Generating ship structures...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SHIP_SCRIPT%" -ShipName "magitech_ship" -Race "human" -Preset Generic -MaxTier 8 -OutputDir "%MOD_PATH%\assets" 2>nul
)

echo Specialized asset generation complete.
echo.

echo.
echo ============================================================
echo   Quality Checking Generated Assets
echo ============================================================
echo.

set QUALITY_CHECKER=%SCRIPT_DIR%starbound_asset_quality_checker.bat
set ASSETS_DIR=%MOD_PATH%\assets

if exist "%QUALITY_CHECKER%" (
    if exist "%ASSETS_DIR%" (
        echo Running quality checker on generated assets...
        echo.
        call "%QUALITY_CHECKER%" "%ASSETS_DIR%"
        set QUALITY_EXIT=%ERRORLEVEL%
        echo.
    ) else (
        echo WARNING: Assets directory not found: %ASSETS_DIR%
        set QUALITY_EXIT=0
    )
) else (
    echo WARNING: Quality checker script not found: %QUALITY_CHECKER%
    set QUALITY_EXIT=0
)

echo.
echo ============================================================
echo   Generation Complete
echo ============================================================
echo.

if %MAIN_EXIT% EQU 0 (
    if %PLACEHOLDER_EXIT% EQU 0 (
        if %ANIMATION_EXIT% EQU 0 (
            if %SPECIALIZED_EXIT% EQU 0 (
                echo All assets generated successfully with C++ backend!
            ) else (
                echo Main assets generated, but some specialized assets had issues.
            )
        ) else (
            echo Main and placeholder assets generated, but animation generation had issues.
        )
    ) else (
        echo Main assets generated, but placeholder generation had issues.
    )
) else (
    echo Asset generation completed with errors.
    echo Check the output above for details.
)

if %QUALITY_EXIT% EQU 0 (
    echo Quality checking completed successfully.
) else (
    echo Quality checking completed with warnings.
)

echo.
echo Assets have been saved to:
echo   %MOD_PATH%\assets\
echo.
echo Quality reports saved to:
echo   %ASSETS_DIR%\ASSET_QUALITY_REPORT.md
echo   %ASSETS_DIR%\BEST_ASSETS_MAPPING.md
echo.

pause
