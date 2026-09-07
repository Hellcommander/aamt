#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Unified Portal System.
    
.DESCRIPTION
    Generates sprites, animations, and effects for:
    - Portal sprites (various types)
    - Portal animations (opening, closing, active)
    - Portal particle effects
    - Portal glow textures
    - Portal frame textures
    
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
Write-Host "  Unified Portal System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PORTAL SPRITES (BY TYPE)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalSprites = @(
    @{
        Id = "portal_standard"
        Name = "Standard Portal"
        Description = "Standard portal sprite, circular portal frame, blue/purple energy, 64x64"
    },
    @{
        Id = "portal_dimensional"
        Name = "Dimensional Portal"
        Description = "Dimensional portal sprite, purple/magenta energy, swirling vortex, 64x64"
    },
    @{
        Id = "portal_temporal"
        Name = "Temporal Portal"
        Description = "Temporal portal sprite, green energy, clockwork appearance, time effects, 64x64"
    },
    @{
        Id = "portal_quantum"
        Name = "Quantum Portal"
        Description = "Quantum portal sprite, blue energy, quantum effects, particle appearance, 64x64"
    },
    @{
        Id = "portal_blink"
        Name = "Blink Portal"
        Description = "Blink portal sprite, yellow/cyan energy, short-range teleport, 64x64"
    },
    @{
        Id = "portal_alt_universe"
        Name = "Alt Universe Portal"
        Description = "Alt universe portal sprite, dark energy, reality distortion, 64x64"
    },
    @{
        Id = "portal_chaos"
        Name = "Chaos Portal"
        Description = "Chaos portal sprite, chaotic energy, unpredictable appearance, 64x64"
    },
    @{
        Id = "portal_mirror"
        Name = "Mirror Portal"
        Description = "Mirror portal sprite, reflective surface, mirror dimension, 64x64"
    },
    @{
        Id = "portal_void"
        Name = "Void Portal"
        Description = "Void portal sprite, dark void energy, black/purple, 64x64"
    },
    @{
        Id = "portal_planetary"
        Name = "Planetary Portal"
        Description = "Planetary portal sprite, surface teleportation, blue energy, 64x64"
    },
    @{
        Id = "portal_orbital"
        Name = "Orbital Portal"
        Description = "Orbital portal sprite, space station access, cyan energy, 64x64"
    },
    @{
        Id = "portal_stellar"
        Name = "Stellar Portal"
        Description = "Stellar portal sprite, star system travel, golden energy, 64x64"
    }
)

# Validate $ModPath before Join-Path
$portalOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($portalOutputDir)) {
    Write-Host "  [FAIL] portalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($portalOutputDir)) {
    Write-Host "  [FAIL] portalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $portalOutputDir)) {
    New-Item -ItemType Directory -Path $portalOutputDir -Force | Out-Null
}

foreach ($portal in $portalSprites) {
    Write-Host "Generating portal sprite: $($portal.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "PortalSprite"
            AssetName = $portal.Id
            Prompt = "$($portal.Description). Portal sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($portal.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($portal.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. PORTAL ANIMATIONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Animations" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalAnimations = @(
    @{
        Id = "portal_opening"
        Name = "Portal Opening Animation"
        Description = "Portal opening animation, 8 frames, expanding portal, energy building"
        FrameCount = 8
        AnimationCycle = 0.8
    },
    @{
        Id = "portal_closing"
        Name = "Portal Closing Animation"
        Description = "Portal closing animation, 8 frames, collapsing portal, energy fading"
        FrameCount = 8
        AnimationCycle = 0.8
    },
    @{
        Id = "portal_active"
        Name = "Portal Active Animation"
        Description = "Portal active animation, 12 frames, pulsing energy, swirling vortex"
        FrameCount = 12
        AnimationCycle = 1.5
    },
    @{
        Id = "portal_unstable"
        Name = "Portal Unstable Animation"
        Description = "Portal unstable animation, 10 frames, flickering energy, instability"
        FrameCount = 10
        AnimationCycle = 0.6
    },
    @{
        Id = "portal_charging"
        Name = "Portal Charging Animation"
        Description = "Portal charging animation, 6 frames, energy building up, charging"
        FrameCount = 6
        AnimationCycle = 1.0
    }
)

foreach ($anim in $portalAnimations) {
    Write-Host "Generating animation: $($anim.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "AnimationSprite"
            AssetName = $anim.Id
            Prompt = "$($anim.Description). Portal animation spritesheet for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $animParamHashtable = @{
            FrameCount = $anim.FrameCount
            AnimationCycle = $anim.AnimationCycle
            AnimationType = "DeviceActivation"
            FrameWidth = 64
            FrameHeight = 64
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
# 3. PORTAL PARTICLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Particle Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalParticles = @(
    @{
        Id = "portal_particle_standard"
        Name = "Standard Portal Particles"
        Description = "Standard portal particle effect, blue/purple particles, energy particles"
    },
    @{
        Id = "portal_particle_dimensional"
        Name = "Dimensional Portal Particles"
        Description = "Dimensional portal particle effect, purple/magenta particles, dimensional energy"
    },
    @{
        Id = "portal_particle_temporal"
        Name = "Temporal Portal Particles"
        Description = "Temporal portal particle effect, green particles, time particles"
    },
    @{
        Id = "portal_particle_quantum"
        Name = "Quantum Portal Particles"
        Description = "Quantum portal particle effect, blue particles, quantum energy"
    },
    @{
        Id = "portal_particle_void"
        Name = "Void Portal Particles"
        Description = "Void portal particle effect, dark particles, void energy"
    },
    @{
        Id = "portal_particle_chaos"
        Name = "Chaos Portal Particles"
        Description = "Chaos portal particle effect, chaotic particles, unpredictable"
    }
)

foreach ($particle in $portalParticles) {
    Write-Host "Generating particle effect: $($particle.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $particle.Id
            Prompt = "$($particle.Description). Portal particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($particle.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($particle.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. PORTAL GLOW TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Glow Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalGlows = @(
    @{
        Id = "portal_glow_standard"
        Name = "Standard Portal Glow"
        Description = "Standard portal glow texture, blue/purple glow, circular, 64x64"
    },
    @{
        Id = "portal_glow_dimensional"
        Name = "Dimensional Portal Glow"
        Description = "Dimensional portal glow texture, purple/magenta glow, 64x64"
    },
    @{
        Id = "portal_glow_temporal"
        Name = "Temporal Portal Glow"
        Description = "Temporal portal glow texture, green glow, 64x64"
    },
    @{
        Id = "portal_glow_quantum"
        Name = "Quantum Portal Glow"
        Description = "Quantum portal glow texture, blue glow, 64x64"
    },
    @{
        Id = "portal_glow_void"
        Name = "Void Portal Glow"
        Description = "Void portal glow texture, dark purple glow, 64x64"
    }
)

foreach ($glow in $portalGlows) {
    Write-Host "Generating glow texture: $($glow.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $glow.Id
            Prompt = "$($glow.Description). Portal glow texture for Starbound emissive effects."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($glow.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($glow.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. PORTAL FRAME TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Frame Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portalFrames = @(
    @{
        Id = "portal_frame_standard"
        Name = "Standard Portal Frame"
        Description = "Standard portal frame texture, circular frame, metallic appearance, 64x64"
    },
    @{
        Id = "portal_frame_ancient"
        Name = "Ancient Portal Frame"
        Description = "Ancient portal frame texture, stone frame, runic patterns, 64x64"
    },
    @{
        Id = "portal_frame_tech"
        Name = "Tech Portal Frame"
        Description = "Tech portal frame texture, technological frame, sci-fi appearance, 64x64"
    },
    @{
        Id = "portal_frame_magic"
        Name = "Magic Portal Frame"
        Description = "Magic portal frame texture, magical frame, arcane patterns, 64x64"
    }
)

foreach ($frame in $portalFrames) {
    Write-Host "Generating frame texture: $($frame.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $frame.Id
            Prompt = "$($frame.Description). Portal frame texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $portalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($frame.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($frame.Name) : $_" -ForegroundColor Red
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
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets\portals')" -ForegroundColor Gray
Write-Host ""
Write-Host "Portal sprites: assets/portals/portal_*.png" -ForegroundColor Gray
Write-Host "Portal animations: assets/portals/portal_*_animation/" -ForegroundColor Gray
Write-Host "Portal particles: assets/portals/portal_particle_*.particle" -ForegroundColor Gray
Write-Host "Portal glows: assets/portals/portal_glow_*.png" -ForegroundColor Gray
Write-Host "Portal frames: assets/portals/portal_frame_*.png" -ForegroundColor Gray
Write-Host ""
