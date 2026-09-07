# Terraria Portal Generator Guide

A comprehensive tool for generating procedural portal effects for Terraria mods with spacetime distortion particles.

## Overview

This generator creates complete portal effect packages including:
- **Portal tile textures** (base, frame, normal map, distortion map)
- **Particle effect JSON profiles** (data-driven particle systems)
- **Shader configuration** (distortion, chromatic aberration)
- **tModLoader code templates** (ready-to-use C# code)

## Quick Start

```powershell
# Generate a void portal
.\TerrariaPortalGenerator.ps1 -PortalName "voidgate" -Preset Void -GeneratePlaceholders

# Custom fire portal
.\TerrariaPortalGenerator.ps1 -PortalName "nethergate" -Preset Fire -Shape Tear -ParticleCount 60
```

## Presets

| Preset | Colors | Motion | Description |
|--------|--------|--------|-------------|
| **Void** | Blue/Cyan | Inward Spiral | Cold blue void portal |
| **Fire** | Red/Orange | Outflow | Fiery red portal |
| **Ice** | Light Blue | Inflow | Frosty blue portal |
| **Electric** | Yellow/Cyan | Random | Electric portal |
| **Nature** | Green | Orbit | Green nature portal |
| **Shadow** | Purple | Inward Spiral | Dark shadow portal |
| **Light** | White/Gold | Outward Spiral | Bright light portal |

## Generated Files

```
voidgate/
├── voidgate_profile.json          # Portal effect profile
├── voidgatePortalTile.cs          # tModLoader tile code
├── PortalEffectManager.cs         # Particle system manager
└── Textures/
    ├── voidgate_Base.png          # Base portal texture
    ├── voidgate_Frame.png         # Frame/anchor texture
    ├── voidgate_Normal.png        # Normal map for lighting
    └── voidgate_Distort.png       # Distortion map (RG channels)
```

## Portal Profile JSON

The profile defines all portal properties:

```json
{
  "id": "voidgate",
  "game": "Terraria",
  "type": "portalEffect",
  "tiles": {
    "size": 32,
    "baseTexture": "Textures/Portals/voidgate_Base.png",
    "frameTexture": "Textures/Portals/voidgate_Frame.png",
    "normalMap": "Textures/Portals/voidgate_Normal.png",
    "distortionMap": "Textures/Portals/voidgate_Distort.png"
  },
  "particles": {
    "count": 40,
    "motion": "orbitInwardSpiral",
    "speedMin": 0.4,
    "speedMax": 1.2,
    "colors": {
      "core": "#b3f0ff",
      "rim": "#3b7fff",
      "accent": "#ff66ff"
    }
  },
  "shader": {
    "distortStrength": 0.04,
    "waveFrequency": 3.2,
    "chromaticAbberation": 0.015
  }
}
```

## Particle Motion Patterns

| Pattern | Description |
|---------|-------------|
| `orbitInwardSpiral` | Particles spiral inward and shrink |
| `orbitOutwardSpiral` | Particles spiral outward and expand |
| `inflow` | Particles flow toward center |
| `outflow` | Particles flow away from center |
| `orbit` | Particles orbit at constant radius |
| `random` | Random chaotic motion |

## Parameters

### Basic

```powershell
-PortalName        # Required. Portal identifier
-Preset            # Preset to use (see above)
-Description       # Natural language description
-OutputDir         # Output directory
```

### Appearance

```powershell
-Shape             # Circle, Ellipse, Tear, Hexagon, Square
-TileSize          # Texture size (default: 32)
-Animated          # Enable animation
-AnimationFrames   # Number of frames
```

### Colors

```powershell
-CoreColor         # Hex color (e.g., "#b3f0ff")
-RimColor          # Rim/border color
-AccentColor       # Highlight color
```

### Particles

```powershell
-ParticleCount     # Number of particles
-MotionPattern     # Motion type (see above)
```

### Shader

```powershell
-DistortStrength   # Distortion intensity (0.0-0.1)
-WaveFrequency     # Wave frequency (1.0-10.0)
-ChromaticAberration # Color shift amount (0.0-0.05)
```

## Examples

### Void Portal (Default)

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "voidgate" `
    -Preset Void `
    -Shape Circle `
    -GeneratePlaceholders
```

### Custom Fire Portal

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "nethergate" `
    -Preset Fire `
    -Shape Tear `
    -CoreColor "#ff3300" `
    -RimColor "#ff0000" `
    -ParticleCount 60 `
    -MotionPattern "outflow" `
    -DistortStrength 0.08 `
    -GeneratePlaceholders
```

### Electric Portal

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "lightning_gate" `
    -Preset Electric `
    -Shape Hexagon `
    -ChromaticAberration 0.025 `
    -GeneratePlaceholders
```

## Texture Specifications

### Base Texture
- **Size**: 32×32 pixels (or custom)
- **Format**: PNG with transparency
- **Content**: Portal core with rim glow

### Frame Texture
- **Size**: Same as base
- **Purpose**: Anchor/frame tiles around portal
- **Style**: Slightly different from base

### Normal Map
- **Size**: Same as base
- **Format**: RGB (normals encoded)
- **Purpose**: Lighting/shading effects

### Distortion Map
- **Size**: Same as base
- **Format**: RGB (offset vectors in RG channels)
- **Purpose**: Screen-space distortion shader

## tModLoader Integration

### 1. Copy Generated Files

```
YourMod/
├── Tiles/
│   └── voidgatePortalTile.cs
├── Systems/
│   └── PortalEffectManager.cs
└── Content/
    └── Textures/
        └── Portals/
            ├── voidgate_Base.png
            ├── voidgate_Frame.png
            ├── voidgate_Normal.png
            └── voidgate_Distort.png
```

### 2. Register Portal

In your mod's `Load()` method:

```csharp
PortalEffectManager.RegisterProfile("voidgate", 
    "Content/voidgate_profile.json");
```

### 3. Add Tile

```csharp
Mod.AddContent<WorldLinkPortalTile>();
```

## Particle System Features

- **Data-driven**: All parameters in JSON
- **Multiple motion patterns**: Spiral, flow, orbit, random
- **Color gradients**: Core → Rim → Accent
- **Alpha curves**: Fade in/out with peak
- **Size curves**: Particles shrink/grow over lifetime
- **Orbit mechanics**: Radius and angle tracking

## Shader Effects

### Distortion
- Uses distortion map texture
- Samples background with UV offsets
- Creates spacetime warping effect

### Chromatic Aberration
- Shifts RGB channels slightly
- Creates prismatic effect
- Configurable strength

### Wave Animation
- Time-based wave function
- Radial ripples
- Configurable frequency

## Tips

1. **Start with presets** - They have balanced values
2. **Test particle counts** - 30-60 is usually good
3. **Adjust distortion** - Too high can be disorienting
4. **Use normal maps** - Adds depth to flat textures
5. **Match colors** - Core/rim/accent should harmonize

## Advanced Usage

### Multiple Portals

Generate different portals for different worlds:

```powershell
.\TerrariaPortalGenerator.ps1 -PortalName "overworld_gate" -Preset Nature
.\TerrariaPortalGenerator.ps1 -PortalName "nether_gate" -Preset Fire
.\TerrariaPortalGenerator.ps1 -PortalName "void_gate" -Preset Void
```

### Animated Portals

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "animated_void" `
    -Animated `
    -AnimationFrames 8
```

## Integration with MultiAssetGenerator

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Terraria `
    -AssetType Portal `
    -AssetName "my_portal" `
    -Description "blue void portal with spacetime distortion"
```

## See Also

- tModLoader Documentation
- Terraria Modding Wiki
- Portal Effect Examples

