#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Solar Wind Shield Aura Generator for Transcendence.
    
.DESCRIPTION
    Complete pipeline for generating solar wind shield aura effects:
    1. Reads aura registry JSON
    2. Generates orbital particle systems
    3. Renders layered aura in Blender (alpha noise, wind streams, distortion, particles)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    4. Exports Transcendence XML/UNID files
    5. Packages assets for game use
    
.PARAMETER RegistryPath
    Path to shield aura registry JSON file
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER BlenderPath
    Path to Blender executable
    
.PARAMETER AuraId
    Specific aura ID to generate (generates all if not specified)
    
.PARAMETER SkipRender
    Skip Blender rendering (use existing spritesheets)
    
.PARAMETER SkipExport
    Skip XML export (only render)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$RegistryPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",  # Defaults to Output/ShieldAuras if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AuraId = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipRender,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set default output directory if not specified
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $toolsRoot = Split-Path -Parent $PSScriptRoot
    $OutputDir = Join-Path $toolsRoot "Output\ShieldAuras"
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

# Validate registry file
if (-not (Test-Path $RegistryPath)) {
    Write-Log "Registry file not found: $RegistryPath" "ERROR"
    exit 1
}

Write-Log "Loading shield aura registry: $RegistryPath" "INFO"
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$auras = $registry.auras

if ($AuraId) {
    $auras = $auras | Where-Object { $_.id -eq $AuraId }
    if (-not $auras) {
        Write-Log "Aura ID not found: $AuraId" "ERROR"
        exit 1
    }
}

Write-Log "Found $($auras.Count) aura(s) to generate" "INFO"

# Create output directories
$spritesDir = Join-Path $OutputDir "Spritesheets"
$xmlDir = Join-Path $OutputDir "XML"
$resourcesDir = Join-Path $OutputDir "Resources"
$particlesDir = Join-Path $OutputDir "Particles"

New-Item -ItemType Directory -Path $spritesDir -Force | Out-Null
New-Item -ItemType Directory -Path $xmlDir -Force | Out-Null
New-Item -ItemType Directory -Path $resourcesDir -Force | Out-Null
New-Item -ItemType Directory -Path $particlesDir -Force | Out-Null

# Find Blender
$blenderExe = $null
if ($BlenderPath) {
    if (Test-Path $BlenderPath) {
        $blenderExe = $BlenderPath
    }
} else {
    $commonPaths = @(
        "D:\tools\Blender Foundation\Blender 5.0\blender.exe",
        "C:\Program Files\Blender Foundation\Blender\blender.exe",
        "C:\Program Files (x86)\Blender Foundation\Blender\blender.exe",
        "${env:LOCALAPPDATA}\Programs\Blender Foundation\Blender\blender.exe"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $blenderExe = $path
            break
        }
    }
}

if (-not $blenderExe -and -not $SkipRender) {
    Write-Log "Blender not found. Use -SkipRender to skip rendering or specify -BlenderPath" "WARN"
    $SkipRender = $true
}

# Process each aura
foreach ($aura in $auras) {
    Write-Log "Processing aura: $($aura.id)" "INFO"
    
    # Step 1: Blender Rendering
    if (-not $SkipRender -and $blenderExe) {
        Write-Log "Rendering aura in Blender..." "INFO"
        $blenderScript = Join-Path $PSScriptRoot "blender_shield_aura_renderer.py"
        
        if (Test-Path $blenderScript) {
            $blenderArgs = @(
                "--background",
                "--python", $blenderScript,
                "--",
                "--registry", $RegistryPath,
                "--aura-id", $aura.id,
                "--output-dir", $spritesDir
            )
            
            try {
                $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                
                if ($process.ExitCode -eq 0) {
                    Write-Log "Aura rendered successfully" "SUCCESS"
                    
                    # Copy to resources directory
                    $sourceFile = Join-Path $spritesDir "$($aura.id).png"
                    $destFile = Join-Path $resourcesDir "$($aura.id).png"
                    if (Test-Path $sourceFile) {
                        Copy-Item $sourceFile $destFile -Force
                        Write-Log "Copied to resources: $destFile" "INFO"
                    }
                    
                    # Copy distortion map if exists
                    $distortionSource = Join-Path $spritesDir "$($aura.id)_distort.png"
                    $distortionDest = Join-Path $resourcesDir "$($aura.id)_distort.png"
                    if (Test-Path $distortionSource) {
                        Copy-Item $distortionSource $distortionDest -Force
                        Write-Log "Copied distortion map: $distortionDest" "INFO"
                    }
                } else {
                    Write-Log "Blender rendering failed. Exit code: $($process.ExitCode)" "ERROR"
                }
            } catch {
                Write-Log "Error running Blender: $_" "ERROR"
            }
        } else {
            Write-Log "Blender script not found: $blenderScript" "WARN"
        }
    }
    
    # Step 2: XML Export
    if (-not $SkipExport) {
        Write-Log "Exporting Transcendence XML..." "INFO"
        $exporterScript = Join-Path $PSScriptRoot "..\Transcendence\transcendence_shield_aura_exporter.py"
        
        if (Test-Path $exporterScript) {
            $pythonExe = Get-Command "python" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
            if (-not $pythonExe) {
                $pythonExe = Get-Command "python3" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
            }
            
            if ($pythonExe) {
                $pythonArgs = @(
                    $exporterScript,
                    "--registry", $RegistryPath,
                    "--output-dir", $xmlDir
                )
                
                try {
                    $process = Start-Process -FilePath $pythonExe -ArgumentList $pythonArgs -Wait -NoNewWindow -PassThru
                    
                    if ($process.ExitCode -eq 0) {
                        Write-Log "XML exported successfully" "SUCCESS"
                    } else {
                        Write-Log "XML export failed. Exit code: $($process.ExitCode)" "ERROR"
                    }
                } catch {
                    Write-Log "Error running Python exporter: $_" "ERROR"
                }
            } else {
                Write-Log "Python not found. Cannot export XML." "WARN"
            }
        } else {
            Write-Log "Exporter script not found: $exporterScript" "WARN"
        }
    }
    
    Write-Log "Completed: $($aura.id)" "SUCCESS"
}

Write-Log "Shield aura generation pipeline complete!" "SUCCESS"
Write-Log "Output directory: $OutputDir" "INFO"
Write-Log "  - Spritesheets: $spritesDir" "INFO"
Write-Log "  - XML files: $xmlDir" "INFO"
Write-Log "  - Resources: $resourcesDir" "INFO"
Write-Log "  - Particles: $particlesDir" "INFO"

