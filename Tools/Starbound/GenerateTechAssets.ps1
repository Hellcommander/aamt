#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Tech Module System.
    
.DESCRIPTION
    Generates sprites, icons, and effects for:
    - Tech module icons
    - Drone sprites
    - Sensor visual effects
    - Overclock visual effects
    - Field module effects
    - Energy core icons
    
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
Write-Host "  Tech Module System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. TECH MODULE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Tech Module Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$techModuleIcons = @(
    @{
        Id = "tech_module_icon"
        Name = "Tech Module Icon"
        Description = "Generic tech module icon, technological appearance, 32x32"
    },
    @{
        Id = "tech_module_drone"
        Name = "Drone Module Icon"
        Description = "Drone module icon, drone silhouette, 32x32"
    },
    @{
        Id = "tech_module_sensor"
        Name = "Sensor Module Icon"
        Description = "Sensor module icon, radar/sensor appearance, 32x32"
    },
    @{
        Id = "tech_module_field"
        Name = "Field Module Icon"
        Description = "Field module icon, field effect appearance, 32x32"
    },
    @{
        Id = "tech_module_overclock"
        Name = "Overclock Module Icon"
        Description = "Overclock module icon, speed/power appearance, 32x32"
    },
    @{
        Id = "tech_module_energy"
        Name = "Energy Module Icon"
        Description = "Energy module icon, energy/power appearance, 32x32"
    }
)

# Validate $ModPath before Join-Path
$techOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($techOutputDir)) {
    Write-Host "  [FAIL] techOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($techOutputDir)) {
    Write-Host "  [FAIL] techOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $techOutputDir)) {
    New-Item -ItemType Directory -Path $techOutputDir -Force | Out-Null
}

foreach ($icon in $techModuleIcons) {
    Write-Host "Generating module icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Tech module icon for Starbound UI."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
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
# 2. DRONE SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Drone Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$droneSprites = @(
    @{
        Id = "drone_basic"
        Name = "Basic Drone"
        Description = "Basic drone sprite, simple drone appearance, 32x32"
    },
    @{
        Id = "drone_combat"
        Name = "Combat Drone"
        Description = "Combat drone sprite, armed drone, weapon appearance, 32x32"
    },
    @{
        Id = "drone_repair"
        Name = "Repair Drone"
        Description = "Repair drone sprite, repair tool appearance, 32x32"
    },
    @{
        Id = "drone_scout"
        Name = "Scout Drone"
        Description = "Scout drone sprite, sensor appearance, 32x32"
    },
    @{
        Id = "drone_cargo"
        Name = "Cargo Drone"
        Description = "Cargo drone sprite, cargo container appearance, 32x32"
    },
    @{
        Id = "drone_mining"
        Name = "Mining Drone"
        Description = "Mining drone sprite, mining tool appearance, 32x32"
    }
)

foreach ($drone in $droneSprites) {
    Write-Host "Generating drone sprite: $($drone.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Sprite"
            AssetName = $drone.Id
            Prompt = "$($drone.Description). Drone sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($drone.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($drone.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SENSOR VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Sensor Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$sensorEffects = @(
    @{
        Id = "sensor_scan"
        Name = "Sensor Scan Effect"
        Description = "Sensor scan particle effect, radar sweep, scanning particles"
    },
    @{
        Id = "sensor_detection"
        Name = "Sensor Detection Effect"
        Description = "Sensor detection particle effect, detection pulse, alert particles"
    },
    @{
        Id = "sensor_range"
        Name = "Sensor Range Indicator"
        Description = "Sensor range indicator texture, circular range indicator, 64x64"
    }
)

foreach ($effect in $sensorEffects) {
    Write-Host "Generating sensor effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        if ($effect.Id -like "*particle*" -or $effect.Id -like "*effect*") {
            $assetType = "Particle"
        } else {
            $assetType = "Texture"
        }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Sensor visual effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
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
# 4. OVERCLOCK VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Overclock Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$overclockEffects = @(
    @{
        Id = "overclock_active"
        Name = "Overclock Active Effect"
        Description = "Overclock active particle effect, speed lines, power particles"
    },
    @{
        Id = "overclock_heat"
        Name = "Overclock Heat Effect"
        Description = "Overclock heat particle effect, heat waves, red/orange particles"
    },
    @{
        Id = "overclock_overheat"
        Name = "Overclock Overheat Effect"
        Description = "Overclock overheat particle effect, critical heat, warning particles"
    },
    @{
        Id = "overclock_heat_indicator"
        Name = "Overclock Heat Indicator"
        Description = "Overclock heat indicator texture, heat gauge, 32x32"
    }
)

foreach ($effect in $overclockEffects) {
    Write-Host "Generating overclock effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        if ($effect.Id -like "*indicator*") {
            $assetType = "Icon"
        } else {
            $assetType = "Particle"
        }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Overclock visual effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
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
# 5. FIELD MODULE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Field Module Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$fieldEffects = @(
    @{
        Id = "field_effect_shield"
        Name = "Shield Field Effect"
        Description = "Shield field particle effect, protective field, barrier particles"
    },
    @{
        Id = "field_effect_heal"
        Name = "Heal Field Effect"
        Description = "Heal field particle effect, healing field, green particles"
    },
    @{
        Id = "field_effect_damage"
        Name = "Damage Field Effect"
        Description = "Damage field particle effect, damage field, red particles"
    },
    @{
        Id = "field_effect_slow"
        Name = "Slow Field Effect"
        Description = "Slow field particle effect, slowing field, blue particles"
    },
    @{
        Id = "field_range_indicator"
        Name = "Field Range Indicator"
        Description = "Field range indicator texture, circular field range, 64x64"
    }
)

foreach ($effect in $fieldEffects) {
    Write-Host "Generating field effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        if ($effect.Id -like "*indicator*") {
            $assetType = "Texture"
        } else {
            $assetType = "Particle"
        }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Description). Field module effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
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
# 6. ENERGY CORE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Energy Core Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$energyCoreIcons = @(
    @{
        Id = "energy_core_icon"
        Name = "Energy Core Icon"
        Description = "Energy core icon, energy/power appearance, 32x32"
    },
    @{
        Id = "energy_core_full"
        Name = "Energy Core Full"
        Description = "Energy core full indicator, full energy, 32x32"
    },
    @{
        Id = "energy_core_empty"
        Name = "Energy Core Empty"
        Description = "Energy core empty indicator, empty energy, 32x32"
    },
    @{
        Id = "energy_core_charging"
        Name = "Energy Core Charging"
        Description = "Energy core charging indicator, charging energy, 32x32"
    }
)

foreach ($icon in $energyCoreIcons) {
    Write-Host "Generating energy core icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Description). Energy core icon for Starbound UI."
            OllamaModel = $OllamaModel
            OutputDir = $techOutputDir
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
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets\tech')" -ForegroundColor Gray
Write-Host ""
Write-Host "Module icons: assets/tech/tech_module_*.png" -ForegroundColor Gray
Write-Host "Drone sprites: assets/tech/drone_*.png" -ForegroundColor Gray
Write-Host "Sensor effects: assets/tech/sensor_*.png/.particle" -ForegroundColor Gray
Write-Host "Overclock effects: assets/tech/overclock_*.png/.particle" -ForegroundColor Gray
Write-Host "Field effects: assets/tech/field_*.png/.particle" -ForegroundColor Gray
Write-Host "Energy core icons: assets/tech/energy_core_*.png" -ForegroundColor Gray
Write-Host ""
