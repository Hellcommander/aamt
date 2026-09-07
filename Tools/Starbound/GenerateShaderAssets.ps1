#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the StarboundShaderSuite system.
    
.DESCRIPTION
    Generates textures and assets for:
    - Noise textures (for dissolve shader)
    - Damage textures (mask and decal)
    - Ripple textures (for water ripple shader)
    - Emissive maps (for emissive glow shader)
    - Normal maps (for cell shading)
    
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
Write-Host "  StarboundShaderSuite Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. NOISE TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Noise Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$noiseTextures = @(
    @{
        Id = "noise"
        Name = "Noise Texture"
        Description = "Procedural noise texture, seamless, grayscale, 256x256, for dissolve shader"
    },
    @{
        Id = "noise_cloud"
        Name = "Cloud Noise Texture"
        Description = "Cloud noise texture, seamless, grayscale, 256x256, soft noise pattern"
    },
    @{
        Id = "noise_perlin"
        Name = "Perlin Noise Texture"
        Description = "Perlin noise texture, seamless, grayscale, 256x256, organic noise pattern"
    },
    @{
        Id = "noise_voronoi"
        Name = "Voronoi Noise Texture"
        Description = "Voronoi noise texture, seamless, grayscale, 256x256, cellular noise pattern"
    }
)

# Validate $ModPath before Join-Path
$noiseOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($noiseOutputDir)) {
    Write-Host "  [FAIL] noiseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($noiseOutputDir)) {
    Write-Host "  [FAIL] noiseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $noiseOutputDir)) {
    New-Item -ItemType Directory -Path $noiseOutputDir -Force | Out-Null
}

foreach ($noise in $noiseTextures) {
    Write-Host "Generating noise texture: $($noise.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $noise.Id
            Prompt = "$($noise.Description). Noise texture for Starbound shaders."
            OllamaModel = $OllamaModel
            OutputDir = $noiseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($noise.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($noise.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. DAMAGE TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Damage Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$damageTextures = @(
    @{
        Id = "damage_mask"
        Name = "Damage Mask"
        Description = "Damage mask texture, grayscale, 256x256, white areas show damage, black areas are intact"
    },
    @{
        Id = "damage_decal"
        Name = "Damage Decal"
        Description = "Damage decal texture, red/orange colors, 256x256, burn marks and scratches"
    },
    @{
        Id = "damage_crack"
        Name = "Damage Crack"
        Description = "Damage crack texture, grayscale, 256x256, crack pattern for damage overlay"
    },
    @{
        Id = "damage_scorch"
        Name = "Damage Scorch"
        Description = "Damage scorch texture, dark colors, 256x256, scorch marks for damage overlay"
    }
)

foreach ($damage in $damageTextures) {
    Write-Host "Generating damage texture: $($damage.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $damage.Id
            Prompt = "$($damage.Description). Damage texture for Starbound damage overlay shader."
            OllamaModel = $OllamaModel
            OutputDir = $noiseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($damage.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($damage.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. RIPPLE TEXTURES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Ripple Textures" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$rippleTextures = @(
    @{
        Id = "ripple"
        Name = "Ripple Texture"
        Description = "Water ripple texture, grayscale, 256x256, circular ripple pattern, seamless"
    },
    @{
        Id = "ripple_wave"
        Name = "Wave Ripple Texture"
        Description = "Wave ripple texture, grayscale, 256x256, wave pattern, seamless"
    },
    @{
        Id = "ripple_distortion"
        Name = "Distortion Ripple Texture"
        Description = "Distortion ripple texture, grayscale, 256x256, distortion pattern, seamless"
    }
)

foreach ($ripple in $rippleTextures) {
    Write-Host "Generating ripple texture: $($ripple.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $ripple.Id
            Prompt = "$($ripple.Description). Ripple texture for Starbound water ripple shader."
            OllamaModel = $OllamaModel
            OutputDir = $noiseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($ripple.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($ripple.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. EMISSIVE MAPS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Emissive Maps" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$emissiveMaps = @(
    @{
        Id = "emissive_glow"
        Name = "Emissive Glow Map"
        Description = "Emissive glow map, grayscale, 256x256, white areas glow, black areas don't"
    },
    @{
        Id = "emissive_pulse"
        Name = "Emissive Pulse Map"
        Description = "Emissive pulse map, grayscale, 256x256, pulsing glow pattern"
    },
    @{
        Id = "emissive_pattern"
        Name = "Emissive Pattern Map"
        Description = "Emissive pattern map, grayscale, 256x256, pattern-based glow"
    }
)

foreach ($emissive in $emissiveMaps) {
    Write-Host "Generating emissive map: $($emissive.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $emissive.Id
            Prompt = "$($emissive.Description). Emissive map for Starbound emissive glow shader."
            OllamaModel = $OllamaModel
            OutputDir = $noiseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($emissive.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($emissive.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. NORMAL MAPS (OPTIONAL)
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Normal Maps" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$normalMaps = @(
    @{
        Id = "normal_default"
        Name = "Default Normal Map"
        Description = "Default normal map, RGB, 256x256, neutral normal map, blue tint"
    },
    @{
        Id = "normal_detail"
        Name = "Detail Normal Map"
        Description = "Detail normal map, RGB, 256x256, surface detail normal map, blue tint"
    }
)

foreach ($normal in $normalMaps) {
    Write-Host "Generating normal map: $($normal.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $normal.Id
            Prompt = "$($normal.Description). Normal map for Starbound cell shading shader."
            OllamaModel = $OllamaModel
            OutputDir = $noiseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($normal.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($normal.Name) : $_" -ForegroundColor Red
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
Write-Host "Assets saved to: $(Join-Path $ModPath 'assets\textures\shaders')" -ForegroundColor Gray
Write-Host ""
Write-Host "Noise textures: assets/textures/shaders/noise*.png" -ForegroundColor Gray
Write-Host "Damage textures: assets/textures/shaders/damage*.png" -ForegroundColor Gray
Write-Host "Ripple textures: assets/textures/shaders/ripple*.png" -ForegroundColor Gray
Write-Host "Emissive maps: assets/textures/shaders/emissive*.png" -ForegroundColor Gray
Write-Host "Normal maps: assets/textures/shaders/normal*.png" -ForegroundColor Gray
Write-Host ""
