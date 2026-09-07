#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the AlchemistBus System.
    
.DESCRIPTION
    Generates visual assets for:
    - Ingredient icons (by type, phase, elemental type)
    - Reaction visual effects
    - Grid reaction visuals
    - Alchemy station UI elements
    - Plant sprites
    - Phase indicators (solid, liquid, gas, plasma)
    - Environmental condition indicators
    - Reaction status indicators
    - Material type icons
    - Elemental type icons
    
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
Write-Host "  AlchemistBus System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. INGREDIENT TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Ingredient Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$ingredientTypes = @(
    @{ Id = "ingredient_basic"; Name = "Basic Ingredient"; Desc = "Basic ingredient icon, basic alchemical ingredient, 32x32" },
    @{ Id = "ingredient_crystal"; Name = "Crystal Ingredient"; Desc = "Crystal ingredient icon, crystalline ingredient, 32x32" },
    @{ Id = "ingredient_organic"; Name = "Organic Ingredient"; Desc = "Organic ingredient icon, organic material, 32x32" },
    @{ Id = "ingredient_metal"; Name = "Metal Ingredient"; Desc = "Metal ingredient icon, metallic ingredient, 32x32" },
    @{ Id = "ingredient_gem"; Name = "Gem Ingredient"; Desc = "Gem ingredient icon, gemstone ingredient, 32x32" },
    @{ Id = "ingredient_catalyst"; Name = "Catalyst Ingredient"; Desc = "Catalyst ingredient icon, reaction catalyst, 32x32" }
)

# Validate $ModPath before Join-Path
$ingredientOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($ingredientOutputDir)) {
    Write-Host "  [FAIL] ingredientOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($ingredientOutputDir)) {
    Write-Host "  [FAIL] ingredientOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $ingredientOutputDir)) {
    New-Item -ItemType Directory -Path $ingredientOutputDir -Force | Out-Null
}

foreach ($type in $ingredientTypes) {
    Write-Host "Generating ingredient type icon: $($type.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $type.Id
            Prompt = "$($type.Desc). Ingredient type icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $ingredientOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($type.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($type.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. PHASE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Phase Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$phases = @(
    @{ Id = "phase_solid"; Name = "Solid Phase"; Desc = "Solid phase indicator icon, solid state, 32x32" },
    @{ Id = "phase_liquid"; Name = "Liquid Phase"; Desc = "Liquid phase indicator icon, liquid state, 32x32" },
    @{ Id = "phase_gas"; Name = "Gas Phase"; Desc = "Gas phase indicator icon, gas state, 32x32" },
    @{ Id = "phase_plasma"; Name = "Plasma Phase"; Desc = "Plasma phase indicator icon, plasma state, 32x32" }
)

# Validate $ModPath before Join-Path
$phaseOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($phaseOutputDir)) {
    Write-Host "  [FAIL] phaseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($phaseOutputDir)) {
    Write-Host "  [FAIL] phaseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $phaseOutputDir)) {
    New-Item -ItemType Directory -Path $phaseOutputDir -Force | Out-Null
}

foreach ($phase in $phases) {
    Write-Host "Generating phase indicator: $($phase.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $phase.Id
            Prompt = "$($phase.Desc). Phase indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $phaseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($phase.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($phase.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. ELEMENTAL TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Elemental Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$elementalTypes = @(
    @{ Id = "element_fire"; Name = "Fire Element"; Desc = "Fire elemental type icon, fire element, 32x32" },
    @{ Id = "element_water"; Name = "Water Element"; Desc = "Water elemental type icon, water element, 32x32" },
    @{ Id = "element_earth"; Name = "Earth Element"; Desc = "Earth elemental type icon, earth element, 32x32" },
    @{ Id = "element_air"; Name = "Air Element"; Desc = "Air elemental type icon, air element, 32x32" },
    @{ Id = "element_void"; Name = "Void Element"; Desc = "Void elemental type icon, void element, 32x32" },
    @{ Id = "element_neutral"; Name = "Neutral Element"; Desc = "Neutral elemental type icon, neutral element, 32x32" }
)

# Validate $ModPath before Join-Path
$elementalOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($elementalOutputDir)) {
    Write-Host "  [FAIL] elementalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($elementalOutputDir)) {
    Write-Host "  [FAIL] elementalOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $elementalOutputDir)) {
    New-Item -ItemType Directory -Path $elementalOutputDir -Force | Out-Null
}

foreach ($element in $elementalTypes) {
    Write-Host "Generating elemental type icon: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $element.Id
            Prompt = "$($element.Desc). Elemental type icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $elementalOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($element.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($element.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. MATERIAL TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Material Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$materialTypes = @(
    @{ Id = "material_metal"; Name = "Metal Material"; Desc = "Metal material type icon, metallic material, 32x32" },
    @{ Id = "material_organic"; Name = "Organic Material"; Desc = "Organic material type icon, organic material, 32x32" },
    @{ Id = "material_crystal"; Name = "Crystal Material"; Desc = "Crystal material type icon, crystalline material, 32x32" },
    @{ Id = "material_gem"; Name = "Gem Material"; Desc = "Gem material type icon, gemstone material, 32x32" },
    @{ Id = "material_wood"; Name = "Wood Material"; Desc = "Wood material type icon, wooden material, 32x32" },
    @{ Id = "material_bone"; Name = "Bone Material"; Desc = "Bone material type icon, bone material, 32x32" }
)

# Validate $ModPath before Join-Path
$materialOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $materialOutputDir)) {
    New-Item -ItemType Directory -Path $materialOutputDir -Force | Out-Null
}

foreach ($material in $materialTypes) {
    Write-Host "Generating material type icon: $($material.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $material.Id
            Prompt = "$($material.Desc). Material type icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $materialOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($material.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($material.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. REACTION VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Reaction Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$reactionEffects = @(
    @{ Id = "reaction_explosion"; Name = "Explosion Reaction"; Desc = "Explosion reaction particle effect, explosive reaction visual, 64x64" },
    @{ Id = "reaction_toxic_smoke"; Name = "Toxic Smoke Reaction"; Desc = "Toxic smoke reaction particle effect, toxic smoke visual, 64x64" },
    @{ Id = "reaction_healing_mist"; Name = "Healing Mist Reaction"; Desc = "Healing mist reaction particle effect, healing mist visual, 64x64" },
    @{ Id = "reaction_intense_heat"; Name = "Intense Heat Reaction"; Desc = "Intense heat reaction particle effect, intense heat visual, 64x64" },
    @{ Id = "reaction_extinguish"; Name = "Extinguish Reaction"; Desc = "Extinguish reaction particle effect, extinguish visual, 64x64" },
    @{ Id = "reaction_steam"; Name = "Steam Reaction"; Desc = "Steam reaction particle effect, steam visual, 64x64" },
    @{ Id = "reaction_energy_storage"; Name = "Energy Storage Reaction"; Desc = "Energy storage reaction particle effect, energy storage visual, 64x64" },
    @{ Id = "reaction_active"; Name = "Active Reaction"; Desc = "Active reaction particle effect, active reaction visual, 64x64" }
)

# Validate $ModPath before Join-Path
$reactionEffectOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($reactionEffectOutputDir)) {
    Write-Host "  [FAIL] reactionEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($reactionEffectOutputDir)) {
    Write-Host "  [FAIL] reactionEffectOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $reactionEffectOutputDir)) {
    New-Item -ItemType Directory -Path $reactionEffectOutputDir -Force | Out-Null
}

foreach ($effect in $reactionEffects) {
    Write-Host "Generating reaction effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Reaction visual effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $reactionEffectOutputDir
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
# 6. GRID REACTION VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Grid Reaction Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$gridVisuals = @(
    @{ Id = "grid_cell"; Name = "Grid Cell"; Desc = "Grid reaction cell texture, reaction grid cell, 32x32" },
    @{ Id = "grid_cell_active"; Name = "Active Grid Cell"; Desc = "Active grid cell texture, active reaction cell, 32x32" },
    @{ Id = "grid_connection"; Name = "Grid Connection"; Desc = "Grid connection line, cell connection, 64x8" },
    @{ Id = "grid_diffusion"; Name = "Diffusion Effect"; Desc = "Diffusion particle effect, material diffusion visual, 64x64" }
)

# Validate $ModPath before Join-Path
$gridOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($gridOutputDir)) {
    Write-Host "  [FAIL] gridOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($gridOutputDir)) {
    Write-Host "  [FAIL] gridOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $gridOutputDir)) {
    New-Item -ItemType Directory -Path $gridOutputDir -Force | Out-Null
}

foreach ($visual in $gridVisuals) {
    Write-Host "Generating grid visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($visual.Id -like "*connection*" -or $visual.Id -like "*cell*") { "Texture" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Grid reaction visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $gridOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($visual.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($visual.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. ALCHEMY STATION UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Alchemy Station UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stationUI = @(
    @{ Id = "ui_panel_alchemy"; Name = "Alchemy Panel"; Desc = "Alchemy station panel background, alchemy UI panel, 256x256" },
    @{ Id = "ui_panel_reactions"; Name = "Reactions Panel"; Desc = "Reactions panel background, reaction management panel, 128x128" },
    @{ Id = "ui_slot_ingredient"; Name = "Ingredient Slot"; Desc = "Ingredient slot background, ingredient slot, 32x32" },
    @{ Id = "ui_slot_output"; Name = "Output Slot"; Desc = "Output slot background, reaction output slot, 32x32" },
    @{ Id = "ui_button_react"; Name = "React Button"; Desc = "React button icon, trigger reaction, 32x32" },
    @{ Id = "ui_button_clear"; Name = "Clear Button"; Desc = "Clear button icon, clear ingredients, 32x32" },
    @{ Id = "ui_indicator_temperature"; Name = "Temperature Indicator"; Desc = "Temperature indicator icon, temperature display, 32x32" },
    @{ Id = "ui_indicator_pressure"; Name = "Pressure Indicator"; Desc = "Pressure indicator icon, pressure display, 32x32" },
    @{ Id = "ui_indicator_humidity"; Name = "Humidity Indicator"; Desc = "Humidity indicator icon, humidity display, 32x32" },
    @{ Id = "ui_indicator_wind"; Name = "Wind Indicator"; Desc = "Wind indicator icon, wind display, 32x32" },
    @{ Id = "ui_indicator_mana"; Name = "Mana Indicator"; Desc = "Mana indicator icon, ambient mana display, 32x32" }
)

# Validate $ModPath before Join-Path
$stationUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stationUIOutputDir)) {
    Write-Host "  [FAIL] stationUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stationUIOutputDir)) {
    Write-Host "  [FAIL] stationUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stationUIOutputDir)) {
    New-Item -ItemType Directory -Path $stationUIOutputDir -Force | Out-Null
}

foreach ($element in $stationUI) {
    Write-Host "Generating station UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*panel*" -or $element.Id -like "*slot*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Alchemy station UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stationUIOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($element.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($element.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 8. PLANT SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Plant Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$plants = @(
    @{ Id = "plant_basic"; Name = "Basic Plant"; Desc = "Basic alchemical plant sprite, alchemy plant, 32x32" },
    @{ Id = "plant_herb"; Name = "Herb Plant"; Desc = "Herb plant sprite, medicinal herb, 32x32" },
    @{ Id = "plant_crystal"; Name = "Crystal Plant"; Desc = "Crystal plant sprite, crystalline plant, 32x32" },
    @{ Id = "plant_magical"; Name = "Magical Plant"; Desc = "Magical plant sprite, magical herb, 32x32" }
)

# Validate $ModPath before Join-Path
$plantOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($plantOutputDir)) {
    Write-Host "  [FAIL] plantOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($plantOutputDir)) {
    Write-Host "  [FAIL] plantOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $plantOutputDir)) {
    New-Item -ItemType Directory -Path $plantOutputDir -Force | Out-Null
}

foreach ($plant in $plants) {
    Write-Host "Generating plant sprite: $($plant.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $plant.Id
            Prompt = "$($plant.Desc). Plant sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $plantOutputDir
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
# 9. ENVIRONMENTAL CONDITION INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Environmental Condition Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$environmentalIndicators = @(
    @{ Id = "env_temperature_high"; Name = "High Temperature"; Desc = "High temperature indicator icon, high temperature, 32x32" },
    @{ Id = "env_temperature_low"; Name = "Low Temperature"; Desc = "Low temperature indicator icon, low temperature, 32x32" },
    @{ Id = "env_pressure_high"; Name = "High Pressure"; Desc = "High pressure indicator icon, high pressure, 32x32" },
    @{ Id = "env_pressure_low"; Name = "Low Pressure"; Desc = "Low pressure indicator icon, low pressure, 32x32" },
    @{ Id = "env_humidity_high"; Name = "High Humidity"; Desc = "High humidity indicator icon, high humidity, 32x32" },
    @{ Id = "env_humidity_low"; Name = "Low Humidity"; Desc = "Low humidity indicator icon, low humidity, 32x32" },
    @{ Id = "env_wind_strong"; Name = "Strong Wind"; Desc = "Strong wind indicator icon, strong wind, 32x32" },
    @{ Id = "env_wind_calm"; Name = "Calm Wind"; Desc = "Calm wind indicator icon, calm wind, 32x32" },
    @{ Id = "env_corrosive"; Name = "Corrosive Atmosphere"; Desc = "Corrosive atmosphere indicator icon, corrosive environment, 32x32" }
)

# Validate $ModPath before Join-Path
$envOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($envOutputDir)) {
    Write-Host "  [FAIL] envOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($envOutputDir)) {
    Write-Host "  [FAIL] envOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $envOutputDir)) {
    New-Item -ItemType Directory -Path $envOutputDir -Force | Out-Null
}

foreach ($indicator in $environmentalIndicators) {
    Write-Host "Generating environmental indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Environmental condition indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $envOutputDir
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
# 10. REACTION STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Reaction Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$reactionStatus = @(
    @{ Id = "status_ready"; Name = "Reaction Ready"; Desc = "Reaction ready indicator icon, ready to react, 32x32" },
    @{ Id = "status_active"; Name = "Reaction Active"; Desc = "Reaction active indicator icon, reaction in progress, 32x32" },
    @{ Id = "status_complete"; Name = "Reaction Complete"; Desc = "Reaction complete indicator icon, reaction finished, 32x32" },
    @{ Id = "status_failed"; Name = "Reaction Failed"; Desc = "Reaction failed indicator icon, reaction failed, 32x32" },
    @{ Id = "status_incompatible"; Name = "Incompatible"; Desc = "Incompatible indicator icon, ingredients incompatible, 32x32" },
    @{ Id = "status_conditions_met"; Name = "Conditions Met"; Desc = "Conditions met indicator icon, reaction conditions satisfied, 32x32" },
    @{ Id = "status_conditions_not_met"; Name = "Conditions Not Met"; Desc = "Conditions not met indicator icon, reaction conditions not satisfied, 32x32" }
)

# Validate $ModPath before Join-Path
$statusOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $statusOutputDir)) {
    New-Item -ItemType Directory -Path $statusOutputDir -Force | Out-Null
}

foreach ($indicator in $reactionStatus) {
    Write-Host "Generating reaction status indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Reaction status indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $statusOutputDir
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
# 11. INGREDIENT STATE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Ingredient State Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$stateIndicators = @(
    @{ Id = "state_rust"; Name = "Rust State"; Desc = "Rust state indicator icon, rusted ingredient, 32x32" },
    @{ Id = "state_hot"; Name = "Hot State"; Desc = "Hot state indicator icon, heated ingredient, 32x32" },
    @{ Id = "state_cold"; Name = "Cold State"; Desc = "Cold state indicator icon, cooled ingredient, 32x32" },
    @{ Id = "state_wet"; Name = "Wet State"; Desc = "Wet state indicator icon, moist ingredient, 32x32" },
    @{ Id = "state_dry"; Name = "Dry State"; Desc = "Dry state indicator icon, dry ingredient, 32x32" },
    @{ Id = "state_charged"; Name = "Mana Charged"; Desc = "Mana charged indicator icon, mana charged ingredient, 32x32" },
    @{ Id = "state_active"; Name = "Active State"; Desc = "Active state indicator icon, active ingredient, 32x32" },
    @{ Id = "state_pure"; Name = "Pure State"; Desc = "Pure state indicator icon, pure ingredient, 32x32" },
    @{ Id = "state_contaminated"; Name = "Contaminated State"; Desc = "Contaminated state indicator icon, contaminated ingredient, 32x32" }
)

# Validate $ModPath before Join-Path
$stateOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stateOutputDir)) {
    New-Item -ItemType Directory -Path $stateOutputDir -Force | Out-Null
}

foreach ($indicator in $stateIndicators) {
    Write-Host "Generating state indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Ingredient state indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stateOutputDir
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
Write-Host "  Ingredients: $(Join-Path $ModPath 'assets\alchemy\ingredients')" -ForegroundColor Gray
Write-Host "  Phases: $(Join-Path $ModPath 'assets\alchemy\phases')" -ForegroundColor Gray
Write-Host "  Elements: $(Join-Path $ModPath 'assets\alchemy\elements')" -ForegroundColor Gray
Write-Host "  Materials: $(Join-Path $ModPath 'assets\alchemy\materials')" -ForegroundColor Gray
Write-Host "  Reaction Effects: $(Join-Path $ModPath 'assets\alchemy\reactions\effects')" -ForegroundColor Gray
Write-Host "  Grid: $(Join-Path $ModPath 'assets\alchemy\grid')" -ForegroundColor Gray
Write-Host "  Station UI: $(Join-Path $ModPath 'assets\alchemy\ui\station')" -ForegroundColor Gray
Write-Host "  Plants: $(Join-Path $ModPath 'assets\alchemy\plants')" -ForegroundColor Gray
Write-Host "  Environment: $(Join-Path $ModPath 'assets\alchemy\environment')" -ForegroundColor Gray
Write-Host "  Status: $(Join-Path $ModPath 'assets\alchemy\status')" -ForegroundColor Gray
Write-Host "  States: $(Join-Path $ModPath 'assets\alchemy\states')" -ForegroundColor Gray
Write-Host ""
