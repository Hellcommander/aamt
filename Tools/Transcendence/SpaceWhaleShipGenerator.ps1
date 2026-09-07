# Space Whale Ship Generator
# Orchestrates the complete pipeline for generating playable space whale ships

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "space_whale_ship_example.json",
    
    [Parameter(Mandatory=$false)]
    [string]$ShipId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TestOutput/SpaceWhaleShips",
    
    [Parameter(Mandatory=$false)]
    [int]$Frames = 16,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBlender = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipXML = $false
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Configuration
. (Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\ToolPaths.ps1")
$BlenderPath = Get-AamtBlenderPath
if (-not $BlenderPath) { $BlenderPath = "E:\tools\Blender Foundation\Blender 5.2\blender.exe" }
$ToolsDir = $PSScriptRoot
$RegistryFile = Join-Path $ToolsDir $RegistryPath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Space Whale Ship Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate registry
Write-Host "Validating registry..." -ForegroundColor Yellow
$schemaPath = Join-Path $ToolsDir "space_whale_ship_registry_schema.json"
if (Test-Path $schemaPath) {
    python (Join-Path $ToolsDir "validate_registry.py") --registry $RegistryFile --schema $schemaPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Registry validation failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Schema not found, skipping validation" -ForegroundColor Yellow
}

# Create output directories
$blenderOutput = Join-Path $OutputDir "Blender"
$xmlOutput = Join-Path $OutputDir "XML"
New-Item -ItemType Directory -Force -Path $blenderOutput | Out-Null
New-Item -ItemType Directory -Force -Path $xmlOutput | Out-Null

# Blender rendering
if (-not $SkipBlender) {
    if (Test-Path $BlenderPath) {
        Write-Host "Rendering ship with Blender..." -ForegroundColor Yellow
        
        $blenderScript = Join-Path $ToolsDir "blender_space_whale_renderer.py"
        $blenderArgs = @(
            "--background",
            "--python", $blenderScript,
            "--",
            "--registry", $RegistryFile,
            "--output-dir", (Resolve-Path $blenderOutput).Path,
            "--frames", $Frames
        )
        
        if ($ShipId) {
            $blenderArgs += "--ship-id", $ShipId
        }
        
        & $BlenderPath $blenderArgs 2>&1 | Out-Host
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Blender rendering failed!" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Blender rendering complete!" -ForegroundColor Green
    } else {
        Write-Host "Blender not found at: $BlenderPath" -ForegroundColor Yellow
        Write-Host "Skipping Blender rendering..." -ForegroundColor Yellow
    }
} else {
    Write-Host "Skipping Blender rendering (--SkipBlender)" -ForegroundColor Yellow
}

# XML export
if (-not $SkipXML) {
    Write-Host "Exporting XML..." -ForegroundColor Yellow
    
    $exporterScript = Join-Path $ToolsDir "transcendence_space_whale_exporter.py"
    $exporterArgs = @(
        "--registry", $RegistryFile,
        "--output-dir", (Resolve-Path $xmlOutput).Path
    )
    
    if ($ShipId) {
        $exporterArgs += "--ship-id", $ShipId
    }
    
    python $exporterScript $exporterArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "XML export failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "XML export complete!" -ForegroundColor Green
} else {
    Write-Host "Skipping XML export (--SkipXML)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Generation complete!" -ForegroundColor Green
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

