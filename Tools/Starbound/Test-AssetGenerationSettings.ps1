#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests the shared asset generation settings configuration.
    
.DESCRIPTION
    Verifies that all shared settings are properly configured and accessible.
#>

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Asset Generation Settings Test" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Load shared settings
$settingsPath = Join-Path $PSScriptRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
    Write-Host "✓ Settings file loaded: $settingsPath" -ForegroundColor Green
} else {
    Write-Host "✗ Settings file not found: $settingsPath" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test ImageMagick configuration
Write-Host "ImageMagick Configuration:" -ForegroundColor Yellow
Write-Host "  Configured Path: $script:ImageMagickPath" -ForegroundColor Gray
Write-Host "  Executable: $script:ImageMagickExe" -ForegroundColor Gray

if (Test-ImageMagickAvailable) {
    $magickPath = Get-ImageMagickPath
    Write-Host "  ✓ ImageMagick is available at: $magickPath" -ForegroundColor Green
    
    # Test version
    try {
        $version = & $magickPath -version 2>&1 | Select-Object -First 1
        Write-Host "  Version: $version" -ForegroundColor Gray
    } catch {
        Write-Host "  ⚠ Could not get version" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ ImageMagick is not available" -ForegroundColor Red
    Write-Host "    Expected at: $script:ImageMagickExe" -ForegroundColor Gray
}

Write-Host ""

# Test output directories
Write-Host "Output Directories:" -ForegroundColor Yellow
Write-Host "  Default: $script:DefaultOutputDir" -ForegroundColor Gray
Write-Host "  Spellstone: $script:SpellstoneOutputDir" -ForegroundColor Gray

if (Test-Path $script:DefaultOutputDir) {
    Write-Host "  ✓ Default output directory exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Default output directory does not exist (will be created)" -ForegroundColor Yellow
}

Write-Host ""

# Test Ollama configuration
Write-Host "Ollama Configuration:" -ForegroundColor Yellow
Write-Host "  URL: $script:OllamaUrl" -ForegroundColor Gray
Write-Host "  Model: $script:OllamaModel" -ForegroundColor Gray
Write-Host "  Planning Model: $script:PlanningModel" -ForegroundColor Gray
Write-Host "  Visual Model: $script:VisualModel" -ForegroundColor Gray

Write-Host ""

# Test defaults
Write-Host "Default Settings:" -ForegroundColor Yellow
Write-Host "  Variants: $script:DefaultVariants" -ForegroundColor Gray
Write-Host "  Animation Frames: $script:DefaultAnimationFrames" -ForegroundColor Gray

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
