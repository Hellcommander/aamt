#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Nova Drift Style FX Generator for Transcendence.
    
.DESCRIPTION
    Complete pipeline for generating Nova Drift-style special effects:
    1. Reads FX registry JSON
    2. Generates particle choreography
    3. Renders layered FX in Blender (core, shockwave, distortion, particles)

# AI-Assisted Modding Tools (AAMT) - Transcendence Toolset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for Nova Drift FX generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Blender", "Python", "ImageMagick") `
    -OptionalTools @("Ollama")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Log "ERROR: Missing required tools for Nova Drift FX generation" "ERROR"
    Show-ToolsetStatus -ToolsetName "Transcendence - Nova Drift FX" `
        -RequiredTools @("Blender", "Python", "ImageMagick") `
        -OptionalTools @("Ollama")
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    Write-Log "Ollama integration enabled" "SUCCESS"
}
    4. Exports Transcendence XML/UNID files
    5. Packages assets for game use
    
.PARAMETER RegistryPath
    Path to FX registry JSON file
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER BlenderPath
    Path to Blender executable
    
.PARAMETER FXId
    Specific FX ID to generate (generates all if not specified)
    
.PARAMETER UseAI
    Use AI for FX profile generation
    
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
    [string]$OutputDir = "",  # Defaults to Output/FX if not specified
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$FXId = "",
    
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
    $toolsRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $OutputDir = Join-Path $toolsRoot "Output\FX"
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

Write-Log "Loading FX registry: $RegistryPath" "INFO"
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$effects = $registry.effects

if ($FXId) {
    $effects = $effects | Where-Object { $_.id -eq $FXId }
    if (-not $effects) {
        Write-Log "FX ID not found: $FXId" "ERROR"
        exit 1
    }
}

Write-Log "Found $($effects.Count) FX effect(s) to generate" "INFO"

# Create output directories
$spritesDir = Join-Path $OutputDir "Spritesheets"
$xmlDir = Join-Path $OutputDir "XML"
$resourcesDir = Join-Path $OutputDir "Resources"
$particlesDir = Join-Path $OutputDir "Particles"

New-Item -ItemType Directory -Path $spritesDir -Force | Out-Null
New-Item -ItemType Directory -Path $xmlDir -Force | Out-Null
New-Item -ItemType Directory -Path $resourcesDir -Force | Out-Null
New-Item -ItemType Directory -Path $particlesDir -Force | Out-Null

# Find Blender (using unified detection)
$blenderExe = $null
if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
    if (Test-Path $BlenderPath) {
        $blenderExe = $BlenderPath
    }
} else {
    # Use unified tool detection
    $blenderExe = Get-BlenderPath
}

if (-not $blenderExe -and -not $SkipRender) {
    Write-Log "Blender not found. Use -SkipRender to skip rendering or specify -BlenderPath" "WARN"
    $SkipRender = $true
}

# Process each FX
foreach ($fx in $effects) {
    Write-Log "Processing FX: $($fx.id)" "INFO"
    
    # Step 1: AI Profile Generation (optional)
    if ($UseAI) {
        Write-Log "Generating AI FX profile for $($fx.id)..." "INFO"
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($py) {
            $profileOut = Join-Path $particlesDir "$($fx.id)_ai_profile.json"
            $fxJson = ($fx | ConvertTo-Json -Depth 10 -Compress)
            $prompt = @"
You are a VFX designer for a Nova Drift / Transcendence style space game.
Given this FX JSON, return ONLY a compact JSON object with keys:
particleCount (int), lifetime (float), color (hex string), glow (0-1), notes (short string).
FX: $fxJson
"@
            $promptFile = Join-Path $particlesDir "$($fx.id)_ai_prompt.txt"
            Set-Content -LiteralPath $promptFile -Value $prompt -Encoding UTF8
            try {
                $raw = & ollama run $OllamaModel $prompt 2>$null
                if ($raw) {
                    $jsonMatch = [regex]::Match(($raw -join "`n"), '\{[\s\S]*\}')
                    if ($jsonMatch.Success) {
                        Set-Content -LiteralPath $profileOut -Value $jsonMatch.Value -Encoding UTF8
                        Write-Log "AI FX profile written: $profileOut" "SUCCESS"
                        try {
                            $prof = $jsonMatch.Value | ConvertFrom-Json
                            if ($prof.particleCount) { $fx | Add-Member -NotePropertyName aiParticleCount -NotePropertyValue $prof.particleCount -Force }
                            if ($prof.color) { $fx | Add-Member -NotePropertyName aiColor -NotePropertyValue $prof.color -Force }
                            if ($prof.glow) { $fx | Add-Member -NotePropertyName aiGlow -NotePropertyValue $prof.glow -Force }
                        } catch { }
                    } else {
                        Write-Log "AI FX profile: no JSON in model response; continuing with registry FX" "WARN"
                    }
                }
            } catch {
                Write-Log "AI FX profile failed: $_; continuing with registry FX" "WARN"
            }
        } else {
            Write-Log "python/ollama unavailable for -UseAI; continuing with registry FX" "WARN"
        }
    }
    
    # Step 2: Particle Choreography
    Write-Log "Generating particle choreography..." "INFO"
    $choreographyScript = Join-Path $PSScriptRoot "..\..\Common\particle_choreography_system.py"
    
    if (Test-Path $choreographyScript) {
        $pythonExe = Get-Command "python" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
        if (-not $pythonExe) {
            $pythonExe = Get-Command "python3" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
        }
        
        if ($pythonExe) {
            # Create temporary FX JSON for choreography
            $tempFxJson = Join-Path $particlesDir "$($fx.id)_temp.json"
            $fx | ConvertTo-Json -Depth 10 | Out-File $tempFxJson
            
            $pythonArgs = @(
                $choreographyScript,
                "--fx-json", $tempFxJson,
                "--output", (Join-Path $particlesDir "$($fx.id)_particles.json")
            )
            
            try {
                $process = Start-Process -FilePath $pythonExe -ArgumentList $pythonArgs -Wait -NoNewWindow -PassThru
                if ($process.ExitCode -eq 0) {
                    Write-Log "Particle choreography generated" "SUCCESS"
                }
            } catch {
                Write-Log "Error generating particle choreography: $_" "ERROR"
            }
        }
    }
    
    # Step 3: Blender Rendering
    if (-not $SkipRender -and $blenderExe) {
        Write-Log "Rendering FX in Blender..." "INFO"
        $blenderScript = Join-Path $PSScriptRoot "blender_nova_drift_fx_renderer.py"
        
        if (Test-Path $blenderScript) {
            $blenderArgs = @(
                "--background",
                "--python", $blenderScript,
                "--",
                "--registry", $RegistryPath,
                "--fx-id", $fx.id,
                "--output-dir", $spritesDir
            )
            
            try {
                $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                
                if ($process.ExitCode -eq 0) {
                    Write-Log "FX rendered successfully" "SUCCESS"
                    
                    # Copy to resources directory
                    $sourceFile = Join-Path $spritesDir "$($fx.id).png"
                    $destFile = Join-Path $resourcesDir "$($fx.id).png"
                    if (Test-Path $sourceFile) {
                        Copy-Item $sourceFile $destFile -Force
                        Write-Log "Copied to resources: $destFile" "INFO"
                    }
                    
                    # Copy distortion map if exists
                    $distortionSource = Join-Path $spritesDir "$($fx.id)_distort.png"
                    $distortionDest = Join-Path $resourcesDir "$($fx.id)_distort.png"
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
    
    # Step 4: XML Export
    if (-not $SkipExport) {
        Write-Log "Exporting Transcendence XML..." "INFO"
        $exporterScript = Join-Path $PSScriptRoot "transcendence_fx_exporter.py"
        
        if (Test-Path $exporterScript) {
            # Use unified tool detection for Python
            $pythonExe = Get-PythonPath
            if (-not $pythonExe) {
                # Fallback to manual detection
                $pythonExe = Get-Command "python" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
                if (-not $pythonExe) {
                    $pythonExe = Get-Command "python3" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
                }
            }
            
            if ($pythonExe) {
                $pythonArgs = @(
                    $exporterScript,
                    "--registry", $RegistryPath,
                    "--output-dir", $xmlDir,
                    "--particle-profiles-dir", $particlesDir
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
    
    Write-Log "Completed: $($fx.id)" "SUCCESS"
}

Write-Log "Nova Drift FX generation pipeline complete!" "SUCCESS"
Write-Log "Output directory: $OutputDir" "INFO"
Write-Log "  - Spritesheets: $spritesDir" "INFO"
Write-Log "  - XML files: $xmlDir" "INFO"
Write-Log "  - Resources: $resourcesDir" "INFO"
Write-Log "  - Particles: $particlesDir" "INFO"

