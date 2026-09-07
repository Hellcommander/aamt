#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Export assets as Caves of Qud tiles.
    
.DESCRIPTION
    Exports assets from the registry as individual PNG tiles in Qud's format.
    Supports 24x24, 32x32, and 48x48 tile sizes, animation frames, and mod metadata generation.
    
.PARAMETER RegistryPath

# AI-Assisted Modding Tools (AAMT) - Caves of Qud Toolset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for Qud tile export
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Blender", "ImageMagick") `
    -OptionalTools @()

if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Qud tile export" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Caves of Qud" `
        -RequiredTools @("Blender", "ImageMagick")
    exit 1
}
    Path to the asset registry JSON file.
    
.PARAMETER AssetId
    Asset ID from the registry to export.
    
.PARAMETER OutputDir
    Output directory for Qud tiles.
    
.PARAMETER TileSize
    Tile size: 24 (classic), 32 (default), or 48 (high-res).
    
.PARAMETER Animated
    Generate animation frames.
    
.PARAMETER FrameCount
    Number of animation frames (if animated).
    
.PARAMETER BlenderPath
    Path to Blender executable (auto-detected if not provided).
    
.EXAMPLE
    .\ExportQudTiles.ps1 -RegistryPath "registry.json" -AssetId "nature_verdant_pulse" -OutputDir "QudTiles"
    
.EXAMPLE
    .\ExportQudTiles.ps1 -RegistryPath "registry.json" -AssetId "spell_fireball" -OutputDir "QudTiles" -Animated -FrameCount 8
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$RegistryPath,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetId,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet(24, 32, 48)]
    [int]$TileSize = 32,
    
    [Parameter(Mandatory=$false)]
    [switch]$Animated,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 4,
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("xml", "json")]
    [string]$MetadataFormat = "xml"
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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
    
    Write-Error "Blender not found. Please install Blender or set BLENDER_PATH environment variable."
    return $null
}
    $commonPaths = @(
        "D:\tools\Blender Foundation",
        "${env:ProgramFiles}\Blender Foundation"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending
            
            foreach ($dir in $blenderDirs) {
                $blenderExe = Join-Path $dir.FullName "blender.exe"
                if (Test-Path $blenderExe) {
                    return $blenderExe
                }
            }
        }
    }
    
    return $null
}

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Caves of Qud Tile Exporter" -ForegroundColor Cyan
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

# Get Qud export settings
$qudExport = $entry.export.qud
if ($qudExport) {
    $TileSize = if ($qudExport.tileSize) { $qudExport.tileSize } else { $TileSize }
    $Animated = if ($qudExport.animated) { $true } else { $Animated }
    $FrameCount = if ($qudExport.frameCount) { $qudExport.frameCount } else { $FrameCount }
    $MetadataFormat = if ($qudExport.metadataFormat) { $qudExport.metadataFormat } else { $MetadataFormat }
}

Write-Host "  Tile Size: ${TileSize}x${TileSize}" -ForegroundColor Gray
Write-Host "  Animated: $Animated" -ForegroundColor Gray
if ($Animated) {
    Write-Host "  Frame Count: $FrameCount" -ForegroundColor Gray
}
Write-Host ""

# Determine output directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "QudTiles" $AssetId
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "Output Directory: $OutputDir" -ForegroundColor Cyan
Write-Host ""

# Get quality from registry
$quality = if ($entry.generation -and $entry.generation.quality) {
    $entry.generation.quality
} else {
    "standard"
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

# Prepare Qud tile export script
$qudScript = Join-Path $PSScriptRoot "qud_tile_exporter.py"
if (-not (Test-Path $qudScript)) {
    Write-Host "Error: qud_tile_exporter.py not found at: $qudScript" -ForegroundColor Red
    exit 1
}

# Build Blender command
$tileName = $AssetId -replace '[^a-zA-Z0-9_]', '_'  # Sanitize for filename

$blenderArgs = @(
    "--background",
    "--python", "`"$qudScript`"",
    "--",
    "--registry", "`"$RegistryPath`"",
    "--assetId", "`"$AssetId`"",
    "--tileName", "`"$tileName`"",
    "--outputDir", "`"$OutputDir`"",
    "--size", $TileSize,
    "--quality", $quality,
    "--metadataFormat", $MetadataFormat
)

if ($Animated) {
    $blenderArgs += "--animated"
    $blenderArgs += "--frameCount"
    $blenderArgs += $FrameCount
}

Write-Host "Exporting Qud tiles..." -ForegroundColor Cyan
Write-Host "  Script: $qudScript" -ForegroundColor Gray
Write-Host ""

try {
    $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "  Qud Tile Export Complete!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        
        # List generated files
        Write-Host "Generated tiles:" -ForegroundColor Cyan
        Get-ChildItem -Path $OutputDir -Filter "*.png" -File | ForEach-Object {
            $fileSize = [math]::Round($_.Length / 1KB, 2)
            Write-Host "  - $($_.Name) ($fileSize KB)" -ForegroundColor Gray
        }
        
        $metadataFiles = Get-ChildItem -Path $OutputDir -Filter "*.$MetadataFormat" -File
        if ($metadataFiles) {
            Write-Host ""
            Write-Host "Metadata files:" -ForegroundColor Cyan
            $metadataFiles | ForEach-Object {
                Write-Host "  - $($_.Name)" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        Write-Host "Output directory: $OutputDir" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Error: Qud tile export failed (exit code: $($process.ExitCode))" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "Error running Blender: $_" -ForegroundColor Red
    exit 1
}

