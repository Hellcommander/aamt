#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the weapon systems (crossbow bolts, etc.).
    
.DESCRIPTION
    Generates sprites, animations, and effects for:
    - Crossbow bolt projectiles
    - Bolt impact effects
    - Bolt trail effects
    - Bolt animations
    - Weapon icons
    
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

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Weapon System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. CROSSBOW BOLT PROJECTILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Crossbow Bolt Projectiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$boltProjectiles = @(
    @{
        Id = "bolt_standard"
        Name = "Standard Bolt"
        Description = "Standard crossbow bolt projectile, wooden shaft with metal tip, arrow-like appearance"
    },
    @{
        Id = "bolt_explosive"
        Name = "Explosive Bolt"
        Description = "Explosive crossbow bolt projectile, red/orange colors, explosive tip, dangerous appearance"
    },
    @{
        Id = "bolt_piercing"
        Name = "Piercing Bolt"
        Description = "Piercing crossbow bolt projectile, sharp metal tip, armor-piercing appearance"
    },
    @{
        Id = "bolt_homing"
        Name = "Homing Bolt"
        Description = "Homing crossbow bolt projectile, magical energy, glowing tip, tracking appearance"
    },
    @{
        Id = "bolt_spell"
        Name = "Spell Bolt"
        Description = "Spell-loaded crossbow bolt projectile, magical energy, purple/blue glow, runic patterns"
    },
    @{
        Id = "bolt_poison"
        Name = "Poison Bolt"
        Description = "Poison crossbow bolt projectile, green toxic appearance, poison tip"
    },
    @{
        Id = "bolt_fire"
        Name = "Fire Bolt"
        Description = "Fire crossbow bolt projectile, flaming tip, red/orange colors, fire effects"
    },
    @{
        Id = "bolt_ice"
        Name = "Ice Bolt"
        Description = "Ice crossbow bolt projectile, frozen tip, blue/white colors, frost effects"
    },
    @{
        Id = "bolt_lightning"
        Name = "Lightning Bolt"
        Description = "Lightning crossbow bolt projectile, electrical energy, yellow/white colors, sparking"
    }
)

foreach ($bolt in $boltProjectiles) {
    Write-Host "Generating bolt projectile: $($bolt.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] Bolt $($bolt.Id): OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
            $failed++
            continue
        }
        
        $params = @{
            AssetType = "Projectile"
            AssetName = $bolt.Id
            Prompt = "$($bolt.Description). Crossbow bolt projectile sprite for Starbound, 32x32 or 48x48 pixel art."
            OllamaModel = $OllamaModel
            OutputDir = $outputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($bolt.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($bolt.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. BOLT IMPACT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Bolt Impact Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$impactEffects = @(
    @{
        Id = "bolt_impact_standard"
        Name = "Standard Bolt Impact"
        Description = "Standard bolt impact particle effect, small impact, wood/metal particles"
    },
    @{
        Id = "bolt_impact_explosive"
        Name = "Explosive Bolt Impact"
        Description = "Explosive bolt impact particle effect, large explosion, fire and smoke"
    },
    @{
        Id = "bolt_impact_piercing"
        Name = "Piercing Bolt Impact"
        Description = "Piercing bolt impact particle effect, sparks, metal fragments"
    },
    @{
        Id = "bolt_impact_spell"
        Name = "Spell Bolt Impact"
        Description = "Spell bolt impact particle effect, magical explosion, purple/blue energy"
    },
    @{
        Id = "bolt_impact_poison"
        Name = "Poison Bolt Impact"
        Description = "Poison bolt impact particle effect, toxic cloud, green particles"
    },
    @{
        Id = "bolt_impact_fire"
        Name = "Fire Bolt Impact"
        Description = "Fire bolt impact particle effect, fire explosion, red/orange flames"
    },
    @{
        Id = "bolt_impact_ice"
        Name = "Ice Bolt Impact"
        Description = "Ice bolt impact particle effect, ice shards, blue/white frost"
    },
    @{
        Id = "bolt_impact_lightning"
        Name = "Lightning Bolt Impact"
        Description = "Lightning bolt impact particle effect, electrical explosion, yellow/white sparks"
    }
)

foreach ($effect in $impactEffects) {
    Write-Host "Generating impact effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Bolt impact particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
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
# 3. BOLT TRAIL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Bolt Trail Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$trailEffects = @(
    @{
        Id = "bolt_trail_standard"
        Name = "Standard Bolt Trail"
        Description = "Standard bolt trail particle effect, subtle trail, minimal particles"
    },
    @{
        Id = "bolt_trail_explosive"
        Name = "Explosive Bolt Trail"
        Description = "Explosive bolt trail particle effect, smoke trail, red/orange particles"
    },
    @{
        Id = "bolt_trail_spell"
        Name = "Spell Bolt Trail"
        Description = "Spell bolt trail particle effect, magical energy trail, purple/blue particles"
    },
    @{
        Id = "bolt_trail_fire"
        Name = "Fire Bolt Trail"
        Description = "Fire bolt trail particle effect, flame trail, red/orange particles"
    },
    @{
        Id = "bolt_trail_ice"
        Name = "Ice Bolt Trail"
        Description = "Ice bolt trail particle effect, frost trail, blue/white particles"
    },
    @{
        Id = "bolt_trail_lightning"
        Name = "Lightning Bolt Trail"
        Description = "Lightning bolt trail particle effect, electrical trail, yellow/white sparks"
    }
)

foreach ($effect in $trailEffects) {
    Write-Host "Generating trail effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] Trail effect $($effect.Id): OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
            $failed++
            continue
        }
        
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Bolt trail particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $outputDir
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
# 4. BOLT ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Bolt Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$boltAnimations = @(
    @{
        Id = "bolt_spin"
        Name = "Bolt Spin Animation"
        Description = "Bolt spinning animation, 8 frames showing bolt rotating in flight"
        FrameCount = 8
        AnimationCycle = 0.3
    },
    @{
        Id = "bolt_glow"
        Name = "Bolt Glow Animation"
        Description = "Bolt glow animation, 6 frames showing pulsing glow effect"
        FrameCount = 6
        AnimationCycle = 0.5
    },
    @{
        Id = "bolt_spark"
        Name = "Bolt Spark Animation"
        Description = "Bolt spark animation, 12 frames showing electrical sparks"
        FrameCount = 12
        AnimationCycle = 0.4
    }
)

foreach ($anim in $boltAnimations) {
    Write-Host "Generating animation: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
$outputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] outputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            Write-Host "  [FAIL] Animation $($anim.Id): OutputDir is null (ModPath: '$ModPath')" -ForegroundColor Red
            $failed++
            continue
        }
        
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = "$($anim.Description). Bolt animation spritesheet for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $outputDir
        }
        
        $animParamHashtable = @{
            FrameCount = $anim.FrameCount
            AnimationCycle = $anim.AnimationCycle
            AnimationType = "SpellCast"
            FrameWidth = 32
            FrameHeight = 32
        }
        $params['Parameters'] = $animParamHashtable
        
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
# 5. WEAPON ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weapon Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weaponIcons = @(
    @{
        Id = "crossbow_icon"
        Name = "Crossbow Icon"
        Description = "Crossbow weapon icon, crossbow silhouette, 32x32 pixel art"
    },
    @{
        Id = "bolt_icon"
        Name = "Bolt Icon"
        Description = "Crossbow bolt icon, arrow/bolt silhouette, 32x32 pixel art"
    }
)

foreach ($icon in $weaponIcons) {
    Write-Host "Generating icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Weapon icon for Starbound UI."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
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
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
$assetsPath = if ($ModPath) { Join-Path $ModPath 'assets' } else { 'assets' }
Write-Host "Assets saved to: $assetsPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Bolt projectiles: assets/projectiles/bolts/" -ForegroundColor Gray
Write-Host "Impact effects: assets/particles/bolts/impact/" -ForegroundColor Gray
Write-Host "Trail effects: assets/particles/bolts/trail/" -ForegroundColor Gray
Write-Host "Animations: assets/animations/bolts/" -ForegroundColor Gray
Write-Host "Icons: assets/interface/icons/weapons/" -ForegroundColor Gray
Write-Host ""
