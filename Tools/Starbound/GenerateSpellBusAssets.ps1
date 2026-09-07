#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the SpellBus System.
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Spell casting effects
    - Material reaction effects
    - Spell composition/chain effects
    - Spellstone icons
    - Spell event effects
    - Durability indicators
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SpellBus System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. SPELL CASTING EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Casting Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellCastingEffects = @(
    @{ Id = "spell_cast_effect"; Name = "Spell Cast Effect"; Desc = "Spell casting particle effect, magical energy buildup" },
    @{ Id = "spell_cast_complete"; Name = "Spell Cast Complete"; Desc = "Spell cast complete particle effect, spell activation" },
    @{ Id = "spell_cast_interrupt"; Name = "Spell Cast Interrupt"; Desc = "Spell cast interrupt particle effect, spell cancellation" },
    @{ Id = "spell_cast_failed"; Name = "Spell Cast Failed"; Desc = "Spell cast failed particle effect, spell failure" }
)

# Validate $ModPath before Join-Path
$spellCastOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($spellCastOutputDir)) {
    Write-Host "  [FAIL] spellCastOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($spellCastOutputDir)) {
    Write-Host "  [FAIL] spellCastOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $spellCastOutputDir)) {
    New-Item -ItemType Directory -Path $spellCastOutputDir -Force | Out-Null
}

foreach ($effect in $spellCastingEffects) {
    Write-Host "Generating spell casting effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Spell casting effect for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $spellCastOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. MATERIAL REACTION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Material Reaction Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$materialReactions = @(
    @{ Id = "reaction_steam_burst"; Name = "Steam Burst Reaction"; Desc = "Steam burst particle effect, water vapor explosion" },
    @{ Id = "reaction_freeze"; Name = "Freeze Reaction"; Desc = "Freeze particle effect, ice crystallization" },
    @{ Id = "reaction_combustion"; Name = "Combustion Reaction"; Desc = "Combustion particle effect, fire explosion" },
    @{ Id = "reaction_melting"; Name = "Melting Reaction"; Desc = "Melting particle effect, material liquefaction" },
    @{ Id = "reaction_evaporation"; Name = "Evaporation Reaction"; Desc = "Evaporation particle effect, liquid to gas" },
    @{ Id = "reaction_condensation"; Name = "Condensation Reaction"; Desc = "Condensation particle effect, gas to liquid" },
    @{ Id = "reaction_electrolysis"; Name = "Electrolysis Reaction"; Desc = "Electrolysis particle effect, electrical separation" },
    @{ Id = "reaction_transmutation"; Name = "Transmutation Reaction"; Desc = "Transmutation particle effect, material transformation" },
    @{ Id = "reaction_dissolution"; Name = "Dissolution Reaction"; Desc = "Dissolution particle effect, material dissolving" },
    @{ Id = "reaction_crystallization"; Name = "Crystallization Reaction"; Desc = "Crystallization particle effect, crystal formation" },
    @{ Id = "reaction_polymerization"; Name = "Polymerization Reaction"; Desc = "Polymerization particle effect, chain formation" }
)

# Validate $ModPath before Join-Path
$reactionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($reactionOutputDir)) {
    Write-Host "  [FAIL] reactionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($reactionOutputDir)) {
    Write-Host "  [FAIL] reactionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $reactionOutputDir)) {
    New-Item -ItemType Directory -Path $reactionOutputDir -Force | Out-Null
}

foreach ($reaction in $materialReactions) {
    Write-Host "Generating material reaction: $($reaction.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $reaction.Id
            Prompt = "$($reaction.Desc). Material reaction effect for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $reactionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($reaction.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($reaction.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SPELL COMPOSITION/CHAIN EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Composition/Chain Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$compositionEffects = @(
    @{ Id = "spell_chain_effect"; Name = "Spell Chain Effect"; Desc = "Spell chain particle effect, linked spell casting" },
    @{ Id = "spell_combo_effect"; Name = "Spell Combo Effect"; Desc = "Spell combo particle effect, combined spell effects" },
    @{ Id = "spell_composition_start"; Name = "Spell Composition Start"; Desc = "Spell composition start particle effect, composition activation" },
    @{ Id = "spell_composition_link"; Name = "Spell Composition Link"; Desc = "Spell composition link particle effect, connecting spells" }
)

# Validate $ModPath before Join-Path
$compositionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($compositionOutputDir)) {
    Write-Host "  [FAIL] compositionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($compositionOutputDir)) {
    Write-Host "  [FAIL] compositionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $compositionOutputDir)) {
    New-Item -ItemType Directory -Path $compositionOutputDir -Force | Out-Null
}

foreach ($effect in $compositionEffects) {
    Write-Host "Generating composition effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Spell composition effect for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $compositionOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. SPELLSTONE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spellstone Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellstoneIcons = @(
    @{ Id = "spellstone_base"; Name = "Base Spellstone"; Desc = "Base spellstone icon, generic magical stone, 32x32" },
    @{ Id = "spellstone_evolved"; Name = "Evolved Spellstone"; Desc = "Evolved spellstone icon, enhanced magical stone, 32x32" },
    @{ Id = "spellstone_fused"; Name = "Fused Spellstone"; Desc = "Fused spellstone icon, combined magical stones, 32x32" },
    @{ Id = "spellstone_durability_high"; Name = "High Durability Spellstone"; Desc = "High durability spellstone icon, pristine condition, 32x32" },
    @{ Id = "spellstone_durability_medium"; Name = "Medium Durability Spellstone"; Desc = "Medium durability spellstone icon, worn condition, 32x32" },
    @{ Id = "spellstone_durability_low"; Name = "Low Durability Spellstone"; Desc = "Low durability spellstone icon, damaged condition, 32x32" },
    @{ Id = "spellstone_durability_critical"; Name = "Critical Durability Spellstone"; Desc = "Critical durability spellstone icon, near broken, 32x32" }
)

# Validate $ModPath before Join-Path
$spellstoneOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($spellstoneOutputDir)) {
    Write-Host "  [FAIL] spellstoneOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($spellstoneOutputDir)) {
    Write-Host "  [FAIL] spellstoneOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $spellstoneOutputDir)) {
    New-Item -ItemType Directory -Path $spellstoneOutputDir -Force | Out-Null
}

foreach ($icon in $spellstoneIcons) {
    Write-Host "Generating spellstone icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Spellstone icon for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $spellstoneOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($icon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($icon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. SPELL EVENT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Event Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellEventEffects = @(
    @{ Id = "spell_event_learn"; Name = "Spell Learn Event"; Desc = "Spell learn particle effect, knowledge acquisition" },
    @{ Id = "spell_event_forget"; Name = "Spell Forget Event"; Desc = "Spell forget particle effect, knowledge loss" },
    @{ Id = "spell_event_upgrade"; Name = "Spell Upgrade Event"; Desc = "Spell upgrade particle effect, spell enhancement" },
    @{ Id = "spell_event_cooldown"; Name = "Spell Cooldown Event"; Desc = "Spell cooldown particle effect, spell recovery" },
    @{ Id = "spell_event_resource"; Name = "Spell Resource Event"; Desc = "Spell resource particle effect, mana/energy consumption" },
    @{ Id = "spell_event_target"; Name = "Spell Target Event"; Desc = "Spell target particle effect, target acquisition" },
    @{ Id = "spell_event_area"; Name = "Spell Area Event"; Desc = "Spell area particle effect, area of effect" },
    @{ Id = "spell_event_counter"; Name = "Spell Counter Event"; Desc = "Spell counter particle effect, spell countering" }
)

# Validate $ModPath before Join-Path
$eventOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $eventOutputDir)) {
    New-Item -ItemType Directory -Path $eventOutputDir -Force | Out-Null
}

foreach ($effect in $spellEventEffects) {
    Write-Host "Generating spell event effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Spell event effect for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $eventOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. PERSISTENT EFFECT VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Persistent Effect Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$persistentEffects = @(
    @{ Id = "persistent_effect_active"; Name = "Active Persistent Effect"; Desc = "Active persistent effect particle effect, ongoing spell effect" },
    @{ Id = "persistent_effect_tick"; Name = "Persistent Effect Tick"; Desc = "Persistent effect tick particle effect, effect pulse" },
    @{ Id = "persistent_effect_expire"; Name = "Persistent Effect Expire"; Desc = "Persistent effect expire particle effect, effect ending" }
)

# Validate $ModPath before Join-Path
$persistentOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($persistentOutputDir)) {
    Write-Host "  [FAIL] persistentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($persistentOutputDir)) {
    Write-Host "  [FAIL] persistentOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $persistentOutputDir)) {
    New-Item -ItemType Directory -Path $persistentOutputDir -Force | Out-Null
}

foreach ($effect in $persistentEffects) {
    Write-Host "Generating persistent effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Persistent effect for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $persistentOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. DURABILITY INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Durability Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$durabilityIndicators = @(
    @{ Id = "durability_change_effect"; Name = "Durability Change Effect"; Desc = "Durability change particle effect, wear indicator" },
    @{ Id = "repair_complete_effect"; Name = "Repair Complete Effect"; Desc = "Repair complete particle effect, spellstone repair" },
    @{ Id = "durability_warning"; Name = "Durability Warning"; Desc = "Durability warning icon, low durability alert, 32x32" }
)

# Validate $ModPath before Join-Path
$durabilityOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($durabilityOutputDir)) {
    Write-Host "  [FAIL] durabilityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($durabilityOutputDir)) {
    Write-Host "  [FAIL] durabilityOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $durabilityOutputDir)) {
    New-Item -ItemType Directory -Path $durabilityOutputDir -Force | Out-Null
}

foreach ($indicator in $durabilityIndicators) {
    Write-Host "Generating durability indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -eq "durability_warning") { "Icon" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Durability indicator for Starbound SpellBus."
            OllamaModel = $OllamaModel
            OutputDir = $durabilityOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  Spell Casting: $(Join-Path $ModPath 'assets\spellbus\casting')" -ForegroundColor Gray
Write-Host "  Material Reactions: $(Join-Path $ModPath 'assets\spellbus\reactions')" -ForegroundColor Gray
Write-Host "  Spell Compositions: $(Join-Path $ModPath 'assets\spellbus\compositions')" -ForegroundColor Gray
Write-Host "  Spellstones: $(Join-Path $ModPath 'assets\spellbus\spellstones')" -ForegroundColor Gray
Write-Host "  Spell Events: $(Join-Path $ModPath 'assets\spellbus\events')" -ForegroundColor Gray
Write-Host "  Persistent Effects: $(Join-Path $ModPath 'assets\spellbus\persistent')" -ForegroundColor Gray
Write-Host "  Durability: $(Join-Path $ModPath 'assets\spellbus\durability')" -ForegroundColor Gray
Write-Host ""
