#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bake line drawings to Caves of Qud tiles.
    
.DESCRIPTION
    Takes your line-based drawings and converts them to Qud-ready tiles (32×32, 24×24, or 48×48)
    with procedural materials, node groups, and full editability.
    
.PARAMETER DrawingPath
    Path to your line drawing image (PNG, JPG, etc.).
    
.PARAMETER OutputPath
    Output PNG path for the Qud tile.
    
.PARAMETER RegistryPath
    Path to asset registry JSON (optional).
    
.PARAMETER AssetId
    Asset ID from registry (optional).
    
.PARAMETER TileSize
    Tile size: 24 (classic), 32 (default), or 48 (high-res).
    
.PARAMETER Palette
    Comma-separated hex colors (e.g., "#4caf50,#81c784,#2e7d32").
    
.PARAMETER Style
    Material style: painterly, pixel, flat, procedural.
    
.PARAMETER Quality
    Quality tier: draft, standard, high, ultra.
    
.PARAMETER ExportNodeGroups
    Save .blend file with editable node groups.
    
.PARAMETER BlendOutput
    Path for .blend file output.
    
.EXAMPLE
    .\BakeQudTile.ps1 -DrawingPath "drawings\spell_icon.png" -OutputPath "QudTiles\spell_icon.png"
    
.EXAMPLE
    .\BakeQudTile.ps1 -DrawingPath "drawings\ship.png" -OutputPath "QudTiles\ship.png" -RegistryPath "registry.json" -AssetId "ship_scout" -ExportNodeGroups
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DrawingPath,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetId = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet(24, 32, 48)]
    [int]$TileSize = 32,
    
    [Parameter(Mandatory=$false)]
    [string]$Palette = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("painterly", "pixel", "flat", "procedural")]
    [string]$Style = "painterly",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("draft", "standard", "high", "ultra")]
    [string]$Quality = "standard",
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportNodeGroups,
    
    [Parameter(Mandatory=$false)]
    [string]$BlendOutput = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("low", "medium", "high")]
    [string]$Contrast = "high",
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = ""
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# AI-Assisted Modding Tools (AAMT) - Caves of Qud Toolset

# Load shared asset generation settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# ------------------------------------------------------------
# Import Unified Tool Detection and Integration
# ------------------------------------------------------------

$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for Qud tile generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Blender", "ImageMagick") `
    -OptionalTools @()

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Qud tile generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Caves of Qud" `
        -RequiredTools @("Blender", "ImageMagick")
    exit 1
}

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

function Find-Blender {
    # Use unified tool detection (already checked at startup)
    $blenderPath = Get-BlenderPath
    if ($blenderPath) {
        return $blenderPath
    }
    
    # Fallback: Check provided path parameter
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
        $providedPath = $BlenderPath.Trim()
        if (Test-Path $providedPath) {
            return $providedPath
        }
    }
    
    # Should not reach here if tool detection worked, but provide error
    Write-Error "Blender not found. Please install Blender or set BLENDER_PATH environment variable."
    return $null
}

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Qud Tile Baker - Drawing to Tile Pipeline" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate drawing file
if (-not (Test-Path $DrawingPath)) {
    Write-Host "Error: Drawing file not found: $DrawingPath" -ForegroundColor Red
    exit 1
}

Write-Host "Drawing: $DrawingPath" -ForegroundColor Green
Write-Host "Output: $OutputPath" -ForegroundColor Green
Write-Host "Size: ${TileSize}x${TileSize}" -ForegroundColor Gray
Write-Host ""

# Load from registry if provided
if (-not [string]::IsNullOrWhiteSpace($RegistryPath) -and -not [string]::IsNullOrWhiteSpace($AssetId)) {
    if (Test-Path $RegistryPath) {
        Write-Host "Loading from registry..." -ForegroundColor Cyan
        try {
            $registry = Get-Content $RegistryPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $entry = $registry.entries | Where-Object { $_.id -eq $AssetId } | Select-Object -First 1
            
            if ($entry) {
                $visual = $entry.visual
                $iconData = $visual.icon
                
                if ($iconData.palette -and [string]::IsNullOrWhiteSpace($Palette)) {
                    $Palette = $iconData.palette -join ","
                }
                
                if (-not [string]::IsNullOrWhiteSpace($iconData.style)) {
                    $Style = $iconData.style
                }
                
                if (-not [string]::IsNullOrWhiteSpace($iconData.contrast)) {
                    $Contrast = $iconData.contrast
                }
                
                $generation = $entry.generation
                if ($generation -and -not [string]::IsNullOrWhiteSpace($generation.quality)) {
                    $Quality = $generation.quality
                }
                
                if ($generation -and $generation.exportNodeGroups) {
                    $ExportNodeGroups = $true
                }
                
                Write-Host "  Loaded: $($entry.name)" -ForegroundColor Gray
            }
        }
        catch {
            Write-Host "  Warning: Could not load registry: $_" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

# Ensure output directory exists
$outputDir = Split-Path -Parent $OutputPath
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Set blend output if node groups enabled
if ($ExportNodeGroups -and [string]::IsNullOrWhiteSpace($BlendOutput)) {
    $BlendOutput = [System.IO.Path]::ChangeExtension($OutputPath, ".blend")
}

# Find Blender
Write-Host "Detecting Blender..." -ForegroundColor Cyan
$blenderExe = Find-Blender
if (-not $blenderExe) {
    Write-Host "Error: Blender not found. Please install Blender or specify -BlenderPath" -ForegroundColor Red
    exit 1
}

Write-Host "  Found: $blenderExe" -ForegroundColor Green
Write-Host ""

# Prepare script
$bakerScript = Join-Path $PSScriptRoot "qud_tile_baker.py"
if (-not (Test-Path $bakerScript)) {
    Write-Host "Error: qud_tile_baker.py not found at: $bakerScript" -ForegroundColor Red
    exit 1
}

# Build Blender command
$blenderArgs = @(
    "--background",
    "--python", "`"$bakerScript`"",
    "--",
    "--drawing", "`"$DrawingPath`"",
    "--size", $TileSize,
    "--output", "`"$OutputPath`"",
    "--style", $Style,
    "--quality", $Quality,
    "--contrast", $Contrast
)

if (-not [string]::IsNullOrWhiteSpace($Palette)) {
    $blenderArgs += "--palette"
    $blenderArgs += "`"$Palette`""
}

if (-not [string]::IsNullOrWhiteSpace($RegistryPath) -and -not [string]::IsNullOrWhiteSpace($AssetId)) {
    $blenderArgs += "--registry"
    $blenderArgs += "`"$RegistryPath`""
    $blenderArgs += "--assetId"
    $blenderArgs += "`"$AssetId`""
}

if ($ExportNodeGroups) {
    $blenderArgs += "--exportNodeGroups"
    if (-not [string]::IsNullOrWhiteSpace($BlendOutput)) {
        $blenderArgs += "--blendOutput"
        $blenderArgs += "`"$BlendOutput`""
    }
}

Write-Host "Baking Qud tile..." -ForegroundColor Cyan
Write-Host "  Script: $bakerScript" -ForegroundColor Gray
Write-Host ""

try {
    $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "  Qud Tile Bake Complete!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        
        if (Test-Path $OutputPath) {
            $fileSize = [math]::Round((Get-Item $OutputPath).Length / 1KB, 2)
            Write-Host "Tile: $OutputPath" -ForegroundColor Green
            Write-Host "  Size: ${TileSize}x${TileSize}" -ForegroundColor Gray
            Write-Host "  File Size: $fileSize KB" -ForegroundColor Gray
        }
        
        if ($ExportNodeGroups -and (Test-Path $BlendOutput)) {
            Write-Host ""
            Write-Host "Blend File: $BlendOutput" -ForegroundColor Green
            Write-Host "  (Editable with node groups)" -ForegroundColor Gray
        }
        
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Error: Qud tile bake failed (exit code: $($process.ExitCode))" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "Error running Blender: $_" -ForegroundColor Red
    exit 1
}

