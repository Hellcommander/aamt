@echo off
REM ============================================================
REM GenerateAllAssetsQuick - Quick Asset Generation
REM ============================================================
REM
REM Quick version that runs without prompts
REM ============================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%GenerateAllModSprites.ps1
set MOD_PATH=F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery
REM Default models:
REM   OllamaModel: codellama:7b-instruct (code-focused, good for structured output)
REM   PlanningModel: codellama:7b-instruct (for structured planning/analysis)
REM   VisualModel: wizardlm-uncensored (best for visual/creative asset descriptions)
REM Alternatives: starcoder:7b, codellama:13b-instruct, codellama:34b-instruct
set OLLAMA_MODEL=codellama:7b-instruct
set PLANNING_MODEL=codellama:7b-instruct
set VISUAL_MODEL=wizardlm-uncensored

if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found
    exit /b 1
)

echo Generating all assets...
pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"

set PLACEHOLDER_SCRIPT=%SCRIPT_DIR%GeneratePlaceholderAssets.ps1
if exist "%PLACEHOLDER_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PLACEHOLDER_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
)

set ANIMATION_SCRIPT=%SCRIPT_DIR%GenerateAnimationSprites.ps1
if exist "%ANIMATION_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ANIMATION_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%"
)

set ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateAlchemicalGrenadeLauncherAssets.ps1
if exist "%ALCHEMICAL_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

set DUNGEON_SCRIPT=%SCRIPT_DIR%GenerateFloatingDungeonAssets.ps1
if exist "%DUNGEON_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%DUNGEON_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

set MECH_ANIM_SCRIPT=%SCRIPT_DIR%GenerateMechWeaponMagicAnimations.ps1
if exist "%MECH_ANIM_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECH_ANIM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

set ENHANCED_ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateEnhancedAlchemicalLauncherAssets.ps1
if exist "%ENHANCED_ALCHEMICAL_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ENHANCED_ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

set MAGIC_ORB_SCRIPT=%SCRIPT_DIR%GenerateMagicOrbAssets.ps1
if exist "%MAGIC_ORB_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MAGIC_ORB_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

set CENTIPEDE_FORM_SCRIPT=%SCRIPT_DIR%GenerateCentipedeFormAssets.ps1
if exist "%CENTIPEDE_FORM_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CENTIPEDE_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -SkipExisting
)

REM Generate specialized assets
set OLLAMA_GENERATOR=%SCRIPT_DIR%StarboundOllamaAssetGenerator.ps1
if exist "%OLLAMA_GENERATOR%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "magicportal" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -OutputDir "%MOD_PATH%\assets" 2>nul
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "spellcast" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -OutputDir "%MOD_PATH%\assets" 2>nul
)

set BEHAVIOR_SCRIPT=%SCRIPT_DIR%StarboundBehaviorGenerator.ps1
if exist "%BEHAVIOR_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BEHAVIOR_SCRIPT%" -BehaviorName "magitech_monster" -Preset Default -OutputDir "%MOD_PATH%\assets" 2>nul
)

set CURSOR_SCRIPT=%SCRIPT_DIR%StarboundCursorGenerator.ps1
if exist "%CURSOR_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CURSOR_SCRIPT%" -CursorName "magitech_cursor" -Preset Default -OutputDir "%MOD_PATH%\assets" 2>nul
)

set TILE_SCRIPT=%SCRIPT_DIR%StarboundTileGenerator.ps1
if exist "%TILE_SCRIPT%" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TILE_SCRIPT%" -TileName "magitech_block" -Preset Basic -OutputDir "%MOD_PATH%\assets" 2>nul
)

echo.
echo Running quality checker on generated assets...
set QUALITY_CHECKER=%SCRIPT_DIR%starbound_asset_quality_checker.bat
set ASSETS_DIR=%MOD_PATH%\assets
if exist "%QUALITY_CHECKER%" if exist "%ASSETS_DIR%" (
    call "%QUALITY_CHECKER%" "%ASSETS_DIR%"
)

echo.
echo Done!
