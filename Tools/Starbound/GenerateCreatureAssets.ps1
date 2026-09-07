#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Creature System.
    
.DESCRIPTION
    Generates sprites, animations, and effects for:
    - Creature spell casting animations (e.g., Poptop mouth animations)
    - Creature sprites
    - Creature animation frames
    - Creature spell effects
    
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
    [bool]$UseCppBackend = $true
)

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
Write-Host "  Creature System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. CREATURE SPELL CASTING ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Creature Spell Casting Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$creatureAnimations = @(
    @{ Id = "poptop_mouth_open"; Name = "Poptop Mouth Open"; Desc = "Poptop creature mouth opening animation, 8 frames, 32x32, spell casting animation" },
    @{ Id = "poptop_mouth_cast"; Name = "Poptop Mouth Cast"; Desc = "Poptop creature mouth casting spell animation, 6 frames, 32x32, spell casting animation" },
    @{ Id = "poptop_mouth_close"; Name = "Poptop Mouth Close"; Desc = "Poptop creature mouth closing animation, 8 frames, 32x32, spell casting animation" },
    @{ Id = "creature_spell_charge"; Name = "Creature Spell Charge"; Desc = "Generic creature spell charging animation, 10 frames, 32x32, spell casting animation" },
    @{ Id = "creature_spell_release"; Name = "Creature Spell Release"; Desc = "Generic creature spell release animation, 8 frames, 32x32, spell casting animation" }
)

# Validate $ModPath before Join-Path
$creatureAnimationOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($creatureAnimationOutputDir)) {
    Write-Host "  [FAIL] creatureAnimationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($creatureAnimationOutputDir)) {
    Write-Host "  [FAIL] creatureAnimationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $creatureAnimationOutputDir)) {
    New-Item -ItemType Directory -Path $creatureAnimationOutputDir -Force | Out-Null
}

foreach ($anim in $creatureAnimations) {
    Write-Host "Generating creature animation: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = "$($anim.Desc). Creature animation for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $creatureAnimationOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($anim.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($anim.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. CREATURE SPELL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Creature Spell Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$creatureSpellEffects = @(
    @{ Id = "creature_spell_effect_poptop"; Name = "Poptop Spell Effect"; Desc = "Poptop creature spell casting particle effect, magical energy burst" },
    @{ Id = "creature_spell_effect_generic"; Name = "Generic Creature Spell Effect"; Desc = "Generic creature spell casting particle effect, magical energy" },
    @{ Id = "creature_spell_charge_effect"; Name = "Creature Spell Charge Effect"; Desc = "Creature spell charging particle effect, energy buildup" },
    @{ Id = "creature_spell_release_effect"; Name = "Creature Spell Release Effect"; Desc = "Creature spell release particle effect, energy burst" }
)

# Validate $ModPath before Join-Path
$creatureEffectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($creatureEffectOutputDir)) {
    Write-Host "  [FAIL] creatureEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($creatureEffectOutputDir)) {
    Write-Host "  [FAIL] creatureEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $creatureEffectOutputDir)) {
    New-Item -ItemType Directory -Path $creatureEffectOutputDir -Force | Out-Null
}

foreach ($effect in $creatureSpellEffects) {
    Write-Host "Generating creature spell effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Creature spell effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $creatureEffectOutputDir
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
# 3. CREATURE SPRITES (if needed for custom creatures)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Creature Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$creatureSprites = @(
    @{ Id = "creature_poptop_base"; Name = "Poptop Base Sprite"; Desc = "Poptop creature base sprite, 32x32, Starbound style" },
    @{ Id = "creature_poptop_mouth_closed"; Name = "Poptop Mouth Closed"; Desc = "Poptop creature with mouth closed sprite, 32x32" },
    @{ Id = "creature_poptop_mouth_open"; Name = "Poptop Mouth Open"; Desc = "Poptop creature with mouth open sprite, 32x32" }
)

# Validate $ModPath before Join-Path
$creatureSpriteOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($creatureSpriteOutputDir)) {
    Write-Host "  [FAIL] creatureSpriteOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($creatureSpriteOutputDir)) {
    Write-Host "  [FAIL] creatureSpriteOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $creatureSpriteOutputDir)) {
    New-Item -ItemType Directory -Path $creatureSpriteOutputDir -Force | Out-Null
}

foreach ($sprite in $creatureSprites) {
    Write-Host "Generating creature sprite: $($sprite.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $sprite.Id
            Prompt = "$($sprite.Desc). Creature sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $creatureSpriteOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($sprite.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($sprite.Name) : $_" -ForegroundColor Red
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
Write-Host "  Creature Animations: $(Join-Path $ModPath 'assets\creatures\animations')" -ForegroundColor Gray
Write-Host "  Creature Effects: $(Join-Path $ModPath 'assets\creatures\effects')" -ForegroundColor Gray
Write-Host "  Creature Sprites: $(Join-Path $ModPath 'assets\creatures\sprites')" -ForegroundColor Gray
Write-Host ""
Write-Host "Creature animations: assets/creatures/animations/*.png" -ForegroundColor Gray
Write-Host "Creature effects: assets/creatures/effects/*.particle" -ForegroundColor Gray
Write-Host "Creature sprites: assets/creatures/sprites/*.png" -ForegroundColor Gray
Write-Host ""
