# Space Whale Visual Language Generator
# Generates visual language assets: color palettes, materials, style guides

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "space_whale_visual_language_registry.json",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/VisualLanguage",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipGeneration
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "Space Whale Visual Language Generator" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if registry exists
if (-not (Test-Path $RegistryPath)) {
    Write-Host "ERROR: Registry file not found: $RegistryPath" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Load registry
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$visualLang = $registry.visualLanguage

Write-Host "Visual Language Registry Loaded" -ForegroundColor Green
Write-Host ""

# Display summary
$palettes = $visualLang.colorPalettes
$materials = $visualLang.materials
$patterns = $visualLang.texturePatterns
$animations = $visualLang.animations
$effects = $visualLang.effects

Write-Host "Registry Contents:" -ForegroundColor Yellow
Write-Host "  Color Palettes: $($palettes.PSObject.Properties.Count)" -ForegroundColor Gray
Write-Host "  Materials: $($materials.PSObject.Properties.Count)" -ForegroundColor Gray
Write-Host "  Texture Patterns: $($patterns.PSObject.Properties.Count)" -ForegroundColor Gray
Write-Host "  Animations: $($animations.PSObject.Properties.Count)" -ForegroundColor Gray
Write-Host "  Effects: $($effects.PSObject.Properties.Count)" -ForegroundColor Gray
Write-Host ""

if (-not $SkipGeneration) {
    # Check for Python and PIL
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        Write-Host "WARNING: Python not found. Skipping asset generation." -ForegroundColor Yellow
        Write-Host "Install Python and PIL (Pillow): pip install Pillow numpy" -ForegroundColor Yellow
    } else {
        Write-Host "Generating visual language assets..." -ForegroundColor Yellow
        
        $generatorScript = "space_whale_visual_asset_generator.py"
        
        if (Test-Path $generatorScript) {
            & python $generatorScript --registry $RegistryPath --output $OutputDir
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Visual language asset generation complete!" -ForegroundColor Green
            } else {
                Write-Host "WARNING: Asset generation may have failed" -ForegroundColor Yellow
            }
        } else {
            Write-Host "WARNING: Generator script not found: $generatorScript" -ForegroundColor Yellow
        }
    }
}

# Display color palettes
Write-Host ""
Write-Host "Color Palettes:" -ForegroundColor Yellow
foreach ($paletteName in $palettes.PSObject.Properties.Name) {
    $palette = $palettes.$paletteName
    Write-Host "  $($palette.name) : $($palette.useCase)" -ForegroundColor Gray
    Write-Host "    Base: $($palette.baseColor), Vein: $($palette.veinColor)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Visual language processing complete!" -ForegroundColor Green
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan

