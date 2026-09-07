#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Production-quality texture generation pipeline for unified asset registry.
    
.DESCRIPTION
    Reads visual blocks from the asset registry, generates procedural materials
    with quality-appropriate detail, and bakes multiple texture maps (Base Color,
    Normal, Roughness, Emission) for use in models, spritesheets, and cross-game exports.
    

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
.PARAMETER RegistryPath
    Path to the asset registry JSON file.
    
.PARAMETER AssetId
    Asset ID from the registry to generate textures for.
    
.PARAMETER Quality
    Quality level: draft, standard, high, ultra (default: standard)
    
.PARAMETER OutputDir
    Output directory for generated textures.
    
.PARAMETER BlenderPath
    Path to Blender executable (auto-detected if not provided).
    
.PARAMETER TextureSize
    Size of generated textures in pixels (default: 512)
    
.PARAMETER Samples
    Cycles render samples (default: 1 for fast, higher for quality)
    
.EXAMPLE
    .\GenerateAssetTextures.ps1 -RegistryPath "asset_registry.json" -AssetId "nature_verdant_pulse" -Quality "high"
    
.EXAMPLE
    .\GenerateAssetTextures.ps1 -RegistryPath "asset_registry.json" -AssetId "nature_verdant_pulse" -Quality "ultra" -TextureSize 1024 -Samples 64
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$RegistryPath,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetId,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("draft", "standard", "high", "ultra")]
    [string]$Quality = "standard",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$TextureSize = 512,
    
    [Parameter(Mandatory=$false)]
    [int]$Samples = 1,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$AIModel = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportNodeGroups,
    
    [Parameter(Mandatory=$false)]
    [string]$BlendOutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SketchPath = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("silhouette", "displacement", "mask", "reference", "heightmap")]
    [string]$UseSketchAs = "silhouette",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("hierarchical", "distance", "region", "thickness")]
    [string]$MappingStrategy = "hierarchical",
    
    [Parameter(Mandatory=$false)]
    [switch]$ProcessAsLineDrawing
)

# ------------------------------------------------------------
# Script Setup
# ------------------------------------------------------------
$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

function Find-Blender {
    <#
    .SYNOPSIS
      Finds Blender installation
    #>
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
        $providedPath = $BlenderPath.Trim()
        if (Test-Path $providedPath) {
            Write-Host "  Using provided Blender path: $providedPath" -ForegroundColor Green
            return $providedPath
        }
    }
    
    # Check environment variables
    $envVars = @("BLENDER_PATH", "BLENDER_DIR", "BLENDER_HOME")
    foreach ($envVar in $envVars) {
        $envPath = [System.Environment]::GetEnvironmentVariable($envVar)
        if (-not [string]::IsNullOrWhiteSpace($envPath) -and (Test-Path $envPath)) {
            $blenderExe = if (Test-Path $envPath -PathType Container) {
                Join-Path $envPath "blender.exe"
            } else {
                $envPath
            }
            if (Test-Path $blenderExe) {
                Write-Host "  Found Blender via $envVar : $blenderExe" -ForegroundColor Green
                return $blenderExe
            }
        }
    }
    
    # Check PATH
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        Write-Host "  Found Blender via PATH: $($blender.Source)" -ForegroundColor Green
        return $blender.Source
    }

    $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py -and (Test-Path -LiteralPath $pipe)) {
        $resolved = & $py -c "import sys; sys.path.insert(0, r'$PSScriptRoot'); import tx_ai_pipeline as t; print(t.find_blender() or '')" 2>$null
        if ($resolved -and (Test-Path -LiteralPath $resolved.Trim())) {
            Write-Host "  Found Blender via Shared/tool_paths: $($resolved.Trim())" -ForegroundColor Green
            return $resolved.Trim()
        }
    }
    
    # Check common paths
    $commonPaths = @(
        "D:\tools\Blender Foundation",
        "${env:ProgramFiles}\Blender Foundation",
        "${env:ProgramFiles(x86)}\Blender Foundation"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending
            
            foreach ($dir in $blenderDirs) {
                $blenderExe = Join-Path $dir.FullName "blender.exe"
                if (Test-Path $blenderExe) {
                    Write-Host "  Found Blender: $blenderExe" -ForegroundColor Green
                    return $blenderExe
                }
            }
        }
    }
    
    Write-Host "  Error: Blender not found" -ForegroundColor Red
    return $null
}

function Get-BlenderVulkanStartupPath {
    param([string]$BlenderExePath)
    
    $blenderDir = Split-Path -Parent $BlenderExePath
    $vulkanCmd = Join-Path $blenderDir "blender_startup_vulkan.cmd"
    
    if (Test-Path $vulkanCmd) {
        return $vulkanCmd
    }
    return $BlenderExePath
}

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Production Texture Generation Pipeline" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate registry file
if (-not (Test-Path $RegistryPath)) {
    Write-Host "Error: Registry file not found: $RegistryPath" -ForegroundColor Red
    exit 1
}

# Load registry
Write-Host "Loading registry..." -ForegroundColor Cyan
try {
    $registry = Get-Content $RegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "  Registry loaded: $($registry.entries.Count) entries" -ForegroundColor Gray
}
catch {
    Write-Host "  Error loading registry: $_" -ForegroundColor Red
    exit 1
}

# Find asset entry
$entry = $registry.entries | Where-Object { $_.id -eq $AssetId } | Select-Object -First 1
if (-not $entry) {
    Write-Host "Error: Asset ID '$AssetId' not found in registry" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Asset: $($entry.name) ($AssetId)" -ForegroundColor Green
Write-Host "  Type: $($entry.type)" -ForegroundColor Gray
Write-Host "  School: $($entry.school)" -ForegroundColor Gray
Write-Host "  Quality: $Quality" -ForegroundColor Gray

# Check for sketch source
$sketchSource = $null
if (-not [string]::IsNullOrWhiteSpace($SketchPath)) {
    $sketchSource = $SketchPath
    Write-Host "  Sketch: $sketchSource" -ForegroundColor Cyan
    Write-Host "  Sketch Method: $UseSketchAs" -ForegroundColor Gray
} elseif ($entry.generation -and $entry.generation.sketchSource) {
    $sketchSource = $entry.generation.sketchSource
    $UseSketchAs = if ($entry.generation.useSketchAs) { $entry.generation.useSketchAs } else { "silhouette" }
    Write-Host "  Sketch: $sketchSource" -ForegroundColor Cyan
    Write-Host "  Sketch Method: $UseSketchAs" -ForegroundColor Gray
}

Write-Host ""

# Optionally generate material spec using AI
$materialSpec = $null
if ($UseAI) {
    Write-Host ""
    Write-Host "Generating AI material specification..." -ForegroundColor Cyan
    $materialSpecScript = Join-Path $PSScriptRoot "..\Common\GenerateMaterialSpec.ps1"
    if (Test-Path $materialSpecScript) {
        $specArgs = @{
            RegistryPath = $RegistryPath
            AssetId = $AssetId
        }
        if (-not [string]::IsNullOrWhiteSpace($AIModel)) {
            $specArgs.Add("Model", $AIModel)
        }
        
        $materialSpec = & $materialSpecScript @specArgs 2>&1 | Out-String
        if ($materialSpec) {
            try {
                $materialSpec = $materialSpec | ConvertFrom-Json
                Write-Host "  ✓ AI material spec generated" -ForegroundColor Green
            }
            catch {
                Write-Host "  Warning: Could not parse AI spec, using registry defaults" -ForegroundColor Yellow
                $materialSpec = $null
            }
        }
    } else {
        Write-Host "  Warning: GenerateMaterialSpec.ps1 not found, skipping AI generation" -ForegroundColor Yellow
    }
}

# Get texture configuration (prefer AI spec, then registry, then defaults)
$textureConfig = if ($materialSpec -and $materialSpec.textures) {
    $materialSpec.textures
} elseif ($entry.textures) {
    $entry.textures
} else {
    @{
        baseColor = $true
        normal = $false
        roughness = $false
        emission = $false
    }
}

Write-Host "Texture Maps:" -ForegroundColor Cyan
foreach ($mapType in @("baseColor", "normal", "roughness", "emission", "metallic")) {
    $enabled = if ($textureConfig.$mapType) { "✓" } else { "-" }
    Write-Host "  $enabled $mapType" -ForegroundColor $(if ($textureConfig.$mapType) { "Green" } else { "Gray" })
}
Write-Host ""

# Determine output directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "GeneratedTextures" $AssetId
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Output Directory: $OutputDir" -ForegroundColor Cyan
Write-Host ""

# No sketch: Shared SD PBR (not Common/bake_texture.py). Sketch paths still use Blender.
$hasSketch = $sketchSource -and (Test-Path -LiteralPath $sketchSource)
if (-not $hasSketch) {
    Write-Host "Using Shared SD PBR skins (tx_ai_pipeline)..." -ForegroundColor Cyan
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
    if (-not $py -or -not (Test-Path -LiteralPath $pipe)) {
        Write-Host "Error: python / tx_ai_pipeline.py required for SD skins" -ForegroundColor Red
        exit 1
    }
    $theme = @($entry.name, $entry.school, $entry.type, $AssetId) -join " "
    & $py $pipe skins --name $AssetId --out-dir $OutputDir --theme $theme --quality $Quality --description "$($entry.name)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: SD PBR skins failed (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "Generated textures:" -ForegroundColor Cyan
    Get-ChildItem -Path $OutputDir -Filter "*.png" -File -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  - $($_.Name)" -ForegroundColor Gray
    }
    Write-Host "Output directory: $OutputDir" -ForegroundColor Green
    exit 0
}

# Find Blender
Write-Host "Detecting Blender..." -ForegroundColor Cyan
$blenderExe = Find-Blender
if (-not $blenderExe) {
    Write-Host "Error: Blender not found. Please install Blender or specify -BlenderPath" -ForegroundColor Red
    exit 1
}

$blenderExe = Get-BlenderVulkanStartupPath -BlenderExePath $blenderExe
Write-Host ""

# Determine which script to use
if ($sketchSource -and (Test-Path $sketchSource)) {
    if ($ProcessAsLineDrawing) {
        # Use line drawing processor
        $bakeScript = Join-Path $PSScriptRoot "..\Common\line_drawing_processor.py"
        if (-not (Test-Path $bakeScript)) {
            Write-Host "Error: line_drawing_processor.py not found at: $bakeScript" -ForegroundColor Red
            exit 1
        }
        Write-Host "Using line drawing processor pipeline" -ForegroundColor Cyan
        Write-Host "  Mapping Strategy: $MappingStrategy" -ForegroundColor Gray
    } else {
        # Use sketch-to-mesh pipeline
        $bakeScript = Join-Path $PSScriptRoot "..\Common\sketch_to_mesh.py"
        if (-not (Test-Path $bakeScript)) {
            Write-Host "Error: sketch_to_mesh.py not found at: $bakeScript" -ForegroundColor Red
            exit 1
        }
        Write-Host "Using sketch-to-mesh pipeline" -ForegroundColor Cyan
    }
} else {
    Write-Host "Error: no sketch and SD PBR path should have exited earlier" -ForegroundColor Red
    exit 1
}

# Convert texture config to JSON
$textureConfigJson = $textureConfig | ConvertTo-Json -Compress

# Build Blender command
if ($sketchSource -and (Test-Path $sketchSource)) {
    if ($ProcessAsLineDrawing) {
        # Line drawing processor pipeline
        $blenderArgs = @(
            "--background",
            "--python", "`"$bakeScript`"",
            "--",
            "--lineDrawing", "`"$sketchSource`"",
            "--registry", "`"$RegistryPath`"",
            "--assetId", "`"$AssetId`"",
            "--mappingStrategy", $MappingStrategy
        )
    } else {
        # Sketch-to-mesh pipeline
        $blenderArgs = @(
            "--background",
            "--python", "`"$bakeScript`"",
            "--",
            "--sketch", "`"$sketchSource`"",
            "--registry", "`"$RegistryPath`"",
            "--assetId", "`"$AssetId`""
        )
    }
    
    if (-not [string]::IsNullOrWhiteSpace($BlendOutputPath)) {
        $blenderArgs += "--output"
        $blenderArgs += "`"$BlendOutputPath`""
    } else {
        $blendPath = Join-Path $OutputDir "$AssetId`_sketch.blend"
        $blenderArgs += "--output"
        $blenderArgs += "`"$blendPath`""
    }
} else {
    Write-Host "Error: missing sketch; SD PBR path should have already exited" -ForegroundColor Red
    exit 1
}

if ($ExportNodeGroups) {
    $blenderArgs += "--exportNodeGroups"
    if (-not [string]::IsNullOrWhiteSpace($BlendOutputPath)) {
        $blenderArgs += "--blendOutput"
        $blenderArgs += "`"$BlendOutputPath`""
    } else {
        $blendPath = Join-Path $OutputDir "$AssetId`_material.blend"
        $blenderArgs += "--blendOutput"
        $blenderArgs += "`"$blendPath`""
    }
    Write-Host "  Node groups export: Enabled" -ForegroundColor Cyan
    Write-Host "  Blend file: $($blenderArgs[-1])" -ForegroundColor Gray
}

Write-Host "Generating textures..." -ForegroundColor Cyan
Write-Host "  Blender: $blenderExe" -ForegroundColor Gray
Write-Host "  Script: $bakeScript" -ForegroundColor Gray
Write-Host ""

try {
    # Use cmd.exe if it's a .cmd file, otherwise run directly
    if ($blenderExe -match '\.cmd$') {
        $processArgs = "/c `"$blenderExe`" $($blenderArgs -join ' ')"
        $process = Start-Process -FilePath "cmd.exe" -ArgumentList $processArgs -Wait -NoNewWindow -PassThru
    } else {
        $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
    }
    
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "  Texture Generation Complete!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        
        # List generated files
        Write-Host "Generated textures:" -ForegroundColor Cyan
        Get-ChildItem -Path $OutputDir -Filter "*.png" -File | ForEach-Object {
            $fileSize = [math]::Round($_.Length / 1KB, 2)
            Write-Host "  - $($_.Name) ($fileSize KB)" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "Output directory: $OutputDir" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Error: Texture generation failed (exit code: $($process.ExitCode))" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "Error running Blender: $_" -ForegroundColor Red
    exit 1
}

