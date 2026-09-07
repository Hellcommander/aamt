# Starbound Particle Generator Guide

Generate Starbound/OpenStarbound-compatible particle effects with presets and full customization.

## Quick Start

### Using Presets

```powershell
# Fire particles
.\StarboundParticleGenerator.ps1 -ParticleName "myfire" -Preset Fire

# Ice particles  
.\StarboundParticleGenerator.ps1 -ParticleName "frosteffect" -Preset Ice

# Poison particles
.\StarboundParticleGenerator.ps1 -ParticleName "toxiccloud" -Preset Poison
```

### Drag-and-Drop

Double-click `StarboundParticleGenerator.bat` and follow the prompts.

---

## Particle Types

### Ember Particles

Simple colored point particles - the most common type.

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "customspark" `
    -ParticleType Ember `
    -Color @(255, 200, 50, 255) `
    -Size 1.0 `
    -TimeToLive 0.5 `
    -InitialVelocity @(0, 5) `
    -FinalVelocity @(0, 10)
```

### Textured Particles

Use an image file for the particle.

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "leafparticle" `
    -ParticleType Textured `
    -ImagePath "/particles/leaf.png" `
    -Size 0.8 `
    -Rotation 0 `
    -AngularVelocity 180
```

### Animated Particles

Use an animation file for animated particles.

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "flameburst" `
    -ParticleType Animated `
    -AnimationPath "/animations/fire/burst.animation" `
    -Looping
```

---

## Presets

| Preset | Type | Description |
|--------|------|-------------|
| `Fire` | Ember | Orange/red rising flames with light emission |
| `Ice` | Ember | Blue crystalline particles drifting upward |
| `Poison` | Ember | Green toxic particles |
| `Electric` | Ember | Fast white/blue sparks |
| `Blood` | Ember | Red splatter particles with gravity |
| `Sparkle` | Ember | Bright yellow/white magic sparkles |
| `Smoke` | Animated | Rising smoke using animation file |
| `Bubble` | Textured | Underwater bubble particles |

---

## Parameters Reference

### Required

| Parameter | Type | Description |
|-----------|------|-------------|
| `-ParticleName` | String | Name/kind of the particle (used in game) |

### Type Selection

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-ParticleType` | String | Ember | Type: Ember, Textured, Animated, Source |
| `-Preset` | String | None | Apply a preset configuration |

### Appearance

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-Color` | Int[] | [255,255,255,255] | RGBA color (Ember/Textured) |
| `-Size` | Float | 1.0 | Particle scale |
| `-Fade` | Float | 0.9 | Fade rate (0-1) |
| `-Layer` | String | middle | Render layer: front, middle, back |
| `-Light` | Int[] | - | RGB light emission |

### Motion

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-InitialVelocity` | Float[] | [0,0] | Starting velocity [X,Y] |
| `-FinalVelocity` | Float[] | [0,0] | Ending velocity [X,Y] |
| `-Approach` | Float[] | [20,20] | Velocity approach rate |
| `-TimeToLive` | Float | 1.0 | Particle lifetime (seconds) |

### Rotation (Textured only)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-Rotation` | Float | 0 | Initial rotation (degrees) |
| `-AngularVelocity` | Float | 0 | Rotation speed (deg/sec) |

### Asset Paths

| Parameter | Type | Description |
|-----------|------|-------------|
| `-ImagePath` | String | Path to image (Textured type) |
| `-AnimationPath` | String | Path to animation (Animated type) |

### Destruction

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-DestructionAction` | String | none | shrink, fade, or none |
| `-DestructionTime` | Float | 0 | Duration of destruction effect |

### Special Flags

| Parameter | Type | Description |
|-----------|------|-------------|
| `-CollidesLiquid` | Switch | Particle collides with liquid |
| `-UnderwaterOnly` | Switch | Only spawn underwater |
| `-Looping` | Switch | Animation loops (Animated type) |

### Variance

Add randomization with `-Variance`:

```powershell
-Variance @{
    initialVelocity = @(2, 2)
    size = 0.5
    color = @(255, 100, 0, 255)
}
```

---

## Output Files

The generator creates:

```
StarboundParticles/
├── myparticle.particle        # Main particle file
├── myparticle2.particle       # Smaller variant
├── myparticledust.particle    # Dust/trail variant
└── particle_metadata.json     # Generation info
```

---

## Using in Your Mod

### File Structure

```
mods/
└── MyMod/
    └── particles/
        └── myparticle.particle
```

### Spawning from Lua

```lua
-- Spawn a single particle
world.spawnProjectile("myparticle", position)

-- Spawn with velocity
world.spawnProjectile("myparticle", position, nil, direction, false)

-- Spawn multiple
for i = 1, 10 do
    world.spawnProjectile("myparticle", position)
end
```

### In Projectile Config

```json
{
  "projectileName" : "myprojectile",
  "physics" : "default",
  "emitters" : [ "myparticle" ]
}
```

### In Status Effect

```json
{
  "name" : "mystatus",
  "particleEmitter" : {
    "particle" : "myparticle",
    "emissionRate" : 5.0
  }
}
```

---

## Examples

### Magical Aura

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "magicaura" `
    -ParticleType Ember `
    -Color @(200, 100, 255, 255) `
    -Size 0.6 `
    -Fade 0.85 `
    -TimeToLive 0.8 `
    -InitialVelocity @(0, 1) `
    -FinalVelocity @(0, 2) `
    -Light @(150, 80, 200) `
    -Variance @{ initialVelocity = @(1.5, 1); size = 0.2 }
```

### Blood Splatter

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "bloodsplat" `
    -Preset Blood `
    -Layer front
```

### Underwater Bubbles

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "mybubbles" `
    -Preset Bubble `
    -Size 0.3
```

### Tech Activation

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "techactivate" `
    -Preset Electric `
    -Color @(100, 200, 255, 255) `
    -Size 0.4 `
    -TimeToLive 0.15
```

---

## Starbound Particle Format Reference

### .particle File Structure

```json
{
  "kind" : "particlename",
  "definition" : {
    "type" : "ember|textured|animated",
    // Type-specific properties
    "size" : 1.0,
    "fade" : 0.9,
    "initialVelocity" : [0, 0],
    "finalVelocity" : [0, 0],
    "approach" : [20, 20],
    "timeToLive" : 1.0,
    "layer" : "middle",
    "variance" : { }
  }
}
```

### .particlesource File Structure

```json
{
  "kind" : "sourcename",
  "definition" : {
    "duration" : 0.2,
    "loops" : true,
    "initialParticles" : [["particle1"]],
    "particles" : [["particle2"]],
    "finalParticles" : [["particle3", "particle3"]]
  }
}
```

---

## Related Tools

- `StarboundAssetGenerator.ps1` - General asset generation
- `MultiAssetGenerator.ps1` - Multi-game asset pipeline
- `ParticleEffectGenerator.ps1` - Cross-game particle effects

---

*Compatible with Starbound 1.4+ and OpenStarbound*

