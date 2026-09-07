#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Starbound Asset Quality Checker - PowerShell Wrapper
    
.DESCRIPTION
    Checks quality of generated Starbound assets and keeps only the best ones.
    Similar to terraria_portal_quality_checker but adapted for Starbound assets.
    
.PARAMETER AssetsDir
    Path to the assets directory to check (default: mod assets directory)
    
.PARAMETER Threshold
    Quality threshold score (default: 7.0)
    
.PARAMETER DryRun
    Dry run mode - don't actually remove files, just report what would be removed
    
.EXAMPLE
    .\starbound_asset_quality_checker.ps1 -AssetsDir "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets"
    
.EXAMPLE
    .\starbound_asset_quality_checker.ps1 -Threshold 8.0 -DryRun
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$AssetsDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets",
    
    [Parameter(Mandatory=$false)]
    [double]$Threshold = 7.0,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Find Python script
$PythonScript = Join-Path $PSScriptRoot "starbound_asset_quality_checker.py"

if (-not (Test-Path $PythonScript)) {
    Write-Error "Python script not found: $PythonScript"
    exit 1
}

# Check for Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Error "Python not found in PATH. Please install Python or add it to your PATH."
    exit 1
}

# Build arguments
$args = @($PythonScript, $AssetsDir, "--threshold", $Threshold.ToString())
if ($DryRun) {
    $args += "--dry-run"
}

# Run quality checker
Write-Host "Running Starbound Asset Quality Checker..." -ForegroundColor Cyan
Write-Host "Assets Directory: $AssetsDir" -ForegroundColor Gray
Write-Host "Quality Threshold: $Threshold" -ForegroundColor Gray
if ($DryRun) {
    Write-Host "Mode: DRY RUN" -ForegroundColor Yellow
}
Write-Host ""

& $pythonCmd $args

if ($LASTEXITCODE -ne 0) {
    Write-Error "Quality checker exited with error code: $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Quality checking completed!" -ForegroundColor Green
