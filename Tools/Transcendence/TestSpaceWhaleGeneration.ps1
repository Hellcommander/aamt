#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test Space Whale Generation - Creates a simple tiny space whale
    Quick test to verify all systems work with minimal variations
#>

param(
    [int]$Variations = 5,
    [string]$OutputDir = "Output/TestSpaceWhale"
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Space Whale Generation Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will generate a simple tiny space whale with:" -ForegroundColor Yellow
$variationsText = "$Variations variations per asset type (instead of 150)"
Write-Host "  - $variationsText" -ForegroundColor Gray
Write-Host "  - All core systems tested" -ForegroundColor Gray
Write-Host "  - Quick verification" -ForegroundColor Gray
Write-Host ""

# Create output directory
$outputPath = Join-Path $PSScriptRoot $OutputDir
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    Write-Host "Created output directory: $outputPath" -ForegroundColor Green
}

$startTime = Get-Date

# Test 1: Visual Language
Write-Host "[1/4] Testing Visual Language Generator..." -ForegroundColor Yellow
$visualScript = Join-Path $PSScriptRoot "..\Common\ollama_visual_variation_generator.py"
if (Test-Path $visualScript) {
    try {
        python $visualScript `
            --registry "space_whale_visual_language_registry.json" `
            --output "$outputPath\VisualLanguage" `
            --count $Variations `
            --model "wizardlm-uncensored:latest" 2>&1 | Out-Host
        Write-Host "  ✓ Visual Language test complete" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Visual Language test failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Visual Language script not found" -ForegroundColor Yellow
}

# Test 2: FX Assets
Write-Host "[2/4] Testing FX Assets Generator..." -ForegroundColor Yellow
$fxScript = Join-Path $PSScriptRoot "space_whale_fx_variation_generator.py"
if (Test-Path $fxScript) {
    try {
        python $fxScript "space_whale_fx_registry.json" $Variations 3 2>&1 | Out-Host
        Write-Host "  ✓ FX Assets test complete" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ FX Assets test failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ FX Assets script not found" -ForegroundColor Yellow
}

# Test 3: Audio Assets
Write-Host "[3/4] Testing Audio Assets Generator..." -ForegroundColor Yellow
$audioScript = Join-Path $PSScriptRoot "space_whale_audio_generator.py"
$audioRegistry = Join-Path $PSScriptRoot "space_whale_audio_registry.json"
if (Test-Path $audioScript -and (Test-Path $audioRegistry)) {
    try {
        python $audioScript `
            --registry $audioRegistry `
            --output "$outputPath\Audio" `
            --variations $Variations 2>&1 | Out-Host
        Write-Host "  ✓ Audio Assets test complete" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Audio Assets test failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Audio Assets script or registry not found" -ForegroundColor Yellow
}

# Test 4: Textures
Write-Host "[4/4] Testing Texture Generator..." -ForegroundColor Yellow
$textureScript = Join-Path $PSScriptRoot "space_whale_texture_generator.py"
$shipRegistry = Join-Path $PSScriptRoot "space_whale_ship_example.json"
$visualRegistry = Join-Path $PSScriptRoot "space_whale_visual_language_registry.json"
$skinningRegistry = Join-Path $PSScriptRoot "space_whale_skinning_registry.json"

if ((Test-Path $textureScript) -and 
    (Test-Path $shipRegistry) -and 
    (Test-Path $visualRegistry) -and 
    (Test-Path $skinningRegistry)) {
    try {
        python $textureScript `
            --ship-registry $shipRegistry `
            --visual-registry $visualRegistry `
            --skinning-registry $skinningRegistry `
            --output "$outputPath\Textures" 2>&1 | Out-Host
        Write-Host "  ✓ Texture Generator test complete" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Texture Generator test failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Texture Generator script or registries not found" -ForegroundColor Yellow
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Duration: $($duration.TotalSeconds) seconds" -ForegroundColor Gray
Write-Host "Output directory: $outputPath" -ForegroundColor Gray
Write-Host ""

# Check what was generated
Write-Host "Generated Files:" -ForegroundColor Yellow
$files = Get-ChildItem -Path $outputPath -Recurse -File -ErrorAction SilentlyContinue
if ($files) {
    foreach ($file in $files) {
        $relativePath = $file.FullName.Replace($outputPath, "").TrimStart("\")
        Write-Host "  ✓ $relativePath" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Total files: $($files.Count)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ No files generated" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "If all tests passed, the system is working correctly!" -ForegroundColor Green
Write-Host "You can now run the full generation." -ForegroundColor Cyan
