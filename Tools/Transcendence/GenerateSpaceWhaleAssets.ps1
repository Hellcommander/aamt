# Space Whale Comprehensive Asset Generator
# Generates 150 variations of each asset type with detailed AI descriptions and quality checking

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/SpaceWhaleComprehensive",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "wizardlm-uncensored:latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseGUI
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Space Whale Comprehensive Asset Generator" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generating 150 variations of each asset type:" -ForegroundColor Yellow
Write-Host "  - Visual Language (color palettes, materials)" -ForegroundColor Gray
Write-Host "  - FX Assets (all 10 systems)" -ForegroundColor Gray
Write-Host "  - Audio Assets (all 4 channels)" -ForegroundColor Gray
Write-Host "  - Textures (for rigging and spritesheets)" -ForegroundColor Gray
Write-Host "  - Quality checking and reporting" -ForegroundColor Gray
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

if ($UseGUI) {
    Write-Host "Launching GUI for progress tracking..." -ForegroundColor Green
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $PSScriptRoot "SpaceWhaleAssetGeneratorGUI.ps1")
    ) -WindowStyle Normal
    Write-Host "GUI launched. Check the window for progress." -ForegroundColor Cyan
    exit 0
}

# Generate Visual Language (150 variations)
Write-Host "[1/4] Generating Visual Language Assets (150 variations)..." -ForegroundColor Yellow
$visualScript = Join-Path $PSScriptRoot "..\Common\ollama_visual_variation_generator.py"
if (Test-Path $visualScript) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python $visualScript --registry "space_whale_visual_language_registry.json" --output (Join-Path $OutputDir "VisualLanguage") --count 150 --model $OllamaModel
        Write-Host "  ✅ Visual Language generation complete" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Python not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  Visual generator not found" -ForegroundColor Yellow
}
Write-Host ""

# Generate FX Assets (150 variations)
Write-Host "[2/4] Generating FX Assets (150 variations per effect)..." -ForegroundColor Yellow
$fxScript = Join-Path $PSScriptRoot "space_whale_fx_variation_generator.py"
if (Test-Path $fxScript) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python $fxScript "space_whale_fx_registry.json" 150 10
        Write-Host "  ✅ FX generation complete" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Python not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  FX generator not found" -ForegroundColor Yellow
}
Write-Host ""

# Generate Audio Assets
Write-Host "[3/5] Generating Audio Assets..." -ForegroundColor Yellow
$audioScript = Join-Path $PSScriptRoot "SpaceWhaleAudioGenerator.ps1"
if (Test-Path $audioScript) {
    & $audioScript -RegistryPath "space_whale_audio_registry.json" -OutputDir (Join-Path $OutputDir "Audio")
    Write-Host "  ✅ Audio generation complete" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Audio generator not found" -ForegroundColor Yellow
}
Write-Host ""

# Generate Textures for Rigging
Write-Host "[4/5] Generating Textures for Rigging..." -ForegroundColor Yellow
$textureScript = Join-Path $PSScriptRoot "space_whale_texture_generator.py"
if (Test-Path $textureScript) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python $textureScript --ship-registry "space_whale_ship_example.json" --visual-registry "space_whale_visual_language_registry.json" --skinning-registry "space_whale_skinning_registry.json" --output (Join-Path $OutputDir "Textures")
        Write-Host "  ✅ Texture generation complete" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Python not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  Texture generator not found" -ForegroundColor Yellow
}
Write-Host ""

# Quality Check
Write-Host "[5/5] Quality Checking and Reporting..." -ForegroundColor Yellow
$qualityScript = Join-Path $PSScriptRoot "space_whale_quality_checker.py"
if (Test-Path $qualityScript) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python $qualityScript $OutputDir
        Write-Host "  ✅ Quality check complete" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Python not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  Quality checker not found" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Comprehensive Asset Generation Complete!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Output Directory: $OutputDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review QUALITY_REPORT_LOW_SCORES.md" -ForegroundColor Gray
Write-Host "  2. Filter low-quality variations (score < 8.0)" -ForegroundColor Gray
Write-Host "  3. Select best variations for production" -ForegroundColor Gray
Write-Host "  4. Load textures in Blender for rigging" -ForegroundColor Gray
Write-Host "  5. Generate final spritesheets with Blender (120 facings)" -ForegroundColor Gray
Write-Host "  6. Export to Transcendence XML" -ForegroundColor Gray
Write-Host ""

