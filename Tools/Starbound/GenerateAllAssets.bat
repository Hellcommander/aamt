@echo off
REM ============================================================
REM GenerateAllAssets - Master Asset Generation Script
REM ============================================================
REM
REM Generates ALL assets for the Magi-Tech Arcane Alchemy and Sorcery mod
REM This includes:
REM   - All system-specific assets (Enchantment, AlchemistBus, Orbital, etc.)
REM   - All placeholder replacement assets
REM   - All mod sprites and animations
REM   - All animation spritesheets
REM   - Specialized assets (particles, behaviors, cursors, tiles, ships)
REM   - Quality checking and best asset selection
REM
REM Specialized generators (Particle, Behavior, Cursor, Tile, Ship) are
REM available as standalone tools and can be run individually as needed.
REM Quality checking automatically processes all generated assets.
REM
REM Quality Assessment:
REM   - Defaults to "full" quality assessment (both vision models)
REM   - Optimized for overnight runs - takes longer but produces highest quality
REM   - Uses Qwen3-VL-8B (mechanical QA) + LLaVA:13b (aesthetic assessment)
REM   - All models automatically unload after use to manage VRAM efficiently
REM
REM VRAM Management:
REM   - All Ollama models are automatically unloaded after each script completes
REM   - Final cleanup unloads all remaining models to free VRAM
REM   - This ensures efficient memory usage during long generation sessions
REM ============================================================

@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   GenerateAllAssets.bat - Starting...
echo ============================================================
echo Current directory: %CD%
echo Script directory: %~dp0
echo.

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%GenerateAllModSprites.ps1
set MOD_PATH=F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery

echo Verifying paths...
echo   Script directory: %SCRIPT_DIR%
echo   PowerShell script: %PS_SCRIPT%
echo   Mod path: %MOD_PATH%
echo.
REM Default models (optimized for asset generation pipeline):
REM   OllamaModel: qwen2.5-coder:7b (simple/fallback tasks)
REM   PlanningModel: qwen2.5-coder:14b (structured asset planning - JSON, atlas layouts, segment definitions)
REM   VisualModel: llama3.1:8b (creative concepting - descriptions, silhouettes, mechform ideas)
REM   AnalysisModel: deepseek-r1:7b (hybrid tasks - concept + structured output, math/balancing)
set OLLAMA_MODEL=qwen2.5-coder:7b
set PLANNING_MODEL=qwen2.5-coder:14b
set VISUAL_MODEL=llama3.1:8b

REM Quality assessment depth (optimized for overnight runs - full assessment with both vision models):
REM   "fast" = sanity checks only (no AI models, fastest)
REM   "mechanical" = Qwen3-VL-8B for technical defect detection
REM   "full" = Both Qwen3-VL-8B (60%) + LLaVA:13b (40%) for complete assessment (default for overnight runs)
set QUALITY_ASSESSMENT_DEPTH=full

REM Check if PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo [ERROR] PowerShell script not found at:
    echo   %PS_SCRIPT%
    echo.
    echo Please verify the script exists and try again.
    if defined STARBOUND_INTERACTIVE pause
    exit /b 1
)

REM Check if ModPath exists
if not exist "%MOD_PATH%" (
    echo [WARNING] Mod path does not exist:
    echo   %MOD_PATH%
    echo.
    echo The script will attempt to create directories as needed.
    echo.
)

echo.
echo ============================================================
echo   Magi-Tech Asset Generation - Complete Suite
echo ============================================================
echo.
echo This will generate ALL assets for the mod:
echo   - System assets (Enchantment, AlchemistBus, Orbital, VFS, etc.)
echo   - Agent assets (Buff, Composition, Durability, Inventory, Portal, etc.)
echo   - All mech form assets (AllMechForm, Animations, Cockpits, etc.)
echo   - Specialized mech forms (Abnormal, Quadruped, Lore, Horror, etc.)
echo   - Additional forms (Raptor, BladeCyclone, TentacledHorror, Hydra, etc.)
echo   - New Magitech Mechforms (Aether Warden, Flux Strider, Iron Bloom, Null Harrier, Shardwright, Helix Bastion)
echo   - Mech variants and custom variants
echo   - Weapon systems (Alchemical Grenade, Enhanced Launcher, Magic Orb)
echo   - Crafting and alchemy assets (Crafting Station, Potions, Reagents, VFX)
echo   - Placeholder replacement assets
echo   - Animation spritesheets
echo   - Specialized assets (particles, behaviors, cursors, tiles, ships)
echo   - Quality checking (keeps only best assets)
echo.
echo Mod Path: %MOD_PATH%
echo Planning Model: %PLANNING_MODEL% (structured asset planning - JSON, atlas layouts, segment definitions)
echo Visual Model: %VISUAL_MODEL% (creative concepting - descriptions, silhouettes, mechform ideas)
echo Quality Assessment: %QUALITY_ASSESSMENT_DEPTH% (full assessment with both vision models - optimized for overnight runs)
echo.
echo NOTE: This script is designed to run overnight. Full quality assessment is enabled by default.
echo       All AI models will be automatically unloaded after use to manage VRAM efficiently.
echo.
REM Non-interactive by default (designed for unattended overnight runs).
REM Set STARBOUND_INTERACTIVE=1 to require a keypress before starting.
if defined STARBOUND_INTERACTIVE (
    echo Press any key to start generation, or Ctrl+C to cancel...
    pause >nul
) else (
    echo [INFO] Non-interactive mode: starting generation automatically.
    echo        Set STARBOUND_INTERACTIVE=1 for a confirmation prompt.
)

echo.
echo Starting asset generation...
echo.

REM Test PowerShell script syntax first
echo [INFO] Testing PowerShell script syntax...
where pwsh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set PS_CMD=powershell
) else (
    set PS_CMD=pwsh
)

%PS_CMD% -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference = 'Stop'; try { $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content '%PS_SCRIPT%' -Raw), [ref]$null); Write-Host '[OK] Script syntax is valid' -ForegroundColor Green } catch { Write-Host '[ERROR] Script has syntax errors:' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 } }"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PowerShell script has syntax errors. Please fix them before running.
    echo.
    if defined STARBOUND_INTERACTIVE pause
    exit /b 1
)

echo.
REM Run the main asset generation script
echo [INFO] Running main asset generation script...
echo Command: %PS_CMD% -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -QualityAssessmentDepth "%QUALITY_ASSESSMENT_DEPTH%"
echo.

REM Check if pwsh exists, fallback to powershell if not
where pwsh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] pwsh not found, trying powershell instead...
    where powershell >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Neither pwsh nor powershell found in PATH!
        echo Please install PowerShell or add it to your PATH.
        if defined STARBOUND_INTERACTIVE pause
        exit /b 1
    )
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference = 'Continue'; try { & '%PS_SCRIPT%' -ModPath '%MOD_PATH%' -OllamaModel '%OLLAMA_MODEL%' -PlanningModel '%PLANNING_MODEL%' -VisualModel '%VISUAL_MODEL%' -QualityAssessmentDepth '%QUALITY_ASSESSMENT_DEPTH%'; if ($LASTEXITCODE -ne 0) { Write-Host '[ERROR] Script exited with code:' $LASTEXITCODE -ForegroundColor Red; exit $LASTEXITCODE } } catch { Write-Host '[ERROR] Script failed:' $_.Exception.Message -ForegroundColor Red; Write-Host $_.ScriptStackTrace -ForegroundColor Yellow; exit 1 } }"
) else (
    pwsh -NoProfile -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference = 'Continue'; try { & '%PS_SCRIPT%' -ModPath '%MOD_PATH%' -OllamaModel '%OLLAMA_MODEL%' -PlanningModel '%PLANNING_MODEL%' -VisualModel '%VISUAL_MODEL%' -QualityAssessmentDepth '%QUALITY_ASSESSMENT_DEPTH%'; if ($LASTEXITCODE -ne 0) { Write-Host '[ERROR] Script exited with code:' $LASTEXITCODE -ForegroundColor Red; exit $LASTEXITCODE } } catch { Write-Host '[ERROR] Script failed:' $_.Exception.Message -ForegroundColor Red; Write-Host $_.ScriptStackTrace -ForegroundColor Yellow; exit 1 } }"
)

set MAIN_EXIT=%ERRORLEVEL%
if not %MAIN_EXIT% EQU 0 (
    echo.
    echo [ERROR] GenerateAllModSprites.ps1 exited with error code %MAIN_EXIT%
    echo Check the output above for details.
    echo.
    if defined STARBOUND_INTERACTIVE (
        echo Press any key to continue with remaining asset generation...
        pause >nul
    ) else (
        echo [INFO] Non-interactive mode: continuing with remaining asset generation.
    )
)

REM Also generate placeholder replacement assets
echo.
echo ============================================================
echo   Generating Placeholder Replacement Assets
echo ============================================================
echo.

set PLACEHOLDER_SCRIPT=%SCRIPT_DIR%GeneratePlaceholderAssets.ps1
if exist "%PLACEHOLDER_SCRIPT%" (
    echo Running GeneratePlaceholderAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PLACEHOLDER_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set PLACEHOLDER_EXIT=%ERRORLEVEL%
    if not %PLACEHOLDER_EXIT% EQU 0 (
        echo [ERROR] GeneratePlaceholderAssets.ps1 exited with error code %PLACEHOLDER_EXIT%
    )
) else (
    echo [WARNING] Placeholder asset generator script not found: %PLACEHOLDER_SCRIPT%
    set PLACEHOLDER_EXIT=0
)

REM Generate animation spritesheets
echo.
echo ============================================================
echo   Generating Animation Spritesheets
echo ============================================================
echo.

set ANIMATION_SCRIPT=%SCRIPT_DIR%GenerateAnimationSprites.ps1
if exist "%ANIMATION_SCRIPT%" (
    echo Running GenerateAnimationSprites.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ANIMATION_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%"
    set ANIMATION_EXIT=%ERRORLEVEL%
    if not %ANIMATION_EXIT% EQU 0 (
        echo [ERROR] GenerateAnimationSprites.ps1 exited with error code %ANIMATION_EXIT%
    )
) else (
    echo [WARNING] Animation sprite generator script not found: %ANIMATION_SCRIPT%
    set ANIMATION_EXIT=0
)

REM Generate Alchemical Grenade Launcher assets
echo.
echo ============================================================
echo   Generating Alchemical Grenade Launcher Assets
echo ============================================================
echo.

set ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateAlchemicalGrenadeLauncherAssets.ps1
if exist "%ALCHEMICAL_SCRIPT%" (
    echo Running GenerateAlchemicalGrenadeLauncherAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ALCHEMICAL_EXIT=%ERRORLEVEL%
    if not %ALCHEMICAL_EXIT% EQU 0 (
        echo [ERROR] GenerateAlchemicalGrenadeLauncherAssets.ps1 exited with error code %ALCHEMICAL_EXIT%
    )
) else (
    echo [WARNING] Alchemical Grenade Launcher asset generator script not found: %ALCHEMICAL_SCRIPT%
    set ALCHEMICAL_EXIT=0
)

REM Generate Floating Dungeon assets
echo.
echo ============================================================
echo   Generating Floating Dungeon Generator Assets
echo ============================================================
echo.

set DUNGEON_SCRIPT=%SCRIPT_DIR%GenerateFloatingDungeonAssets.ps1
if exist "%DUNGEON_SCRIPT%" (
    echo Running GenerateFloatingDungeonAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%DUNGEON_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set DUNGEON_EXIT=%ERRORLEVEL%
    if not %DUNGEON_EXIT% EQU 0 (
        echo [ERROR] GenerateFloatingDungeonAssets.ps1 exited with error code %DUNGEON_EXIT%
    )
) else (
    echo [WARNING] Floating Dungeon asset generator script not found: %DUNGEON_SCRIPT%
    set DUNGEON_EXIT=0
)

REM Generate Mech Weapon & Magic Animations
echo.
echo ============================================================
echo   Generating Mech Weapon & Magic Animations
echo ============================================================
echo.

set MECH_ANIM_SCRIPT=%SCRIPT_DIR%GenerateMechWeaponMagicAnimations.ps1
if exist "%MECH_ANIM_SCRIPT%" (
    echo Running GenerateMechWeaponMagicAnimations.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECH_ANIM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set MECH_ANIM_EXIT=%ERRORLEVEL%
    if not %MECH_ANIM_EXIT% EQU 0 (
        echo [ERROR] GenerateMechWeaponMagicAnimations.ps1 exited with error code %MECH_ANIM_EXIT%
    )
) else (
    echo [WARNING] Mech Weapon & Magic Animation generator script not found: %MECH_ANIM_SCRIPT%
    set MECH_ANIM_EXIT=0
)

REM Generate Enhanced Alchemical Launcher Assets
echo.
echo ============================================================
echo   Generating Enhanced Alchemical Launcher Assets
echo ============================================================
echo.

set ENHANCED_ALCHEMICAL_SCRIPT=%SCRIPT_DIR%GenerateEnhancedAlchemicalLauncherAssets.ps1
if exist "%ENHANCED_ALCHEMICAL_SCRIPT%" (
    echo Running GenerateEnhancedAlchemicalLauncherAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ENHANCED_ALCHEMICAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ENHANCED_ALCHEMICAL_EXIT=%ERRORLEVEL%
    if not %ENHANCED_ALCHEMICAL_EXIT% EQU 0 (
        echo [ERROR] GenerateEnhancedAlchemicalLauncherAssets.ps1 exited with error code %ENHANCED_ALCHEMICAL_EXIT%
    )
) else (
    echo [WARNING] Enhanced Alchemical Launcher asset generator script not found: %ENHANCED_ALCHEMICAL_SCRIPT%
    set ENHANCED_ALCHEMICAL_EXIT=0
)

REM Generate Magic Orb Assets
echo.
echo ============================================================
echo   Generating Magic Orb Weapon System Assets
echo ============================================================
echo.

set MAGIC_ORB_SCRIPT=%SCRIPT_DIR%GenerateMagicOrbAssets.ps1
if exist "%MAGIC_ORB_SCRIPT%" (
    echo Running GenerateMagicOrbAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MAGIC_ORB_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set MAGIC_ORB_EXIT=%ERRORLEVEL%
    if not %MAGIC_ORB_EXIT% EQU 0 (
        echo [ERROR] GenerateMagicOrbAssets.ps1 exited with error code %MAGIC_ORB_EXIT%
    )
) else (
    echo [WARNING] Magic Orb asset generator script not found: %MAGIC_ORB_SCRIPT%
    set MAGIC_ORB_EXIT=0
)

REM Generate Centipede Form Assets
echo.
echo ============================================================
echo   Generating Centipede Form Assets
echo ============================================================
echo.

set CENTIPEDE_FORM_SCRIPT=%SCRIPT_DIR%GenerateCentipedeFormAssets.ps1
if exist "%CENTIPEDE_FORM_SCRIPT%" (
    echo Running GenerateCentipedeFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CENTIPEDE_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set CENTIPEDE_FORM_EXIT=%ERRORLEVEL%
    if not %CENTIPEDE_FORM_EXIT% EQU 0 (
        echo [ERROR] GenerateCentipedeFormAssets.ps1 exited with error code %CENTIPEDE_FORM_EXIT%
    )
) else (
    echo [WARNING] Centipede Form asset generator script not found: %CENTIPEDE_FORM_SCRIPT%
    set CENTIPEDE_FORM_EXIT=0
)

REM Generate All Mech Form Assets
echo.
echo ============================================================
echo   Generating All Mech Form Assets
echo ============================================================
echo.

set ALL_MECH_FORM_SCRIPT=%SCRIPT_DIR%GenerateAllMechFormAssets.ps1
if exist "%ALL_MECH_FORM_SCRIPT%" (
    echo Running GenerateAllMechFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALL_MECH_FORM_SCRIPT%" -ModPath "%MOD_PATH%"
    set ALL_MECH_FORM_EXIT=%ERRORLEVEL%
    if not %ALL_MECH_FORM_EXIT% EQU 0 (
        echo [ERROR] GenerateAllMechFormAssets.ps1 exited with error code %ALL_MECH_FORM_EXIT%
    )
) else (
    echo [WARNING] All Mech Form asset generator script not found: %ALL_MECH_FORM_SCRIPT%
    set ALL_MECH_FORM_EXIT=0
)

REM Generate Mech Form Animations
echo.
echo ============================================================
echo   Generating Mech Form Animations
echo ============================================================
echo.

set MECH_FORM_ANIM_SCRIPT=%SCRIPT_DIR%GenerateMechFormAnimations.ps1
if exist "%MECH_FORM_ANIM_SCRIPT%" (
    echo Running GenerateMechFormAnimations.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECH_FORM_ANIM_SCRIPT%" -ModPath "%MOD_PATH%"
    set MECH_FORM_ANIM_EXIT=%ERRORLEVEL%
    if not %MECH_FORM_ANIM_EXIT% EQU 0 (
        echo [ERROR] GenerateMechFormAnimations.ps1 exited with error code %MECH_FORM_ANIM_EXIT%
    )
) else (
    echo [WARNING] Mech Form Animations generator script not found: %MECH_FORM_ANIM_SCRIPT%
    set MECH_FORM_ANIM_EXIT=0
)

REM Generate Mech Cockpit Assets
echo.
echo ============================================================
echo   Generating Mech Cockpit Assets
echo ============================================================
echo.

set MECH_COCKPIT_SCRIPT=%SCRIPT_DIR%GenerateMechCockpitAssets.ps1
if exist "%MECH_COCKPIT_SCRIPT%" (
    echo Running GenerateMechCockpitAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECH_COCKPIT_SCRIPT%" -ModPath "%MOD_PATH%"
    set MECH_COCKPIT_EXIT=%ERRORLEVEL%
    if not %MECH_COCKPIT_EXIT% EQU 0 (
        echo [ERROR] GenerateMechCockpitAssets.ps1 exited with error code %MECH_COCKPIT_EXIT%
    )
) else (
    echo [WARNING] Mech Cockpit asset generator script not found: %MECH_COCKPIT_SCRIPT%
    set MECH_COCKPIT_EXIT=0
)

REM Generate Hook Slinger Form Assets
echo.
echo ============================================================
echo   Generating Hook Slinger Form Assets
echo ============================================================
echo.

set HOOK_SLINGER_SCRIPT=%SCRIPT_DIR%GenerateHookSlingerFormAssets.ps1
if exist "%HOOK_SLINGER_SCRIPT%" (
    echo Running GenerateHookSlingerFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%HOOK_SLINGER_SCRIPT%" -ModPath "%MOD_PATH%"
    set HOOK_SLINGER_EXIT=%ERRORLEVEL%
    if not %HOOK_SLINGER_EXIT% EQU 0 (
        echo [ERROR] GenerateHookSlingerFormAssets.ps1 exited with error code %HOOK_SLINGER_EXIT%
    )
) else (
    echo [WARNING] Hook Slinger Form asset generator script not found: %HOOK_SLINGER_SCRIPT%
    set HOOK_SLINGER_EXIT=0
)

REM Generate Form Wheel UI Assets
echo.
echo ============================================================
echo   Generating Form Wheel UI Assets
echo ============================================================
echo.

set FORM_WHEEL_SCRIPT=%SCRIPT_DIR%GenerateFormWheelUI.ps1
if exist "%FORM_WHEEL_SCRIPT%" (
    echo Running GenerateFormWheelUI.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%FORM_WHEEL_SCRIPT%" -ModPath "%MOD_PATH%"
    set FORM_WHEEL_EXIT=%ERRORLEVEL%
    if not %FORM_WHEEL_EXIT% EQU 0 (
        echo [ERROR] GenerateFormWheelUI.ps1 exited with error code %FORM_WHEEL_EXIT%
    )
) else (
    echo [WARNING] Form Wheel UI asset generator script not found: %FORM_WHEEL_SCRIPT%
    set FORM_WHEEL_EXIT=0
)

REM Generate Abnormal Forms Assets
echo.
echo ============================================================
echo   Generating Abnormal Forms Assets
echo ============================================================
echo.

set ABNORMAL_FORMS_SCRIPT=%SCRIPT_DIR%GenerateAbnormalFormsAssets.ps1
if exist "%ABNORMAL_FORMS_SCRIPT%" (
    echo Running GenerateAbnormalFormsAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ABNORMAL_FORMS_SCRIPT%" -ModPath "%MOD_PATH%"
    set ABNORMAL_FORMS_EXIT=%ERRORLEVEL%
    if not %ABNORMAL_FORMS_EXIT% EQU 0 (
        echo [ERROR] GenerateAbnormalFormsAssets.ps1 exited with error code %ABNORMAL_FORMS_EXIT%
    )
) else (
    echo [WARNING] Abnormal Forms asset generator script not found: %ABNORMAL_FORMS_SCRIPT%
    set ABNORMAL_FORMS_EXIT=0
)

REM Generate Quadruped Forms Assets
echo.
echo ============================================================
echo   Generating Quadruped Forms Assets
echo ============================================================
echo.

set QUADRUPED_FORMS_SCRIPT=%SCRIPT_DIR%GenerateQuadrapedFormsAssets.ps1
if exist "%QUADRUPED_FORMS_SCRIPT%" (
    echo Running GenerateQuadrapedFormsAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%QUADRUPED_FORMS_SCRIPT%" -ModPath "%MOD_PATH%"
    set QUADRUPED_FORMS_EXIT=%ERRORLEVEL%
    if not %QUADRUPED_FORMS_EXIT% EQU 0 (
        echo [ERROR] GenerateQuadrapedFormsAssets.ps1 exited with error code %QUADRUPED_FORMS_EXIT%
    )
) else (
    echo [WARNING] Quadruped Forms asset generator script not found: %QUADRUPED_FORMS_SCRIPT%
    set QUADRUPED_FORMS_EXIT=0
)

REM Generate Starbound Lore Forms Assets
echo.
echo ============================================================
echo   Generating Starbound Lore Forms Assets
echo ============================================================
echo.

set LORE_FORMS_SCRIPT=%SCRIPT_DIR%GenerateStarboundLoreFormsAssets.ps1
if exist "%LORE_FORMS_SCRIPT%" (
    echo Running GenerateStarboundLoreFormsAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%LORE_FORMS_SCRIPT%" -ModPath "%MOD_PATH%"
    set LORE_FORMS_EXIT=%ERRORLEVEL%
    if not %LORE_FORMS_EXIT% EQU 0 (
        echo [ERROR] GenerateStarboundLoreFormsAssets.ps1 exited with error code %LORE_FORMS_EXIT%
    )
) else (
    echo [WARNING] Starbound Lore Forms asset generator script not found: %LORE_FORMS_SCRIPT%
    set LORE_FORMS_EXIT=0
)

REM Generate Horror Forms Assets
echo.
echo ============================================================
echo   Generating Horror Forms Assets
echo ============================================================
echo.

set HORROR_FORMS_SCRIPT=%SCRIPT_DIR%GenerateHorrorFormsAssets.ps1
if exist "%HORROR_FORMS_SCRIPT%" (
    echo Running GenerateHorrorFormsAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%HORROR_FORMS_SCRIPT%" -ModPath "%MOD_PATH%"
    set HORROR_FORMS_EXIT=%ERRORLEVEL%
    if not %HORROR_FORMS_EXIT% EQU 0 (
        echo [ERROR] GenerateHorrorFormsAssets.ps1 exited with error code %HORROR_FORMS_EXIT%
    )
) else (
    echo [WARNING] Horror Forms asset generator script not found: %HORROR_FORMS_SCRIPT%
    set HORROR_FORMS_EXIT=0
)

REM Generate All Mech Variants
echo.
echo ============================================================
echo   Generating All Mech Variants
echo ============================================================
echo.

set ALL_MECH_VARIANTS_SCRIPT=%SCRIPT_DIR%GenerateAllMechVariants.ps1
if exist "%ALL_MECH_VARIANTS_SCRIPT%" (
    echo Running GenerateAllMechVariants.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALL_MECH_VARIANTS_SCRIPT%" -ModPath "%MOD_PATH%"
    set ALL_MECH_VARIANTS_EXIT=%ERRORLEVEL%
    if not %ALL_MECH_VARIANTS_EXIT% EQU 0 (
        echo [ERROR] GenerateAllMechVariants.ps1 exited with error code %ALL_MECH_VARIANTS_EXIT%
    )
) else (
    echo [WARNING] All Mech Variants generator script not found: %ALL_MECH_VARIANTS_SCRIPT%
    set ALL_MECH_VARIANTS_EXIT=0
)

REM Generate MechSet Variants (Game-Usable Complete MechSets)
echo.
echo ============================================================
echo   Generating MechSet Variants (Game-Usable)
echo ============================================================
echo.

set MECHSET_VARIANTS_SCRIPT=%SCRIPT_DIR%GenerateMechSetVariants.ps1
if exist "%MECHSET_VARIANTS_SCRIPT%" (
    echo Running GenerateMechSetVariants.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MECHSET_VARIANTS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set MECHSET_VARIANTS_EXIT=%ERRORLEVEL%
    if not %MECHSET_VARIANTS_EXIT% EQU 0 (
        echo [ERROR] GenerateMechSetVariants.ps1 exited with error code %MECHSET_VARIANTS_EXIT%
    )
) else (
    echo [WARNING] MechSet Variants generator script not found: %MECHSET_VARIANTS_SCRIPT%
    echo [INFO] Creating MechSet Variants generator script...
    set MECHSET_VARIANTS_EXIT=0
)

REM Generate System Assets (Enchantment, AlchemistBus, Orbital, etc.)
echo.
echo ============================================================
echo   Generating System Assets
echo ============================================================
echo.

set ENCHANTMENT_SCRIPT=%SCRIPT_DIR%GenerateEnchantmentAssets.ps1
if exist "%ENCHANTMENT_SCRIPT%" (
    echo Running GenerateEnchantmentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ENCHANTMENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ENCHANTMENT_EXIT=%ERRORLEVEL%
    if not %ENCHANTMENT_EXIT% EQU 0 (
        echo [ERROR] GenerateEnchantmentAssets.ps1 exited with error code %ENCHANTMENT_EXIT%
    )
) else (
    echo [WARNING] Enchantment asset generator script not found: %ENCHANTMENT_SCRIPT%
    set ENCHANTMENT_EXIT=0
)

set ALCHEMIST_BUS_SCRIPT=%SCRIPT_DIR%GenerateAlchemistBusAssets.ps1
if exist "%ALCHEMIST_BUS_SCRIPT%" (
    echo Running GenerateAlchemistBusAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ALCHEMIST_BUS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ALCHEMIST_BUS_EXIT=%ERRORLEVEL%
    if not %ALCHEMIST_BUS_EXIT% EQU 0 (
        echo [ERROR] GenerateAlchemistBusAssets.ps1 exited with error code %ALCHEMIST_BUS_EXIT%
    )
) else (
    echo [WARNING] AlchemistBus asset generator script not found: %ALCHEMIST_BUS_SCRIPT%
    set ALCHEMIST_BUS_EXIT=0
)

set ORBITAL_SCRIPT=%SCRIPT_DIR%GenerateOrbitalAssets.ps1
if exist "%ORBITAL_SCRIPT%" (
    echo Running GenerateOrbitalAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ORBITAL_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ORBITAL_EXIT=%ERRORLEVEL%
    if not %ORBITAL_EXIT% EQU 0 (
        echo [ERROR] GenerateOrbitalAssets.ps1 exited with error code %ORBITAL_EXIT%
    )
) else (
    echo [WARNING] Orbital asset generator script not found: %ORBITAL_SCRIPT%
    set ORBITAL_EXIT=0
)

REM Generate Agent Assets
echo.
echo ============================================================
echo   Generating Agent Assets
echo ============================================================
echo.

set BUFF_AGENT_SCRIPT=%SCRIPT_DIR%GenerateBuffAgentAssets.ps1
if exist "%BUFF_AGENT_SCRIPT%" (
    echo Running GenerateBuffAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BUFF_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set BUFF_AGENT_EXIT=%ERRORLEVEL%
    if not %BUFF_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateBuffAgentAssets.ps1 exited with error code %BUFF_AGENT_EXIT%
    )
) else (
    echo [WARNING] BuffAgent asset generator script not found: %BUFF_AGENT_SCRIPT%
    set BUFF_AGENT_EXIT=0
)

set COMPOSITION_AGENT_SCRIPT=%SCRIPT_DIR%GenerateCompositionAgentAssets.ps1
if exist "%COMPOSITION_AGENT_SCRIPT%" (
    echo Running GenerateCompositionAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%COMPOSITION_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set COMPOSITION_AGENT_EXIT=%ERRORLEVEL%
    if not %COMPOSITION_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateCompositionAgentAssets.ps1 exited with error code %COMPOSITION_AGENT_EXIT%
    )
) else (
    echo [WARNING] CompositionAgent asset generator script not found: %COMPOSITION_AGENT_SCRIPT%
    set COMPOSITION_AGENT_EXIT=0
)

set DURABILITY_AGENT_SCRIPT=%SCRIPT_DIR%GenerateDurabilityAgentAssets.ps1
if exist "%DURABILITY_AGENT_SCRIPT%" (
    echo Running GenerateDurabilityAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%DURABILITY_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set DURABILITY_AGENT_EXIT=%ERRORLEVEL%
    if not %DURABILITY_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateDurabilityAgentAssets.ps1 exited with error code %DURABILITY_AGENT_EXIT%
    )
) else (
    echo [WARNING] DurabilityAgent asset generator script not found: %DURABILITY_AGENT_SCRIPT%
    set DURABILITY_AGENT_EXIT=0
)

set INVENTORY_AGENT_SCRIPT=%SCRIPT_DIR%GenerateInventoryAgentAssets.ps1
if exist "%INVENTORY_AGENT_SCRIPT%" (
    echo Running GenerateInventoryAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%INVENTORY_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set INVENTORY_AGENT_EXIT=%ERRORLEVEL%
    if not %INVENTORY_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateInventoryAgentAssets.ps1 exited with error code %INVENTORY_AGENT_EXIT%
    )
) else (
    echo [WARNING] InventoryAgent asset generator script not found: %INVENTORY_AGENT_SCRIPT%
    set INVENTORY_AGENT_EXIT=0
)

set PORTAL_AGENT_SCRIPT=%SCRIPT_DIR%GeneratePortalAgentAssets.ps1
if exist "%PORTAL_AGENT_SCRIPT%" (
    echo Running GeneratePortalAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PORTAL_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set PORTAL_AGENT_EXIT=%ERRORLEVEL%
    if not %PORTAL_AGENT_EXIT% EQU 0 (
        echo [ERROR] GeneratePortalAgentAssets.ps1 exited with error code %PORTAL_AGENT_EXIT%
    )
) else (
    echo [WARNING] PortalAgent asset generator script not found: %PORTAL_AGENT_SCRIPT%
    set PORTAL_AGENT_EXIT=0
)

set SIMULATION_AGENT_SCRIPT=%SCRIPT_DIR%GenerateSimulationAgentAssets.ps1
if exist "%SIMULATION_AGENT_SCRIPT%" (
    echo Running GenerateSimulationAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SIMULATION_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set SIMULATION_AGENT_EXIT=%ERRORLEVEL%
    if not %SIMULATION_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateSimulationAgentAssets.ps1 exited with error code %SIMULATION_AGENT_EXIT%
    )
) else (
    echo [WARNING] SimulationAgent asset generator script not found: %SIMULATION_AGENT_SCRIPT%
    set SIMULATION_AGENT_EXIT=0
)

set WAND_AGENT_SCRIPT=%SCRIPT_DIR%GenerateWandAgentAssets.ps1
if exist "%WAND_AGENT_SCRIPT%" (
    echo Running GenerateWandAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%WAND_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set WAND_AGENT_EXIT=%ERRORLEVEL%
    if not %WAND_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateWandAgentAssets.ps1 exited with error code %WAND_AGENT_EXIT%
    )
) else (
    echo [WARNING] WandAgent asset generator script not found: %WAND_AGENT_SCRIPT%
    set WAND_AGENT_EXIT=0
)

set MEGA_FORM_AGENT_SCRIPT=%SCRIPT_DIR%GenerateMegaFormAgentAssets.ps1
if exist "%MEGA_FORM_AGENT_SCRIPT%" (
    echo Running GenerateMegaFormAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%MEGA_FORM_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set MEGA_FORM_AGENT_EXIT=%ERRORLEVEL%
    if not %MEGA_FORM_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateMegaFormAgentAssets.ps1 exited with error code %MEGA_FORM_AGENT_EXIT%
    )
) else (
    echo [WARNING] MegaFormAgent asset generator script not found: %MEGA_FORM_AGENT_SCRIPT%
    set MEGA_FORM_AGENT_EXIT=0
)

set GENERATOR_AGENT_SCRIPT=%SCRIPT_DIR%GenerateGeneratorAgentAssets.ps1
if exist "%GENERATOR_AGENT_SCRIPT%" (
    echo Running GenerateGeneratorAgentAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%GENERATOR_AGENT_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set GENERATOR_AGENT_EXIT=%ERRORLEVEL%
    if not %GENERATOR_AGENT_EXIT% EQU 0 (
        echo [ERROR] GenerateGeneratorAgentAssets.ps1 exited with error code %GENERATOR_AGENT_EXIT%
    )
) else (
    echo [WARNING] GeneratorAgent asset generator script not found: %GENERATOR_AGENT_SCRIPT%
    set GENERATOR_AGENT_EXIT=0
)

REM Generate Additional System Assets
echo.
echo ============================================================
echo   Generating Additional System Assets
echo ============================================================
echo.

set VFS_SCRIPT=%SCRIPT_DIR%GenerateVFSAssets.ps1
if exist "%VFS_SCRIPT%" (
    echo Running GenerateVFSAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%VFS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set VFS_EXIT=%ERRORLEVEL%
    if not %VFS_EXIT% EQU 0 (
        echo [ERROR] GenerateVFSAssets.ps1 exited with error code %VFS_EXIT%
    )
) else (
    echo [WARNING] VFS asset generator script not found: %VFS_SCRIPT%
    set VFS_EXIT=0
)

set GOLEM_SCRIPT=%SCRIPT_DIR%GenerateGolemAssets.ps1
if exist "%GOLEM_SCRIPT%" (
    echo Running GenerateGolemAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%GOLEM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set GOLEM_EXIT=%ERRORLEVEL%
    if not %GOLEM_EXIT% EQU 0 (
        echo [ERROR] GenerateGolemAssets.ps1 exited with error code %GOLEM_EXIT%
    )
) else (
    echo [WARNING] Golem asset generator script not found: %GOLEM_SCRIPT%
    set GOLEM_EXIT=0
)

set PLUGIN_SCRIPT=%SCRIPT_DIR%GeneratePluginAssets.ps1
if exist "%PLUGIN_SCRIPT%" (
    echo Running GeneratePluginAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%PLUGIN_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set PLUGIN_EXIT=%ERRORLEVEL%
    if not %PLUGIN_EXIT% EQU 0 (
        echo [ERROR] GeneratePluginAssets.ps1 exited with error code %PLUGIN_EXIT%
    )
) else (
    echo [WARNING] Plugin asset generator script not found: %PLUGIN_SCRIPT%
    set PLUGIN_EXIT=0
)

set ANOMALY_SCRIPT=%SCRIPT_DIR%GenerateAnomalyAssets.ps1
if exist "%ANOMALY_SCRIPT%" (
    echo Running GenerateAnomalyAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%ANOMALY_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set ANOMALY_EXIT=%ERRORLEVEL%
    if not %ANOMALY_EXIT% EQU 0 (
        echo [ERROR] GenerateAnomalyAssets.ps1 exited with error code %ANOMALY_EXIT%
    )
) else (
    echo [WARNING] Anomaly asset generator script not found: %ANOMALY_SCRIPT%
    set ANOMALY_EXIT=0
)

set REMAINING_SYSTEM_SCRIPT=%SCRIPT_DIR%GenerateRemainingSystemAssets.ps1
if exist "%REMAINING_SYSTEM_SCRIPT%" (
    echo Running GenerateRemainingSystemAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%REMAINING_SYSTEM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set REMAINING_SYSTEM_EXIT=%ERRORLEVEL%
    if not %REMAINING_SYSTEM_EXIT% EQU 0 (
        echo [ERROR] GenerateRemainingSystemAssets.ps1 exited with error code %REMAINING_SYSTEM_EXIT%
    )
) else (
    echo [WARNING] Remaining System asset generator script not found: %REMAINING_SYSTEM_SCRIPT%
    set REMAINING_SYSTEM_EXIT=0
)

set SKILL_SYSTEM_SCRIPT=%SCRIPT_DIR%GenerateSkillSystemAssets.ps1
if exist "%SKILL_SYSTEM_SCRIPT%" (
    echo Running GenerateSkillSystemAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SKILL_SYSTEM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set SKILL_SYSTEM_EXIT=%ERRORLEVEL%
    if not %SKILL_SYSTEM_EXIT% EQU 0 (
        echo [ERROR] GenerateSkillSystemAssets.ps1 exited with error code %SKILL_SYSTEM_EXIT%
    )
) else (
    echo [WARNING] Skill System asset generator script not found: %SKILL_SYSTEM_SCRIPT%
    set SKILL_SYSTEM_EXIT=0
)

set TAMING_SYSTEM_SCRIPT=%SCRIPT_DIR%GenerateTamingSystemAssets.ps1
if exist "%TAMING_SYSTEM_SCRIPT%" (
    echo Running GenerateTamingSystemAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TAMING_SYSTEM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set TAMING_SYSTEM_EXIT=%ERRORLEVEL%
    if not %TAMING_SYSTEM_EXIT% EQU 0 (
        echo [ERROR] GenerateTamingSystemAssets.ps1 exited with error code %TAMING_SYSTEM_EXIT%
    )
) else (
    echo [WARNING] Taming System asset generator script not found: %TAMING_SYSTEM_SCRIPT%
    set TAMING_SYSTEM_EXIT=0
)

set STAR_SYSTEM_SCRIPT=%SCRIPT_DIR%GenerateStarSystemAssets.ps1
if exist "%STAR_SYSTEM_SCRIPT%" (
    echo Running GenerateStarSystemAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%STAR_SYSTEM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set STAR_SYSTEM_EXIT=%ERRORLEVEL%
    if not %STAR_SYSTEM_EXIT% EQU 0 (
        echo [ERROR] GenerateStarSystemAssets.ps1 exited with error code %STAR_SYSTEM_EXIT%
    )
) else (
    echo [WARNING] Star System asset generator script not found: %STAR_SYSTEM_SCRIPT%
    set STAR_SYSTEM_EXIT=0
)

REM Generate Additional Form Assets
echo.
echo ============================================================
echo   Generating Additional Form Assets
echo ============================================================
echo.

set RAPTOR_FORM_SCRIPT=%SCRIPT_DIR%GenerateRaptorFormAssets.ps1
if exist "%RAPTOR_FORM_SCRIPT%" (
    echo Running GenerateRaptorFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%RAPTOR_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set RAPTOR_FORM_EXIT=%ERRORLEVEL%
    if not %RAPTOR_FORM_EXIT% EQU 0 (
        echo [ERROR] GenerateRaptorFormAssets.ps1 exited with error code %RAPTOR_FORM_EXIT%
    )
) else (
    echo [WARNING] Raptor Form asset generator script not found: %RAPTOR_FORM_SCRIPT%
    set RAPTOR_FORM_EXIT=0
)

set BLADE_CYCLONE_FORM_SCRIPT=%SCRIPT_DIR%GenerateBladeCycloneFormAssets.ps1
if exist "%BLADE_CYCLONE_FORM_SCRIPT%" (
    echo Running GenerateBladeCycloneFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BLADE_CYCLONE_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set BLADE_CYCLONE_FORM_EXIT=%ERRORLEVEL%
    if not %BLADE_CYCLONE_FORM_EXIT% EQU 0 (
        echo [ERROR] GenerateBladeCycloneFormAssets.ps1 exited with error code %BLADE_CYCLONE_FORM_EXIT%
    )
) else (
    echo [WARNING] Blade Cyclone Form asset generator script not found: %BLADE_CYCLONE_FORM_SCRIPT%
    set BLADE_CYCLONE_FORM_EXIT=0
)

REM Generate New Magitech Mechforms Assets
echo.
echo ============================================================
echo   Generating New Magitech Mechforms Assets
echo ============================================================
echo.

set NEW_MAGITECH_MECHFORMS_SCRIPT=%SCRIPT_DIR%GenerateNewMagitechMechformsAssets.ps1
if exist "%NEW_MAGITECH_MECHFORMS_SCRIPT%" (
    echo Running GenerateNewMagitechMechformsAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%NEW_MAGITECH_MECHFORMS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set NEW_MAGITECH_MECHFORMS_EXIT=%ERRORLEVEL%
    if not %NEW_MAGITECH_MECHFORMS_EXIT% EQU 0 (
        echo [ERROR] GenerateNewMagitechMechformsAssets.ps1 exited with error code %NEW_MAGITECH_MECHFORMS_EXIT%
    )
) else (
    echo [WARNING] New Magitech Mechforms asset generator script not found: %NEW_MAGITECH_MECHFORMS_SCRIPT%
    set NEW_MAGITECH_MECHFORMS_EXIT=0
)

set TENTACLED_HORROR_FORM_SCRIPT=%SCRIPT_DIR%GenerateTentacledHorrorFormAssets.ps1
if exist "%TENTACLED_HORROR_FORM_SCRIPT%" (
    echo Running GenerateTentacledHorrorFormAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TENTACLED_HORROR_FORM_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set TENTACLED_HORROR_FORM_EXIT=%ERRORLEVEL%
    if not %TENTACLED_HORROR_FORM_EXIT% EQU 0 (
        echo [ERROR] GenerateTentacledHorrorFormAssets.ps1 exited with error code %TENTACLED_HORROR_FORM_EXIT%
    )
) else (
    echo [WARNING] Tentacled Horror Form asset generator script not found: %TENTACLED_HORROR_FORM_SCRIPT%
    set TENTACLED_HORROR_FORM_EXIT=0
)

set HYDRA_CHASSIS_SCRIPT=%SCRIPT_DIR%GenerateHydraChassisAssets.ps1
if exist "%HYDRA_CHASSIS_SCRIPT%" (
    echo Running GenerateHydraChassisAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%HYDRA_CHASSIS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set HYDRA_CHASSIS_EXIT=%ERRORLEVEL%
    if not %HYDRA_CHASSIS_EXIT% EQU 0 (
        echo [ERROR] GenerateHydraChassisAssets.ps1 exited with error code %HYDRA_CHASSIS_EXIT%
    )
) else (
    echo [WARNING] Hydra Chassis asset generator script not found: %HYDRA_CHASSIS_SCRIPT%
    set HYDRA_CHASSIS_EXIT=0
)

REM Generate Crafting and Alchemy Assets
echo.
echo ============================================================
echo   Generating Crafting and Alchemy Assets
echo ============================================================
echo.

set CRAFTING_STATION_SCRIPT=%SCRIPT_DIR%GenerateCraftingStationAssets.ps1
if exist "%CRAFTING_STATION_SCRIPT%" (
    echo Running GenerateCraftingStationAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CRAFTING_STATION_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set CRAFTING_STATION_EXIT=%ERRORLEVEL%
    if not %CRAFTING_STATION_EXIT% EQU 0 (
        echo [ERROR] GenerateCraftingStationAssets.ps1 exited with error code %CRAFTING_STATION_EXIT%
    )
) else (
    echo [WARNING] Crafting Station asset generator script not found: %CRAFTING_STATION_SCRIPT%
    set CRAFTING_STATION_EXIT=0
)

set DYNAMIC_POTION_AMMO_SCRIPT=%SCRIPT_DIR%GenerateDynamicPotionAmmoAssets.ps1
if exist "%DYNAMIC_POTION_AMMO_SCRIPT%" (
    echo Running GenerateDynamicPotionAmmoAssets.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%DYNAMIC_POTION_AMMO_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set DYNAMIC_POTION_AMMO_EXIT=%ERRORLEVEL%
    if not %DYNAMIC_POTION_AMMO_EXIT% EQU 0 (
        echo [ERROR] GenerateDynamicPotionAmmoAssets.ps1 exited with error code %DYNAMIC_POTION_AMMO_EXIT%
    )
) else (
    echo [WARNING] Dynamic Potion Ammo asset generator script not found: %DYNAMIC_POTION_AMMO_SCRIPT%
    set DYNAMIC_POTION_AMMO_EXIT=0
)

set REACTION_VFX_SCRIPT=%SCRIPT_DIR%GenerateReactionVFX.ps1
if exist "%REACTION_VFX_SCRIPT%" (
    echo Running GenerateReactionVFX.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%REACTION_VFX_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set REACTION_VFX_EXIT=%ERRORLEVEL%
    if not %REACTION_VFX_EXIT% EQU 0 (
        echo [ERROR] GenerateReactionVFX.ps1 exited with error code %REACTION_VFX_EXIT%
    )
) else (
    echo [WARNING] Reaction VFX generator script not found: %REACTION_VFX_SCRIPT%
    set REACTION_VFX_EXIT=0
)

set REAGENT_ICONS_SCRIPT=%SCRIPT_DIR%GenerateReagentIcons.ps1
if exist "%REAGENT_ICONS_SCRIPT%" (
    echo Running GenerateReagentIcons.ps1...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%REAGENT_ICONS_SCRIPT%" -ModPath "%MOD_PATH%" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%"
    set REAGENT_ICONS_EXIT=%ERRORLEVEL%
    if not %REAGENT_ICONS_EXIT% EQU 0 (
        echo [ERROR] GenerateReagentIcons.ps1 exited with error code %REAGENT_ICONS_EXIT%
    )
) else (
    echo [WARNING] Reagent Icons generator script not found: %REAGENT_ICONS_SCRIPT%
    set REAGENT_ICONS_EXIT=0
)

REM Generate specialized assets (particles, behaviors, cursors, tiles, ships)
echo.
echo ============================================================
echo   Generating Specialized Assets
echo ============================================================
echo.

set SPECIALIZED_EXIT=0
set SPECIALIZED_FAILED=0
set OLLAMA_GENERATOR=%SCRIPT_DIR%StarboundOllamaAssetGenerator.ps1

REM Ensure assets directory exists
if not exist "%MOD_PATH%\assets" (
    echo Creating assets directory...
    mkdir "%MOD_PATH%\assets"
)

REM Generate common particle effects
echo Generating particle effects...
if exist "%OLLAMA_GENERATOR%" (
    echo   - magicportal...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "magicportal" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -QualityAssessmentDepth "%QUALITY_ASSESSMENT_DEPTH%" -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magicportal particle
        set /a SPECIALIZED_FAILED+=1
    )
    echo   - spellcast...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "spellcast" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -QualityAssessmentDepth "%QUALITY_ASSESSMENT_DEPTH%" -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate spellcast particle
        set /a SPECIALIZED_FAILED+=1
    )
    echo   - magicaura...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%OLLAMA_GENERATOR%" -AssetType Particle -AssetName "magicaura" -OllamaModel "%OLLAMA_MODEL%" -PlanningModel "%PLANNING_MODEL%" -VisualModel "%VISUAL_MODEL%" -QualityAssessmentDepth "%QUALITY_ASSESSMENT_DEPTH%" -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magicaura particle
        set /a SPECIALIZED_FAILED+=1
    )
) else (
    echo   [WARNING] Ollama generator script not found: %OLLAMA_GENERATOR%
    set /a SPECIALIZED_FAILED+=1
)

REM Generate common behaviors
echo Generating AI behaviors...
set BEHAVIOR_SCRIPT=%SCRIPT_DIR%StarboundBehaviorGenerator.ps1
if exist "%BEHAVIOR_SCRIPT%" (
    echo   - magitech_monster...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BEHAVIOR_SCRIPT%" -BehaviorName "magitech_monster" -Preset Default -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_monster behavior
        set /a SPECIALIZED_FAILED+=1
    )
    echo   - magitech_boss...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%BEHAVIOR_SCRIPT%" -BehaviorName "magitech_boss" -Preset Boss -HealthStages 3 -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_boss behavior
        set /a SPECIALIZED_FAILED+=1
    )
) else (
    echo   [WARNING] Behavior generator script not found: %BEHAVIOR_SCRIPT%
)

REM Generate common cursors
echo Generating cursors...
set CURSOR_SCRIPT=%SCRIPT_DIR%StarboundCursorGenerator.ps1
if exist "%CURSOR_SCRIPT%" (
    echo   - magitech_cursor...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CURSOR_SCRIPT%" -CursorName "magitech_cursor" -Preset Default -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_cursor
        set /a SPECIALIZED_FAILED+=1
    )
    echo   - magitech_pointer...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%CURSOR_SCRIPT%" -CursorName "magitech_pointer" -Preset Pointer -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_pointer
        set /a SPECIALIZED_FAILED+=1
    )
) else (
    echo   [WARNING] Cursor generator script not found: %CURSOR_SCRIPT%
)

REM Generate common tiles
echo Generating tiles...
set TILE_SCRIPT=%SCRIPT_DIR%StarboundTileGenerator.ps1
if exist "%TILE_SCRIPT%" (
    echo   - magitech_block...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TILE_SCRIPT%" -TileName "magitech_block" -Preset Basic -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_block
        set /a SPECIALIZED_FAILED+=1
    )
    echo   - magitech_protection...
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%TILE_SCRIPT%" -TileName "magitech_protection" -Preset Protection -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_protection
        set /a SPECIALIZED_FAILED+=1
    )
) else (
    echo   [WARNING] Tile generator script not found: %TILE_SCRIPT%
)

REM Generate ship structures (if needed)
echo Generating ship structures...
set SHIP_SCRIPT=%SCRIPT_DIR%StarboundShipGenerator.ps1
if exist "%SHIP_SCRIPT%" (
    echo   - magitech_ship...
    REM Ships are typically race-specific, so we'll generate a generic one
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%SHIP_SCRIPT%" -ShipName "magitech_ship" -Race "human" -Preset Generic -MaxTier 8 -OutputDir "%MOD_PATH%\assets"
    if errorlevel 1 (
        echo     [ERROR] Failed to generate magitech_ship
        set /a SPECIALIZED_FAILED+=1
    )
) else (
    echo   [WARNING] Ship generator script not found: %SHIP_SCRIPT%
)

if %SPECIALIZED_FAILED% GTR 0 (
    echo.
    echo [WARNING] Specialized asset generation completed with %SPECIALIZED_FAILED% failures
    set SPECIALIZED_EXIT=1
) else (
    echo.
    echo [SUCCESS] Specialized asset generation completed successfully
)
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

REM Count total errors and build failure list
set TOTAL_ERRORS=0
set FAILED_SCRIPTS=

if not %MAIN_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAllModSprites.ps1
)
if not %PLACEHOLDER_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GeneratePlaceholderAssets.ps1
)
if not %ANIMATION_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAnimationSprites.ps1
)
if not %ALCHEMICAL_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAlchemicalGrenadeLauncherAssets.ps1
)
if not %DUNGEON_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateFloatingDungeonAssets.ps1
)
if not %MECH_ANIM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMechWeaponMagicAnimations.ps1
)
if not %ENHANCED_ALCHEMICAL_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateEnhancedAlchemicalLauncherAssets.ps1
)
if not %MAGIC_ORB_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMagicOrbAssets.ps1
)
if not %CENTIPEDE_FORM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateCentipedeFormAssets.ps1
)
if not %ALL_MECH_FORM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAllMechFormAssets.ps1
)
if not %MECH_FORM_ANIM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMechFormAnimations.ps1
)
if not %MECH_COCKPIT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMechCockpitAssets.ps1
)
if not %HOOK_SLINGER_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateHookSlingerFormAssets.ps1
)
if not %FORM_WHEEL_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateFormWheelUI.ps1
)
if not %ABNORMAL_FORMS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAbnormalFormsAssets.ps1
)
if not %QUADRUPED_FORMS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateQuadrapedFormsAssets.ps1
)
if not %LORE_FORMS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateStarboundLoreFormsAssets.ps1
)
if not %HORROR_FORMS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateHorrorFormsAssets.ps1
)
if not %ALL_MECH_VARIANTS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAllMechVariants.ps1
)
if not %MECHSET_VARIANTS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMechSetVariants.ps1
)
if not %ENCHANTMENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateEnchantmentAssets.ps1
)
if not %ALCHEMIST_BUS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAlchemistBusAssets.ps1
)
if not %ORBITAL_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateOrbitalAssets.ps1
)
if not %BUFF_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateBuffAgentAssets.ps1
)
if not %COMPOSITION_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateCompositionAgentAssets.ps1
)
if not %DURABILITY_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateDurabilityAgentAssets.ps1
)
if not %INVENTORY_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateInventoryAgentAssets.ps1
)
if not %PORTAL_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GeneratePortalAgentAssets.ps1
)
if not %SIMULATION_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateSimulationAgentAssets.ps1
)
if not %WAND_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateWandAgentAssets.ps1
)
if not %MEGA_FORM_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateMegaFormAgentAssets.ps1
)
if not %GENERATOR_AGENT_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateGeneratorAgentAssets.ps1
)
if not %VFS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateVFSAssets.ps1
)
if not %GOLEM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateGolemAssets.ps1
)
if not %PLUGIN_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GeneratePluginAssets.ps1
)
if not %ANOMALY_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateAnomalyAssets.ps1
)
if not %REMAINING_SYSTEM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateRemainingSystemAssets.ps1
)
if not %SKILL_SYSTEM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateSkillSystemAssets.ps1
)
if not %TAMING_SYSTEM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateTamingSystemAssets.ps1
)
if not %STAR_SYSTEM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateStarSystemAssets.ps1
)
if not %RAPTOR_FORM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateRaptorFormAssets.ps1
)
if not %BLADE_CYCLONE_FORM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateBladeCycloneFormAssets.ps1
)
if not %TENTACLED_HORROR_FORM_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateTentacledHorrorFormAssets.ps1
)
if not %HYDRA_CHASSIS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateHydraChassisAssets.ps1
)
if not %CRAFTING_STATION_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateCraftingStationAssets.ps1
)
if not %DYNAMIC_POTION_AMMO_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateDynamicPotionAmmoAssets.ps1
)
if not %REACTION_VFX_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateReactionVFX.ps1
)
if not %REAGENT_ICONS_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% GenerateReagentIcons.ps1
)
if not %SPECIALIZED_EXIT% EQU 0 (
    set /a TOTAL_ERRORS+=1
    set FAILED_SCRIPTS=%FAILED_SCRIPTS% SpecializedAssets
)

REM Check for failure report from GenerateAllModSprites.ps1
set FAILURE_REPORT=%MOD_PATH%\ASSET_GENERATION_FAILURES.txt
if exist "%FAILURE_REPORT%" (
    echo.
    echo ============================================================
    echo   Failed Assets Report (from GenerateAllModSprites.ps1)
    echo ============================================================
    echo.
    type "%FAILURE_REPORT%"
    echo.
)

if %TOTAL_ERRORS% EQU 0 (
    echo [SUCCESS] All asset generation scripts completed successfully!
    echo.
    echo Total Scripts Executed: 50+
    echo Successful: All
    echo Failed: 0
) else (
    echo.
    echo ============================================================
    echo   FAILURE SUMMARY
    echo ============================================================
    echo.
    echo [WARNING] Asset generation completed with %TOTAL_ERRORS% script error(s).
    echo.
    echo Total Scripts Executed: 50+
    echo Successful: ~%TOTAL_ERRORS% failed
    echo Failed: %TOTAL_ERRORS%
    echo.
    echo Failed Scripts:
    echo %FAILED_SCRIPTS%
    echo.
    echo Check the output above for detailed error messages.
    echo.
    if exist "%FAILURE_REPORT%" (
        echo Detailed failure report available at:
        echo   %FAILURE_REPORT%
        echo.
    )
)

if %QUALITY_EXIT% EQU 0 (
    echo Quality checking completed successfully.
) else (
    echo Quality checking completed with warnings.
)

echo.
echo ============================================================
echo   Asset Generation Summary
echo ============================================================
echo.
echo Assets have been saved to:
echo   %MOD_PATH%\assets\
echo   %MOD_PATH%\interface\
echo.
if exist "%FAILURE_REPORT%" (
    echo Failure report saved to:
    echo   %FAILURE_REPORT%
    echo.
)
echo Quality reports saved to:
echo   %ASSETS_DIR%\ASSET_QUALITY_REPORT.md
echo   %ASSETS_DIR%\BEST_ASSETS_MAPPING.md
echo.

REM Unload all Ollama models to free VRAM
echo.
echo ============================================================
echo   Cleaning Up - Unloading Ollama Models
echo ============================================================
echo.
echo Unloading all Ollama models to free VRAM...
pwsh -NoProfile -ExecutionPolicy Bypass -Command "& { try { $ollamaUrl = 'http://localhost:11434'; $response = Invoke-RestMethod -Uri '$ollamaUrl/api/ps' -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue; if ($response -and $response.models) { foreach ($model in $response.models) { if ($model.name) { try { $unloadBody = @{ model = $model.name; prompt = ''; keep_alive = 0; stream = $false } | ConvertTo-Json -Compress; $null = Invoke-RestMethod -Uri '$ollamaUrl/api/generate' -Method Post -Body $unloadBody -ContentType 'application/json' -TimeoutSec 5 -ErrorAction SilentlyContinue; Write-Host \"  Unloaded: $($model.name)\" -ForegroundColor Gray } catch { try { $null = & ollama stop $($model.name) 2>&1 } catch { } } } } Write-Host \"  VRAM freed\" -ForegroundColor Green } else { Write-Host \"  No models loaded\" -ForegroundColor Gray } } catch { Write-Host \"  Could not check Ollama status\" -ForegroundColor Yellow } }"
echo.

echo Next steps:
echo   1. Review generated assets and quality reports
if %TOTAL_ERRORS% GTR 0 (
    echo   2. Review failed assets and fix issues
    echo   3. Re-run failed generation scripts
    echo   4. Update code references if needed
    echo   5. Test assets in-game
) else (
    echo   2. Update code references if needed
    echo   3. Test assets in-game
)
echo.
echo ============================================================
if %TOTAL_ERRORS% GTR 0 (
    echo   Window will remain open. Review errors above, then close this window when done.
) else (
    echo   Window will remain open. Close this window when you're finished reviewing the output.
)
echo ============================================================
echo.
echo To close this window, click the X button or type 'exit' and press Enter.
echo.
REM Keep window open - user must manually close it
cmd /k
