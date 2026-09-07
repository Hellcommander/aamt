#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Master batch generator for all Transcendence asset types.
    
.DESCRIPTION
    Generates all asset types in sequence: Projectiles, Shields/Armor, FX, and Auras.
    Provides progress tracking and error handling.
    
.PARAMETER ProjectileRegistry

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    Path to projectile registry JSON (optional)
    
.PARAMETER ShieldArmorRegistry
    Path to shield/armor registry JSON (optional)
    
.PARAMETER FXRegistry
    Path to FX registry JSON (optional)
    
.PARAMETER AuraRegistry
    Path to aura registry JSON (optional)
    
.PARAMETER OutputBaseDir
    Base output directory (default: "TranscendenceArt")
    
.PARAMETER BlenderPath
    Path to Blender executable
    
.PARAMETER SkipRender
    Skip Blender rendering for all systems
    
.PARAMETER SkipExport
    Skip XML export for all systems
    
.PARAMETER UseExamples
    Use example registry files if specific registries not provided
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectileRegistry = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ShieldArmorRegistry = "",
    
    [Parameter(Mandatory=$false)]
    [string]$FXRegistry = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AuraRegistry = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputBaseDir = "TranscendenceArt",
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipRender,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExport,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseExamples
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        "SECTION" { "Cyan" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Log "========================================" "SECTION"
Write-Log "Transcendence Asset Generator - Master Batch" "SECTION"
Write-Log "========================================" "SECTION"
Write-Log ""

# Determine registry paths
if ($UseExamples) {
    $exampleDir = $PSScriptRoot
    
    if (-not $ProjectileRegistry) {
        $ProjectileRegistry = Join-Path $exampleDir "projectile_registry_example.json"
    }
    if (-not $ShieldArmorRegistry) {
        $ShieldArmorRegistry = Join-Path $exampleDir "shield_armor_example.json"
    }
    if (-not $FXRegistry) {
        $FXRegistry = Join-Path $exampleDir "nova_drift_fx_example.json"
    }
    if (-not $AuraRegistry) {
        $AuraRegistry = Join-Path $exampleDir "shield_aura_example.json"
    }
}

# Build common parameters
$commonParams = @{}
if ($BlenderPath) {
    $commonParams['BlenderPath'] = $BlenderPath
}
if ($SkipRender) {
    $commonParams['SkipRender'] = $true
}
if ($SkipExport) {
    $commonParams['SkipExport'] = $true
}

$totalSystems = 0
$completedSystems = 0
$failedSystems = 0

# 1. Generate Projectiles
if ($ProjectileRegistry -and (Test-Path $ProjectileRegistry)) {
    $totalSystems++
    Write-Log "========================================" "SECTION"
    Write-Log "Generating Projectiles..." "SECTION"
    Write-Log "========================================" "SECTION"
    
    try {
        $outputDir = Join-Path $OutputBaseDir "Projectiles"
        & (Join-Path $PSScriptRoot "ProjectileSystemGenerator.ps1") `
            -RegistryPath $ProjectileRegistry `
            -OutputDir $outputDir `
            @commonParams
        
        if ($LASTEXITCODE -eq 0) {
            $completedSystems++
            Write-Log "Projectiles generated successfully" "SUCCESS"
        } else {
            $failedSystems++
            Write-Log "Projectile generation failed" "ERROR"
        }
    } catch {
        $failedSystems++
        Write-Log "Error generating projectiles: $_" "ERROR"
    }
    Write-Log ""
} else {
    Write-Log "Skipping projectiles (registry not found or not specified)" "WARN"
}

# 2. Generate Shields/Armor
if ($ShieldArmorRegistry -and (Test-Path $ShieldArmorRegistry)) {
    $totalSystems++
    Write-Log "========================================" "SECTION"
    Write-Log "Generating Shields and Armor..." "SECTION"
    Write-Log "========================================" "SECTION"
    
    try {
        $outputDir = Join-Path $OutputBaseDir "ShieldsArmor"
        $particleProfile = Join-Path $PSScriptRoot "particle_profiles_example.json"
        
        $params = @{
            RegistryPath = $ShieldArmorRegistry
            OutputDir = $outputDir
        }
        if (Test-Path $particleProfile) {
            $params['ParticleProfilePath'] = $particleProfile
        }
        $params += $commonParams
        
        & (Join-Path $PSScriptRoot "ShieldArmorSystemGenerator.ps1") @params
        
        if ($LASTEXITCODE -eq 0) {
            $completedSystems++
            Write-Log "Shields/Armor generated successfully" "SUCCESS"
        } else {
            $failedSystems++
            Write-Log "Shield/Armor generation failed" "ERROR"
        }
    } catch {
        $failedSystems++
        Write-Log "Error generating shields/armor: $_" "ERROR"
    }
    Write-Log ""
} else {
    Write-Log "Skipping shields/armor (registry not found or not specified)" "WARN"
}

# 3. Generate FX
if ($FXRegistry -and (Test-Path $FXRegistry)) {
    $totalSystems++
    Write-Log "========================================" "SECTION"
    Write-Log "Generating Nova Drift FX..." "SECTION"
    Write-Log "========================================" "SECTION"
    
    try {
        $outputDir = Join-Path $OutputBaseDir "FX"
        & (Join-Path $PSScriptRoot "NovaDriftFXGenerator.ps1") `
            -RegistryPath $FXRegistry `
            -OutputDir $outputDir `
            @commonParams
        
        if ($LASTEXITCODE -eq 0) {
            $completedSystems++
            Write-Log "FX generated successfully" "SUCCESS"
        } else {
            $failedSystems++
            Write-Log "FX generation failed" "ERROR"
        }
    } catch {
        $failedSystems++
        Write-Log "Error generating FX: $_" "ERROR"
    }
    Write-Log ""
} else {
    Write-Log "Skipping FX (registry not found or not specified)" "WARN"
}

# 4. Generate Shield Auras
if ($AuraRegistry -and (Test-Path $AuraRegistry)) {
    $totalSystems++
    Write-Log "========================================" "SECTION"
    Write-Log "Generating Shield Auras..." "SECTION"
    Write-Log "========================================" "SECTION"
    
    try {
        $outputDir = Join-Path $OutputBaseDir "Auras"
        & (Join-Path $PSScriptRoot "ShieldAuraGenerator.ps1") `
            -RegistryPath $AuraRegistry `
            -OutputDir $outputDir `
            @commonParams
        
        if ($LASTEXITCODE -eq 0) {
            $completedSystems++
            Write-Log "Auras generated successfully" "SUCCESS"
        } else {
            $failedSystems++
            Write-Log "Aura generation failed" "ERROR"
        }
    } catch {
        $failedSystems++
        Write-Log "Error generating auras: $_" "ERROR"
    }
    Write-Log ""
} else {
    Write-Log "Skipping auras (registry not found or not specified)" "WARN"
}

# Summary
Write-Log "========================================" "SECTION"
Write-Log "Generation Summary" "SECTION"
Write-Log "========================================" "SECTION"
Write-Log "Total Systems: $totalSystems" "INFO"
Write-Log "Completed: $completedSystems" "SUCCESS"
Write-Log "Failed: $failedSystems" $(if ($failedSystems -gt 0) { "ERROR" } else { "INFO" })
Write-Log ""
Write-Log "Output Base Directory: $OutputBaseDir" "INFO"
Write-Log ""

if ($failedSystems -eq 0) {
    Write-Log "All asset generation completed successfully!" "SUCCESS"
    exit 0
} else {
    Write-Log "Some asset generation failed. Check errors above." "ERROR"
    exit 1
}

