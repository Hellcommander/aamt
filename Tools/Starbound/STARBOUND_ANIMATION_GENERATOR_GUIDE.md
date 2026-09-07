# Starbound Animation Generator Guide

Generate Starbound/OpenStarbound-compatible `.animation` and `.frames` files for particle effects, status effects, and other animated elements.

## Quick Start

### Using Presets

```powershell
# Fire animation (4 frames, 32x32)
.\StarboundAnimationGenerator.ps1 -AnimationName "myfire" -Preset Fire

# Smoke animation (8 frames, 32x32)
.\StarboundAnimationGenerator.ps1 -AnimationName "customsmoke" -Preset Smoke

# With placeholder image for testing
.\StarboundAnimationGenerator.ps1 -AnimationName "testeffect" -Preset Sparkle -GeneratePlaceholderImage
```

### Custom Animation

```powershell
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "myeffect" `
    -FrameCount 8 `
    -FrameSize @(32, 32) `
    -AnimationCycle 0.5
```

### From Existing Spritesheet

```powershell
# Drag-and-drop an image onto StarboundAnimationGenerator.bat
# Or use command line:
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "imported" `
    -ImagePath "myspritesheet.png" `
    -FrameCount 6 `
    -FrameSize @(48, 48)
```

---

## Starbound Animation Format

### .animation File

```json
{
  "frames" : "animationname.png",
  "variants" : 1,
  "frameNumber" : 8,
  "animationCycle" : 0.5,
  "offset" : [0, 0]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `frames` | String | Path to spritesheet PNG |
| `variants` | Int | Number of animation variants (rows) |
| `frameNumber` | Int | Number of frames (columns) |
| `animationCycle` | Float | Duration of animation in seconds |
| `offset` | [x, y] | Pixel offset for positioning |
| `loops` | Float | (Optional) Number of loops before stopping |

### .frames File

```json
{
  "frameGrid" : {
    "size" : [32, 32],
    "dimensions" : [8, 1]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `frameGrid.size` | [w, h] | Size of each frame in pixels |
| `frameGrid.dimensions` | [cols, rows] | Grid layout (frames × variants) |

---

## Presets

| Preset | Frames | Size | Cycle | Description |
|--------|--------|------|-------|-------------|
| `Fire` | 4 | 32×32 | 0.4s | Burning flame |
| `Ice` | 6 | 32×32 | 0.6s | Ice crystal shimmer |
| `Poison` | 8 | 32×32 | 0.8s | Toxic gas cloud |
| `Electric` | 4 | 24×24 | 0.15s | Electric spark |
| `Smoke` | 8 | 32×32 | 0.4s | Rising smoke |
| `Sparkle` | 4 | 16×16 | 0.6s | Magic sparkle |
| `Poof` | 6 | 48×48 | 0.3s | Explosion poof |
| `HitSpark` | 4 | 16×16 | 0.15s | Weapon hit spark |
| `Gas` | 8 | 32×32 | 0.8s | Gas cloud |
| `Charge` | 17 | 48×48 | 0.4s | Charging energy |

---

## Parameters Reference

### Required

| Parameter | Type | Description |
|-----------|------|-------------|
| `-AnimationName` | String | Name for the animation files |

### Animation Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-FrameCount` | Int | 8 | Number of animation frames |
| `-FrameSize` | Int[] | [32,32] | Size of each frame [width, height] |
| `-AnimationCycle` | Float | 0.5 | Animation duration in seconds |
| `-Variants` | Int | 1 | Number of animation variants |
| `-Offset` | Int[] | [0,0] | Animation offset [x, y] |
| `-Loops` | Float | 0 | Number of loops (0 = infinite) |

### Source Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `-ImagePath` | String | Path to existing spritesheet |
| `-Preset` | String | Use a preset configuration |

### Output Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `-OutputDir` | String | Output directory (default: StarboundAnimations) |
| `-GeneratePlaceholderImage` | Switch | Create a test spritesheet |
| `-PlaceholderColor` | Int[] | RGBA color for placeholder |

---

## Output Structure

```
StarboundAnimations/
└── myeffect/
    ├── myeffect.animation    # Animation definition
    ├── myeffect.frames       # Frame grid definition
    ├── myeffect.png          # Spritesheet (if generated/copied)
    └── animation_metadata.json
```

---

## Spritesheet Requirements

### Layout

Spritesheets must be arranged in a horizontal strip (or grid for variants):

```
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ F1 │ F2 │ F3 │ F4 │ F5 │ F6 │ F7 │ F8 │  ← Variant 1
└────┴────┴────┴────┴────┴────┴────┴────┘
```

With multiple variants:
```
┌────┬────┬────┬────┐
│ F1 │ F2 │ F3 │ F4 │  ← Variant 1
├────┼────┼────┼────┤
│ F1 │ F2 │ F3 │ F4 │  ← Variant 2
└────┴────┴────┴────┘
```

### Size Calculation

- **Total Width** = Frame Width × Frame Count
- **Total Height** = Frame Height × Variants

Example: 8 frames at 32×32 = 256×32 spritesheet

---

## Using in Particles

Reference animations in `.particle` files:

```json
{
  "kind" : "myparticle",
  "definition" : {
    "type" : "animated",
    "animation" : "/animations/myeffect/myeffect.animation",
    "position" : [0, 0],
    "finalVelocity" : [0, 2],
    "approach" : [0, 50],
    "size" : 1.0,
    "timeToLive" : 0.5
  }
}
```

---

## Examples

### Status Effect Animation

```powershell
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "burningstatus" `
    -FrameCount 4 `
    -FrameSize @(32, 32) `
    -AnimationCycle 0.8 `
    -Loops 20
```

### Large Explosion

```powershell
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "bigexplosion" `
    -FrameCount 12 `
    -FrameSize @(64, 64) `
    -AnimationCycle 0.6
```

### Multi-Variant Effect

```powershell
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "coloreffect" `
    -FrameCount 6 `
    -FrameSize @(32, 32) `
    -AnimationCycle 0.5 `
    -Variants 4
```

### From Existing Image

```powershell
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "imported" `
    -ImagePath "C:\Art\myspritesheet.png" `
    -FrameSize @(48, 48)
# Frame count auto-detected from image width
```

---

## Integration with StarboundParticleGenerator

Create a complete animated particle:

```powershell
# Step 1: Generate animation files
.\StarboundAnimationGenerator.ps1 `
    -AnimationName "magicaura" `
    -Preset Sparkle `
    -GeneratePlaceholderImage

# Step 2: Generate particle using the animation
.\StarboundParticleGenerator.ps1 `
    -ParticleName "magicauraparticle" `
    -ParticleType Animated `
    -AnimationPath "/animations/magicaura/magicaura.animation" `
    -TimeToLive 0.6
```

---

## Mod Structure

```
mods/
└── MyMod/
    ├── animations/
    │   └── myeffect/
    │       ├── myeffect.animation
    │       ├── myeffect.frames
    │       └── myeffect.png
    └── particles/
        └── myparticle.particle
```

---

## Tips

1. **Test animations** with `-GeneratePlaceholderImage` before creating art
2. **Match timing** - AnimationCycle should match particle TimeToLive for seamless loops
3. **Use power-of-2 sizes** (16, 32, 64) for best compatibility
4. **Keep frames consistent** - All frames should be exactly the same size

---

*Compatible with Starbound 1.4+ and OpenStarbound*

