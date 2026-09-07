#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Biome Generation System.
    
.DESCRIPTION
    Generates sprites, textures, icons, and effects for:
    - Island terrain tiles
    - Island features (caves, waterfalls, peaks, edges)
    - Island hazards
    - Vegetation sprites
    - Resource node icons
    - Ship spawn markers
    - Creature spawn markers
    - Building site markers
    - Atmospheric layer textures
    - Wind and turbulence effects
    - Entry/exit point markers
    - Atmospheric hazard effects
    
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
Write-Host "  Biome Generation System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. ISLAND TERRAIN TILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Island Terrain Tiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$islandTiles = @(
    @{ Id = "island_ground_stone"; Name = "Island Ground Stone"; Desc = "Seamless 16x16 stone ground tile for floating islands, grey/brown" },
    @{ Id = "island_ground_grass"; Name = "Island Ground Grass"; Desc = "Seamless 16x16 grass ground tile for floating islands, green" },
    @{ Id = "island_ground_dirt"; Name = "Island Ground Dirt"; Desc = "Seamless 16x16 dirt ground tile for floating islands, brown" },
    @{ Id = "island_ground_rock"; Name = "Island Ground Rock"; Desc = "Seamless 16x16 rock ground tile for floating islands, grey" },
    @{ Id = "island_surface_top"; Name = "Island Surface Top"; Desc = "Seamless 16x16 top surface tile for floating islands, grass/stone" },
    @{ Id = "island_surface_edge"; Name = "Island Surface Edge"; Desc = "Seamless 16x16 edge surface tile for floating islands, cliff edge" },
    @{ Id = "island_erosion_decal"; Name = "Island Erosion Decal"; Desc = "Erosion decal texture for floating islands, weathered look" }
)

# Validate $ModPath before Join-Path
$islandTileOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($islandTileOutputDir)) {
    Write-Host "  [FAIL] islandTileOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping island tile generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $islandTileOutputDir)) {
        New-Item -ItemType Directory -Path $islandTileOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($islandTileOutputDir)) {
    foreach ($tile in $islandTiles) {
        Write-Host "Generating island tile: $($tile.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "DungeonFloorTile"
                AssetName = $tile.Id
                Prompt = "$($tile.Desc). Terrain tile for Starbound floating islands."
                OllamaModel = $OllamaModel
                OutputDir = $islandTileOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""
    }
}

# ============================================================
# 2. ISLAND FEATURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Island Features" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$islandFeatures = @(
    @{ Id = "island_feature_cave"; Name = "Cave Feature"; Desc = "Cave entrance sprite for floating islands, 32x32" },
    @{ Id = "island_feature_waterfall"; Name = "Waterfall Feature"; Desc = "Waterfall sprite for floating islands, flowing water, 32x32" },
    @{ Id = "island_feature_peak"; Name = "Peak Feature"; Desc = "Mountain peak sprite for floating islands, rocky peak, 32x32" },
    @{ Id = "island_feature_edge"; Name = "Edge Feature"; Desc = "Cliff edge sprite for floating islands, steep drop, 32x32" }
)

# Validate $ModPath before Join-Path
$islandFeatureOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($islandFeatureOutputDir)) {
    Write-Host "  [FAIL] islandFeatureOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping island feature generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $islandFeatureOutputDir)) {
        New-Item -ItemType Directory -Path $islandFeatureOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($islandFeatureOutputDir)) {
    foreach ($feature in $islandFeatures) {
    Write-Host "Generating island feature: $($feature.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "DungeonDecorTile"
            AssetName = $feature.Id
            Prompt = "$($feature.Desc). Island feature sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $islandFeatureOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($feature.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($feature.Name) : $_" -ForegroundColor Red
    }
    
        Write-Host ""
    }
}

# ============================================================
# 3. ISLAND HAZARDS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Island Hazard Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$islandHazards = @(
    @{ Id = "island_hazard_unstable"; Name = "Unstable Ground Hazard"; Desc = "Unstable ground particle effect, shaking/cracking" },
    @{ Id = "island_hazard_low_gravity"; Name = "Low Gravity Hazard"; Desc = "Low gravity visual effect, floating particles" },
    @{ Id = "island_hazard_erosion"; Name = "Erosion Hazard"; Desc = "Erosion particle effect, crumbling debris" }
)

# Validate $ModPath before Join-Path
$islandHazardOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($islandHazardOutputDir)) {
    Write-Host "  [FAIL] islandHazardOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping island hazard generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $islandHazardOutputDir)) {
        New-Item -ItemType Directory -Path $islandHazardOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($islandHazardOutputDir)) {
    foreach ($hazard in $islandHazards) {
        Write-Host "Generating island hazard: $($hazard.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $hazard.Id
                Prompt = "$($hazard.Desc). Island hazard particle effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $islandHazardOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($hazard.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($hazard.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""`n    }`n}

# ============================================================
# 4. ISLAND VEGETATION
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Island Vegetation" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$islandVegetation = @(
    @{ Id = "island_vegetation_tree"; Name = "Island Tree"; Desc = "Floating island tree sprite, 32x32" },
    @{ Id = "island_vegetation_plant"; Name = "Island Plant"; Desc = "Floating island plant sprite, 16x16" },
    @{ Id = "island_vegetation_grass"; Name = "Island Grass"; Desc = "Floating island grass sprite, 8x8" },
    @{ Id = "island_vegetation_shrub"; Name = "Island Shrub"; Desc = "Floating island shrub sprite, 16x16" }
)

# Validate $ModPath before Join-Path
$islandVegetationOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($islandVegetationOutputDir)) {
    Write-Host "  [FAIL] islandVegetationOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping island vegetation generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $islandVegetationOutputDir)) {
        New-Item -ItemType Directory -Path $islandVegetationOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($islandVegetationOutputDir)) {
    foreach ($veg in $islandVegetation) {
    Write-Host "Generating island vegetation: $($veg.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "PlantSprite"
            AssetName = $veg.Id
            Prompt = "$($veg.Desc). Vegetation sprite for Starbound floating islands."
            OllamaModel = $OllamaModel
            OutputDir = $islandVegetationOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($veg.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($veg.Name) : $_" -ForegroundColor Red
    }
    
        Write-Host ""
    }
}

# ============================================================
# 5. RESOURCE NODE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Resource Node Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$resourceNodes = @(
    @{ Id = "resource_node_ore"; Name = "Ore Resource Node"; Desc = "Ore resource node icon, metallic, 32x32" },
    @{ Id = "resource_node_crystal"; Name = "Crystal Resource Node"; Desc = "Crystal resource node icon, gem-like, 32x32" },
    @{ Id = "resource_node_organic"; Name = "Organic Resource Node"; Desc = "Organic resource node icon, plant-based, 32x32" },
    @{ Id = "resource_node_energy"; Name = "Energy Resource Node"; Desc = "Energy resource node icon, glowing, 32x32" }
)

# Validate $ModPath before Join-Path
$resourceNodeOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($resourceNodeOutputDir)) {
    Write-Host "  [FAIL] resourceNodeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping resource node generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $resourceNodeOutputDir)) {
        New-Item -ItemType Directory -Path $resourceNodeOutputDir -Force | Out-Null
    }
}

    foreach ($node in $resourceNodes) {
        Write-Host "Generating resource node: $($node.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $node.Id
                Prompt = "$($node.Desc). Resource node icon for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $resourceNodeOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($node.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($node.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""`n    }`n}

# ============================================================
# 6. SPAWN MARKERS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Spawn Markers" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$spawnMarkers = @(
    @{ Id = "spawn_marker_ship"; Name = "Ship Spawn Marker"; Desc = "Ship spawn point marker icon, anchor/ship symbol, 32x32" },
    @{ Id = "spawn_marker_creature"; Name = "Creature Spawn Marker"; Desc = "Creature spawn point marker icon, creature symbol, 32x32" },
    @{ Id = "spawn_marker_building"; Name = "Building Site Marker"; Desc = "Building site marker icon, construction symbol, 32x32" }
)

# Validate $ModPath before Join-Path
$spawnMarkerOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($spawnMarkerOutputDir)) {
    Write-Host "  [FAIL] spawnMarkerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping spawn marker generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $spawnMarkerOutputDir)) {
        New-Item -ItemType Directory -Path $spawnMarkerOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($spawnMarkerOutputDir)) {
    foreach ($marker in $spawnMarkers) {
        Write-Host "Generating spawn marker: $($marker.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = $marker.Id
                Prompt = "$($marker.Desc). Spawn marker icon for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $spawnMarkerOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($marker.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($marker.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""`n    }`n}

# ============================================================
# 7. ATMOSPHERIC LAYER TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Atmospheric Layer Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$atmosphericLayers = @(
    @{ Id = "atmosphere_cloud_troposphere"; Name = "Troposphere Clouds"; Desc = "Cloud texture for troposphere layer, white fluffy clouds, 64x64" },
    @{ Id = "atmosphere_cloud_stratosphere"; Name = "Stratosphere Clouds"; Desc = "Cloud texture for stratosphere layer, thin wispy clouds, 64x64" },
    @{ Id = "atmosphere_sky_low"; Name = "Low Altitude Sky"; Desc = "Sky texture for low altitude, blue sky, 64x64" },
    @{ Id = "atmosphere_sky_high"; Name = "High Altitude Sky"; Desc = "Sky texture for high altitude, dark blue/black, 64x64" },
    @{ Id = "atmosphere_fog"; Name = "Atmospheric Fog"; Desc = "Fog texture for atmospheric layers, white/grey mist, 64x64" }
)

# Validate $ModPath before Join-Path
$atmosphericOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($atmosphericOutputDir)) {
    Write-Host "  [FAIL] atmosphericOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping atmospheric layer generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $atmosphericOutputDir)) {
        New-Item -ItemType Directory -Path $atmosphericOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($atmosphericOutputDir)) {
    foreach ($layer in $atmosphericLayers) {
        Write-Host "Generating atmospheric texture: $($layer.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Texture"
                AssetName = $layer.Id
                Prompt = "$($layer.Desc). Atmospheric texture for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $atmosphericOutputDir
            }
            
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            
            $generated++
            Write-Host "  [OK] Generated: $($layer.Name)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] $($layer.Name) : $_" -ForegroundColor Red
        }
        
        Write-Host ""`n    }`n}

# ============================================================
# 8. WIND AND TURBULENCE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wind and Turbulence Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$windEffects = @(
    @{ Id = "wind_effect_light"; Name = "Light Wind Effect"; Desc = "Light wind particle effect, gentle breeze" },
    @{ Id = "wind_effect_medium"; Name = "Medium Wind Effect"; Desc = "Medium wind particle effect, moderate breeze" },
    @{ Id = "wind_effect_strong"; Name = "Strong Wind Effect"; Desc = "Strong wind particle effect, strong gusts" },
    @{ Id = "turbulence_effect_light"; Name = "Light Turbulence Effect"; Desc = "Light turbulence particle effect, minor air disturbance" },
    @{ Id = "turbulence_effect_medium"; Name = "Medium Turbulence Effect"; Desc = "Medium turbulence particle effect, moderate air disturbance" },
    @{ Id = "turbulence_effect_strong"; Name = "Strong Turbulence Effect"; Desc = "Strong turbulence particle effect, severe air disturbance" }
)

foreach ($effect in $windEffects) {
    Write-Host "Generating wind/turbulence effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Wind/turbulence particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $atmosphericOutputDir
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
# 9. ENTRY/EXIT POINT MARKERS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Entry/Exit Point Markers" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$entryExitMarkers = @(
    @{ Id = "entry_point_marker"; Name = "Entry Point Marker"; Desc = "Atmospheric entry point marker icon, entry symbol, 32x32" },
    @{ Id = "exit_point_marker"; Name = "Exit Point Marker"; Desc = "Atmospheric exit point marker icon, exit symbol, 32x32" }
)

foreach ($marker in $entryExitMarkers) {
    Write-Host "Generating entry/exit marker: $($marker.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $marker.Id
            Prompt = "$($marker.Desc). Entry/exit marker icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $spawnMarkerOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($marker.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($marker.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 10. ATMOSPHERIC HAZARD EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Atmospheric Hazard Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$atmosphericHazards = @(
    @{ Id = "atmosphere_hazard_storm"; Name = "Storm Hazard"; Desc = "Atmospheric storm particle effect, lightning and rain" },
    @{ Id = "atmosphere_hazard_wind_shear"; Name = "Wind Shear Hazard"; Desc = "Wind shear particle effect, dangerous air currents" },
    @{ Id = "atmosphere_hazard_void"; Name = "Void Hazard"; Desc = "Void atmospheric hazard particle effect, dark void" },
    @{ Id = "atmosphere_hazard_toxic"; Name = "Toxic Atmosphere Hazard"; Desc = "Toxic atmosphere particle effect, green/yellow toxic gas" }
)

foreach ($hazard in $atmosphericHazards) {
    Write-Host "Generating atmospheric hazard: $($hazard.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $hazard.Id
            Prompt = "$($hazard.Desc). Atmospheric hazard particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $atmosphericOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($hazard.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($hazard.Name) : $_" -ForegroundColor Red
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
Write-Host "  Island Tiles: $(Join-Path $ModPath 'assets\biomes\islands\tiles')" -ForegroundColor Gray
Write-Host "  Island Features: $(Join-Path $ModPath 'assets\biomes\islands\features')" -ForegroundColor Gray
Write-Host "  Island Hazards: $(Join-Path $ModPath 'assets\biomes\islands\hazards')" -ForegroundColor Gray
Write-Host "  Island Vegetation: $(Join-Path $ModPath 'assets\biomes\islands\vegetation')" -ForegroundColor Gray
Write-Host "  Resource Nodes: $(Join-Path $ModPath 'assets\biomes\resources')" -ForegroundColor Gray
Write-Host "  Spawn Markers: $(Join-Path $ModPath 'assets\biomes\markers')" -ForegroundColor Gray
Write-Host "  Atmospheric Textures: $(Join-Path $ModPath 'assets\biomes\atmosphere')" -ForegroundColor Gray
Write-Host ""
