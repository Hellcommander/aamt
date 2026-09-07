#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Cluster Bomb Generator system.
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Cluster bomb sprites (casing, fuse)
    - Fragment sprites (shards, bolts, spheres)
    - Explosion effects (core, smoke, debris)
    - Bomb animations (fuse burning, shell cracking)
    - Explosion decals (scorch marks, cracks)
    
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
Write-Host "  Cluster Bomb Generator Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. CLUSTER BOMB SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cluster Bomb Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$bombSprites = @(
    @{
        Id = "cluster_bomb_basic"
        Name = "Basic Cluster Bomb"
        Description = "Basic cluster bomb sprite, spherical shell with fuse, metallic appearance, 32x32"
    },
    @{
        Id = "cluster_bomb_incendiary"
        Name = "Incendiary Cluster Bomb"
        Description = "Incendiary cluster bomb sprite, red/orange colors, fire appearance, 32x32"
    },
    @{
        Id = "cluster_bomb_emp"
        Name = "EMP Cluster Bomb"
        Description = "EMP cluster bomb sprite, blue/cyan colors, electrical appearance, 32x32"
    },
    @{
        Id = "cluster_bomb_frag"
        Name = "Fragmentation Cluster Bomb"
        Description = "Fragmentation cluster bomb sprite, jagged appearance, shrapnel, 32x32"
    },
    @{
        Id = "cluster_bomb_fuse"
        Name = "Bomb Fuse"
        Description = "Bomb fuse sprite, burning fuse, sparking, 16x16"
    }
)

# Validate $ModPath before Join-Path
$bombOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($bombOutputDir)) {
    Write-Host "  [FAIL] bombOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($bombOutputDir)) {
    Write-Host "  [FAIL] bombOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $bombOutputDir)) {
    New-Item -ItemType Directory -Path $bombOutputDir -Force | Out-Null
}

foreach ($bomb in $bombSprites) {
    Write-Host "Generating bomb sprite: $($bomb.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $bomb.Id
            Prompt = "$($bomb.Description). Cluster bomb sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $bombOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($bomb.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($bomb.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. FRAGMENT SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Fragment Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$fragmentSprites = @(
    @{
        Id = "fragment_shard"
        Name = "Fragment Shard"
        Description = "Fragment shard sprite, jagged metal shard, sharp edges, 16x16"
    },
    @{
        Id = "fragment_bolt"
        Name = "Fragment Bolt"
        Description = "Fragment bolt sprite, metal bolt, cylindrical, 16x16"
    },
    @{
        Id = "fragment_sphere"
        Name = "Fragment Sphere"
        Description = "Fragment sphere sprite, metal sphere, round, 16x16"
    },
    @{
        Id = "fragment_incendiary"
        Name = "Incendiary Fragment"
        Description = "Incendiary fragment sprite, burning fragment, red/orange, 16x16"
    },
    @{
        Id = "fragment_emp"
        Name = "EMP Fragment"
        Description = "EMP fragment sprite, electrical fragment, blue/cyan, 16x16"
    }
)

foreach ($fragment in $fragmentSprites) {
    Write-Host "Generating fragment sprite: $($fragment.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $fragment.Id
            Prompt = "$($fragment.Description). Fragment sprite for Starbound cluster bombs."
            OllamaModel = $OllamaModel
            OutputDir = $bombOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($fragment.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($fragment.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. EXPLOSION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Explosion Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$explosionEffects = @(
    @{
        Id = "explosion_core"
        Name = "Explosion Core"
        Description = "Explosion core particle effect, expanding fire burst, intense explosion"
    },
    @{
        Id = "explosion_smoke"
        Name = "Explosion Smoke"
        Description = "Explosion smoke particle effect, billowing smoke ring, dark smoke"
    },
    @{
        Id = "explosion_debris"
        Name = "Explosion Debris"
        Description = "Explosion debris particle effect, grit particles, dust, rock fragments"
    },
    @{
        Id = "explosion_incendiary"
        Name = "Incendiary Explosion"
        Description = "Incendiary explosion particle effect, fire explosion, red/orange flames"
    },
    @{
        Id = "explosion_emp"
        Name = "EMP Explosion"
        Description = "EMP explosion particle effect, electrical explosion, blue/cyan sparks"
    }
)

foreach ($explosion in $explosionEffects) {
    Write-Host "Generating explosion effect: $($explosion.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $explosion.Id
            Prompt = "$($explosion.Description). Explosion particle effect for Starbound cluster bombs."
            OllamaModel = $OllamaModel
            OutputDir = $bombOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($explosion.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($explosion.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. BOMB ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Bomb Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$bombAnimations = @(
    @{
        Id = "bomb_fuse_burning"
        Name = "Fuse Burning Animation"
        Description = "Fuse burning animation, 8 frames, sparking fuse, burning down"
        FrameCount = 8
        AnimationCycle = 1.0
    },
    @{
        Id = "bomb_shell_cracking"
        Name = "Shell Cracking Animation"
        Description = "Shell cracking animation, 10 frames, shell breaking, cracks appearing"
        FrameCount = 10
        AnimationCycle = 0.3
    },
    @{
        Id = "bomb_detonating"
        Name = "Bomb Detonating Animation"
        Description = "Bomb detonating animation, 12 frames, explosion starting, shell breaking"
        FrameCount = 12
        AnimationCycle = 0.4
    }
)

foreach ($anim in $bombAnimations) {
    Write-Host "Generating animation: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = "$($anim.Description). Bomb animation spritesheet for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $bombOutputDir
        }
        
        $animParamHashtable = @{
            FrameCount = $anim.FrameCount
            AnimationCycle = $anim.AnimationCycle
            AnimationType = "DeviceActivation"
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
# 5. EXPLOSION DECALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Explosion Decals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$explosionDecals = @(
    @{
        Id = "explosion_decal_scorch"
        Name = "Explosion Scorch Decal"
        Description = "Explosion scorch decal texture, black scorch mark, burn mark, 64x64"
    },
    @{
        Id = "explosion_decal_crack"
        Name = "Explosion Crack Decal"
        Description = "Explosion crack decal texture, crack pattern, impact crack, 64x64"
    },
    @{
        Id = "explosion_decal_incendiary"
        Name = "Incendiary Scorch Decal"
        Description = "Incendiary scorch decal texture, red/orange scorch mark, fire burn, 64x64"
    },
    @{
        Id = "explosion_decal_emp"
        Name = "EMP Burn Decal"
        Description = "EMP burn decal texture, electrical burn mark, blue/cyan, 64x64"
    }
)

foreach ($decal in $explosionDecals) {
    Write-Host "Generating explosion decal: $($decal.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $decal.Id
            Prompt = "$($decal.Description). Explosion decal texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $bombOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($decal.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($decal.Name) : $_" -ForegroundColor Red
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
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets\projectiles\cluster_bombs')" -ForegroundColor Gray
Write-Host ""
Write-Host "Bomb sprites: assets/projectiles/cluster_bombs/cluster_bomb_*.png" -ForegroundColor Gray
Write-Host "Fragment sprites: assets/projectiles/cluster_bombs/fragment_*.png" -ForegroundColor Gray
Write-Host "Explosion effects: assets/projectiles/cluster_bombs/explosion_*.particle" -ForegroundColor Gray
Write-Host "Bomb animations: assets/projectiles/cluster_bombs/bomb_*_animation/" -ForegroundColor Gray
Write-Host "Explosion decals: assets/projectiles/cluster_bombs/explosion_decal_*.png" -ForegroundColor Gray
Write-Host ""
