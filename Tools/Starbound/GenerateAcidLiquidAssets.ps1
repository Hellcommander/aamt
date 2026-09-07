#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Acid/Liquid Projectile Generator system.
    
.DESCRIPTION
    Generates sprites, particles, and effects for:
    - Acid projectile sprites
    - Liquid droplet sprites
    - Acid impact effects
    - Liquid splatter effects
    - Corrosive decals
    - Bubble particle effects
    
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
    [bool]$UseCppBackend = $true
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
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Acid/Liquid Projectile Generator Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. ACID PROJECTILE SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Acid Projectile Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$acidProjectiles = @(
    @{
        Id = "acid_projectile_basic"
        Name = "Basic Acid Projectile"
        Description = "Basic acid projectile sprite, green toxic droplet, 32x32"
    },
    @{
        Id = "acid_projectile_strong"
        Name = "Strong Acid Projectile"
        Description = "Strong acid projectile sprite, dark green toxic droplet, 32x32"
    },
    @{
        Id = "acid_projectile_corrosive"
        Name = "Corrosive Acid Projectile"
        Description = "Corrosive acid projectile sprite, yellow-green toxic droplet, 32x32"
    },
    @{
        Id = "acid_projectile_spray"
        Name = "Acid Spray Projectile"
        Description = "Acid spray projectile sprite, multiple small droplets, 32x32"
    }
)

# Validate $ModPath before Join-Path
$acidOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($acidOutputDir)) {
    Write-Host "  [FAIL] acidOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($acidOutputDir)) {
    Write-Host "  [FAIL] acidOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $acidOutputDir)) {
    New-Item -ItemType Directory -Path $acidOutputDir -Force | Out-Null
}

foreach ($projectile in $acidProjectiles) {
    Write-Host "Generating acid projectile: $($projectile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $projectile.Id
            Prompt = "$($projectile.Description). Acid projectile sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $acidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($projectile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($projectile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. LIQUID DROPLET SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Liquid Droplet Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$liquidDroplets = @(
    @{
        Id = "liquid_droplet_water"
        Name = "Water Droplet"
        Description = "Water droplet sprite, blue transparent droplet, 32x32"
    },
    @{
        Id = "liquid_droplet_oil"
        Name = "Oil Droplet"
        Description = "Oil droplet sprite, dark brown/black droplet, 32x32"
    },
    @{
        Id = "liquid_droplet_poison"
        Name = "Poison Droplet"
        Description = "Poison droplet sprite, purple toxic droplet, 32x32"
    },
    @{
        Id = "liquid_droplet_healing"
        Name = "Healing Droplet"
        Description = "Healing droplet sprite, green healing droplet, 32x32"
    },
    @{
        Id = "liquid_droplet_magma"
        Name = "Magma Droplet"
        Description = "Magma droplet sprite, red/orange molten droplet, 32x32"
    }
)

# Validate $ModPath before Join-Path
$liquidOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($liquidOutputDir)) {
    Write-Host "  [FAIL] liquidOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($liquidOutputDir)) {
    Write-Host "  [FAIL] liquidOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $liquidOutputDir)) {
    New-Item -ItemType Directory -Path $liquidOutputDir -Force | Out-Null
}

foreach ($droplet in $liquidDroplets) {
    Write-Host "Generating liquid droplet: $($droplet.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Projectile"
            AssetName = $droplet.Id
            Prompt = "$($droplet.Description). Liquid droplet sprite for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $liquidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($droplet.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($droplet.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. ACID IMPACT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Acid Impact Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$acidImpacts = @(
    @{
        Id = "acid_impact_basic"
        Name = "Basic Acid Impact"
        Description = "Basic acid impact particle effect, green toxic splash, corrosive particles"
    },
    @{
        Id = "acid_impact_strong"
        Name = "Strong Acid Impact"
        Description = "Strong acid impact particle effect, dark green toxic splash, intense corrosive"
    },
    @{
        Id = "acid_impact_corrosive"
        Name = "Corrosive Acid Impact"
        Description = "Corrosive acid impact particle effect, yellow-green toxic splash, severe corrosive"
    },
    @{
        Id = "acid_impact_spray"
        Name = "Acid Spray Impact"
        Description = "Acid spray impact particle effect, multiple small splashes, widespread corrosive"
    }
)

foreach ($impact in $acidImpacts) {
    Write-Host "Generating acid impact: $($impact.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $impact.Id
            Prompt = "$($impact.Description). Acid impact particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $acidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($impact.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($impact.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. LIQUID SPLATTER EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Liquid Splatter Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$liquidSplatters = @(
    @{
        Id = "liquid_splatter_water"
        Name = "Water Splatter"
        Description = "Water splatter particle effect, blue water splash, fluid particles"
    },
    @{
        Id = "liquid_splatter_oil"
        Name = "Oil Splatter"
        Description = "Oil splatter particle effect, dark brown/black oil splash, viscous particles"
    },
    @{
        Id = "liquid_splatter_poison"
        Name = "Poison Splatter"
        Description = "Poison splatter particle effect, purple toxic splash, poison particles"
    },
    @{
        Id = "liquid_splatter_magma"
        Name = "Magma Splatter"
        Description = "Magma splatter particle effect, red/orange molten splash, fire particles"
    }
)

foreach ($splatter in $liquidSplatters) {
    Write-Host "Generating liquid splatter: $($splatter.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $splatter.Id
            Prompt = "$($splatter.Description). Liquid splatter particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $liquidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($splatter.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($splatter.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. CORROSIVE DECALS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Corrosive Decals" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$corrosiveDecals = @(
    @{
        Id = "corrosive_decal_basic"
        Name = "Basic Corrosive Decal"
        Description = "Basic corrosive decal texture, green acid burn mark, 64x64"
    },
    @{
        Id = "corrosive_decal_strong"
        Name = "Strong Corrosive Decal"
        Description = "Strong corrosive decal texture, dark green acid burn mark, 64x64"
    },
    @{
        Id = "corrosive_decal_severe"
        Name = "Severe Corrosive Decal"
        Description = "Severe corrosive decal texture, yellow-green severe acid burn, 64x64"
    }
)

foreach ($decal in $corrosiveDecals) {
    Write-Host "Generating corrosive decal: $($decal.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $decal.Id
            Prompt = "$($decal.Description). Corrosive decal texture for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $acidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($decal.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($decal.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. BUBBLE PARTICLE EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Bubble Particle Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$bubbleEffects = @(
    @{
        Id = "bubble_effect_acid"
        Name = "Acid Bubble Effect"
        Description = "Acid bubble particle effect, green toxic bubbles, corrosive bubbles"
    },
    @{
        Id = "bubble_effect_water"
        Name = "Water Bubble Effect"
        Description = "Water bubble particle effect, blue water bubbles, fluid bubbles"
    },
    @{
        Id = "bubble_effect_oil"
        Name = "Oil Bubble Effect"
        Description = "Oil bubble particle effect, dark brown/black oil bubbles, viscous bubbles"
    },
    @{
        Id = "bubble_effect_poison"
        Name = "Poison Bubble Effect"
        Description = "Poison bubble particle effect, purple toxic bubbles, poison bubbles"
    }
)

foreach ($bubble in $bubbleEffects) {
    Write-Host "Generating bubble effect: $($bubble.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $bubble.Id
            Prompt = "$($bubble.Description). Bubble particle effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $acidOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($bubble.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($bubble.Name) : $_" -ForegroundColor Red
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
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  Acid: $(Join-Path $ModPath 'assets\projectiles\acid')" -ForegroundColor Gray
Write-Host "  Liquid: $(Join-Path $ModPath 'assets\projectiles\liquid')" -ForegroundColor Gray
Write-Host ""
Write-Host "Acid projectiles: assets/projectiles/acid/acid_projectile_*.png" -ForegroundColor Gray
Write-Host "Liquid droplets: assets/projectiles/liquid/liquid_droplet_*.png" -ForegroundColor Gray
Write-Host "Acid impacts: assets/projectiles/acid/acid_impact_*.particle" -ForegroundColor Gray
Write-Host "Liquid splatters: assets/projectiles/liquid/liquid_splatter_*.particle" -ForegroundColor Gray
Write-Host "Corrosive decals: assets/projectiles/acid/corrosive_decal_*.png" -ForegroundColor Gray
Write-Host "Bubble effects: assets/projectiles/acid/bubble_effect_*.particle" -ForegroundColor Gray
Write-Host ""
