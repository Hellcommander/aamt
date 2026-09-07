#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Ship Steering System.
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Thruster/engine effects
    - Weapon projectiles
    - Shield visual effects
    - Landing/takeoff effects
    - Hazard warning indicators
    - Combat impact effects
    - Steering indicators
    
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
Write-Host "  Ship Steering System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. THRUSTER/ENGINE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Thruster/Engine Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$thrusterEffects = @(
    @{ Id = "thruster_exhaust_chemical"; Name = "Chemical Thruster Exhaust"; Desc = "Chemical thruster exhaust particle effect, orange/yellow flame" },
    @{ Id = "thruster_exhaust_nuclear"; Name = "Nuclear Thruster Exhaust"; Desc = "Nuclear thruster exhaust particle effect, blue/white energy" },
    @{ Id = "thruster_exhaust_ion"; Name = "Ion Thruster Exhaust"; Desc = "Ion thruster exhaust particle effect, blue/purple ion stream" },
    @{ Id = "thruster_exhaust_plasma"; Name = "Plasma Thruster Exhaust"; Desc = "Plasma thruster exhaust particle effect, purple/pink plasma" },
    @{ Id = "thruster_exhaust_fusion"; Name = "Fusion Thruster Exhaust"; Desc = "Fusion thruster exhaust particle effect, white/blue fusion energy" },
    @{ Id = "thruster_trail"; Name = "Thruster Trail"; Desc = "Thruster trail particle effect, exhaust trail" },
    @{ Id = "engine_afterburner"; Name = "Afterburner Effect"; Desc = "Afterburner particle effect, intense flame burst" }
)

# Validate $ModPath before Join-Path
$thrusterOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($thrusterOutputDir)) {
    Write-Host "  [FAIL] thrusterOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($thrusterOutputDir)) {
    Write-Host "  [FAIL] thrusterOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $thrusterOutputDir)) {
    New-Item -ItemType Directory -Path $thrusterOutputDir -Force | Out-Null
}

foreach ($effect in $thrusterEffects) {
    Write-Host "Generating thruster effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Thruster effect for Starbound ship steering."
            OllamaModel = $OllamaModel
            OutputDir = $thrusterOutputDir
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
# 2. WEAPON PROJECTILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Weapon Projectiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$weaponProjectiles = @(
    @{ Id = "projectile_laser"; Name = "Laser Projectile"; Desc = "Laser projectile sprite, red energy beam, 32x32" },
    @{ Id = "projectile_plasma"; Name = "Plasma Projectile"; Desc = "Plasma projectile sprite, purple/pink plasma, 32x32" },
    @{ Id = "projectile_missile"; Name = "Missile Projectile"; Desc = "Missile projectile sprite, rocket with trail, 32x32" },
    @{ Id = "projectile_kinetic"; Name = "Kinetic Projectile"; Desc = "Kinetic projectile sprite, bullet/shell, 32x32" },
    @{ Id = "projectile_ion"; Name = "Ion Projectile"; Desc = "Ion projectile sprite, blue/purple ion, 32x32" },
    @{ Id = "projectile_emp"; Name = "EMP Projectile"; Desc = "EMP projectile sprite, electrical energy, 32x32" },
    @{ Id = "projectile_torpedo"; Name = "Torpedo Projectile"; Desc = "Torpedo projectile sprite, large explosive, 64x64" },
    @{ Id = "projectile_beam"; Name = "Beam Projectile"; Desc = "Beam projectile sprite, continuous energy beam, 32x32" }
)

# Validate $ModPath before Join-Path
$weaponOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($weaponOutputDir)) {
    Write-Host "  [FAIL] weaponOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($weaponOutputDir)) {
    Write-Host "  [FAIL] weaponOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $weaponOutputDir)) {
    New-Item -ItemType Directory -Path $weaponOutputDir -Force | Out-Null
}

foreach ($proj in $weaponProjectiles) {
    Write-Host "Generating weapon projectile: $($proj.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $proj.Id
            Prompt = "$($proj.Desc). Weapon projectile for Starbound ship combat."
            OllamaModel = $OllamaModel
            OutputDir = $weaponOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($proj.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($proj.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SHIELD VISUAL EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Shield Visual Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$shieldEffects = @(
    @{ Id = "shield_active"; Name = "Active Shield"; Desc = "Active shield particle effect, energy barrier" },
    @{ Id = "shield_hit"; Name = "Shield Hit"; Desc = "Shield hit particle effect, impact on shield" },
    @{ Id = "shield_regen"; Name = "Shield Regeneration"; Desc = "Shield regeneration particle effect, energy rebuilding" },
    @{ Id = "shield_depleted"; Name = "Shield Depleted"; Desc = "Shield depleted particle effect, shield failure" }
)

# Validate $ModPath before Join-Path
$shieldOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($shieldOutputDir)) {
    Write-Host "  [FAIL] shieldOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($shieldOutputDir)) {
    Write-Host "  [FAIL] shieldOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $shieldOutputDir)) {
    New-Item -ItemType Directory -Path $shieldOutputDir -Force | Out-Null
}

foreach ($effect in $shieldEffects) {
    Write-Host "Generating shield effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Shield effect for Starbound ship combat."
            OllamaModel = $OllamaModel
            OutputDir = $shieldOutputDir
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
# 4. LANDING/TAKEOFF EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Landing/Takeoff Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$landingEffects = @(
    @{ Id = "landing_effect"; Name = "Landing Effect"; Desc = "Landing particle effect, dust/debris on landing" },
    @{ Id = "takeoff_effect"; Name = "Takeoff Effect"; Desc = "Takeoff particle effect, exhaust and dust on takeoff" },
    @{ Id = "landing_zone_marker"; Name = "Landing Zone Marker"; Desc = "Landing zone marker icon, landing target, 32x32" }
)

# Validate $ModPath before Join-Path
$landingOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($landingOutputDir)) {
    Write-Host "  [FAIL] landingOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($landingOutputDir)) {
    Write-Host "  [FAIL] landingOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $landingOutputDir)) {
    New-Item -ItemType Directory -Path $landingOutputDir -Force | Out-Null
}

foreach ($effect in $landingEffects) {
    Write-Host "Generating landing effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($effect.Id -eq "landing_zone_marker") { "Icon" } else { "Particle" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Landing/takeoff effect for Starbound ship steering."
            OllamaModel = $OllamaModel
            OutputDir = $landingOutputDir
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
# 5. HAZARD WARNING INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Hazard Warning Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$hazardIndicators = @(
    @{ Id = "hazard_warning_low"; Name = "Low Hazard Warning"; Desc = "Low hazard warning icon, yellow warning, 32x32" },
    @{ Id = "hazard_warning_medium"; Name = "Medium Hazard Warning"; Desc = "Medium hazard warning icon, orange warning, 32x32" },
    @{ Id = "hazard_warning_high"; Name = "High Hazard Warning"; Desc = "High hazard warning icon, red warning, 32x32" },
    @{ Id = "hazard_warning_critical"; Name = "Critical Hazard Warning"; Desc = "Critical hazard warning icon, red flashing, 32x32" },
    @{ Id = "hazard_effect"; Name = "Hazard Effect"; Desc = "Hazard particle effect, dangerous area warning" }
)

# Validate $ModPath before Join-Path
$hazardOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($hazardOutputDir)) {
    Write-Host "  [FAIL] hazardOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($hazardOutputDir)) {
    Write-Host "  [FAIL] hazardOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $hazardOutputDir)) {
    New-Item -ItemType Directory -Path $hazardOutputDir -Force | Out-Null
}

foreach ($hazard in $hazardIndicators) {
    Write-Host "Generating hazard indicator: $($hazard.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($hazard.Id -eq "hazard_effect") { "Particle" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $hazard.Id
            Prompt = "$($hazard.Desc). Hazard indicator for Starbound ship steering."
            OllamaModel = $OllamaModel
            OutputDir = $hazardOutputDir
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
# 6. COMBAT IMPACT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Combat Impact Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$impactEffects = @(
    @{ Id = "impact_laser"; Name = "Laser Impact"; Desc = "Laser impact particle effect, energy explosion" },
    @{ Id = "impact_plasma"; Name = "Plasma Impact"; Desc = "Plasma impact particle effect, plasma explosion" },
    @{ Id = "impact_missile"; Name = "Missile Impact"; Desc = "Missile impact particle effect, explosive burst" },
    @{ Id = "impact_kinetic"; Name = "Kinetic Impact"; Desc = "Kinetic impact particle effect, bullet impact" },
    @{ Id = "impact_ion"; Name = "Ion Impact"; Desc = "Ion impact particle effect, ion burst" },
    @{ Id = "impact_emp"; Name = "EMP Impact"; Desc = "EMP impact particle effect, electrical burst" },
    @{ Id = "impact_torpedo"; Name = "Torpedo Impact"; Desc = "Torpedo impact particle effect, large explosion" },
    @{ Id = "impact_beam"; Name = "Beam Impact"; Desc = "Beam impact particle effect, continuous energy impact" }
)

# Validate $ModPath before Join-Path
$impactOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($impactOutputDir)) {
    Write-Host "  [FAIL] impactOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($impactOutputDir)) {
    Write-Host "  [FAIL] impactOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $impactOutputDir)) {
    New-Item -ItemType Directory -Path $impactOutputDir -Force | Out-Null
}

foreach ($impact in $impactEffects) {
    Write-Host "Generating impact effect: $($impact.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $impact.Id
            Prompt = "$($impact.Desc). Combat impact effect for Starbound ship combat."
            OllamaModel = $OllamaModel
            OutputDir = $impactOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($impact.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($impact.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. STEERING INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Steering Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$steeringIndicators = @(
    @{ Id = "steering_waypoint"; Name = "Waypoint Indicator"; Desc = "Waypoint indicator icon, navigation target, 32x32" },
    @{ Id = "steering_path"; Name = "Path Indicator"; Desc = "Path indicator icon, navigation path, 32x32" },
    @{ Id = "steering_autopilot"; Name = "Autopilot Indicator"; Desc = "Autopilot indicator icon, autopilot active, 32x32" },
    @{ Id = "steering_velocity"; Name = "Velocity Indicator"; Desc = "Velocity indicator icon, speed indicator, 32x32" }
)

# Validate $ModPath before Join-Path
$steeringOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($steeringOutputDir)) {
    Write-Host "  [FAIL] steeringOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($steeringOutputDir)) {
    Write-Host "  [FAIL] steeringOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $steeringOutputDir)) {
    New-Item -ItemType Directory -Path $steeringOutputDir -Force | Out-Null
}

foreach ($indicator in $steeringIndicators) {
    Write-Host "Generating steering indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Steering indicator for Starbound ship steering."
            OllamaModel = $OllamaModel
            OutputDir = $steeringOutputDir
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
Write-Host "  Thrusters: $(Join-Path $ModPath 'assets\ships\thrusters')" -ForegroundColor Gray
Write-Host "  Weapons: $(Join-Path $ModPath 'assets\ships\weapons')" -ForegroundColor Gray
Write-Host "  Shields: $(Join-Path $ModPath 'assets\ships\shields')" -ForegroundColor Gray
Write-Host "  Landing: $(Join-Path $ModPath 'assets\ships\landing')" -ForegroundColor Gray
Write-Host "  Hazards: $(Join-Path $ModPath 'assets\ships\hazards')" -ForegroundColor Gray
Write-Host "  Combat: $(Join-Path $ModPath 'assets\ships\combat')" -ForegroundColor Gray
Write-Host "  Steering: $(Join-Path $ModPath 'assets\ships\steering')" -ForegroundColor Gray
Write-Host ""
