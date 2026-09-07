#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the spell system.
    
.DESCRIPTION
    Generates sprites, animations, and effects for:
    - Spell icons (UI display)
    - Spell projectiles (sprites)
    - Spell animations
    - Impact particle effects
    - Trail particle effects
    
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
Write-Host "  Spell System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. SPELL ICONS (UI)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellIcons = @(
    @{
        Id = "fireBolt"
        Name = "Fire Bolt"
        Description = "Fire bolt spell icon, red/orange colors, flame symbol"
    },
    @{
        Id = "iceBolt"
        Name = "Ice Bolt"
        Description = "Ice bolt spell icon, blue/white colors, ice crystal symbol"
    },
    @{
        Id = "lightningBolt"
        Name = "Lightning Bolt"
        Description = "Lightning bolt spell icon, yellow/white colors, lightning symbol"
    },
    @{
        Id = "arcaneBolt"
        Name = "Arcane Bolt"
        Description = "Arcane bolt spell icon, purple colors, magical symbol"
    },
    @{
        Id = "fireball"
        Name = "Fireball"
        Description = "Fireball spell icon, red/orange colors, explosive fire symbol"
    },
    @{
        Id = "iceStorm"
        Name = "Ice Storm"
        Description = "Ice storm spell icon, blue/white colors, blizzard symbol"
    },
    @{
        Id = "plasmaBolt"
        Name = "Plasma Bolt"
        Description = "Plasma bolt spell icon, green/purple colors, plasma energy symbol"
    }
)

foreach ($icon in $spellIcons) {
    Write-Host "Generating icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Spell icon for Starbound UI, 32x32 pixel art."
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
# 2. SPELL PROJECTILE SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Projectile Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellProjectiles = @(
    @{
        Id = "fire_bolt_projectile"
        Name = "Fire Bolt Projectile"
        Description = "Fire bolt projectile sprite, red/orange energy, trailing flames, pixel art"
    },
    @{
        Id = "ice_bolt_projectile"
        Name = "Ice Bolt Projectile"
        Description = "Ice bolt projectile sprite, blue/white energy, frost particles, pixel art"
    },
    @{
        Id = "lightning_bolt_projectile"
        Name = "Lightning Bolt Projectile"
        Description = "Lightning bolt projectile sprite, yellow/white energy, electrical arcs, pixel art"
    },
    @{
        Id = "arcane_bolt_projectile"
        Name = "Arcane Bolt Projectile"
        Description = "Arcane bolt projectile sprite, purple energy, magical particles, pixel art"
    },
    @{
        Id = "fireball_projectile"
        Name = "Fireball Projectile"
        Description = "Fireball projectile sprite, large red/orange sphere, explosive appearance, pixel art"
    },
    @{
        Id = "plasma_bolt_projectile"
        Name = "Plasma Bolt Projectile"
        Description = "Plasma bolt projectile sprite, green/purple energy, plasma effects, pixel art"
    }
)

foreach ($projectile in $spellProjectiles) {
    Write-Host "Generating projectile: $($projectile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $projectile.Id
            Prompt = "$($projectile.Description). Spell projectile sprite for Starbound, 32x32 or 48x48 pixel art."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($projectile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($projectile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SPELL ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spell Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spellAnimations = @(
    @{
        Id = "spell_rotate"
        Name = "Rotate Animation"
        Description = "Spell rotation animation, 8 frames showing projectile rotating"
        FrameCount = 8
        AnimationCycle = 0.5
    },
    @{
        Id = "spell_spin"
        Name = "Spin Animation"
        Description = "Spell spin animation, 8 frames showing projectile spinning"
        FrameCount = 8
        AnimationCycle = 0.4
    },
    @{
        Id = "spell_electric"
        Name = "Electric Animation"
        Description = "Electric spell animation, 12 frames showing electrical arcs"
        FrameCount = 12
        AnimationCycle = 0.3
    },
    @{
        Id = "spell_float"
        Name = "Float Animation"
        Description = "Spell float animation, 6 frames showing gentle floating motion"
        FrameCount = 6
        AnimationCycle = 0.8
    },
    @{
        Id = "spell_pulse"
        Name = "Pulse Animation"
        Description = "Spell pulse animation, 8 frames showing pulsing energy"
        FrameCount = 8
        AnimationCycle = 0.6
    }
)

foreach ($anim in $spellAnimations) {
    Write-Host "Generating animation: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = "$($anim.Description). Spell animation spritesheet for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
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
# 4. IMPACT PARTICLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Impact Particle Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$impactEffects = @(
    @{
        Id = "fire_explosion"
        Name = "Fire Explosion"
        Description = "Fire explosion particle effect, red/orange flames, explosive burst"
    },
    @{
        Id = "ice_impact"
        Name = "Ice Impact"
        Description = "Ice impact particle effect, blue/white frost, shattering ice"
    },
    @{
        Id = "lightning_impact"
        Name = "Lightning Impact"
        Description = "Lightning impact particle effect, yellow/white electrical arcs, sparks"
    },
    @{
        Id = "arcane_explosion"
        Name = "Arcane Explosion"
        Description = "Arcane explosion particle effect, purple magical energy, swirling particles"
    },
    @{
        Id = "plasma_explosion"
        Name = "Plasma Explosion"
        Description = "Plasma explosion particle effect, green/purple plasma, energy burst"
    },
    @{
        Id = "fireBurst"
        Name = "Fire Burst"
        Description = "Fire burst particle effect, small fire explosion, red/orange"
    },
    @{
        Id = "iceBurst"
        Name = "Ice Burst"
        Description = "Ice burst particle effect, small ice explosion, blue/white"
    },
    @{
        Id = "lightningBurst"
        Name = "Lightning Burst"
        Description = "Lightning burst particle effect, small electrical explosion, yellow/white"
    },
    @{
        Id = "arcaneBurst"
        Name = "Arcane Burst"
        Description = "Arcane burst particle effect, small magical explosion, purple"
    },
    @{
        Id = "fireballExplosion"
        Name = "Fireball Explosion"
        Description = "Fireball explosion particle effect, large fire explosion, red/orange"
    },
    @{
        Id = "iceStorm"
        Name = "Ice Storm"
        Description = "Ice storm particle effect, blizzard particles, blue/white"
    }
)

foreach ($effect in $impactEffects) {
    Write-Host "Generating impact effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Impact particle effect for Starbound spells."
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
# 5. TRAIL PARTICLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Trail Particle Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$trailEffects = @(
    @{
        Id = "fire_trail"
        Name = "Fire Trail"
        Description = "Fire trail particle effect, trailing flames, red/orange"
    },
    @{
        Id = "ice_trail"
        Name = "Ice Trail"
        Description = "Ice trail particle effect, trailing frost, blue/white"
    },
    @{
        Id = "lightning_trail"
        Name = "Lightning Trail"
        Description = "Lightning trail particle effect, trailing sparks, yellow/white"
    },
    @{
        Id = "arcane_trail"
        Name = "Arcane Trail"
        Description = "Arcane trail particle effect, trailing magical energy, purple"
    },
    @{
        Id = "plasma_trail"
        Name = "Plasma Trail"
        Description = "Plasma trail particle effect, trailing plasma, green/purple"
    }
)

foreach ($effect in $trailEffects) {
    Write-Host "Generating trail effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Trail particle effect for Starbound spells."
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
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets')" -ForegroundColor Gray
Write-Host ""
Write-Host "Spell icons: assets/interface/icons/spells/" -ForegroundColor Gray
Write-Host "Projectiles: assets/projectiles/spells/" -ForegroundColor Gray
Write-Host "Animations: assets/animations/spells/" -ForegroundColor Gray
Write-Host "Particles: assets/particles/spells/" -ForegroundColor Gray
Write-Host ""
