#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Star System.
    
.DESCRIPTION
    Generates sprites, icons, and textures for:
    - Star type icons
    - Planet icons
    - Star map textures
    - Galaxy visualization assets
    
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
Write-Host "  Star System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. STAR TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Star Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$starTypes = @(
    @{ Id = "star_yellow_dwarf"; Name = "Yellow Dwarf Star"; Desc = "Yellow dwarf star icon, yellow sun-like star, 32x32" },
    @{ Id = "star_red_giant"; Name = "Red Giant Star"; Desc = "Red giant star icon, large red star, 32x32" },
    @{ Id = "star_white_dwarf"; Name = "White Dwarf Star"; Desc = "White dwarf star icon, small white star, 32x32" },
    @{ Id = "star_neutron"; Name = "Neutron Star"; Desc = "Neutron star icon, dense neutron star, 32x32" },
    @{ Id = "star_black_hole"; Name = "Black Hole"; Desc = "Black hole icon, dark void with accretion disk, 32x32" }
)

# Validate ModPath before creating output directory
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "  [FAIL] Cannot generate star icons: ModPath is null or empty" -ForegroundColor Red
    exit 1
}

# Validate $ModPath before Join-Path
$starOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($starOutputDir)) {
    Write-Host "  [FAIL] starOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($starOutputDir)) {
    Write-Host "  [FAIL] starOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if ([string]::IsNullOrWhiteSpace($starOutputDir)) {
    Write-Host "  [FAIL] Cannot create output directory: ModPath resulted in null path" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $starOutputDir)) {
    try {
        New-Item -ItemType Directory -Path $starOutputDir -Force | Out-Null
    } catch {
        Write-Host "  [FAIL] Cannot create directory '$starOutputDir': $_" -ForegroundColor Red
        exit 1
    }
}

foreach ($star in $starTypes) {
    Write-Host "Generating star icon: $($star.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "StarIcon"
            AssetName = $star.Id
            Prompt = "$($star.Desc). Star icon for Starbound star system."
            OllamaModel = $OllamaModel
            OutputDir = $starOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($star.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($star.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. PLANET ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Planet Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$planetTypes = @(
    @{ Id = "planet_terrestrial"; Name = "Terrestrial Planet"; Desc = "Terrestrial planet icon, rocky planet, 32x32" },
    @{ Id = "planet_gas_giant"; Name = "Gas Giant Planet"; Desc = "Gas giant planet icon, large gas planet, 32x32" },
    @{ Id = "planet_ice_giant"; Name = "Ice Giant Planet"; Desc = "Ice giant planet icon, icy gas planet, 32x32" },
    @{ Id = "planet_dwarf"; Name = "Dwarf Planet"; Desc = "Dwarf planet icon, small rocky planet, 32x32" },
    @{ Id = "planet_barren"; Name = "Barren Planet"; Desc = "Barren planet icon, lifeless planet, 32x32" },
    @{ Id = "planet_ocean"; Name = "Ocean Planet"; Desc = "Ocean planet icon, water-covered planet, 32x32" },
    @{ Id = "planet_desert"; Name = "Desert Planet"; Desc = "Desert planet icon, sandy planet, 32x32" },
    @{ Id = "planet_forest"; Name = "Forest Planet"; Desc = "Forest planet icon, forest-covered planet, 32x32" }
)

# Validate $ModPath before Join-Path
$planetOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($planetOutputDir)) {
    Write-Host "  [FAIL] planetOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($planetOutputDir)) {
    Write-Host "  [FAIL] planetOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $planetOutputDir)) {
    New-Item -ItemType Directory -Path $planetOutputDir -Force | Out-Null
}

foreach ($planet in $planetTypes) {
    Write-Host "Generating planet icon: $($planet.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "PlanetIcon"
            AssetName = $planet.Id
            Prompt = "$($planet.Desc). Planet icon for Starbound star system."
            OllamaModel = $OllamaModel
            OutputDir = $planetOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($planet.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($planet.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. STAR MAP TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Star Map Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$starMapTextures = @(
    @{ Id = "starmap_background"; Name = "Star Map Background"; Desc = "Star map background texture, space background, 256x256" },
    @{ Id = "starmap_grid"; Name = "Star Map Grid"; Desc = "Star map grid texture, navigation grid, 256x256" },
    @{ Id = "starmap_nebula"; Name = "Nebula Texture"; Desc = "Nebula texture for star map, colorful nebula clouds, 256x256" },
    @{ Id = "starmap_connection_line"; Name = "Connection Line"; Desc = "Star system connection line texture, navigation path, 32x4" }
)

# Validate $ModPath before Join-Path
$starmapOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($starmapOutputDir)) {
    Write-Host "  [FAIL] starmapOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($starmapOutputDir)) {
    Write-Host "  [FAIL] starmapOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if ([string]::IsNullOrWhiteSpace($starmapOutputDir)) {
    Write-Host "  [FAIL] Cannot create starmap output directory: ModPath resulted in null path" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $starmapOutputDir)) {
    try {
        New-Item -ItemType Directory -Path $starmapOutputDir -Force | Out-Null
    } catch {
        Write-Host "  [FAIL] Cannot create directory '$starmapOutputDir': $_" -ForegroundColor Red
        exit 1
    }
}

foreach ($texture in $starMapTextures) {
    Write-Host "Generating star map texture: $($texture.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $texture.Id
            Prompt = "$($texture.Desc). Star map texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $starmapOutputDir
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
Write-Host "  Stars: $(Join-Path $ModPath 'assets\stars')" -ForegroundColor Gray
Write-Host "  Planets: $(Join-Path $ModPath 'assets\planets')" -ForegroundColor Gray
Write-Host "  Star Map: $(Join-Path $ModPath 'assets\starmap')" -ForegroundColor Gray
Write-Host ""
Write-Host "Star icons: assets/stars/star_*.png" -ForegroundColor Gray
Write-Host "Planet icons: assets/planets/planet_*.png" -ForegroundColor Gray
Write-Host "Star map textures: assets/starmap/starmap_*.png" -ForegroundColor Gray
Write-Host ""
