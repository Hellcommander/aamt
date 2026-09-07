# Starbound Cursor Generator Guide

A PowerShell tool for generating Starbound/OpenStarbound cursor files (`.cursor` and `.frames`).

## Overview

Starbound cursors consist of:
- **`.cursor`** - Main cursor definition with hotspot and image reference
- **`.frames`** - Frame definitions for multi-state cursors (optional)
- **`.png`** - The actual cursor image/spritesheet

## Quick Start

```powershell
# Simple cursor
.\StarboundCursorGenerator.ps1 -CursorName "mycursor" -Preset Default

# Joystick-style directional cursor
.\StarboundCursorGenerator.ps1 -CursorName "joystick" -Preset Joystick

# Pointer with click states
.\StarboundCursorGenerator.ps1 -CursorName "pointer" -Preset Pointer -GeneratePlaceholderImage
```

## File Formats

### .cursor File

```json
{
  "offset": [15, 15],
  "image": "/cursors/joystick.png:neutral"
}
```

| Property | Description |
|----------|-------------|
| `offset` | [x, y] hotspot position (where clicks register) |
| `image` | Path to image, optionally with `:framename` suffix |

### .frames File

```json
{
  "frameGrid": {
    "size": [30, 30],
    "dimensions": [5, 1],
    "names": [
      ["neutral", "down", "up", "left", "right"]
    ]
  }
}
```

| Property | Description |
|----------|-------------|
| `size` | [width, height] of each frame |
| `dimensions` | [columns, rows] in spritesheet |
| `names` | 2D array of frame names by row |

## Available Presets

| Preset | Size | Frames | Description |
|--------|------|--------|-------------|
| `Default` | 16×16 | 1 | Simple single-frame cursor |
| `Pointer` | 16×16 | 3 | normal, hover, click |
| `Crosshair` | 32×32 | 2 | default, active (centered) |
| `Joystick` | 30×30 | 5 | neutral, down, up, left, right |
| `Hand` | 24×24 | 3 | open, pointing, grabbing |
| `Text` | 8×16 | 1 | I-beam text cursor |
| `Wait` | 24×24 | 8 | Animated loading spinner |
| `Move` | 24×24 | 1 | Move/drag indicator |
| `Resize` | 24×24 | 4 | horizontal, vertical, diagonal1, diagonal2 |

## Parameters

### Basic Parameters

```powershell
-CursorName    # Required. Cursor filename
-Preset        # Preset to use (see above)
-OutputDir     # Output directory (default: "StarboundCursors")
```

### Customization Parameters

```powershell
-Offset        # [x, y] hotspot position
-FrameSize     # [width, height] of each frame
-FrameNames    # 2D array of frame names
-FrameColumns  # Number of columns in spritesheet
-FrameRows     # Number of rows in spritesheet
-DefaultFrame  # Default frame to display
-ImagePath     # Custom image path (relative to assets)
```

### Flags

```powershell
-GeneratePlaceholderImage  # Create a placeholder PNG
-Animated                  # Mark cursor as animated
```

## Examples

### Simple Default Cursor

```powershell
.\StarboundCursorGenerator.ps1 -CursorName "simplecursor" -Preset Default
```

Generates:
- `simplecursor.cursor`

### Joystick Cursor (matches your example)

```powershell
.\StarboundCursorGenerator.ps1 -CursorName "joystick" -Preset Joystick
```

Generates:
- `joystick.cursor` with offset [15, 15]
- `joystick.frames` with 5 states

### Custom Multi-State Cursor

```powershell
.\StarboundCursorGenerator.ps1 `
    -CursorName "customcursor" `
    -Preset Custom `
    -FrameSize @(24, 24) `
    -Offset @(12, 12) `
    -FrameNames @(@("idle", "hover", "active", "disabled")) `
    -FrameColumns 4 `
    -FrameRows 1 `
    -DefaultFrame "idle" `
    -GeneratePlaceholderImage
```

### Animated Wait Cursor

```powershell
.\StarboundCursorGenerator.ps1 `
    -CursorName "loading" `
    -Preset Wait `
    -GeneratePlaceholderImage
```

Generates 8-frame loading animation.

## Hotspot Positioning

The `offset` determines where clicks register:

| Cursor Type | Typical Offset |
|-------------|---------------|
| Pointer | [1, 1] - tip of arrow |
| Crosshair | [center, center] - dead center |
| Hand | [8, 4] - fingertip |
| I-beam | [half-width, half-height] |

## Usage in Starbound

### In Interface Config

```json
{
  "cursor": "/cursors/mycursor.cursor"
}
```

### In Lua Scripts

```lua
-- Set cursor
cursor.setCursor("/cursors/mycursor.png:normal")

-- Change to different state
cursor.setCursor("/cursors/mycursor.png:click")
```

### In Pane Config

```json
{
  "paneLayout": {
    "cursor": "/cursors/mycursor.cursor"
  }
}
```

## Spritesheet Layout

For multi-frame cursors, arrange frames left-to-right, top-to-bottom:

```
┌────────┬────────┬────────┬────────┬────────┐
│ frame1 │ frame2 │ frame3 │ frame4 │ frame5 │
└────────┴────────┴────────┴────────┴────────┘
   30px     30px     30px     30px     30px
```

The `.frames` file maps these positions to names.

## Integration with MultiAssetGenerator

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Starbound `
    -AssetType Cursor `
    -AssetName "mycursor" `
    -Description "custom pointer"
```

## Tips

1. **Hotspot Accuracy**: Test your cursor hotspot in-game
2. **Size Consistency**: Keep cursor sizes reasonable (16-32px typical)
3. **Frame Names**: Use descriptive names for easy scripting
4. **Transparency**: Cursors should have transparent backgrounds

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cursor not visible | Check image path is correct |
| Click position wrong | Adjust offset values |
| Wrong frame showing | Verify default frame name matches |
| Frames not switching | Check frame names in scripts match .frames file |

## See Also

- `StarboundParticleGenerator.ps1` - Particle effects
- `StarboundAnimationGenerator.ps1` - Sprite animations
- `StarboundBehaviorGenerator.ps1` - AI behavior trees

