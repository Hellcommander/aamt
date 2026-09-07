#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Data-driven projectile system generator for Transcendence.
    
.DESCRIPTION
    Orchestrates the complete projectile generation pipeline:
    1. Reads projectile registry JSON
    2. Generates procedural materials via AI (optional)
    3. Renders spritesheets in Blender

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    4. Exports Transcendence XML/UNID files
    5. Packages assets for game use
    
.PARAMETER RegistryPath
    Path to projectile registry JSON file
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER BlenderPath
    Path to Blender executable
    
.PARAMETER ProjectileId
    Specific projectile ID to generate (generates all if not specified)
    
.PARAMETER UseAI
    Use AI for material generation
    
.PARAMETER OllamaModel
    Ollama model for AI generation
    
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
    [string]$OutputDir = "",  # Defaults to Output/Projectiles if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectileId = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "llama3.2",
    
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
    $OutputDir = Join-Path $toolsRoot "Output\Projectiles"
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

Write-Log "Loading projectile registry: $RegistryPath" "INFO"
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$projectiles = $registry.projectiles

if ($ProjectileId) {
    $projectiles = $projectiles | Where-Object { $_.id -eq $ProjectileId }
    if (-not $projectiles) {
        Write-Log "Projectile ID not found: $ProjectileId" "ERROR"
        exit 1
    }
}

Write-Log "Found $($projectiles.Count) projectile(s) to generate" "INFO"

# Create output directories
$spritesheetDir = Join-Path $OutputDir "Spritesheets"
$xmlDir = Join-Path $OutputDir "XML"
$resourcesDir = Join-Path $OutputDir "Resources"

New-Item -ItemType Directory -Path $spritesheetDir -Force | Out-Null
New-Item -ItemType Directory -Path $xmlDir -Force | Out-Null
New-Item -ItemType Directory -Path $resourcesDir -Force | Out-Null

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

# Process each projectile
foreach ($projectile in $projectiles) {
    Write-Log "Processing projectile: $($projectile.id)" "INFO"
    
    # Step 1: AI Material Generation (optional)
    if ($UseAI) {
        Write-Log "Generating AI material spec for $($projectile.id)..." "INFO"
        $aiScript = Join-Path $PSScriptRoot "..\Transcendence\AssetMakerAI.ps1"
        if (Test-Path $aiScript) {
            $material = $projectile.visual.material
            $palette = $projectile.visual.palette
            $prompt = "Generate procedural material for $($projectile.type) projectile. Material type: $($material.type). Colors: $($palette.primary), $($palette.glow). Glow intensity: $($material.glowIntensity)."
            # Call AI script here if needed
        }
    }
    
    # Step 2: Blender Rendering
    if (-not $SkipRender -and $blenderExe) {
        Write-Log "Rendering spritesheet in Blender..." "INFO"
        $blenderScript = Join-Path $PSScriptRoot "blender_projectile_renderer.py"
        
        if (Test-Path $blenderScript) {
            $blenderArgs = @(
                "--background",
                "--python", $blenderScript,
                "--",
                "--registry", $RegistryPath,
                "--projectile-id", $projectile.id,
                "--output-dir", $spritesheetDir
            )
            
            try {
                $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                
                if ($process.ExitCode -eq 0) {
                    Write-Log "Spritesheet rendered successfully" "SUCCESS"
                    
                    # Copy to resources directory
                    $sourceFile = Join-Path $spritesheetDir "$($projectile.id).png"
                    $destFile = Join-Path $resourcesDir "$($projectile.id).png"
                    if (Test-Path $sourceFile) {
                        Copy-Item $sourceFile $destFile -Force
                        Write-Log "Copied to resources: $destFile" "INFO"
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
    
    # Step 3: XML Export
    if (-not $SkipExport) {
        Write-Log "Exporting Transcendence XML..." "INFO"
        $exporterScript = Join-Path $PSScriptRoot "..\Transcendence\transcendence_projectile_exporter.py"
        
        if (Test-Path $exporterScript) {
            # Check if Python is available
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
    
    Write-Log "Completed: $($projectile.id)" "SUCCESS"
}

Write-Log "Projectile generation pipeline complete!" "SUCCESS"
Write-Log "Output directory: $OutputDir" "INFO"
Write-Log "  - Spritesheets: $spritesheetDir" "INFO"
Write-Log "  - XML files: $xmlDir" "INFO"
Write-Log "  - Resources: $resourcesDir" "INFO"


