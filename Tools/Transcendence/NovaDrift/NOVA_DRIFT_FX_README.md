# Nova Drift Style FX System

A complete pipeline for generating Nova Drift-style special effects in Transcendence: high-energy bursts, smooth additive glows, procedural distortion fields, particle-driven motion, and layered FX composition.

## Overview

The system generates Nova Drift-style effects with:
- **Core Glow**: Soft, additive, color-driven, pulsing or expanding
- **Shockwave Ring**: Thin, expanding circle, fades quickly, sometimes double-ringed
- **Particle Bloom**: Radial burst, small bright particles, short lifetime
- **Distortion Field**: Heat-haze wobble, radial displacement, subtle chromatic aberration
- **Procedural Noise**: Perlin/Voronoi/Simplex, animated, masked by shape

## Core Components

### 1. Registry Schema (`nova_drift_fx_registry_schema.json`)

Defines FX structure:
- Visual: colors, distortion, noise, sprite size, frames, layers
- Particles: burst count, speed, lifetime, motion patterns
- Timing: expansion times, fade out, easing curves
- Export: UNID, Transcendence format, resource paths

### 2. Blender Renderer (`blender_nova_drift_fx_renderer.py`)

Renders layered FX:
- Core glow with emission and pulse
- Shockwave ring with expanding animation
- Distortion map generation
- Particle system integration
- Frame-by-frame animation
- Spritesheet compositing

### 3. Particle Choreography (`particle_choreography_system.py`)

Generates particle motion patterns:
- **Radial Burst**: Explode outward in all directions
- **Spiral**: Swirling spiral path
- **Chaotic**: Random directions with turbulence
- **Orbital**: Circular motion patterns
- Core particles: Slow drift
- Shockwave particles: Ring expansion

### 4. XML Exporter (`transcendence_fx_exporter.py`)

Exports to Transcendence format:
- Image elements with spritesheet references
- EffectType elements for explosions/impacts
- Particle system definitions
- Frame count, ticks per frame, rotation

### 5. AI Prompt Templates (`ai_fx_prompt_templates.md`)

Structured prompts for AI generation:
- Core template for any FX type
- Specific prompts for explosions, impacts, muzzle flashes, trails
- Style variations (high-energy, subtle, chaotic)
- Color palette suggestions
- Motion pattern descriptions
- Timing curve examples

### 6. Pipeline Orchestrator (`NovaDriftFXGenerator.ps1`)

Main PowerShell script:
- Reads FX registry
- Generates particle choreography
- Calls Blender for rendering
- Exports XML files
- Packages assets

## Usage

### Basic Usage

```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -OutputDir "Output"
```

### Generate Specific FX

```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -FXId "nova_burst_01" -OutputDir "Output"
```

### With AI Generation

```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -UseAI -OllamaModel "llama3.2" -OutputDir "Output"
```

### Skip Rendering (XML Only)

```powershell
.\NovaDriftFXGenerator.ps1 -RegistryPath "nova_drift_fx_example.json" -SkipRender -OutputDir "Output"
```

## Registry Example

See `nova_drift_fx_example.json` for complete examples:
- **nova_burst_01**: Standard Nova Drift burst with distortion
- **plasma_explosion**: Large explosion with multiple layers
- **energy_impact**: Quick impact effect

## FX Layers

### Core Glow
- Emission shader with color and intensity
- Pulsing animation
- Expanding scale
- Additive blending

### Shockwave Ring
- Thin torus mesh
- Expanding radius animation
- Fade out over time
- Single or double rings

### Bloom
- Halo effect around core
- Larger radius than core
- Softer glow
- Fades faster

### Distortion Field
- Procedural noise texture
- Radial displacement
- Heat-haze effect
- Optional chromatic aberration

### Particles
- Burst particles: High speed, short life
- Core particles: Slow drift, longer life
- Shockwave particles: Ring expansion

## Motion Patterns

### Radial Burst
- Even 360-degree distribution
- High initial speed
- Decelerates over time
- Best for: explosions, impacts

### Spiral
- Swirling outward path
- Dynamic, interesting motion
- More complex than radial
- Best for: large explosions, special abilities

### Chaotic
- Random directions
- Turbulence added
- Organic, unpredictable
- Best for: complex explosions, exotic effects

## Timing Curves

### Quick Snap
- Fast expansion (0.08s)
- Quick fade (0.2s)
- Sharp cut-off
- Best for: impacts, quick bursts

### Smooth Bloom
- Moderate expansion (0.15s)
- Longer fade (0.4s)
- Smooth curves
- Best for: explosions, dramatic effects

### Dramatic Build
- Slow build (0.2s)
- Delayed shockwave (0.3s)
- Long sustain (0.5s)
- Best for: special abilities, boss attacks

## Transcendence Integration

### XML Format

```xml
<Image UNID="&fxNovaBurst01;">
    <ImageDesc
        bitmap="Resources/FX/nova_burst_01.png"
        bitmask="none"
        frameCount="12"
        ticksPerFrame="1"
        rotationCount="1"
    />
</Image>
```

### EffectType

```xml
<EffectType unid="&efNovaBurst01;">
    <name>Nova Burst</name>
    <image>&fxNovaBurst01;</image>
    <distortion strength="0.04"/>
</EffectType>
```

## AI Generation

### Using Prompt Templates

```python
from ai_fx_prompt_templates import generate_fx_with_ai

prompt = """
Generate a Nova Drift-style plasma explosion effect.
Large explosion, hot orange/red colors, high energy, spiral particles.
"""

fx_profile = generate_fx_with_ai(prompt, model="llama3.2")
```

### Custom Prompts

See `ai_fx_prompt_templates.md` for:
- Complete prompt templates
- Effect type-specific prompts
- Style variation prompts
- Color palette suggestions
- Motion pattern descriptions

## File Structure

```
Tools/
├── nova_drift_fx_registry_schema.json    # JSON schema
├── nova_drift_fx_example.json           # Example registry
├── blender_nova_drift_fx_renderer.py   # Blender renderer
├── particle_choreography_system.py      # Particle motion
├── transcendence_fx_exporter.py        # XML exporter
├── ai_fx_prompt_templates.md          # AI prompts
├── NovaDriftFXGenerator.ps1           # Main orchestrator
└── NOVA_DRIFT_FX_README.md            # This file
```

## Workflow

1. **Author FX Profile**: Create JSON registry entry or use AI
2. **Generate Particles**: Create particle choreography
3. **Render in Blender**: Generate layered spritesheet
4. **Export XML**: Create Transcendence XML files
5. **Package Assets**: Copy to game resources

## Integration with Other Systems

- **Projectile System**: FX can be triggered by projectile impacts
- **Shield System**: FX can be used for shield breaks
- **Weapon System**: FX can be used for muzzle flashes and explosions

## Performance Considerations

- Limit particle counts per FX (24-40 recommended)
- Use sprite strips instead of real-time particles when possible
- Provide LOD: High/Medium/Low quality settings
- Batch FX draws by blend mode

## Testing Checklist

- [ ] FX renders correctly in Blender
- [ ] Spritesheet frames are sequential
- [ ] Particle choreography matches registry
- [ ] XML exports correctly
- [ ] Transcendence can load FX
- [ ] Timing curves feel right
- [ ] Colors match Nova Drift aesthetic
- [ ] Distortion effects visible
- [ ] Performance acceptable

## Future Enhancements

- Real-time preview GUI
- Iterative AI tweak loop
- Advanced shader effects
- 3D particle systems
- Sound effect integration
- Multi-layer compositing

