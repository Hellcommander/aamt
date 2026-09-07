# Space Whale Visual Language Guide

## Overview

Complete visual language system for Space Whale ships, combining **Nova Drift's high-energy aesthetic** with **organic whale-like characteristics**.

## Core Aesthetic

### Base Style: Nova Drift
- High-energy glows with smooth additive blending
- Procedural distortion (heat-haze, radial displacement)
- Particle-driven motion
- Layered composition (core + shockwave + bloom + particles)

### Adaptation: Space Whale
- Organic flow along spline spine
- Bioluminescent skin with subsurface scattering
- Breathing rhythm synced with Bio-Core
- Gravity aura with visible distortion
- Shockwave expansion with turbulence

## Color Palettes

### Primary (Cyan-Blue Energy)
**Use Case**: Default space whale
- Base: `#1a2a3a` (Dark blue-gray)
- Vein: `#66ccff` (Bright cyan)
- Carapace: `#4a5a6a` (Medium gray-blue)
- Emissive: `#88ffff` (Light cyan)
- Accent: `#ff66ff` (Magenta-pink)

### Bio-Core (Green-Cyan Bio-Energy)
**Use Case**: Bio-Core active state
- Base: `#1a3a2a` (Dark green-gray)
- Vein: `#00ff88` (Bright green-cyan)
- Carapace: `#4a6a5a` (Medium green-gray)
- Emissive: `#44ffaa` (Light green-cyan)
- Accent: `#88ffcc` (Pale green-cyan)

### Orbit Field (Cyan Gravity Aura)
**Use Case**: Orbit Field active
- Base: `#1a2a3a` (Dark blue-gray)
- Vein: `#66ccff` (Bright cyan)
- Carapace: `#4a5a6a` (Medium gray-blue)
- Emissive: `#aaffff` (Very light cyan)
- Accent: `#88ddff` (Light cyan-blue)

### Song Pulse (Purple-Pink Shockwave)
**Use Case**: Song Pulse ability
- Base: `#2a1a3a` (Dark purple-gray)
- Vein: `#ff66ff` (Bright magenta-pink)
- Carapace: `#5a4a6a` (Medium purple-gray)
- Emissive: `#ff99ff` (Light magenta)
- Accent: `#ffccff` (Pale magenta)

### Swallow (Red-Pink Implosion)
**Use Case**: Swallow consumption
- Base: `#3a1a2a` (Dark red-gray)
- Vein: `#ff0066` (Bright red-pink)
- Carapace: `#6a4a5a` (Medium red-gray)
- Emissive: `#ff4488` (Light red-pink)
- Accent: `#ff88aa` (Pale red-pink)

### Regeneration (Green Healing)
**Use Case**: Regenerative tissue active
- Base: `#1a3a2a` (Dark green-gray)
- Vein: `#00ff44` (Bright green)
- Carapace: `#4a6a5a` (Medium green-gray)
- Emissive: `#44ff88` (Light green)
- Accent: `#88ffaa` (Pale green)

## Materials

### Bioluminescent Skin
**Type**: Organic  
**Shader**: Principled BSDF + Emission

**Properties**:
- Base Color: `#1a2a3a`
- Subsurface Scattering: Enabled (radius: 0.1)
- Emission: `#66ccff` at intensity 3.5 (animated)
- Vein Flow: Enabled (speed: 1.2, pattern: noise)
- Roughness: 0.6
- Metallic: 0.0

**Texture Patterns**:
- Vein flow (noise texture, animated)
- Breathing pulse (sine wave, animated)
- Energy flow (flow map along spine)

### Carapace Plating
**Type**: Armor  
**Shader**: Principled BSDF + Emission

**Properties**:
- Base Color: `#4a5a6a`
- Metallic: 0.3
- Roughness: 0.6
- Emission: `#4a5a6a` at intensity 1.5
- Rim Glow: Enabled (intensity: 0.3)

**Texture Patterns**:
- Plating seams (Voronoi pattern)
- Wear marks (noise texture)

### Hybrid Skin/Carapace
**Type**: Hybrid  
**Shader**: Principled BSDF + Emission

**Properties**:
- Base Color: `#2a3a4a`
- Subsurface Scattering: Enabled
- Metallic: 0.15
- Roughness: 0.5
- Emission: `#66ccff` at intensity 2.5 (animated)

**Texture Patterns**:
- Vein flow + Plating seams

## Texture Patterns

### Vein Flow
- **Method**: Noise texture
- **Scale**: 5.0
- **Detail**: 8.0
- **Animated**: Yes (speed: 1.2)
- **Application**: Emission mask
- **Use Case**: Bioluminescent skin

### Breathing Pulse
- **Method**: Sine wave
- **Frequency**: 0.8 Hz
- **Amplitude**: 0.05
- **Animated**: Yes
- **Application**: Scale modifier
- **Use Case**: Organic breathing

### Energy Flow
- **Method**: Flow map
- **Direction**: Spine flow
- **Speed**: 1.0
- **Intensity**: 0.6
- **Animated**: Yes
- **Application**: Emission intensity
- **Use Case**: Spine energy

### Plating Seams
- **Method**: Voronoi
- **Scale**: 3.0
- **Randomness**: 0.5
- **Animated**: No
- **Application**: Normal map
- **Use Case**: Carapace detail

### Wear Marks
- **Method**: Noise texture
- **Scale**: 2.0
- **Detail**: 4.0
- **Animated**: No
- **Application**: Roughness map
- **Use Case**: Carapace aging

## Animations

### Breathing
- **Type**: Organic
- **Method**: Scale modulation
- **Speed**: 0.8 cycles/second
- **Amplitude**: 0.05 (5% scale change)
- **Pattern**: Sine wave
- **Sync**: Bio-Core rhythm
- **Duration**: Continuous
- **Frames**: 16

### Tail Sweep
- **Type**: Motion
- **Method**: Rotation animation
- **Trigger**: Acceleration
- **Amplitude**: 15 degrees
- **Damping**: 0.8
- **Speed**: 1.0
- **Duration**: Event-based

### Gill Vent Pulse
- **Type**: Organic
- **Method**: Scale pulse
- **Count**: 6 vents
- **Speed**: 1.5 cycles/second
- **Amplitude**: 0.5 (50% scale change)
- **Phase Offset**: 0.2 between vents
- **Pattern**: Sine wave
- **Duration**: Continuous

### Dorsal Crest Glow
- **Type**: Emission
- **Method**: Intensity modulation
- **Speed**: 0.6 cycles/second
- **Amplitude**: 0.3 (30% intensity change)
- **Pattern**: Sine wave
- **Sync**: Bio-Core
- **Duration**: Continuous

### Vein Flow
- **Type**: Texture
- **Method**: UV offset
- **Direction**: Spine flow
- **Speed**: 1.2 units/second
- **Pattern**: Noise
- **Scale**: 5.0
- **Duration**: Continuous

## Effects

### Bioluminescent Glow
- **Type**: Emission
- **Intensity**: 3.5
- **Color**: `#66ccff`
- **Blend Mode**: Additive
- **Falloff**: Inverse square
- **Animated**: Yes
- **Use Case**: Skin emission

### Bloom
- **Type**: Post-process
- **Intensity**: 1.2
- **Radius**: 1.5
- **Threshold**: 0.8
- **Use Case**: Glow enhancement

### Subsurface Scattering
- **Type**: Material
- **Enabled**: Yes
- **Radius**: [0.1, 0.1, 0.1]
- **Color**: `#1a2a3a`
- **Intensity**: 0.3
- **Use Case**: Organic skin

### Distortion
- **Type**: Post-process
- **Strength**: 0.08
- **Type**: Gravity well
- **Noise**: Perlin
- **Speed**: 0.5
- **Scale**: 2.0
- **Use Case**: Orbit Field

### Chromatic Aberration
- **Type**: Post-process
- **Enabled**: Yes
- **Strength**: 0.04
- **Radial**: Yes
- **Use Case**: High-energy effects

## Lighting

### Self-Illumination
- **Enabled**: Yes
- **Intensity**: 3.5
- **Color**: `#66ccff`
- **Range**: 100 units
- **Falloff**: Inverse square

### Ambient
- **Enabled**: Yes
- **Color**: `#0a1a2a`
- **Intensity**: 0.2

### Rim Light
- **Enabled**: Yes
- **Color**: `#ffffff`
- **Intensity**: 1.0
- **Angle**: 90 degrees

## Module Visual Assignments

### Head Module
- **Material**: Bioluminescent Skin
- **Color Palette**: Primary
- **Animations**: Breathing, Vein Flow
- **Effects**: Glow, Subsurface Scattering
- **Special**: Maw glow, Eye emission

### Mid Section
- **Material**: Bioluminescent Skin
- **Color Palette**: Primary
- **Animations**: Breathing, Gill Vent Pulse, Vein Flow
- **Effects**: Glow, Subsurface Scattering
- **Special**: Dorsal crest, Gills

### Belly Bay
- **Material**: Hybrid
- **Color Palette**: Primary
- **Animations**: Breathing
- **Effects**: Glow
- **Special**: Bay entrance, Drone portal

### Tail Module
- **Material**: Bioluminescent Skin
- **Color Palette**: Primary
- **Animations**: Breathing, Tail Sweep, Vein Flow
- **Effects**: Glow, Subsurface Scattering
- **Special**: Tail fins, Propulsion glow

### Dorsal Crest
- **Material**: Carapace Plating
- **Color Palette**: Primary
- **Animations**: Dorsal Crest Glow
- **Effects**: Glow, Rim Light
- **Special**: Crest emission

## Integration with Systems

### Bio-Core Active
- **Color Shift**: Primary → Bio-Core palette
- **Emission Intensity**: Scales with energy (0-100%)
- **Animation Speed**: Scales with regen rate

### Orbit Field Active
- **Color Shift**: Primary → Orbit Field palette
- **Distortion**: Enabled (strength scales with field strength)
- **Particle Trails**: Orbital particles visible

### Song Pulse
- **Color Shift**: Primary → Song Pulse palette
- **Shockwave Rings**: Expanding distortion
- **Particle Burst**: Radial particles

### Swallow Active
- **Color Shift**: Primary → Swallow palette
- **Implosion Effect**: Inward distortion
- **Plasma Harmonics**: Visible on maw

### Regeneration Active
- **Color Shift**: Primary → Regeneration palette (on damaged segments)
- **Emission**: Subtle glow on healing areas
- **Particle Flow**: Gentle upward particles

## Export Settings

### Formats
- **PNG**: Standard format (with alpha)
- **DDS**: Compressed format (with mipmaps)
- **EXR**: High dynamic range (for HDR workflows)

### Resolutions
- **Ship**: 512×512 (standard)
- **Large**: 1024×1024 (high detail)
- **Spritesheet**: 4096×512 (animation frames)

### Compression
- **Quality**: High
- **Alpha**: Enabled
- **Mipmaps**: Enabled

## Usage

### Generate Assets
```powershell
.\SpaceWhaleVisualLanguageGenerator.ps1 -RegistryPath "space_whale_visual_language_registry.json" -OutputDir "Output/VisualLanguage"
```

### Use in Blender
1. Load color palette swatches
2. Apply material definitions
3. Use texture patterns
4. Set up animations
5. Export with settings

### Integration
- Color palettes → Material colors
- Materials → Blender shader setup
- Texture patterns → Procedural textures
- Animations → Keyframe sequences
- Effects → Post-process settings

## Files

- `space_whale_visual_language_registry.json` - Complete visual language definition
- `space_whale_visual_asset_generator.py` - Asset generator script
- `SpaceWhaleVisualLanguageGenerator.ps1` - Generator orchestrator
- `SPACE_WHALE_VISUAL_LANGUAGE_GUIDE.md` - This guide

## Next Steps

1. **Generate assets** using generator script
2. **Review color palettes** and material previews
3. **Apply to Blender** ship models
4. **Set up animations** based on patterns
5. **Export** for game integration

## Conclusion

The visual language system provides a **complete, cohesive aesthetic** that combines Nova Drift's high-energy style with organic whale characteristics. All assets are ready for generation and integration! 🎨

