# Starbound Ship Generator Guide

A PowerShell tool for generating Starbound/OpenStarbound ship files (`.structure`, `blockKey.config`).

## Overview

Starbound ships consist of multiple files per upgrade tier:
- **`blockKey.config`** - Color-to-object mapping (shared across tiers)
- **`shipnameT#.structure`** - Ship structure definition per tier
- **`shipnameT#blocks.png`** - Block map (colored pixels = objects/tiles)
- **`shipnameT#.png`** - Ship sprite (visual appearance)
- **`shipnameT#lit.png`** - Lit overlay (glowing elements)

## Quick Start

```powershell
# Generate human-style ship
.\StarboundShipGenerator.ps1 -ShipName "myship" -Race "myrace" -Preset Human

# Generate all tiers with placeholders
.\StarboundShipGenerator.ps1 -ShipName "customship" -IncludeAllTiers -GeneratePlaceholders

# Minimal generation (T0 and T8 only)
.\StarboundShipGenerator.ps1 -ShipName "minimal" -MaxTier 8
```

## Block Key Colors

The block map uses colored pixels to define objects and tiles:

| Color | RGB | Purpose |
|-------|-----|---------|
| White | (255, 255, 255) | Empty space (outside ship) |
| Blue | (0, 0, 255) | Interior floor (walkable) |
| Red | (255, 0, 0) | Solid wall (foreground + background) |
| Green | (0, 255, 0) | Ship Locker |
| Light Green | (142, 255, 142) | Tech Station |
| Salmon | (255, 90, 90) | Fuel Hatch |
| Yellow | (255, 255, 0) | Ship Light |
| Orange | (255, 102, 0) | Ship Door |
| Purple | (156, 0, 255) | Teleporter (spawn point) |
| Cyan | (0, 255, 255) | Captain's Chair |
| Light Blue | (167, 167, 255) | Booster Flame |
| Gray | (122, 122, 122) | Invisible Light |
| Brown | (174, 137, 81) | Ship Engine |

## Parameters

### Basic Parameters

```powershell
-ShipName      # Required. Base name (generates shipnameTX files)
-Race          # Race name for race-specific objects
-Preset        # Ship style preset
-OutputDir     # Output directory (default: "StarboundShips")
-MaxTier       # Maximum tier to generate (1-8, default: 8)
```

### Generation Options

```powershell
-IncludeAllTiers      # Generate all tiers (T0-T8)
-GeneratePlaceholders # Create placeholder block map PNGs
-SpritePosition       # [x, y] offset for sprite overlays
```

### Custom Configuration

```powershell
-TierCapabilities    # Hashtable of capabilities per tier
-TierCrewSizes      # Hashtable of crew sizes per tier
-CustomBlockEntries # Additional block key entries
```

## Ship Tiers

| Tier | Crew | Capabilities | Description |
|------|------|--------------|-------------|
| T0 | 2 | None | Broken starter ship |
| T1 | 2 | None | Basic repairs |
| T2 | 2 | Teleport | Teleporter enabled |
| T3 | 2 | Teleport, Travel | Full FTL |
| T4 | 4 | Teleport, Travel | First expansion |
| T5 | 6 | Teleport, Travel | Medium ship |
| T6 | 8 | Teleport, Travel | Large ship |
| T7 | 10 | Teleport, Travel | Huge ship |
| T8 | 12 | Teleport, Travel | Maximum size |

## Examples

### Custom Race Ship

```powershell
.\StarboundShipGenerator.ps1 `
    -ShipName "avali" `
    -Race "avali" `
    -Preset Generic `
    -MaxTier 8 `
    -IncludeAllTiers `
    -GeneratePlaceholders
```

### Minimal Test Ship

```powershell
.\StarboundShipGenerator.ps1 `
    -ShipName "testship" `
    -Race "human" `
    -MaxTier 4
```

### Custom Tier Configuration

```powershell
$customCaps = @{
    0 = @()
    1 = @("teleport")
    2 = @("teleport", "planetTravel")
    3 = @("teleport", "planetTravel", "systemTravel")
}

$customCrew = @{
    0 = 1
    1 = 2
    2 = 4
    3 = 6
}

.\StarboundShipGenerator.ps1 `
    -ShipName "custom" `
    -MaxTier 3 `
    -TierCapabilities $customCaps `
    -TierCrewSizes $customCrew
```

## Generated File Structure

```
StarboundShips/
└── myship/
    ├── blockKey.config          # Color mappings
    ├── myshipT0.structure       # Tier 0 definition
    ├── myshipT0blocks.png       # Tier 0 block map
    ├── myshipT8.structure       # Tier 8 definition
    ├── myshipT8blocks.png       # Tier 8 block map
    └── README.md               # Color reference
```

## Structure File Format

```json
{
  "config": {
    "shipUpgrades": {
      "capabilities": ["teleport", "planetTravel", "systemTravel"],
      "crewSize": 8
    }
  },
  "backgroundOverlays": [
    {
      "image": "myshipT6.png",
      "position": [8, 14],
      "fullbright": true
    },
    {
      "image": "myshipT6lit.png",
      "position": [8, 14]
    }
  ],
  "blockKey": "blockKey.config:blockKey",
  "blockImage": "myshipT6blocks.png"
}
```

## Creating Block Maps

1. **Start with red background** - This is "outside" the ship
2. **Draw interior with blue** - Walkable areas
3. **Add objects as single pixels** - Use color codes above
4. **Required objects:**
   - Teleporter (purple) - Player spawn
   - Captain's Chair (cyan) - Required for travel
   - Fuel Hatch (salmon) - Required for FTL
5. **Scale:** 8 pixels = 1 game tile

### Example Block Map Layout

```
RRRRRRRRRRRRRRRRRRRR
RRRRRBBBBBBBBBBRRRRR  R = Red (outside)
RRRBBBBBBBBBBBBBBRRR  B = Blue (interior)
RRRBBPBBBBBBBBCBRRR   P = Purple (teleporter)
RRRBBGBBBBBBBBBBBRRR  G = Green (locker)
RRRRRBBBBBBBBBBRRRRR  C = Cyan (chair)
RRRRRRRRRRRRRRRRRRRR
```

## Creating Ship Sprites

The `.png` sprite is the visual ship:
- Can be any resolution (typically 2-4x block map size)
- Position offset in structure file aligns it with block map
- Use transparency for non-ship areas

The `.lit.png` overlay:
- Same size and position as main sprite
- Only contains glowing elements (thrusters, lights)
- Everything else transparent

## Registering Your Ship

Add to your race's `.species` file:

```json
{
  "kind": "myrace",
  "shipConfig": {
    "shipPackage": "/ships/myship/blockKey.config",
    "shipUpgrades": "/ships/myship/myshipT0.structure"
  }
}
```

## Tips

1. **Start small** - Create T0 and T8 first
2. **Test block maps** - Spawn in-game to verify layout
3. **Keep it simple** - Complex shapes are hard to block-map
4. **Use templates** - Base your layout on existing ships
5. **Check object placement** - Objects need proper anchor pixels

## See Also

- `StarboundParticleGenerator.ps1` - Particle effects
- `StarboundAnimationGenerator.ps1` - Sprite animations
- `StarboundBehaviorGenerator.ps1` - AI behavior trees
- `StarboundTileGenerator.ps1` - Tile/material files
- `StarboundCursorGenerator.ps1` - Mouse cursors

