# Starbound Tile Generator Guide

A PowerShell tool for generating Starbound/OpenStarbound tile files (`.frames`, `.material`, `.matmod`).

## Overview

Starbound tiles use a different frames format than animations/cursors:
- **`.frames`** - Uses `frameList` with explicit pixel coordinates `[x1, y1, x2, y2]`
- **`.material`** - Defines tile properties (health, sounds, drops)
- **`.matmod`** - Material modifiers (overlays on tiles)
- **`.png`** - The tile spritesheet

## Quick Start

```powershell
# Simple tile with 5 variants (like your example)
.\StarboundTileGenerator.ps1 -TileName "blockprotection" -Preset Protection

# Tile with material definition
.\StarboundTileGenerator.ps1 -TileName "mystone" -Preset Basic -GenerateMaterial

# Custom tile with placeholder image
.\StarboundTileGenerator.ps1 -TileName "custom" -TileCount 8 -GeneratePlaceholderImage
```

## File Formats

### .frames File (frameList format)

```json
{
  "frameList" : {
    "1" : [0, 0, 8, 8],
    "2" : [8, 0, 16, 8],
    "3" : [16, 0, 24, 8],
    "4" : [24, 0, 32, 8],
    "5" : [32, 0, 40, 8]
  }
}
```

Each entry: `"name" : [x1, y1, x2, y2]`
- `x1, y1` - Top-left corner coordinates
- `x2, y2` - Bottom-right corner coordinates

### .material File

```json
{
  "materialId": 12345,
  "materialName": "mytile",
  "particleColor": [100, 100, 100, 255],
  "itemDrop": "mytile",
  "footstepSound": "/sfx/blocks/footstep_stone.ogg",
  "health": 1.0,
  "category": "materials",
  "renderTemplate": "/tiles/classicmaterialtemplate.config",
  "renderParameters": {
    "texture": "/tiles/mytile.png",
    "variants": 1
  },
  "damageTable": "/tiles/damagetypes.config:normal"
}
```

## Available Presets

| Preset | Variants | Health | Sound | Use Case |
|--------|----------|--------|-------|----------|
| `Basic` | 1 | 1.0 | Stone | Simple blocks |
| `Protection` | 5 | 10.0 | Stone | Protected areas |
| `Platform` | 4 | 0.5 | Wood | Jump-through platforms |
| `Ore` | 1 | 3.0 | Stone | Mineable ores |
| `Brick` | 16 | 2.0 | Stone | Building materials |
| `Natural` | 4 | 0.8 | Dirt | Terrain |
| `Metal` | 1 | 3.0 | Metal | Industrial |
| `Glass` | 1 | 0.5 | Glass | Windows |
| `Organic` | 4 | 0.6 | Flesh | Alien terrain |
| `Tech` | 8 | 2.5 | Metal | Sci-fi blocks |

## Parameters

### Basic Parameters

```powershell
-TileName      # Required. Tile/material name
-Preset        # Preset to use (see above)
-OutputDir     # Output directory (default: "StarboundTiles")
```

### Tile Properties

```powershell
-TileSize      # Size of each tile in pixels (default: 8)
-TileCount     # Number of tile variants
-Columns       # Columns in spritesheet (default: all in one row)
-FrameNames    # Custom frame names (default: numbered)
```

### Material Properties

```powershell
-GenerateMaterial   # Generate .material file
-MaterialId         # Unique material ID (auto-assigned if 0)
-MaterialCategory   # Category: materials, platforms, ores
-Health             # Tile health/durability
-FootstepSound      # Sound when walked on
-DamageTable        # Damage configuration
-ItemDrop           # Items dropped when mined
```

### Matmod Properties

```powershell
-GenerateMatmod     # Generate .matmod file
-MatmodId          # Unique matmod ID
```

### Rendering

```powershell
-RenderTemplate    # Render template config path
-RenderParameters  # Additional render parameters
-Multicolored     # Has color variants
```

## Examples

### Protection Block (matches your example)

```powershell
.\StarboundTileGenerator.ps1 -TileName "blockprotection" -Preset Protection
```

Generates:
```json
{
  "frameList" : {
    "1" : [0, 0, 8, 8],
    "2" : [8, 0, 16, 8],
    "3" : [16, 0, 24, 8],
    "4" : [24, 0, 32, 8],
    "5" : [32, 0, 40, 8]
  }
}
```

### Mineable Ore with Material

```powershell
.\StarboundTileGenerator.ps1 `
    -TileName "goldore" `
    -Preset Ore `
    -GenerateMaterial `
    -Health 5.0 `
    -ItemDrop @(@{ item = "goldbar"; count = 2 })
```

### Multi-Row Tileset

```powershell
.\StarboundTileGenerator.ps1 `
    -TileName "dungeontiles" `
    -TileCount 16 `
    -Columns 4 `
    -GenerateMaterial `
    -GeneratePlaceholderImage
```

### Platform Tiles

```powershell
.\StarboundTileGenerator.ps1 `
    -TileName "woodplatform" `
    -Preset Platform `
    -GenerateMaterial
```

### Custom Named Frames

```powershell
.\StarboundTileGenerator.ps1 `
    -TileName "dirtvariant" `
    -TileCount 4 `
    -FrameNames @("clean", "mossy", "rocky", "grassy") `
    -Preset Natural
```

## Spritesheet Layout

Tiles are arranged left-to-right, then top-to-bottom:

```
For 8 tiles, 4 columns:
┌───────┬───────┬───────┬───────┐
│  0,0  │  8,0  │ 16,0  │ 24,0  │  Row 0
│  8x8  │  8x8  │  8x8  │  8x8  │
├───────┼───────┼───────┼───────┤
│  0,8  │  8,8  │ 16,8  │ 24,8  │  Row 1
│  8x8  │  8x8  │  8x8  │  8x8  │
└───────┴───────┴───────┴───────┘
```

## Integration with MultiAssetGenerator

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Starbound `
    -AssetType Tile `
    -AssetName "mytile" `
    -Description "stone brick pattern"
```

## Footstep Sounds

| Sound | Path |
|-------|------|
| Stone | `/sfx/blocks/footstep_stone.ogg` |
| Wood | `/sfx/blocks/footstep_wood.ogg` |
| Metal | `/sfx/blocks/footstep_metal.ogg` |
| Dirt | `/sfx/blocks/footstep_dirt.ogg` |
| Glass | `/sfx/blocks/footstep_glass.ogg` |
| Flesh | `/sfx/blocks/footstep_flesh.ogg` |

## Damage Tables

| Type | Path |
|------|------|
| Normal | `/tiles/damagetypes.config:normal` |
| Platform | `/tiles/damagetypes.config:platform` |
| Ore | `/tiles/damagetypes.config:ore` |
| Glass | `/tiles/damagetypes.config:glass` |
| Organic | `/tiles/damagetypes.config:organic` |

## Tips

1. **Material IDs**: Must be unique across all mods
2. **Tile Size**: Standard is 8x8 pixels
3. **Variants**: More variants = more visual variety
4. **Category**: Affects crafting station placement

## See Also

- `StarboundParticleGenerator.ps1` - Particle effects
- `StarboundAnimationGenerator.ps1` - Sprite animations
- `StarboundBehaviorGenerator.ps1` - AI behavior trees
- `StarboundCursorGenerator.ps1` - Mouse cursors

