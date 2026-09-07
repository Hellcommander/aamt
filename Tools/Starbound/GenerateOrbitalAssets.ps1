#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the OrbitalWorldManager System.
    
.DESCRIPTION
    Generates visual assets for:
    - Planet icons
    - Atmospheric layer visuals
    - Entry trajectory visuals
    - Burnout effects
    - Plasma effects
    - Entry trail effects
    - Atmospheric scattering effects
    - Orbital UI elements
    - Entry status indicators
    - Layer transition effects
    - Heat indicators
    - Speed indicators
    - Altitude indicators
    - G-force indicators
    
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
Write-Host "  OrbitalWorldManager System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PLANET ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Planet Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$planets = @(
    @{ Id = "planet_terrestrial"; Name = "Terrestrial Planet"; Desc = "Terrestrial planet icon, rocky planet, 64x64" },
    @{ Id = "planet_gas_giant"; Name = "Gas Giant"; Desc = "Gas giant planet icon, gas giant, 64x64" },
    @{ Id = "planet_ice"; Name = "Ice Planet"; Desc = "Ice planet icon, icy planet, 64x64" },
    @{ Id = "planet_lava"; Name = "Lava Planet"; Desc = "Lava planet icon, volcanic planet, 64x64" },
    @{ Id = "planet_ocean"; Name = "Ocean Planet"; Desc = "Ocean planet icon, water world, 64x64" },
    @{ Id = "planet_barren"; Name = "Barren Planet"; Desc = "Barren planet icon, barren world, 64x64" }
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

foreach ($planet in $planets) {
    Write-Host "Generating planet icon: $($planet.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $planet.Id
            Prompt = "$($planet.Desc). Planet icon for Starbound."
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
# 2. ATMOSPHERIC LAYER VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Atmospheric Layer Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$atmosphericLayers = @(
    @{ Id = "layer_space"; Name = "Space Layer"; Desc = "Space atmospheric layer texture, space layer, 128x128" },
    @{ Id = "layer_exosphere"; Name = "Exosphere Layer"; Desc = "Exosphere atmospheric layer texture, exosphere layer, 128x128" },
    @{ Id = "layer_thermosphere"; Name = "Thermosphere Layer"; Desc = "Thermosphere atmospheric layer texture, thermosphere layer, 128x128" },
    @{ Id = "layer_mesosphere"; Name = "Mesosphere Layer"; Desc = "Mesosphere atmospheric layer texture, mesosphere layer, 128x128" },
    @{ Id = "layer_stratosphere"; Name = "Stratosphere Layer"; Desc = "Stratosphere atmospheric layer texture, stratosphere layer, 128x128" },
    @{ Id = "layer_troposphere"; Name = "Troposphere Layer"; Desc = "Troposphere atmospheric layer texture, troposphere layer, 128x128" }
)

# Validate $ModPath before Join-Path
$layerOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($layerOutputDir)) {
    Write-Host "  [FAIL] layerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($layerOutputDir)) {
    Write-Host "  [FAIL] layerOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $layerOutputDir)) {
    New-Item -ItemType Directory -Path $layerOutputDir -Force | Out-Null
}

foreach ($layer in $atmosphericLayers) {
    Write-Host "Generating atmospheric layer: $($layer.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $layer.Id
            Prompt = "$($layer.Desc). Atmospheric layer texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $layerOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($layer.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($layer.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. ENTRY TRAJECTORY VISUALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Entry Trajectory Visuals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$trajectoryVisuals = @(
    @{ Id = "trajectory_line"; Name = "Trajectory Line"; Desc = "Entry trajectory line texture, trajectory path, 256x8" },
    @{ Id = "trajectory_waypoint"; Name = "Trajectory Waypoint"; Desc = "Trajectory waypoint icon, waypoint marker, 32x32" },
    @{ Id = "trajectory_safe"; Name = "Safe Trajectory"; Desc = "Safe trajectory indicator icon, safe entry path, 32x32" },
    @{ Id = "trajectory_unsafe"; Name = "Unsafe Trajectory"; Desc = "Unsafe trajectory indicator icon, unsafe entry path, 32x32" },
    @{ Id = "trajectory_optimal"; Name = "Optimal Trajectory"; Desc = "Optimal trajectory indicator icon, optimal entry path, 32x32" }
)

# Validate $ModPath before Join-Path
$trajectoryOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($trajectoryOutputDir)) {
    Write-Host "  [FAIL] trajectoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($trajectoryOutputDir)) {
    Write-Host "  [FAIL] trajectoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $trajectoryOutputDir)) {
    New-Item -ItemType Directory -Path $trajectoryOutputDir -Force | Out-Null
}

foreach ($visual in $trajectoryVisuals) {
    Write-Host "Generating trajectory visual: $($visual.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($visual.Id -like "*line*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $visual.Id
            Prompt = "$($visual.Desc). Entry trajectory visual for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $trajectoryOutputDir
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
# 4. BURNOUT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Burnout Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$burnoutEffects = @(
    @{ Id = "burnout_start"; Name = "Burnout Start"; Desc = "Burnout start particle effect, burnout initiation visual, 64x64" },
    @{ Id = "burnout_active"; Name = "Burnout Active"; Desc = "Burnout active particle effect, active burnout visual, 64x64" },
    @{ Id = "burnout_end"; Name = "Burnout End"; Desc = "Burnout end particle effect, burnout completion visual, 64x64" },
    @{ Id = "burnout_critical"; Name = "Critical Burnout"; Desc = "Critical burnout particle effect, critical burnout visual, 64x64" }
)

# Validate $ModPath before Join-Path
$burnoutOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($burnoutOutputDir)) {
    Write-Host "  [FAIL] burnoutOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($burnoutOutputDir)) {
    Write-Host "  [FAIL] burnoutOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $burnoutOutputDir)) {
    New-Item -ItemType Directory -Path $burnoutOutputDir -Force | Out-Null
}

foreach ($effect in $burnoutEffects) {
    Write-Host "Generating burnout effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Burnout effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $burnoutOutputDir
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
# 5. PLASMA EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Plasma Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$plasmaEffects = @(
    @{ Id = "plasma_ionization"; Name = "Plasma Ionization"; Desc = "Plasma ionization particle effect, ionization visual, 64x64" },
    @{ Id = "plasma_glow"; Name = "Plasma Glow"; Desc = "Plasma glow particle effect, plasma glow visual, 64x64" },
    @{ Id = "plasma_trail"; Name = "Plasma Trail"; Desc = "Plasma trail particle effect, plasma trail visual, 128x32" },
    @{ Id = "plasma_intense"; Name = "Intense Plasma"; Desc = "Intense plasma particle effect, intense plasma visual, 64x64" }
)

# Validate $ModPath before Join-Path
$plasmaOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($plasmaOutputDir)) {
    Write-Host "  [FAIL] plasmaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($plasmaOutputDir)) {
    Write-Host "  [FAIL] plasmaOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $plasmaOutputDir)) {
    New-Item -ItemType Directory -Path $plasmaOutputDir -Force | Out-Null
}

foreach ($effect in $plasmaEffects) {
    Write-Host "Generating plasma effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Plasma effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $plasmaOutputDir
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
# 6. ENTRY TRAIL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Entry Trail Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$trailEffects = @(
    @{ Id = "trail_entry"; Name = "Entry Trail"; Desc = "Entry trail particle effect, entry trail visual, 128x32" },
    @{ Id = "trail_atmospheric"; Name = "Atmospheric Trail"; Desc = "Atmospheric trail particle effect, atmospheric trail visual, 128x32" },
    @{ Id = "trail_heat"; Name = "Heat Trail"; Desc = "Heat trail particle effect, heat trail visual, 128x32" },
    @{ Id = "trail_smoke"; Name = "Smoke Trail"; Desc = "Smoke trail particle effect, smoke trail visual, 128x32" }
)

# Validate $ModPath before Join-Path
$trailOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($trailOutputDir)) {
    Write-Host "  [FAIL] trailOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($trailOutputDir)) {
    Write-Host "  [FAIL] trailOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $trailOutputDir)) {
    New-Item -ItemType Directory -Path $trailOutputDir -Force | Out-Null
}

foreach ($effect in $trailEffects) {
    Write-Host "Generating trail effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Entry trail effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $trailOutputDir
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
# 7. ATMOSPHERIC SCATTERING EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Atmospheric Scattering Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$scatteringEffects = @(
    @{ Id = "scattering_light"; Name = "Light Scattering"; Desc = "Light scattering particle effect, atmospheric light scattering, 64x64" },
    @{ Id = "scattering_rayleigh"; Name = "Rayleigh Scattering"; Desc = "Rayleigh scattering particle effect, rayleigh scattering visual, 64x64" },
    @{ Id = "scattering_mie"; Name = "Mie Scattering"; Desc = "Mie scattering particle effect, mie scattering visual, 64x64" }
)

# Validate $ModPath before Join-Path
$scatteringOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($scatteringOutputDir)) {
    Write-Host "  [FAIL] scatteringOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($scatteringOutputDir)) {
    Write-Host "  [FAIL] scatteringOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $scatteringOutputDir)) {
    New-Item -ItemType Directory -Path $scatteringOutputDir -Force | Out-Null
}

foreach ($effect in $scatteringEffects) {
    Write-Host "Generating scattering effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Atmospheric scattering effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $scatteringOutputDir
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
# 8. ORBITAL UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Orbital UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$orbitalUI = @(
    @{ Id = "ui_panel_orbital"; Name = "Orbital Panel"; Desc = "Orbital panel background, orbital UI panel, 256x256" },
    @{ Id = "ui_panel_trajectory"; Name = "Trajectory Panel"; Desc = "Trajectory panel background, trajectory management panel, 128x128" },
    @{ Id = "ui_button_start_entry"; Name = "Start Entry Button"; Desc = "Start entry button icon, start orbital entry, 32x32" },
    @{ Id = "ui_button_cancel_entry"; Name = "Cancel Entry Button"; Desc = "Cancel entry button icon, cancel orbital entry, 32x32" },
    @{ Id = "ui_button_calculate_trajectory"; Name = "Calculate Trajectory Button"; Desc = "Calculate trajectory button icon, calculate entry path, 32x32" }
)

# Validate $ModPath before Join-Path
$orbitalUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($orbitalUIOutputDir)) {
    Write-Host "  [FAIL] orbitalUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($orbitalUIOutputDir)) {
    Write-Host "  [FAIL] orbitalUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $orbitalUIOutputDir)) {
    New-Item -ItemType Directory -Path $orbitalUIOutputDir -Force | Out-Null
}

foreach ($element in $orbitalUI) {
    Write-Host "Generating orbital UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*panel*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). Orbital UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $orbitalUIOutputDir
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
# 9. ENTRY STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Entry Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$statusIndicators = @(
    @{ Id = "status_entry_ready"; Name = "Entry Ready"; Desc = "Entry ready indicator icon, ready for entry, 32x32" },
    @{ Id = "status_entry_active"; Name = "Entry Active"; Desc = "Entry active indicator icon, entry in progress, 32x32" },
    @{ Id = "status_entry_complete"; Name = "Entry Complete"; Desc = "Entry complete indicator icon, entry finished, 32x32" },
    @{ Id = "status_entry_cancelled"; Name = "Entry Cancelled"; Desc = "Entry cancelled indicator icon, entry cancelled, 32x32" }
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

foreach ($indicator in $statusIndicators) {
    Write-Host "Generating status indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Entry status indicator for Starbound."
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
# 10. LAYER TRANSITION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Layer Transition Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$transitionEffects = @(
    @{ Id = "transition_layer"; Name = "Layer Transition"; Desc = "Layer transition particle effect, atmospheric layer transition, 64x64" },
    @{ Id = "transition_enter"; Name = "Enter Layer"; Desc = "Enter layer particle effect, entering layer visual, 64x64" },
    @{ Id = "transition_exit"; Name = "Exit Layer"; Desc = "Exit layer particle effect, exiting layer visual, 64x64" }
)

# Validate $ModPath before Join-Path
$transitionOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($transitionOutputDir)) {
    Write-Host "  [FAIL] transitionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($transitionOutputDir)) {
    Write-Host "  [FAIL] transitionOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $transitionOutputDir)) {
    New-Item -ItemType Directory -Path $transitionOutputDir -Force | Out-Null
}

foreach ($effect in $transitionEffects) {
    Write-Host "Generating transition effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Layer transition effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $transitionOutputDir
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
# 11. METRIC INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Metric Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$metricIndicators = @(
    @{ Id = "metric_heat"; Name = "Heat Indicator"; Desc = "Heat indicator icon, temperature display, 32x32" },
    @{ Id = "metric_speed"; Name = "Speed Indicator"; Desc = "Speed indicator icon, velocity display, 32x32" },
    @{ Id = "metric_altitude"; Name = "Altitude Indicator"; Desc = "Altitude indicator icon, height display, 32x32" },
    @{ Id = "metric_gforce"; Name = "G-Force Indicator"; Desc = "G-force indicator icon, acceleration display, 32x32" },
    @{ Id = "metric_drag"; Name = "Drag Indicator"; Desc = "Drag indicator icon, drag force display, 32x32" },
    @{ Id = "metric_ionization"; Name = "Ionization Indicator"; Desc = "Ionization indicator icon, plasma level display, 32x32" },
    @{ Id = "metric_bar_heat"; Name = "Heat Bar"; Desc = "Heat bar background texture, heat meter, 128x16" },
    @{ Id = "metric_bar_speed"; Name = "Speed Bar"; Desc = "Speed bar background texture, speed meter, 128x16" },
    @{ Id = "metric_bar_altitude"; Name = "Altitude Bar"; Desc = "Altitude bar background texture, altitude meter, 128x16" }
)

# Validate $ModPath before Join-Path
$metricOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($metricOutputDir)) {
    Write-Host "  [FAIL] metricOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($metricOutputDir)) {
    Write-Host "  [FAIL] metricOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $metricOutputDir)) {
    New-Item -ItemType Directory -Path $metricOutputDir -Force | Out-Null
}

foreach ($indicator in $metricIndicators) {
    Write-Host "Generating metric indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($indicator.Id -like "*bar*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Metric indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $metricOutputDir
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
Write-Host "  Planets: $(Join-Path $ModPath 'assets\orbital\planets')" -ForegroundColor Gray
Write-Host "  Atmospheric Layers: $(Join-Path $ModPath 'assets\orbital\atmosphere\layers')" -ForegroundColor Gray
Write-Host "  Trajectory: $(Join-Path $ModPath 'assets\orbital\trajectory')" -ForegroundColor Gray
Write-Host "  Burnout: $(Join-Path $ModPath 'assets\orbital\burnout')" -ForegroundColor Gray
Write-Host "  Plasma: $(Join-Path $ModPath 'assets\orbital\plasma')" -ForegroundColor Gray
Write-Host "  Trails: $(Join-Path $ModPath 'assets\orbital\trails')" -ForegroundColor Gray
Write-Host "  Scattering: $(Join-Path $ModPath 'assets\orbital\scattering')" -ForegroundColor Gray
Write-Host "  UI: $(Join-Path $ModPath 'assets\orbital\ui')" -ForegroundColor Gray
Write-Host "  Status: $(Join-Path $ModPath 'assets\orbital\status')" -ForegroundColor Gray
Write-Host "  Transitions: $(Join-Path $ModPath 'assets\orbital\transitions')" -ForegroundColor Gray
Write-Host "  Metrics: $(Join-Path $ModPath 'assets\orbital\metrics')" -ForegroundColor Gray
Write-Host ""
