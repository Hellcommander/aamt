#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the procedural mech system.
    
.DESCRIPTION
    Generates textures, icons, and preview sprites for:
    - Mech part textures (materials)
    - Mech part icons (UI)
    - Mech preview sprites
    - Material textures for different mech types
    
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
Write-Host "  Procedural Mech System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. MECH PART TEXTURES (MATERIALS)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mech Part Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$mechTextures = @(
    @{
        Id = "mech_metal"
        Name = "Metal Mech Texture"
        Description = "Metallic mech texture, gray/silver metal, industrial appearance, seamless"
    },
    @{
        Id = "mech_armor"
        Name = "Armor Mech Texture"
        Description = "Armored mech texture, reinforced plates, military appearance, seamless"
    },
    @{
        Id = "mech_energy"
        Name = "Energy Mech Texture"
        Description = "Energy mech texture, glowing energy panels, blue/purple glow, seamless"
    },
    @{
        Id = "mech_organic"
        Name = "Organic Mech Texture"
        Description = "Organic mech texture, bio-mechanical appearance, green/brown colors, seamless"
    },
    @{
        Id = "mech_crystal"
        Name = "Crystal Mech Texture"
        Description = "Crystal mech texture, crystalline structure, faceted appearance, seamless"
    },
    @{
        Id = "mech_rust"
        Name = "Rust Mech Texture"
        Description = "Rust mech texture, weathered metal, orange/brown rust, seamless"
    }
)

foreach ($texture in $mechTextures) {
    Write-Host "Generating texture: $($texture.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $texture.Id
            Prompt = "$($texture.Description). Mech part material texture for Starbound, 256x256 seamless texture."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($texture.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($texture.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. MECH PART ICONS (UI)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mech Part Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$mechPartIcons = @(
    @{
        Id = "mech_part_body"
        Name = "Body Part Icon"
        Description = "Mech body part icon, main body/core, robotic appearance"
    },
    @{
        Id = "mech_part_head"
        Name = "Head Part Icon"
        Description = "Mech head part icon, cockpit/head, robotic appearance"
    },
    @{
        Id = "mech_part_torso"
        Name = "Torso Part Icon"
        Description = "Mech torso part icon, upper torso, robotic appearance"
    },
    @{
        Id = "mech_part_arm"
        Name = "Arm Part Icon"
        Description = "Mech arm part icon, robotic arm, mechanical appearance"
    },
    @{
        Id = "mech_part_hand"
        Name = "Hand Part Icon"
        Description = "Mech hand part icon, gripper/hand, robotic appearance"
    },
    @{
        Id = "mech_part_leg"
        Name = "Leg Part Icon"
        Description = "Mech leg part icon, robotic leg, mechanical appearance"
    },
    @{
        Id = "mech_part_foot"
        Name = "Foot Part Icon"
        Description = "Mech foot part icon, ground contact, robotic appearance"
    },
    @{
        Id = "mech_part_wing"
        Name = "Wing Part Icon"
        Description = "Mech wing part icon, wing/jet, aerodynamic appearance"
    },
    @{
        Id = "mech_part_weapon"
        Name = "Weapon Part Icon"
        Description = "Mech weapon part icon, weapon system, military appearance"
    },
    @{
        Id = "mech_part_shield"
        Name = "Shield Part Icon"
        Description = "Mech shield part icon, shield system, defensive appearance"
    }
)

foreach ($icon in $mechPartIcons) {
    Write-Host "Generating icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Mech part icon for Starbound UI, 32x32 pixel art."
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
# 3. MECH PREVIEW SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mech Preview Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$mechPreviews = @(
    @{
        Id = "mech_preview_bipedal"
        Name = "Bipedal Mech Preview"
        Description = "Bipedal mech preview sprite, humanoid mech, side view, 64x64 pixel art"
    },
    @{
        Id = "mech_preview_quadruped"
        Name = "Quadruped Mech Preview"
        Description = "Quadruped mech preview sprite, four-legged mech, side view, 64x64 pixel art"
    },
    @{
        Id = "mech_preview_hover"
        Name = "Hover Mech Preview"
        Description = "Hover mech preview sprite, floating mech, side view, 64x64 pixel art"
    },
    @{
        Id = "mech_preview_tank"
        Name = "Tank Mech Preview"
        Description = "Tank mech preview sprite, tank-like mech, side view, 64x64 pixel art"
    }
)

foreach ($preview in $mechPreviews) {
    Write-Host "Generating preview: $($preview.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "MechSprite"
            AssetName = $preview.Id
            Prompt = "$($preview.Description). Mech preview sprite for Starbound UI."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($preview.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($preview.Name) : $_" -ForegroundColor Red
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
Write-Host "Textures: assets/textures/mech/" -ForegroundColor Gray
Write-Host "Icons: assets/interface/icons/mech/" -ForegroundColor Gray
Write-Host "Previews: assets/mechs/previews/" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: Mech meshes are generated procedurally, these are supporting assets" -ForegroundColor Yellow
Write-Host ""
