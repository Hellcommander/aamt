#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the dungeon generation system.
    
.DESCRIPTION
    Generates tile atlases and individual tiles for:
    - Floor tiles
    - Wall tiles
    - Ceiling tiles
    - Background tiles
    - Midground tiles
    - Foreground tiles
    - Decorative tiles
    
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
Write-Host "  Dungeon System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. FLOOR TILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Floor Tiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$floorTiles = @(
    @{
        Id = "floor_stone"
        Name = "Stone Floor"
        Description = "Stone floor tile, gray stone texture, 16x16 pixel art"
    },
    @{
        Id = "floor_brick"
        Name = "Brick Floor"
        Description = "Brick floor tile, red brick pattern, 16x16 pixel art"
    },
    @{
        Id = "floor_wood"
        Name = "Wooden Floor"
        Description = "Wooden floor tile, wooden planks, 16x16 pixel art"
    },
    @{
        Id = "floor_metal"
        Name = "Metal Floor"
        Description = "Metal floor tile, metallic grates, 16x16 pixel art"
    },
    @{
        Id = "floor_dirt"
        Name = "Dirt Floor"
        Description = "Dirt floor tile, brown dirt texture, 16x16 pixel art"
    },
    @{
        Id = "floor_arcane"
        Name = "Arcane Floor"
        Description = "Arcane floor tile, magical runes, purple glow, 16x16 pixel art"
    }
)

foreach ($tile in $floorTiles) {
    Write-Host "Generating floor tile: $($tile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $tile.Id
            Prompt = "$($tile.Description). Dungeon floor tile for Starbound, seamless tileable texture."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. WALL TILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wall Tiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$wallTiles = @(
    @{
        Id = "wall_stone"
        Name = "Stone Wall"
        Description = "Stone wall tile, gray stone blocks, 16x16 pixel art"
    },
    @{
        Id = "wall_brick"
        Name = "Brick Wall"
        Description = "Brick wall tile, red brick blocks, 16x16 pixel art"
    },
    @{
        Id = "wall_wood"
        Name = "Wooden Wall"
        Description = "Wooden wall tile, wooden planks, 16x16 pixel art"
    },
    @{
        Id = "wall_metal"
        Name = "Metal Wall"
        Description = "Metal wall tile, metallic panels, 16x16 pixel art"
    },
    @{
        Id = "wall_arcane"
        Name = "Arcane Wall"
        Description = "Arcane wall tile, magical runes, purple glow, 16x16 pixel art"
    },
    @{
        Id = "wall_corner"
        Name = "Wall Corner"
        Description = "Wall corner tile, corner piece, 16x16 pixel art"
    }
)

foreach ($tile in $wallTiles) {
    Write-Host "Generating wall tile: $($tile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $tile.Id
            Prompt = "$($tile.Description). Dungeon wall tile for Starbound, seamless tileable texture."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. CEILING TILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Ceiling Tiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$ceilingTiles = @(
    @{
        Id = "ceiling_stone"
        Name = "Stone Ceiling"
        Description = "Stone ceiling tile, gray stone texture, 16x16 pixel art"
    },
    @{
        Id = "ceiling_wood"
        Name = "Wooden Ceiling"
        Description = "Wooden ceiling tile, wooden beams, 16x16 pixel art"
    },
    @{
        Id = "ceiling_metal"
        Name = "Metal Ceiling"
        Description = "Metal ceiling tile, metallic panels, 16x16 pixel art"
    }
)

foreach ($tile in $ceilingTiles) {
    Write-Host "Generating ceiling tile: $($tile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $tile.Id
            Prompt = "$($tile.Description). Dungeon ceiling tile for Starbound, seamless tileable texture."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. DECORATIVE TILES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Decorative Tiles" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$decorativeTiles = @(
    @{
        Id = "decor_rune"
        Name = "Rune Decoration"
        Description = "Rune decorative tile, magical rune symbol, 16x16 pixel art"
    },
    @{
        Id = "decor_crack"
        Name = "Crack Decoration"
        Description = "Crack decorative tile, stone crack pattern, 16x16 pixel art"
    },
    @{
        Id = "decor_moss"
        Name = "Moss Decoration"
        Description = "Moss decorative tile, green moss growth, 16x16 pixel art"
    },
    @{
        Id = "decor_blood"
        Name = "Blood Decoration"
        Description = "Blood decorative tile, red bloodstain, 16x16 pixel art"
    }
)

foreach ($tile in $decorativeTiles) {
    Write-Host "Generating decorative tile: $($tile.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Texture"
            AssetName = $tile.Id
            Prompt = "$($tile.Description). Dungeon decorative tile for Starbound, 16x16 pixel art."
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($tile.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($tile.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. CREATE TILE ATLAS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Creating Tile Atlas" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

Write-Host "Note: Tile atlas assembly requires manual creation or use of atlas builder tool" -ForegroundColor Gray
Write-Host "Individual tiles have been generated and can be assembled into atlases" -ForegroundColor Gray
Write-Host ""

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated tiles" -ForegroundColor Green
Write-Host "Failed: $failed tiles" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Tiles saved to: $(Join-Path $ModPath 'assets\textures\dungeon\tiles')" -ForegroundColor Gray
Write-Host ""
Write-Host "Next step: Assemble tiles into texture atlases for dungeon system" -ForegroundColor Yellow
Write-Host ""
