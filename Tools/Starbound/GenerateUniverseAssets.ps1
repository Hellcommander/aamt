#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the universe generation system.
    
.DESCRIPTION
    Generates sprites, animations, and effects for:
    - Portal entities (reflective, wormhole, etc.)
    - Star system icons
    - Planet icons
    - Portal particle effects
    - UI elements for universe navigation
    
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
Write-Host "  Universe System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PORTAL ASSETS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Portal Assets" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$portals = @(
    @{
        Id = "portal_reflective"
        Name = "Reflective Portal"
        Description = "A reflective portal that mirrors the destination, shimmering surface, magical energy"
        Type = "reflective"
    },
    @{
        Id = "portal_wormhole"
        Name = "Wormhole Portal"
        Description = "A wormhole portal with swirling void energy, dark center, gravitational distortion"
        Type = "wormhole"
    },
    @{
        Id = "portal_arcane"
        Name = "Arcane Portal"
        Description = "An arcane portal with purple magical energy, runic patterns, swirling particles"
        Type = "arcane"
    },
    @{
        Id = "portal_void"
        Name = "Void Portal"
        Description = "A void portal with dark energy, void corruption, shadowy appearance"
        Type = "void"
    },
    @{
        Id = "portal_quantum"
        Name = "Quantum Portal"
        Description = "A quantum portal with reality-bending effects, quantum instability, shimmering"
        Type = "quantum"
    },
    @{
        Id = "portal_temporal"
        Name = "Temporal Portal"
        Description = "A temporal portal with time distortion effects, clockwork patterns, temporal energy"
        Type = "temporal"
    }
)

foreach ($portal in $portals) {
    Write-Host "Generating: $($portal.Name)" -ForegroundColor Cyan
    
    # Generate portal sprite
    try {
        # Validate $ModPath before Join-Path
        $tempOutputDir = Join-Path $ModPath "assets"
        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            Write-Host "  Skipping portal sprite generation" -ForegroundColor Yellow
        } else {
            $params = @{
                AssetType = "ItemSprite"
                AssetName = $portal.Id
                Prompt = "$($portal.Description). Portal entity sprite for Starbound, pixel art style."
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($portal.Name)" -ForegroundColor Green
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] $($portal.Name) : $_" -ForegroundColor Red
    }
    
    # Generate portal animation
    Write-Host "  Generating animation..." -ForegroundColor Gray
    try {
        # Validate $ModPath before Join-Path
        $tempOutputDir = Join-Path $ModPath "assets"
        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            Write-Host "  Skipping portal animation generation" -ForegroundColor Yellow
        } else {
            $animParams = @{
                AssetType = "AnimationSprite"
                AssetName = "$($portal.Id)_animation"
                Prompt = "$($portal.Description). Portal activation animation, 8 frames showing portal opening and energy swirling."
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            
            $animParamHashtable = @{
                FrameCount = 8
                AnimationCycle = 0.8
                AnimationType = "SpellCast"
                FrameWidth = 64
                FrameHeight = 64
            }
            $animParams['Parameters'] = $animParamHashtable
            
            if ($UseCppBackend) {
                $animParams['UseCppBackend'] = $true
            }
            
            & $assetGenerator @animParams | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated animation: $($portal.Name)" -ForegroundColor Green
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] Animation for $($portal.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. STAR SYSTEM ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Star System Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$starTypes = @(
    @{
        Id = "star_normal"
        Name = "Normal Star"
        Description = "A normal star icon, yellow/white, glowing sphere"
    },
    @{
        Id = "star_arcane"
        Name = "Arcane Star"
        Description = "An arcane star icon, purple magical energy, runic patterns"
    },
    @{
        Id = "star_void"
        Name = "Void Star"
        Description = "A void star icon, dark energy, shadowy appearance"
    },
    @{
        Id = "star_quantum"
        Name = "Quantum Star"
        Description = "A quantum star icon, reality-bending effects, shimmering"
    },
    @{
        Id = "star_temporal"
        Name = "Temporal Star"
        Description = "A temporal star icon, time distortion effects, clockwork patterns"
    },
    @{
        Id = "star_chaos"
        Name = "Chaos Star"
        Description = "A chaos star icon, random magical effects, unstable appearance"
    },
    @{
        Id = "star_order"
        Name = "Order Star"
        Description = "An order star icon, stable magical fields, structured appearance"
    }
)

foreach ($star in $starTypes) {
    Write-Host "Generating: $($star.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
        $tempOutputDir = Join-Path $ModPath "assets"
        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            Write-Host "  Skipping star icon generation" -ForegroundColor Yellow
        } else {
            $params = @{
                AssetType = "Icon"
                AssetName = $star.Id
                Prompt = "$($star.Description). Star system icon for Starbound UI, 32x32 pixel art."
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($star.Name)" -ForegroundColor Green
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] $($star.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. PLANET ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Planet Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$planetTypes = @(
    @{
        Id = "planet_normal"
        Name = "Normal Planet"
        Description = "A normal planet icon, blue/green, standard appearance"
    },
    @{
        Id = "planet_arcane_forest"
        Name = "Arcane Forest Planet"
        Description = "An arcane forest planet icon, magical trees, purple/green colors"
    },
    @{
        Id = "planet_void_wastes"
        Name = "Void Wastes Planet"
        Description = "A void wastes planet icon, corrupted landscape, dark colors"
    },
    @{
        Id = "planet_quantum_plains"
        Name = "Quantum Plains Planet"
        Description = "A quantum plains planet icon, reality-bending terrain, shimmering"
    },
    @{
        Id = "planet_temporal_mountains"
        Name = "Temporal Mountains Planet"
        Description = "A temporal mountains planet icon, time-shifted peaks, clockwork patterns"
    },
    @{
        Id = "planet_chaos_swamps"
        Name = "Chaos Swamps Planet"
        Description = "A chaos swamps planet icon, random magical effects, unstable appearance"
    },
    @{
        Id = "planet_order_gardens"
        Name = "Order Gardens Planet"
        Description = "An order gardens planet icon, stable magical zones, structured appearance"
    }
)

foreach ($planet in $planetTypes) {
    Write-Host "Generating: $($planet.Name)" -ForegroundColor Cyan
    
    try {
        # Validate $ModPath before Join-Path
        $tempOutputDir = Join-Path $ModPath "assets"
        if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
            Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            Write-Host "  Skipping planet icon generation" -ForegroundColor Yellow
        } else {
            $params = @{
                AssetType = "Icon"
                AssetName = $planet.Id
                Prompt = "$($planet.Description). Planet icon for Starbound UI, 32x32 pixel art."
                OllamaModel = $OllamaModel
                OutputDir = $tempOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($planet.Name)" -ForegroundColor Green
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] $($planet.Name) : $_" -ForegroundColor Red
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
Write-Host "Portal sprites: assets/items/sprites/" -ForegroundColor Gray
Write-Host "Portal animations: assets/animations/" -ForegroundColor Gray
Write-Host "Star/Planet icons: assets/interface/icons/" -ForegroundColor Gray
Write-Host ""
