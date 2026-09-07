#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Update animation files to reference newly generated spritesheets.
    
.DESCRIPTION
    Updates .animation files to use generated spritesheets instead of placeholder assets.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Updating Animation Sprite References" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if animations directory exists
# Validate $ModPath before Join-Path
$animationsDir = Join-Path $ModPath "assets\animations"
 if ([string]::IsNullOrWhiteSpace($animationsDir)) {
    Write-Host "  [FAIL] animationsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($animationsDir)) {
    Write-Host "  [FAIL] animationsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $animationsDir)) {
    Write-Host "Error: Animations directory not found: $animationsDir" -ForegroundColor Red
    Write-Host "Run GenerateAnimationSprites.ps1 first to generate animations." -ForegroundColor Yellow
    exit 1
}

# Get all generated animations
$generatedAnimations = Get-ChildItem -Path $animationsDir -Directory | ForEach-Object {
    $_.Name
}

Write-Host "Found $($generatedAnimations.Count) generated animations" -ForegroundColor Green
Write-Host ""

# Update magitech_device.animation
# Validate $ModPath before Join-Path
$magitechAnimFile = Join-Path $ModPath "animations\magitech\magitech_device.animation"
 if ([string]::IsNullOrWhiteSpace($magitechAnimFile)) {
    Write-Host "  [FAIL] magitechAnimFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($magitechAnimFile)) {
    Write-Host "  [FAIL] magitechAnimFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $magitechAnimFile -and $generatedAnimations -contains "magitech_device") {
    Write-Host "Updating magitech_device.animation..." -ForegroundColor Cyan
    
    $content = Get-Content $magitechAnimFile -Raw
    $data = $content | ConvertFrom-Json
    
    # Update image paths to use generated spritesheet
    if ($data.animatedParts.parts.device) {
        $data.animatedParts.parts.device.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.device.partStates.activation.inactive.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.device.partStates.activation.active.properties.image = "/animations/magitech_device/magitech_device.png"
    }
    
    if ($data.animatedParts.parts.deviceFullbright) {
        $data.animatedParts.parts.deviceFullbright.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.deviceFullbright.partStates.activation.inactive.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.deviceFullbright.partStates.activation.active.properties.image = "/animations/magitech_device/magitech_device.png"
    }
    
    $jsonContent = $data | ConvertTo-Json -Depth 20
    $jsonContent = $jsonContent -replace '(?<="):\s*', ' : '
    $jsonContent | Set-Content -Path $magitechAnimFile -Encoding UTF8
    
    Write-Host "  Updated: magitech_device.animation" -ForegroundColor Green
    Write-Host ""
}

# Update mt_magitech_device.animation
# Validate $ModPath before Join-Path
$mtMagitechAnimFile = Join-Path $ModPath "animations\magitech\mt_magitech_device.animation"
 if ([string]::IsNullOrWhiteSpace($mtMagitechAnimFile)) {
    Write-Host "  [FAIL] mtMagitechAnimFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($mtMagitechAnimFile)) {
    Write-Host "  [FAIL] mtMagitechAnimFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $mtMagitechAnimFile -and $generatedAnimations -contains "magitech_device") {
    Write-Host "Updating mt_magitech_device.animation..." -ForegroundColor Cyan
    
    $content = Get-Content $mtMagitechAnimFile -Raw
    $data = $content | ConvertFrom-Json
    
    # Update image paths
    if ($data.animatedParts.parts.device) {
        $data.animatedParts.parts.device.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.device.partStates.activation.inactive.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.device.partStates.activation.active.properties.image = "/animations/magitech_device/magitech_device.png"
    }
    
    if ($data.animatedParts.parts.deviceFullbright) {
        $data.animatedParts.parts.deviceFullbright.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.deviceFullbright.partStates.activation.inactive.properties.image = "/animations/magitech_device/magitech_device.png"
        $data.animatedParts.parts.deviceFullbright.partStates.activation.active.properties.image = "/animations/magitech_device/magitech_device.png"
    }
    
    $jsonContent = $data | ConvertTo-Json -Depth 20
    $jsonContent = $jsonContent -replace '(?<="):\s*', ' : '
    $jsonContent | Set-Content -Path $mtMagitechAnimFile -Encoding UTF8
    
    Write-Host "  Updated: mt_magitech_device.animation" -ForegroundColor Green
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Update Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "All animation files have been updated to reference generated spritesheets." -ForegroundColor Green
Write-Host ""
