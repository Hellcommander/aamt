# Elin Texture Generator Guide

A PowerShell tool for generating Elin mod texture files with animation support.

## Overview

Elin textures follow specific patterns:
- **Standard textures**: `item.png`
- **Animated textures**: `item_anime.png` + `item_anime.ini`
- **Snow variants**: `item_snow.png`
- **Numbered variants**: `item.png`, `item2.png`, `item3.png`

## Quick Start

```powershell
# Basic item texture
.\ElinTextureGenerator.ps1 -TextureName "my_item" -TextureType Item -Preset Basic

# Animated fountain with snow variant
.\ElinTextureGenerator.ps1 -TextureName "my_fountain" -Preset Fountain -Animated -GenerateSnowVariant

# Multiple wagon variants
.\ElinTextureGenerator.ps1 -TextureName "wagon_custom" -Preset Wagon -NumberedVariants 3 -GenerateSnowVariant
```

## Texture Types

| Type | Default Size | Folder | Animation | Snow |
|------|--------------|--------|-----------|------|
| Item | 48×48 | Texture/Item | ✓ | ✓ |
| Chara | 32×48 | Texture/Chara | ✓ | ✗ |
| CharaSprite | 32×32 | Texture/CharaSprite | ✓ | ✗ |
| Map | 256×256 | Texture/Map | ✗ | ✓ |
| MapTile | 48×24 | Texture/MapTile | ✓ | ✓ |
| Effect | 64×64 | Texture/Effect | ✓ | ✗ |
| UI | 32×32 | Texture/UI | ✗ | ✗ |
| Icon | 32×32 | Texture/Icon | ✗ | ✗ |
| Portrait | 80×112 | Texture/Portrait | ✗ | ✗ |

## Presets

| Preset | Size | Features |
|--------|------|----------|
| Basic | 48×48 | Standard item |
| Furniture | 48×72 | Taller furniture pieces |
| Statue | 48×96 | Tall statues |
| Sign | 48×48 | Signs with snow support |
| Wagon | 96×72 | Large wagons with snow |
| Boat | 72×48 | Boats with animation |
| Tree | 48×96 | Tall trees |
| Fountain | 48×72 | Animated fountains with snow |
| Tent | 72×72 | Tents with snow |

## Parameters

### Basic Parameters

```powershell
-TextureName      # Required. Base name for the texture
-TextureType      # Type of texture (see above)
-Preset           # Built-in preset to use
-OutputDir        # Output directory (default: "ElinTextures")
```

### Dimensions

```powershell
-Width            # Override width in pixels
-Height           # Override height in pixels
```

### Animation

```powershell
-Animated         # Enable animation
-FrameCount       # Number of animation frames (default: 4)
-AnimationSpeed   # Milliseconds per frame (default: 100)
-AnimationLoop    # Enable animation looping
```

### Variants

```powershell
-GenerateSnowVariant  # Create snow version
-NumberedVariants     # Number of variants to generate (1, 2, 3...)
```

### Other

```powershell
-GeneratePlaceholder  # Create placeholder PNG images
-BaseColor            # RGB array for placeholder color, e.g., @(255, 0, 0)
-Description          # Description text
```

## Examples

### Animated Fountain

```powershell
.\ElinTextureGenerator.ps1 `
    -TextureName "magic_fountain" `
    -TextureType Item `
    -Preset Fountain `
    -Animated `
    -FrameCount 4 `
    -AnimationSpeed 150 `
    -GenerateSnowVariant `
    -GeneratePlaceholder
```

Generated files:
```
Item/
├── magic_fountain.png
├── magic_fountain_anime.png
├── magic_fountain_anime.ini
├── magic_fountain_snow.png
└── magic_fountain_README.md
```

### Multiple Wagon Variants

```powershell
.\ElinTextureGenerator.ps1 `
    -TextureName "wagon_big" `
    -Preset Wagon `
    -NumberedVariants 5 `
    -GenerateSnowVariant
```

Generated files:
```
Item/
├── wagon_big.png
├── wagon_big_snow.png
├── wagon_big2.png
├── wagon_big2_snow.png
├── wagon_big3.png
├── wagon_big3_snow.png
├── wagon_big4.png
├── wagon_big4_snow.png
├── wagon_big5.png
└── wagon_big5_snow.png
```

### Character Sprite

```powershell
.\ElinTextureGenerator.ps1 `
    -TextureName "custom_npc" `
    -TextureType Chara `
    -Animated `
    -FrameCount 4
```

### Portrait

```powershell
.\ElinTextureGenerator.ps1 `
    -TextureName "hero_portrait" `
    -TextureType Portrait `
    -GeneratePlaceholder
```

## Animation INI Format

The `.ini` file controls animation playback:

```ini
[Animation]
Frames=4
Speed=100
Loop=true
```

| Property | Description |
|----------|-------------|
| Frames | Number of horizontal frames in the spritesheet |
| Speed | Milliseconds per frame |
| Loop | Whether the animation repeats |

## Spritesheet Layout

For animated textures, frames are arranged horizontally:

```
┌────────┬────────┬────────┬────────┐
│ Frame1 │ Frame2 │ Frame3 │ Frame4 │
│ 48px   │ 48px   │ 48px   │ 48px   │
└────────┴────────┴────────┴────────┘
Total width: 192px (48 × 4 frames)
```

## Elin Mod Structure

Place generated textures in your mod folder:

```
Package/
└── YourMod/
    └── Texture/
        ├── Item/
        │   ├── my_item.png
        │   ├── my_item_anime.png
        │   └── my_item_anime.ini
        ├── Chara/
        │   └── custom_npc.png
        └── Portrait/
            └── hero_portrait.png
```

## Snow Variant Tips

1. Snow overlays appear on top portion of textures
2. Use semi-transparent white for snow effect
3. Consider multiple snow density levels
4. Match snow style with existing Elin assets

## Integration with MultiAssetGenerator

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Elin `
    -AssetType Texture `
    -AssetName "my_texture" `
    -Description "animated fountain"
```

## See Also

- `ElinSpellAssetGenerator.ps1` - Spell/ability assets
- `MultiAssetGenerator.ps1` - Multi-game asset generation

