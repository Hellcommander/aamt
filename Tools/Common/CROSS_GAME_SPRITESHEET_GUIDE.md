# Cross-Game Spritesheet Generator - Guide

Unified spritesheet generation system for Terraria and Starbound modding.

## Overview

Generate game-compatible spritesheets with metadata for both Terraria (tModLoader) and Starbound from a single texture source. Supports batch processing, automatic metadata generation, and seamless integration with your existing texture pipeline.

## Features

- **Unified Pipeline**: One texture source → multiple game formats
- **Automatic Metadata**: Generates Terraria JSON and Starbound .frames files
- **Animation Support**: Handles multi-frame animations for both games
- **Batch Processing**: Process entire texture directories at once
- **Format-Aware**: Respects game-specific requirements (tile sizes, padding, etc.)

## Quick Start

### Basic Usage

```powershell
# Generate spritesheets for both games
.\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Both -TileSize 16 -Columns 8

# Terraria only
.\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Terraria -TileSize 32

# Starbound only
.\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Starbound -TileSize 16
```

### Generate Textures and Assemble

```powershell
# Generate textures and create spritesheets in one step
.\CrossGameSpritesheet.ps1 -GenerateTextures -TextureDescriptions @("wood", "stone", "metal") -GameFormat Both -TileSize 16
```

## Game-Specific Requirements

### Terraria (tModLoader)

- **Tile Sizes**: 16×16 or 32×32 pixels (common)
- **Animation**: Horizontal strips (frames side-by-side)
- **Metadata**: JSON file with frame definitions
- **No Padding**: Not required, but recommended for clean modding

**Example Layout** (4-frame animation):
```
[frame0][frame1][frame2][frame3]
```

**Generated JSON**:
```json
{
  "frames": 4,
  "frameWidth": 16,
  "frameHeight": 16,
  "animationSpeed": 5,
  "items": 1,
  "animations": {
    "item_0": {
      "frames": [0, 1, 2, 3],
      "speed": 5
    }
  }
}
```

### Starbound

- **Tile Sizes**: 8-pixel grid alignment (8, 16, 24, 32, etc.)
- **Animation**: Variable frame sizes, explicit .frames metadata
- **Metadata**: .frames JSON file with frameGrid and aliases
- **Padding**: Optional, but recommended

**Example .frames file**:
```json
{
  "frameGrid": {
    "size": [16, 16],
    "dimensions": [4, 1]
  },
  "aliases": {
    "default": [0, 1, 2, 3]
  }
}
```

## Parameters

### CrossGameSpritesheet.ps1

- **`-InputDir`**: Directory containing source PNG textures
- **`-OutputDir`**: Output directory (default: `GameSpritesheets`)
- **`-GameFormat`**: Target format: `Terraria`, `Starbound`, or `Both` (default)
- **`-TileSize`**: Tile size in pixels (default: 16)
- **`-Columns`**: Number of columns in spritesheet (default: 8)
- **`-AnimationFrames`**: Frames per item for animations (default: 1)
- **`-AnimationSpeed`**: Animation speed in FPS for Terraria (default: 5)
- **`-GenerateTextures`**: Generate textures before assembly
- **`-TextureDescriptions`**: Array of texture descriptions
- **`-SpritesheetName`**: Base name for output files (default: `spritesheet`)

## Workflow Examples

### Placeholder Asset Generation

```powershell
# Generate 50 placeholder textures and create spritesheets
$textures = @(
    "wood", "stone", "metal", "crystal", "fabric",
    "leather", "bone", "ice", "fire", "earth"
    # ... add more
)

.\CrossGameSpritesheet.ps1 `
    -GenerateTextures `
    -TextureDescriptions $textures `
    -GameFormat Both `
    -TileSize 16 `
    -Columns 10 `
    -OutputDir "PlaceholderAssets"
```

### Animation Spritesheets

```powershell
# Create animated item spritesheet (4 frames per item)
.\CrossGameSpritesheet.ps1 `
    -InputDir "AnimatedTextures" `
    -GameFormat Both `
    -TileSize 32 `
    -AnimationFrames 4 `
    -AnimationSpeed 10 `
    -Columns 4
```

### Batch Processing Multiple Categories

```powershell
# Process different asset categories
$categories = @("Items", "Tiles", "Effects", "UI")

foreach ($cat in $categories) {
    .\CrossGameSpritesheet.ps1 `
        -InputDir "Assets\$cat" `
        -GameFormat Both `
        -TileSize 16 `
        -SpritesheetName $cat `
        -OutputDir "GameAssets\$cat"
}
```

## Integration with Existing Pipeline

### With AssetMakerAI

```powershell
# 1. Generate textures using AI
.\AssetMakerAI.ps1 -Action BatchTextures -InputData "textures.txt" -OutputPath "Textures"

# 2. Assemble into game spritesheets
.\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Both
```

### With BatchBakeTextures

```powershell
# 1. Bake procedural textures
.\BatchBakeTextures.ps1 -MaterialList @("wood", "stone") -OutputDir "Textures"

# 2. Create cross-game spritesheets
.\CrossGameSpritesheet.ps1 -InputDir "Textures" -GameFormat Both -TileSize 16
```

## Output Files

For `Both` format with name `spritesheet`:

- **`spritesheet.png`** - Base spritesheet (shared)
- **`spritesheet_terraria.png`** - Terraria-compatible sheet
- **`spritesheet_terraria.json`** - Terraria metadata
- **`spritesheet_starbound.png`** - Starbound-compatible sheet
- **`spritesheet.frames`** - Starbound frames metadata

## Advanced Usage

### Custom Animation Layouts

```powershell
# 8-frame animation, 2 items
.\CrossGameSpritesheet.ps1 `
    -InputDir "Textures" `
    -GameFormat Both `
    -TileSize 16 `
    -AnimationFrames 8 `
    -Columns 8 `
    -AnimationSpeed 12
```

### Python Script Direct Usage

```bash
# Direct Python usage
python cross_game_spritesheet.py \
    --input Textures \
    --output Output \
    --tile-size 16 \
    --columns 8 \
    --frames 4 \
    --both
```

## Design Principles

- **Deterministic**: Same inputs = same outputs
- **Modular**: Works standalone or integrated
- **Format-Aware**: Respects game-specific requirements
- **Batch-Friendly**: Process entire directories
- **Placeholder-First**: Perfect for rapid prototyping

## Troubleshooting

### Python Not Found
- Install Python 3.x
- Ensure Python is in PATH
- Or specify full path in script

### No Textures Found
- Check input directory path
- Ensure PNG files are present
- Verify file extensions (.png, not .PNG)

### Metadata Issues
- Verify tile size matches game requirements
- Check animation frame count matches texture count
- Ensure columns × rows ≥ total textures

## Future Enhancements

- [ ] Automatic padding generation
- [ ] UV mapping support
- [ ] Multi-pass texture baking (Normal, Roughness)
- [ ] Animation preview generation
- [ ] Game-specific optimization (compression, formats)
- [ ] Integration with tModLoader and Starbound mod tools

## References

- [Terraria tModLoader Documentation](https://github.com/tModLoader/tModLoader/wiki)
- [Starbound Modding Guide](https://starbound.fandom.com/wiki/Modding)
- [PIL/Pillow Documentation](https://pillow.readthedocs.io/)

