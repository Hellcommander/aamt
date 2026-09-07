#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the alchemy system.
    
.DESCRIPTION
    Generates sprites, icons, and effects for:
    - Alchemy ingredient icons
    - Plant sprites (for plant growth system)
    - Reaction effect particles
    - Alchemy station sprites
    
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
Write-Host "  Alchemy System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. ALCHEMY INGREDIENT ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Alchemy Ingredient Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$ingredientIcons = @(
    @{
        Id = "ingredient_metal"
        Name = "Metal Ingredient"
        Description = "Metal ingredient icon, metallic appearance, gray/silver colors"
    },
    @{
        Id = "ingredient_organic"
        Name = "Organic Ingredient"
        Description = "Organic ingredient icon, plant-based appearance, green/brown colors"
    },
    @{
        Id = "ingredient_crystal"
        Name = "Crystal Ingredient"
        Description = "Crystal ingredient icon, crystalline structure, clear/sparkling"
    },
    @{
        Id = "ingredient_gem"
        Name = "Gem Ingredient"
        Description = "Gem ingredient icon, faceted gem appearance, colorful"
    },
    @{
        Id = "ingredient_liquid"
        Name = "Liquid Ingredient"
        Description = "Liquid ingredient icon, fluid appearance, blue/clear colors"
    },
    @{
        Id = "ingredient_gas"
        Name = "Gas Ingredient"
        Description = "Gas ingredient icon, gaseous appearance, wispy, transparent"
    },
    @{
        Id = "ingredient_acidic"
        Name = "Acidic Ingredient"
        Description = "Acidic ingredient icon, corrosive appearance, green/yellow colors"
    },
    @{
        Id = "ingredient_magical"
        Name = "Magical Ingredient"
        Description = "Magical ingredient icon, magical energy, purple/blue glow"
    },
    @{
        Id = "ingredient_bio_ooze"
        Name = "Bio Ooze"
        Description = "Bio ooze ingredient icon, organic slime, green/brown colors"
    },
    @{
        Id = "ingredient_mutagene"
        Name = "Mutagene"
        Description = "Mutagene ingredient icon, unstable appearance, purple/green colors"
    },
    @{
        Id = "ingredient_quantum_fluid"
        Name = "Quantum Fluid"
        Description = "Quantum fluid ingredient icon, reality-bending appearance, shimmering"
    },
    @{
        Id = "ingredient_particle_destabilizer"
        Name = "Particle Destabilizer"
        Description = "Particle destabilizer ingredient icon, unstable energy, chaotic appearance"
    }
)

foreach ($icon in $ingredientIcons) {
    Write-Host "Generating icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Alchemy ingredient icon for Starbound UI, 32x32 pixel art."
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
# 2. PLANT SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Plant Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$plantSprites = @(
    @{
        Id = "plant_leaf"
        Name = "Plant Leaf"
        Description = "Plant leaf sprite, green leaf, organic appearance"
    },
    @{
        Id = "plant_growing"
        Name = "Growing Plant"
        Description = "Growing plant sprite, small plant with leaves, green colors"
    },
    @{
        Id = "plant_mature"
        Name = "Mature Plant"
        Description = "Mature plant sprite, full-grown plant, green/brown colors"
    },
    @{
        Id = "plant_dead"
        Name = "Dead Plant"
        Description = "Dead plant sprite, withered plant, brown/gray colors"
    },
    @{
        Id = "plant_fibre"
        Name = "Plant Fibre"
        Description = "Plant fibre sprite, fibrous material, brown/tan colors"
    }
)

foreach ($plant in $plantSprites) {
    Write-Host "Generating plant sprite: $($plant.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $plant.Id
            Prompt = "$($plant.Description). Plant sprite for Starbound alchemy system, pixel art style."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($plant.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($plant.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. REACTION EFFECT PARTICLES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Reaction Effect Particles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$reactionEffects = @(
    @{
        Id = "reaction_rust"
        Name = "Rust Reaction"
        Description = "Rust reaction particle effect, orange/brown rust particles, corrosion"
    },
    @{
        Id = "reaction_combustion"
        Name = "Combustion Reaction"
        Description = "Combustion reaction particle effect, fire explosion, red/orange flames"
    },
    @{
        Id = "reaction_crystallization"
        Name = "Crystallization Reaction"
        Description = "Crystallization reaction particle effect, crystal formation, sparkling particles"
    },
    @{
        Id = "reaction_dissolution"
        Name = "Dissolution Reaction"
        Description = "Dissolution reaction particle effect, dissolving particles, bubbling"
    },
    @{
        Id = "reaction_plant_growth"
        Name = "Plant Growth Reaction"
        Description = "Plant growth reaction particle effect, green growth particles, organic"
    },
    @{
        Id = "reaction_particle_destabilization"
        Name = "Particle Destabilization"
        Description = "Particle destabilization reaction effect, reality rift, chaotic particles"
    },
    @{
        Id = "reaction_super_fertilizer"
        Name = "Super Fertilizer Reaction"
        Description = "Super fertilizer reaction effect, green/brown organic particles, growth boost"
    },
    @{
        Id = "reaction_unstable_growth"
        Name = "Unstable Growth Reaction"
        Description = "Unstable growth liquid reaction effect, green/yellow particles, unstable"
    }
)

foreach ($effect in $reactionEffects) {
    Write-Host "Generating reaction effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Alchemy reaction particle effect for Starbound."
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
# 4. ALCHEMY STATION SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Alchemy Station Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stationSprites = @(
    @{
        Id = "alchemy_workbench"
        Name = "Alchemy Workbench"
        Description = "Alchemy workbench sprite, crafting station, magical appearance, pixel art"
    },
    @{
        Id = "alchemy_cauldron"
        Name = "Alchemy Cauldron"
        Description = "Alchemy cauldron sprite, brewing vessel, metal cauldron, pixel art"
    },
    @{
        Id = "alchemy_mortar_pestle"
        Name = "Mortar and Pestle"
        Description = "Mortar and pestle sprite, grinding tool, stone/metal, pixel art"
    }
)

foreach ($station in $stationSprites) {
    Write-Host "Generating station sprite: $($station.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $station.Id
            Prompt = "$($station.Description). Alchemy station sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($station.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($station.Name) : $_" -ForegroundColor Red
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
Write-Host "Ingredient icons: assets/interface/icons/alchemy/" -ForegroundColor Gray
Write-Host "Plant sprites: assets/items/sprites/plants/" -ForegroundColor Gray
Write-Host "Reaction effects: assets/particles/alchemy/" -ForegroundColor Gray
Write-Host "Station sprites: assets/objects/alchemy/" -ForegroundColor Gray
Write-Host ""
