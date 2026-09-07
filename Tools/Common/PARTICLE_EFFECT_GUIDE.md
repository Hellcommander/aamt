# Particle Effect Generator Guide

## Overview

The **Particle Effect Generator** creates animated particle spritesheets for use in game assets. It supports multiple particle types, animation frames, and game format exports.

## Features

- **Multiple Particle Types**: Generate different particle variations (orbs, sparks, fragments, etc.)
- **Animated Sequences**: Each particle can have multiple frames for animation
- **Game Format Support**: Export to Terraria, Elin, Starbound, Transcendence
- **Effect Types**: Portal, Spell, Projectile, Explosion, Trail, Custom
- **AI Integration**: Optional AI-powered particle design
- **Blender Rendering**: High-quality procedural particle generation

## Quick Start

### Basic Particle Generation

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "EnergyParticles" `
    -ParticleCount 4 `
    -FrameCount 4 `
    -ParticleSize 8
```

### Portal Particles

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "NetherPortal_Particles" `
    -ParticleCount 6 `
    -FrameCount 6 `
    -ParticleSize 8 `
    -GameFormat @("Terraria")
```

### Spell Particles with AI

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Spell" `
    -EffectName "MagicMissile_Particles" `
    -ParticleCount 5 `
    -FrameCount 4 `
    -UseAI `
    -EffectDescription "Magical energy particles with sparkles and mana orbs"
```

## Parameters

- **`-EffectType`**: Type of effect (Portal, Spell, Projectile, Explosion, Trail, Custom)
- **`-EffectName`**: Name for the particle effect
- **`-ParticleCount`**: Number of different particle types (default: 4)
- **`-FrameCount`**: Animation frames per particle (default: 4)
- **`-ParticleSize`**: Size of each particle in pixels (default: 8)
- **`-OutputDir`**: Output directory (default: "ParticleEffects")
- **`-GameFormat`**: Target formats (default: All)
- **`-UseAI`**: Use AI for particle design
- **`-ColorPalette`**: Color palette (e.g., "purple,blue,cyan")
- **`-EffectDescription`**: Description for AI generation

## Effect Types

### Portal Particles
- **Colors**: Purple, blue, cyan
- **Types**: Energy orbs, sparks, fragments
- **Use**: Portal effects, teleportation visuals

### Spell Particles
- **Colors**: Blue, white, light blue
- **Types**: Magic sparkles, mana particles, arcane fragments
- **Use**: Spell casting, magic effects

### Projectile Particles
- **Colors**: Yellow, orange, red
- **Types**: Trail particles, sparks, embers
- **Use**: Projectile trails, weapon effects

### Explosion Particles
- **Colors**: Orange, red, yellow
- **Types**: Sparks, debris, smoke, fire embers
- **Use**: Explosions, impacts, destruction effects

### Trail Particles
- **Colors**: Blue, cyan, white
- **Types**: Energy trails, spark trails, glow trails
- **Use**: Movement trails, speed effects

## Spritesheet Format

The generator creates a spritesheet with:
- **Width**: `ParticleSize × FrameCount` (all frames of one particle horizontally)
- **Height**: `ParticleSize × ParticleCount` (each particle type on a separate row)
- **Layout**: Horizontal frames, vertical particle types

Example (4 particles, 4 frames, 8px each):
- Width: 32px (4 frames × 8px)
- Height: 32px (4 particles × 8px)
- Total: 32×32 spritesheet

## Integration with Portal Generator

Generate particles automatically with portals:

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "NetherPortal" `
    -GenerateParticles `
    -ParticleCount 6 `
    -ParticleFrames 4
```

This will:
1. Generate the portal tile
2. Generate matching particle effects
3. Add particle code to the tile class
4. Export particles to game format

## Game Format Support

### Terraria
- Spritesheet with JSON metadata
- Particle count and frame information
- Ready for tModLoader integration

### Elin
- Spritesheet with JSON metadata
- Spell/effect particle format
- Compatible with Elin's particle system

### Starbound
- Spritesheet format
- Frame definitions
- Compatible with Starbound effects

### Transcendence
- Spritesheet format
- Game-specific metadata
- Ready for mod integration

## Usage Examples

### Example 1: Portal Energy Particles

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "PortalEnergy" `
    -ParticleCount 6 `
    -FrameCount 6 `
    -ParticleSize 8 `
    -ColorPalette "purple,blue,cyan"
```

### Example 2: Spell Casting Particles

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Spell" `
    -EffectName "FireballParticles" `
    -ParticleCount 5 `
    -FrameCount 4 `
    -ParticleSize 12 `
    -ColorPalette "orange,red,yellow"
```

### Example 3: Explosion Debris

```powershell
.\ParticleEffectGenerator.ps1 `
    -EffectType "Explosion" `
    -EffectName "ExplosionDebris" `
    -ParticleCount 8 `
    -FrameCount 5 `
    -ParticleSize 10 `
    -GameFormat @("Terraria", "Starbound")
```

## Customization

### Particle Shapes

The generator creates different particle shapes:
- **Type 0**: Energy orb (sphere)
- **Type 1**: Spark (elongated cube)
- **Type 2**: Fragment (irregular sphere)

Modify the Blender script in the generator to add custom shapes.

### Animation

Particles fade out over frames:
- **Size**: Decreases by 50% over frames
- **Alpha**: Fades by 70% over frames
- **Effect**: Creates smooth fade-out animation

### Colors

Colors are automatically selected based on effect type, but you can override with `-ColorPalette`.

## Integration with Control Room

Use the Control Room to refine particle designs:

```powershell
# Generate particles
.\ParticleEffectGenerator.ps1 `
    -EffectType "Portal" `
    -EffectName "TestParticles" `
    -OutputDir "TempParticles"

# Review in Control Room
.\AssetGeneratorControlRoom.ps1 `
    -WatchDirectory "TempParticles" `
    -AssetType "Texture"
```

## Best Practices

1. **Particle Count**: 4-6 particles for most effects
2. **Frame Count**: 4-6 frames for smooth animation
3. **Particle Size**: 8-12 pixels for most games
4. **Color Palette**: Match the main asset colors
5. **Effect Type**: Choose appropriate type for visual consistency

## Troubleshooting

### Particles Not Rendering

- Check Blender is installed and accessible
- Verify particle size is appropriate
- Check file paths are correct

### Animation Not Smooth

- Increase frame count
- Adjust fade-out rates in Blender script
- Check particle size consistency

### Colors Not Matching

- Override with `-ColorPalette`
- Check effect type matches desired colors
- Regenerate with different palette

## Advanced Usage

### Custom Particle Shapes

Modify the Blender script generation to create custom shapes:

```python
# Add custom shape
if particle_type == 3:
    # Custom particle shape
    bpy.ops.mesh.primitive_torus_add(...)
```

### Multiple Effect Types

Generate multiple particle sets:

```powershell
.\ParticleEffectGenerator.ps1 -EffectType "Portal" -EffectName "PortalParticles"
.\ParticleEffectGenerator.ps1 -EffectType "Spell" -EffectName "SpellParticles"
.\ParticleEffectGenerator.ps1 -EffectType "Explosion" -EffectName "ExplosionParticles"
```

### Batch Generation

Generate particles for multiple assets:

```powershell
$effects = @("FirePortal", "IcePortal", "VoidPortal")
foreach ($effect in $effects) {
    .\ParticleEffectGenerator.ps1 `
        -EffectType "Portal" `
        -EffectName "${effect}_Particles" `
        -ParticleCount 4 `
        -FrameCount 4
}
```

## References

- **Terraria Portal Generator**: For portal-specific particles
- **Asset Generator Control Room**: For visual refinement
- **Cross-Game Spritesheet**: For format conversion

---

**Generated by**: Particle Effect Generator  
**Compatible with**: Terraria, Elin, Starbound, Transcendence  
**Version**: 1.0

