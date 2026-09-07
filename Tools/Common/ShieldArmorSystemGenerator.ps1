#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Data-driven shield and armor system generator for Transcendence.
    
.DESCRIPTION
    Orchestrates the complete shield/armor generation pipeline:
    1. Reads shield/armor registry JSON
    2. Generates procedural materials and shaders
    3. Renders shield visuals in Blender

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    4. Generates particle system definitions
    5. Exports Transcendence XML/UNID files
    6. Packages assets for game use
    
.PARAMETER RegistryPath
    Path to shield/armor registry JSON file
    
.PARAMETER ParticleProfilePath
    Path to particle profile JSON file
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER BlenderPath
    Path to Blender executable
    
.PARAMETER ShieldId
    Specific shield ID to generate (generates all if not specified)
    
.PARAMETER UseAI
    Use AI for material generation
    
.PARAMETER OllamaModel
    Ollama model for AI generation
    
.PARAMETER SkipRender
    Skip Blender rendering (use existing sprites)
    
.PARAMETER SkipExport
    Skip XML export (only render)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$RegistryPath,
    
    [Parameter(Mandatory=$false)]
    [string]$ParticleProfilePath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",  # Defaults to Output/ShieldsArmor if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ShieldId = "",
    
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
    $OutputDir = Join-Path $toolsRoot "Output\ShieldsArmor"
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

Write-Log "Loading shield/armor registry: $RegistryPath" "INFO"
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$shields = $registry.shields
$armor = $registry.armor

if ($ShieldId) {
    $shields = $shields | Where-Object { $_.id -eq $ShieldId }
    if (-not $shields) {
        Write-Log "Shield ID not found: $ShieldId" "ERROR"
        exit 1
    }
}

Write-Log "Found $($shields.Count) shield(s) and $($armor.Count) armor item(s) to generate" "INFO"

# Create output directories
$spritesDir = Join-Path $OutputDir "Sprites"
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

# Process shields
foreach ($shield in $shields) {
    Write-Log "Processing shield: $($shield.id)" "INFO"
    
    # Step 1: AI Material Generation (optional)
    if ($UseAI) {
        Write-Log "Generating AI material spec for $($shield.id)..." "INFO"
        $aiMat = Join-Path $PSScriptRoot "ai_material_generator.py"
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($py -and (Test-Path -LiteralPath $aiMat)) {
            $enhanced = Join-Path $OutputDir "$($shield.id)_material_enhanced.json"
            $tmpReg = Join-Path $OutputDir "$($shield.id)_material_in.json"
            (@{ shields = @($shield) } | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $tmpReg -Encoding UTF8
            & $py $aiMat --registry $tmpReg --output $enhanced --model $OllamaModel
            if (Test-Path -LiteralPath $enhanced) {
                Write-Log "AI material spec written: $enhanced" "SUCCESS"
                try {
                    $loaded = Get-Content -LiteralPath $enhanced -Raw | ConvertFrom-Json
                    if ($loaded.shields) { $shield = $loaded.shields[0] }
                    elseif ($loaded.projectiles) { $shield = $loaded.projectiles[0] }
                } catch { }
            } else {
                Write-Log "AI material generator produced no output; continuing with registry visuals" "WARN"
            }
        } else {
            Write-Log "ai_material_generator.py / python unavailable; skipping AI material step" "WARN"
        }
    }
    
    # Step 2: Blender Rendering
    if (-not $SkipRender -and $blenderExe) {
        Write-Log "Rendering shield in Blender..." "INFO"
        $blenderScript = Join-Path $PSScriptRoot "blender_shield_renderer.py"
        
        if (Test-Path $blenderScript) {
            $blenderArgs = @(
                "--background",
                "--python", $blenderScript,
                "--",
                "--registry", $RegistryPath,
                "--shield-id", $shield.id,
                "--output-dir", $spritesDir
            )
            
            try {
                $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                
                if ($process.ExitCode -eq 0) {
                    Write-Log "Shield rendered successfully" "SUCCESS"
                    
                    # Copy to resources directory
                    $sourceFile = Join-Path $spritesDir "$($shield.id)_spritesheet.png"
                    $destFile = Join-Path $resourcesDir "$($shield.id).png"
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
    
    # Step 3: Particle System Export
    if ($ParticleProfilePath -and (Test-Path $ParticleProfilePath)) {
        Write-Log "Exporting particle system..." "INFO"
        $particleProfile = Get-Content $ParticleProfilePath | ConvertFrom-Json
        $profileId = $shield.visual.particleProfile
        
        if ($profileId) {
            $profile = $particleProfile.profiles | Where-Object { $_.id -eq $profileId }
            if ($profile) {
                $particleOutput = Join-Path $particlesDir "$($shield.id)_particles.json"
                $profile | ConvertTo-Json -Depth 10 | Out-File $particleOutput
                Write-Log "Particle profile exported: $particleOutput" "SUCCESS"
            }
        }
    }
    
    # Step 4: XML Export
    if (-not $SkipExport) {
        Write-Log "Exporting Transcendence XML..." "INFO"
        $exporterScript = Join-Path $PSScriptRoot "..\Transcendence\transcendence_shield_armor_exporter.py"
        
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
    
    Write-Log "Completed: $($shield.id)" "SUCCESS"
}

# Process armor
foreach ($armorItem in $armor) {
    Write-Log "Processing armor: $($armorItem.id)" "INFO"
    
    # XML Export for armor
    if (-not $SkipExport) {
        # Already handled by exporter script above
        Write-Log "Armor export handled by XML exporter" "INFO"
    }
}

Write-Log "Shield/armor generation pipeline complete!" "SUCCESS"
Write-Log "Output directory: $OutputDir" "INFO"
Write-Log "  - Sprites: $spritesDir" "INFO"
Write-Log "  - XML files: $xmlDir" "INFO"
Write-Log "  - Resources: $resourcesDir" "INFO"
Write-Log "  - Particles: $particlesDir" "INFO"

