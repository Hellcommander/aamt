#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Anomaly Systems.
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Black hole effects
    - Wormhole gates
    - Quantum fluctuations
    - Gravity wells
    - Gamma ray bursts
    - Event horizons
    - Dust clouds
    - Accretion disks
    
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
Write-Host "  Anomaly System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. BLACK HOLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Black Hole Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$blackHoleEffects = @(
    @{ Id = "blackhole_core"; Name = "Black Hole Core"; Desc = "Black hole core sprite, dark void center, 64x64" },
    @{ Id = "blackhole_event_horizon"; Name = "Event Horizon"; Desc = "Black hole event horizon particle effect, gravitational distortion" },
    @{ Id = "blackhole_pull_effect"; Name = "Gravitational Pull"; Desc = "Black hole gravitational pull particle effect, matter being pulled" },
    @{ Id = "blackhole_consume"; Name = "Consume Effect"; Desc = "Black hole consume particle effect, entity being consumed" },
    @{ Id = "blackhole_lensing"; Name = "Gravitational Lensing"; Desc = "Black hole gravitational lensing effect, light distortion" }
)

# Validate $ModPath before Join-Path
$blackHoleOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($blackHoleOutputDir)) {
    Write-Host "  [FAIL] blackHoleOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping black hole effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $blackHoleOutputDir)) {
        try {
            New-Item -ItemType Directory -Path $blackHoleOutputDir -Force | Out-Null
        } catch {
            Write-Host "  [FAIL] Cannot create directory '$blackHoleOutputDir': $_" -ForegroundColor Red
            $blackHoleOutputDir = $null
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($blackHoleOutputDir)) {
    foreach ($effect in $blackHoleEffects) {
        Write-Host "Generating black hole effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($effect.Id -like "*core*") { "Sprite" } else { "Particle" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Black hole effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $blackHoleOutputDir
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
}

# ============================================================
# 2. WORMHOLE GATE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wormhole Gate Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wormholeEffects = @(
    @{ Id = "wormhole_gate_sprite"; Name = "Wormhole Gate"; Desc = "Wormhole gate sprite, portal gate, 64x64" },
    @{ Id = "wormhole_portal_effect"; Name = "Portal Effect"; Desc = "Wormhole portal particle effect, active portal" },
    @{ Id = "wormhole_warp_effect"; Name = "Warp Effect"; Desc = "Wormhole warp particle effect, entity warping" },
    @{ Id = "wormhole_connection"; Name = "Connection Line"; Desc = "Wormhole connection visual effect, gate connection" }
)

# Validate $ModPath before Join-Path
$wormholeOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($wormholeOutputDir)) {
    Write-Host "  [FAIL] wormholeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping wormhole effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $wormholeOutputDir)) {
        New-Item -ItemType Directory -Path $wormholeOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($wormholeOutputDir)) {
    foreach ($effect in $wormholeEffects) {
    Write-Host "Generating wormhole effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($effect.Id -like "*sprite*") { "Sprite" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Wormhole effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $wormholeOutputDir
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
}

# ============================================================
# 3. QUANTUM FLUCTUATION EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Quantum Fluctuation Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$quantumEffects = @(
    @{ Id = "quantum_fluctuation_particle"; Name = "Quantum Fluctuation"; Desc = "Quantum fluctuation particle effect, quantum instability" },
    @{ Id = "quantum_teleport"; Name = "Quantum Teleport"; Desc = "Quantum teleport particle effect, entity teleporting" },
    @{ Id = "quantum_swap"; Name = "Quantum Swap"; Desc = "Quantum swap particle effect, entities swapping" },
    @{ Id = "quantum_invert"; Name = "Quantum Invert"; Desc = "Quantum invert particle effect, control inversion" }
)

# Validate $ModPath before Join-Path
$quantumOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($quantumOutputDir)) {
    Write-Host "  [FAIL] quantumOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping quantum effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $quantumOutputDir)) {
        New-Item -ItemType Directory -Path $quantumOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($quantumOutputDir)) {
    foreach ($effect in $quantumEffects) {
        Write-Host "Generating quantum effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Quantum fluctuation effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $quantumOutputDir
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
}

# ============================================================
# 4. GRAVITY WELL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Gravity Well Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$gravityWellEffects = @(
    @{ Id = "gravity_well_visual"; Name = "Gravity Well Visual"; Desc = "Gravity well visual sprite, gravitational anomaly, 64x64" },
    @{ Id = "gravity_well_distortion"; Name = "Gravity Distortion"; Desc = "Gravity well distortion particle effect, space distortion" },
    @{ Id = "gravity_well_pull"; Name = "Gravity Pull"; Desc = "Gravity well pull particle effect, matter being pulled" }
)

# Validate $ModPath before Join-Path
$gravityWellOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($gravityWellOutputDir)) {
    Write-Host "  [FAIL] gravityWellOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping gravity well effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $gravityWellOutputDir)) {
        New-Item -ItemType Directory -Path $gravityWellOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($gravityWellOutputDir)) {
    foreach ($effect in $gravityWellEffects) {
    Write-Host "Generating gravity well effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($effect.Id -like "*visual*") { "Sprite" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Gravity well effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $gravityWellOutputDir
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
}

# ============================================================
# 5. GAMMA RAY BURST EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Gamma Ray Burst Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$gammaRayEffects = @(
    @{ Id = "gamma_ray_burst_projectile"; Name = "Gamma Ray Projectile"; Desc = "Gamma ray burst projectile sprite, gamma ray beam, 32x32" },
    @{ Id = "gamma_ray_burst_effect"; Name = "Gamma Ray Burst"; Desc = "Gamma ray burst particle effect, burst explosion" },
    @{ Id = "gamma_ray_trail"; Name = "Gamma Ray Trail"; Desc = "Gamma ray trail particle effect, beam trail" },
    @{ Id = "gamma_ray_impact"; Name = "Gamma Ray Impact"; Desc = "Gamma ray impact particle effect, ray impact" }
)

# Validate $ModPath before Join-Path
$gammaRayOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($gammaRayOutputDir)) {
    Write-Host "  [FAIL] gammaRayOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping gamma ray effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $gammaRayOutputDir)) {
        New-Item -ItemType Directory -Path $gammaRayOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($gammaRayOutputDir)) {
    foreach ($effect in $gammaRayEffects) {
        Write-Host "Generating gamma ray effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($effect.Id -like "*projectile*") { "Sprite" } else { "Particle" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Gamma ray burst effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $gammaRayOutputDir
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
}

# ============================================================
# 6. EVENT HORIZON EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Event Horizon Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$eventHorizonEffects = @(
    @{ Id = "event_horizon_distortion"; Name = "Event Horizon Distortion"; Desc = "Event horizon distortion particle effect, space-time distortion" },
    @{ Id = "event_horizon_screen_effect"; Name = "Screen Distortion"; Desc = "Event horizon screen distortion effect, visual distortion" },
    @{ Id = "event_horizon_entity_distortion"; Name = "Entity Distortion"; Desc = "Event horizon entity distortion effect, entity visual distortion" }
)

# Validate $ModPath before Join-Path
$eventHorizonOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($eventHorizonOutputDir)) {
    Write-Host "  [FAIL] eventHorizonOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping event horizon effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $eventHorizonOutputDir)) {
        New-Item -ItemType Directory -Path $eventHorizonOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($eventHorizonOutputDir)) {
    foreach ($effect in $eventHorizonEffects) {
    Write-Host "Generating event horizon effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Event horizon effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $eventHorizonOutputDir
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
}

# ============================================================
# 7. DUST CLOUD EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Dust Cloud Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$dustCloudEffects = @(
    @{ Id = "dust_cloud_particle"; Name = "Dust Cloud Particle"; Desc = "Dust cloud particle effect, floating dust particles" },
    @{ Id = "dust_cloud_texture"; Name = "Dust Cloud Texture"; Desc = "Dust cloud texture, cloud texture, 64x64" },
    @{ Id = "dust_cloud_status"; Name = "Dust Cloud Status"; Desc = "Dust cloud status effect, entity in dust cloud" }
)

# Validate $ModPath before Join-Path
$dustCloudOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($dustCloudOutputDir)) {
    Write-Host "  [FAIL] dustCloudOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping dust cloud effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $dustCloudOutputDir)) {
        New-Item -ItemType Directory -Path $dustCloudOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($dustCloudOutputDir)) {
    foreach ($effect in $dustCloudEffects) {
        Write-Host "Generating dust cloud effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($effect.Id -like "*texture*") { "Texture" } elseif ($effect.Id -like "*status*") { "Particle" } else { "Particle" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Dust cloud effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $dustCloudOutputDir
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
}

# ============================================================
# 8. ACCRETION DISK EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Accretion Disk Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$accretionDiskEffects = @(
    @{ Id = "accretion_disk_particle"; Name = "Accretion Disk Particle"; Desc = "Accretion disk particle effect, rotating matter particles" },
    @{ Id = "accretion_disk_visual"; Name = "Accretion Disk Visual"; Desc = "Accretion disk visual sprite, rotating disk, 128x128" },
    @{ Id = "accretion_disk_glow"; Name = "Accretion Disk Glow"; Desc = "Accretion disk glow particle effect, disk glow effect" }
)

# Validate $ModPath before Join-Path
$accretionDiskOutputDir = Join-Path $ModPath "assets"
if ([string]::IsNullOrWhiteSpace($accretionDiskOutputDir)) {
    Write-Host "  [FAIL] accretionDiskOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    Write-Host "  Skipping accretion disk effect generation" -ForegroundColor Yellow
} else {
    if (-not (Test-Path $accretionDiskOutputDir)) {
        New-Item -ItemType Directory -Path $accretionDiskOutputDir -Force | Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($accretionDiskOutputDir)) {
    foreach ($effect in $accretionDiskEffects) {
        Write-Host "Generating accretion disk effect: $($effect.Name)" -ForegroundColor Cyan
        
        try {
            $assetType = if ($effect.Id -like "*visual*") { "Sprite" } else { "Particle" }
            
            $params = @{
                AssetType = $assetType
                AssetName = $effect.Id
                Prompt = "$($effect.Desc). Accretion disk effect for Starbound."
                OllamaModel = $OllamaModel
                OutputDir = $accretionDiskOutputDir
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
Write-Host "  Black Hole: $(Join-Path $ModPath 'assets\anomalies\blackhole')" -ForegroundColor Gray
Write-Host "  Wormhole: $(Join-Path $ModPath 'assets\anomalies\wormhole')" -ForegroundColor Gray
Write-Host "  Quantum: $(Join-Path $ModPath 'assets\anomalies\quantum')" -ForegroundColor Gray
Write-Host "  Gravity Well: $(Join-Path $ModPath 'assets\anomalies\gravity_well')" -ForegroundColor Gray
Write-Host "  Gamma Ray: $(Join-Path $ModPath 'assets\anomalies\gamma_ray')" -ForegroundColor Gray
Write-Host "  Event Horizon: $(Join-Path $ModPath 'assets\anomalies\event_horizon')" -ForegroundColor Gray
Write-Host "  Dust Cloud: $(Join-Path $ModPath 'assets\anomalies\dust_cloud')" -ForegroundColor Gray
Write-Host "  Accretion Disk: $(Join-Path $ModPath 'assets\anomalies\accretion_disk')" -ForegroundColor Gray
Write-Host ""
