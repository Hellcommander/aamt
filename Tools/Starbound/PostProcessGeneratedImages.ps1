#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Post-processes all AI-generated images in a directory with ImageMagick.
    
.DESCRIPTION
    Scans a directory for AI-generated images and processes them with ImageMagick
    to ensure game compatibility, optimal quality, and consistent format.
    
.PARAMETER InputDir
    Directory containing AI-generated images
    
.PARAMETER GameType
    Game type for format requirements (default: Starbound)
    
.PARAMETER Quality
    Quality level: low, medium, high, ultra (default: high)
    
.PARAMETER Recursive
    Process images recursively in subdirectories
    
.EXAMPLE
    .\PostProcessGeneratedImages.ps1 -InputDir ".\generated\" -GameType "Starbound"
    
.EXAMPLE
    .\PostProcessGeneratedImages.ps1 -InputDir ".\assets\" -Recursive -Quality "ultra"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$InputDir,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Starbound", "Qud", "Terraria", "CDDA", "Soulash", "Elin", "Generic")]
    [string]$GameType = "Starbound",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("low", "medium", "high", "ultra")]
    [string]$Quality = "high",
    
    [Parameter(Mandatory=$false)]
    [switch]$Recursive
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load shared settings
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Load post-processor module
$postProcessorPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\ImageMagickPostProcessor.psm1"
if (-not (Test-Path $postProcessorPath)) {
    Write-Host "Error: ImageMagickPostProcessor.psm1 not found" -ForegroundColor Red
    Write-Host "  Expected at: $postProcessorPath" -ForegroundColor Gray
    exit 1
}

Import-Module $postProcessorPath -Force

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Post-Process AI-Generated Images" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $InputDir)) {
    Write-Host "Error: Input directory not found: $InputDir" -ForegroundColor Red
    exit 1
}

Write-Host "Input Directory: $InputDir" -ForegroundColor Green
Write-Host "Game Type: $GameType" -ForegroundColor Green
Write-Host "Quality: $Quality" -ForegroundColor Green
Write-Host "Recursive: $Recursive" -ForegroundColor Green
Write-Host ""

# Find all image files
$imageExtensions = @("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp")
$images = @()

foreach ($ext in $imageExtensions) {
    if ($Recursive) {
        $images += Get-ChildItem -Path $InputDir -Filter $ext -Recurse -File
    } else {
        $images += Get-ChildItem -Path $InputDir -Filter $ext -File
    }
}

if ($images.Count -eq 0) {
    Write-Host "No images found in: $InputDir" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($images.Count) image(s) to process" -ForegroundColor Yellow
Write-Host ""

# Process images
$imagePaths = $images | ForEach-Object { $_.FullName }
$result = Process-AIGeneratedImages `
    -InputPaths $imagePaths `
    -GameType $GameType `
    -Quality $Quality

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Processing Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Processed: $($result.Processed)" -ForegroundColor Green
Write-Host "Failed: $($result.Failed)" -ForegroundColor $(if ($result.Failed -gt 0) { "Red" } else { "Gray" })
Write-Host ""
