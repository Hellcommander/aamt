#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for all new Magitech Mechforms.
    
.DESCRIPTION
    Generates all assets needed for the 6 new Magitech mechforms:
    - Aether Warden (Support/battlefield control)
    - Flux Strider (Hit-and-run skirmisher)
    - Iron Bloom (Area control/sustain)
    - Null Harrier (Disruption/assassination)
    - Shardwright (Adaptive offense/fragmentation)
    - Helix Bastion (Mobile artillery/area denial)
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER SkipExisting
    Skip assets that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  New Magitech Mechforms Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$mechforms = @(
    @{
        Id = "aetherWarden"
        Name = "Aether Warden"
        Role = "Support/Battlefield Control"
        Element = "Aether"
        Colors = "blue/aether, ethereal glow, shield energy"
        Description = "Support mech with shield projection and tether anchors"
    },
    @{
        Id = "fluxStrider"
        Name = "Flux Strider"
        Role = "Hit-and-Run Skirmisher"
        Element = "Energy"
        Colors = "yellow/orange, energy blades, thruster glow"
        Description = "Highly mobile skirmisher with blade dash attacks, glide mode for sustained speed, and burst overdrive for rapid repositioning"
    },
    @{
        Id = "ironBloom"
        Name = "Iron Bloom"
        Role = "Area Control/Sustain"
        Element = "Nature"
        Colors = "brown/rust, organic petals, metallic bloom"
        Description = "Heavy mech with healing auras and petal projectiles"
    },
    @{
        Id = "nullHarrier"
        Name = "Null Harrier"
        Role = "Disruption/Assassination"
        Element = "Void"
        Colors = "purple/black, void energy, EMP effects"
        Description = "Stealthy disruption mech with teleportation and EMP"
    },
    @{
        Id = "shardwright"
        Name = "Shardwright"
        Role = "Adaptive Offense/Fragmentation"
        Element = "Crystal"
        Colors = "blue/crystal, shard fragments, modular design"
        Description = "Adaptive mech that sheds and reabsorbs shards"
    },
    @{
        Id = "helixBastion"
        Name = "Helix Bastion"
        Role = "Mobile Artillery/Area Denial"
        Element = "Earth"
        Colors = "brown/gray, heavy armor, turret array"
        Description = "Heavy segmented platform with spiral turret array"
    }
)

$totalGenerated = 0
$totalFailed = 0
$totalSkipped = 0

foreach ($form in $mechforms) {
    Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Magenta
    Write-Host "  Processing: $($form.Name) ($($form.Role))" -ForegroundColor Magenta
    Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Magenta
    Write-Host ""
    
    $generated = 0
    $failed = 0
    $skipped = 0
    
    # Generate form icon
    Write-Host "Generating Form Icon..." -ForegroundColor Yellow
    # Validate $ModPath before Join-Path
$iconPath = Join-Path $ModPath "assets\$($form.Id)_icon.png"
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($iconPath)) {
        Write-Host "  [FAIL] iconPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $iconPath)) {
        $skipped++
        $totalSkipped++
        Write-Host "  [SKIP] Form icon already exists" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Icon"
                AssetName = "$($form.Id)_icon"
                Prompt = "An icon for the $($form.Name) mech form. $($form.Description). $($form.Element) elemental, $($form.Colors), 64x64 pixels"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            $totalGenerated++
            Write-Host "  [OK] Generated form icon" -ForegroundColor Green
        } catch {
            $failed++
            $totalFailed++
            Write-Host "  [FAIL] Form icon: $_" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    
    # Generate VFX particles (enter, loop, exit)
    Write-Host "Generating VFX Particles..." -ForegroundColor Yellow
    $particles = @(
        @{Id="$($form.Id)Enter"; Desc="Enter effect when transforming into $($form.Name), $($form.Element) energy manifestation"},
        @{Id="$($form.Id)Loop"; Desc="Continuous effect while in $($form.Name) form, $($form.Element) energy aura"},
        @{Id="$($form.Id)Exit"; Desc="Exit effect when leaving $($form.Name) form, $($form.Element) energy dissipation"}
    )
    
    foreach ($particle in $particles) {
        # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\$($form.Id)\$($particle.Id).particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
            Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
            Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        if ($SkipExisting -and (Test-Path $particlePath)) {
            $skipped++
            $totalSkipped++
            Write-Host "  [SKIP] Particle already exists: $($particle.Id)" -ForegroundColor Gray
        } else {
            try {
                $params = @{
                    AssetType = "Particle"
                    AssetName = $particle.Id
                    Prompt = "A particle effect: $($particle.Desc). $($form.Element) type, $($form.Colors)"
                    OllamaModel = $OllamaModel
                    # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
            OutputDir = $tempOutputDir
                }
                if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
                if ($VisualModel) { $params['VisualModel'] = $VisualModel }
                $params['UseCppBackend'] = $UseCppBackend
                
                & $assetGenerator @params | Out-Null
                $generated++
                $totalGenerated++
                Write-Host "  [OK] Generated particle: $($particle.Id)" -ForegroundColor Green
            } catch {
                $failed++
                $totalFailed++
                Write-Host "  [FAIL] Particle $($particle.Id): $_" -ForegroundColor Red
            }
        }
    }
    
    Write-Host ""
    Write-Host "Summary for $($form.Name): Generated: $generated, Failed: $failed, Skipped: $skipped" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Final Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Total Generated: $totalGenerated" -ForegroundColor Green
Write-Host "  Total Failed: $totalFailed" -ForegroundColor $(if ($totalFailed -eq 0) { "Green" } else { "Red" })
Write-Host "  Total Skipped: $totalSkipped" -ForegroundColor Gray
Write-Host ""
