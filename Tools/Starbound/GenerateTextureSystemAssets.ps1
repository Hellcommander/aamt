#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the MeshTextureGenerator system.
    
.DESCRIPTION
    Generates palette files and material templates for:
    - Color palettes (JSON format)
    - Material texture templates
    - Example baked texture references
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

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
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  MeshTextureGenerator System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. COLOR PALETTE FILES (JSON)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Color Palette Files" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$paletteOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($paletteOutputDir)) {
    Write-Host "  [FAIL] paletteOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($paletteOutputDir)) {
    Write-Host "  [FAIL] paletteOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $paletteOutputDir)) {
    New-Item -ItemType Directory -Path $paletteOutputDir -Force | Out-Null
}

# Starbound Default Palette
$starboundDefaultPalette = @{
    name = "starbound_default"
    colorCount = 32
    isIndexed = $false
    colors = @(
        @{r=0.0; g=0.0; b=0.0; a=1.0},      # Black
        @{r=0.2; g=0.2; b=0.2; a=1.0},      # Dark gray
        @{r=0.4; g=0.4; b=0.4; a=1.0},      # Gray
        @{r=0.6; g=0.6; b=0.6; a=1.0},      # Light gray
        @{r=0.8; g=0.8; b=0.8; a=1.0},      # Very light gray
        @{r=1.0; g=1.0; b=1.0; a=1.0},      # White
        @{r=0.5; g=0.3; b=0.2; a=1.0},      # Brown
        @{r=0.7; g=0.5; b=0.3; a=1.0},      # Light brown
        @{r=0.3; g=0.5; b=0.2; a=1.0},      # Green
        @{r=0.5; g=0.7; b=0.3; a=1.0},      # Light green
        @{r=0.2; g=0.3; b=0.5; a=1.0},      # Blue
        @{r=0.3; g=0.5; b=0.7; a=1.0},      # Light blue
        @{r=0.5; g=0.2; b=0.3; a=1.0},      # Red
        @{r=0.7; g=0.3; b=0.5; a=1.0},      # Light red
        @{r=0.5; g=0.5; b=0.2; a=1.0},      # Yellow
        @{r=0.7; g=0.7; b=0.3; a=1.0},      # Light yellow
        @{r=0.2; g=0.5; b=0.5; a=1.0},      # Cyan
        @{r=0.3; g=0.7; b=0.7; a=1.0},      # Light cyan
        @{r=0.5; g=0.2; b=0.5; a=1.0},      # Magenta
        @{r=0.7; g=0.3; b=0.7; a=1.0},      # Light magenta
        @{r=0.8; g=0.6; b=0.4; a=1.0},      # Orange
        @{r=0.9; g=0.7; b=0.5; a=1.0},      # Light orange
        @{r=0.4; g=0.6; b=0.8; a=1.0},      # Sky blue
        @{r=0.5; g=0.7; b=0.9; a=1.0},      # Light sky blue
        @{r=0.6; g=0.4; b=0.8; a=1.0},      # Purple
        @{r=0.7; g=0.5; b=0.9; a=1.0},      # Light purple
        @{r=0.8; g=0.4; b=0.6; a=1.0},      # Pink
        @{r=0.9; g=0.5; b=0.7; a=1.0},      # Light pink
        @{r=0.4; g=0.8; b=0.6; a=1.0},      # Teal
        @{r=0.5; g=0.9; b=0.7; a=1.0},      # Light teal
        @{r=0.8; g=0.8; b=0.4; a=1.0},      # Lime
        @{r=0.9; g=0.9; b=0.5; a=1.0},      # Light lime
        @{r=0.0; g=0.0; b=0.0; a=0.0}       # Transparent
    )
}

$palettePath = Join-Path $paletteOutputDir "starbound_default.json"
$starboundDefaultPalette | ConvertTo-Json -Depth 10 | Out-File $palettePath -Encoding UTF8 -NoNewline
$generated++
Write-Host "  [OK] Generated: starbound_default.json" -ForegroundColor Green

# Starbound Warm Palette
$starboundWarmPalette = @{
    name = "starbound_warm"
    colorCount = 24
    isIndexed = $false
    colors = @(
        @{r=0.0; g=0.0; b=0.0; a=1.0},      # Black
        @{r=0.2; g=0.1; b=0.0; a=1.0},      # Dark brown
        @{r=0.4; g=0.2; b=0.0; a=1.0},      # Brown
        @{r=0.6; g=0.3; b=0.0; a=1.0},      # Light brown
        @{r=0.8; g=0.4; b=0.0; a=1.0},      # Orange brown
        @{r=1.0; g=0.5; b=0.0; a=1.0},      # Orange
        @{r=1.0; g=0.7; b=0.0; a=1.0},      # Yellow orange
        @{r=1.0; g=0.9; b=0.0; a=1.0},      # Yellow
        @{r=0.8; g=0.8; b=0.0; a=1.0},      # Olive
        @{r=0.6; g=0.6; b=0.0; a=1.0},      # Dark olive
        @{r=0.4; g=0.4; b=0.0; a=1.0},      # Very dark olive
        @{r=0.2; g=0.2; b=0.0; a=1.0},      # Almost black olive
        @{r=0.5; g=0.3; b=0.1; a=1.0},      # Red brown
        @{r=0.7; g=0.4; b=0.1; a=1.0},      # Light red brown
        @{r=0.9; g=0.5; b=0.1; a=1.0},      # Very light red brown
        @{r=0.3; g=0.2; b=0.1; a=1.0},      # Dark red brown
        @{r=0.1; g=0.1; b=0.0; a=1.0},      # Very dark brown
        @{r=0.6; g=0.4; b=0.2; a=1.0},      # Tan
        @{r=0.8; g=0.6; b=0.3; a=1.0},      # Light tan
        @{r=0.4; g=0.3; b=0.2; a=1.0},      # Dark tan
        @{r=0.2; g=0.1; b=0.1; a=1.0},      # Very dark tan
        @{r=0.9; g=0.7; b=0.4; a=1.0},      # Cream
        @{r=0.7; g=0.5; b=0.3; a=1.0},      # Dark cream
        @{r=0.0; g=0.0; b=0.0; a=0.0}       # Transparent
    )
}

$palettePath = Join-Path $paletteOutputDir "starbound_warm.json"
$starboundWarmPalette | ConvertTo-Json -Depth 10 | Out-File $palettePath -Encoding UTF8 -NoNewline
$generated++
Write-Host "  [OK] Generated: starbound_warm.json" -ForegroundColor Green

# Starbound Cool Palette
$starboundCoolPalette = @{
    name = "starbound_cool"
    colorCount = 24
    isIndexed = $false
    colors = @(
        @{r=0.0; g=0.0; b=0.0; a=1.0},      # Black
        @{r=0.0; g=0.1; b=0.2; a=1.0},      # Dark blue
        @{r=0.0; g=0.2; b=0.4; a=1.0},      # Blue
        @{r=0.0; g=0.3; b=0.6; a=1.0},      # Light blue
        @{r=0.0; g=0.4; b=0.8; a=1.0},      # Very light blue
        @{r=0.0; g=0.5; b=1.0; a=1.0},     # Cyan blue
        @{r=0.0; g=0.7; b=1.0; a=1.0},     # Light cyan
        @{r=0.0; g=0.9; b=1.0; a=1.0},     # Very light cyan
        @{r=0.0; g=0.8; b=0.8; a=1.0},     # Teal
        @{r=0.0; g=0.6; b=0.6; a=1.0},     # Dark teal
        @{r=0.0; g=0.4; b=0.4; a=1.0},     # Very dark teal
        @{r=0.0; g=0.2; b=0.2; a=1.0},     # Almost black teal
        @{r=0.1; g=0.0; b=0.5; a=1.0},     # Dark purple
        @{r=0.2; g=0.0; b=0.7; a=1.0},     # Purple
        @{r=0.3; g=0.0; b=0.9; a=1.0},     # Light purple
        @{r=0.1; g=0.0; b=0.3; a=1.0},     # Very dark purple
        @{r=0.0; g=0.0; b=0.1; a=1.0},     # Almost black purple
        @{r=0.2; g=0.4; b=0.6; a=1.0},     # Steel blue
        @{r=0.3; g=0.5; b=0.7; a=1.0},     # Light steel blue
        @{r=0.1; g=0.3; b=0.5; a=1.0},     # Dark steel blue
        @{r=0.0; g=0.2; b=0.4; a=1.0},     # Very dark steel blue
        @{r=0.4; g=0.6; b=0.8; a=1.0},     # Sky blue
        @{r=0.2; g=0.4; b=0.6; a=1.0},     # Dark sky blue
        @{r=0.0; g=0.0; b=0.0; a=0.0}      # Transparent
    )
}

$palettePath = Join-Path $paletteOutputDir "starbound_cool.json"
$starboundCoolPalette | ConvertTo-Json -Depth 10 | Out-File $palettePath -Encoding UTF8 -NoNewline
$generated++
Write-Host "  [OK] Generated: starbound_cool.json" -ForegroundColor Green

Write-Host ""

# ============================================================
# 2. MATERIAL TEXTURE TEMPLATES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Material Texture Templates" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$materialTemplates = @(
    @{
        Id = "material_metal"
        Name = "Metal Material"
        Description = "Metal material texture template, seamless, gray metallic appearance, 256x256"
    },
    @{
        Id = "material_wood"
        Name = "Wood Material"
        Description = "Wood material texture template, seamless, brown wood grain, 256x256"
    },
    @{
        Id = "material_stone"
        Name = "Stone Material"
        Description = "Stone material texture template, seamless, gray stone texture, 256x256"
    },
    @{
        Id = "material_fabric"
        Name = "Fabric Material"
        Description = "Fabric material texture template, seamless, cloth texture, 256x256"
    },
    @{
        Id = "material_glass"
        Name = "Glass Material"
        Description = "Glass material texture template, seamless, transparent glass appearance, 256x256"
    },
    @{
        Id = "material_emissive"
        Name = "Emissive Material"
        Description = "Emissive material texture template, seamless, glowing appearance, 256x256"
    }
)

# Validate $ModPath before Join-Path
$materialOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($materialOutputDir)) {
    Write-Host "  [FAIL] materialOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $materialOutputDir)) {
    New-Item -ItemType Directory -Path $materialOutputDir -Force | Out-Null
}

foreach ($material in $materialTemplates) {
    Write-Host "Generating material template: $($material.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $material.Id
            Prompt = "$($material.Description). Material texture template for Starbound mesh baking."
            OllamaModel = $OllamaModel
            OutputDir = $materialOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($material.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($material.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. EXAMPLE BAKED TEXTURE REFERENCES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Example Baked Texture References" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$bakedExamples = @(
    @{
        Id = "baked_example_8dir"
        Name = "8-Direction Baked Example"
        Description = "Example 8-direction baked texture atlas, showing all 8 directions, 64x64 per direction"
    },
    @{
        Id = "baked_example_4dir"
        Name = "4-Direction Baked Example"
        Description = "Example 4-direction baked texture atlas, showing all 4 directions, 64x64 per direction"
    },
    @{
        Id = "baked_example_1dir"
        Name = "1-Direction Baked Example"
        Description = "Example single-direction baked texture atlas, 64x64"
    }
)

# Validate $ModPath before Join-Path
$bakedOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($bakedOutputDir)) {
    Write-Host "  [FAIL] bakedOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($bakedOutputDir)) {
    Write-Host "  [FAIL] bakedOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $bakedOutputDir)) {
    New-Item -ItemType Directory -Path $bakedOutputDir -Force | Out-Null
}

foreach ($example in $bakedExamples) {
    Write-Host "Generating baked example: $($example.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $example.Id
            Prompt = "$($example.Description). Example baked texture atlas for Starbound mesh texture generator reference."
            OllamaModel = $OllamaModel
            OutputDir = $bakedOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($example.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($example.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets')" -ForegroundColor Gray
Write-Host ""
Write-Host "Palettes: assets/textures/palettes/" -ForegroundColor Gray
Write-Host "Material templates: assets/textures/materials/" -ForegroundColor Gray
Write-Host "Baked examples: assets/textures/baked_examples/" -ForegroundColor Gray
Write-Host ""
