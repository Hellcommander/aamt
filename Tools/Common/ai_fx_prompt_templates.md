# AI Prompt Templates for Nova Drift Style FX Generation

## Core Prompt Template

```
Generate a Nova Drift-style special effects profile in JSON format.

The effect should be:
- High-energy and neon-bright
- Additive blending with smooth glows
- Procedural distortion fields
- Particle-driven motion
- Layered composition: core → bloom → shockwave → debris
- Tight timing curves with smooth easing

Output a JSON object matching the Nova Drift FX registry schema with the following structure:
{
  "id": "unique_fx_id",
  "type": "fx|explosion|impact|muzzle|trail",
  "style": "novaDrift",
  "visual": {
    "coreColor": "#hex_color",
    "rimColor": "#hex_color",
    "shockwaveColor": "#hex_color",
    "distortionStrength": 0.0-1.0,
    "noiseType": "perlin|voronoi|simplex|cellular",
    "spriteSize": 64,
    "frames": 12
  },
  "particles": {
    "burstCount": 24,
    "burstSpeedMin": 0.8,
    "burstSpeedMax": 2.4,
    "motionPattern": "radialBurst|spiral|chaotic|orbital"
  },
  "timing": {
    "coreExpandTime": 0.12,
    "shockwaveExpandTime": 0.18,
    "fadeOutTime": 0.3
  }
}

Do not generate final art; generate the procedural description only.
Return only valid JSON, no additional text.
```

## Specific Effect Type Prompts

### Explosion Effect

```
Generate a Nova Drift-style explosion effect profile.

Requirements:
- Large, dramatic burst (spriteSize: 128, frames: 16)
- Bright core glow with intense bloom
- Double shockwave rings expanding outward
- High particle count (40-60 burst particles)
- Spiral or chaotic motion pattern
- Turbulent distortion field
- Chromatic aberration enabled
- Total duration: 0.4-0.6 seconds

Color palette: Hot (orange/red) or cool (cyan/blue) based on damage type.
```

### Impact Effect

```
Generate a Nova Drift-style impact effect profile.

Requirements:
- Small, quick burst (spriteSize: 48, frames: 8)
- Sharp core glow
- Single thin shockwave ring
- Moderate particle count (16-24 burst particles)
- Radial burst motion pattern
- Subtle radial distortion
- Fast timing (total duration: 0.2-0.3 seconds)

Color palette: Match projectile color (energy = cyan, plasma = orange, etc.)
```

### Muzzle Flash Effect

```
Generate a Nova Drift-style muzzle flash effect profile.

Requirements:
- Very small, brief flash (spriteSize: 32, frames: 4-6)
- Intense core glow
- No shockwave (or very subtle)
- Low particle count (8-12 particles)
- Radial burst motion
- Minimal distortion
- Very fast timing (total duration: 0.1-0.15 seconds)

Color palette: Match weapon type (laser = blue/white, plasma = orange, etc.)
```

### Trail Effect

```
Generate a Nova Drift-style trail effect profile.

Requirements:
- Elongated sprite (spriteSize: 64x256 or similar)
- Soft core glow with fade
- No shockwave
- Continuous particle stream
- Linear or orbital motion pattern
- Subtle heat haze distortion
- Long duration (1.0+ seconds, looping)

Color palette: Match projectile/ship color
```

## Style Variation Prompts

### High-Energy Burst

```
Generate a Nova Drift-style high-energy burst with:
- Maximum intensity core glow (intensity: 4.0+)
- Strong distortion field (distortionStrength: 0.06+)
- High particle count (40+)
- Fast expansion (coreExpandTime: 0.08-0.12)
- Bright, saturated colors (#ff00ff, #00ffff, etc.)
```

### Subtle Glow

```
Generate a Nova Drift-style subtle glow effect with:
- Moderate intensity core glow (intensity: 2.0-2.5)
- Light distortion (distortionStrength: 0.02-0.03)
- Lower particle count (12-16)
- Slower expansion (coreExpandTime: 0.15-0.2)
- Softer, pastel colors
```

### Chaotic Explosion

```
Generate a Nova Drift-style chaotic explosion with:
- Turbulent distortion (distortionType: "turbulent", distortionStrength: 0.08+)
- Chaotic particle motion (motionPattern: "chaotic")
- High particle count (50+)
- Voronoi or cellular noise
- Multiple shockwave rings (ringCount: 2-3)
- Longer duration (0.5-0.7 seconds)
```

## Color Palette Prompts

### Neon Pink/Purple

```
Use color palette:
- coreColor: "#ff66ff" (bright magenta)
- rimColor: "#ffffff" (white)
- shockwaveColor: "#ff99ff" (light magenta)
- bloomColor: "#ffccff" (pale pink)
```

### Electric Blue/Cyan

```
Use color palette:
- coreColor: "#00ffff" (cyan)
- rimColor: "#ffffff" (white)
- shockwaveColor: "#88ffff" (light cyan)
- bloomColor: "#aaffff" (pale cyan)
```

### Plasma Orange/Red

```
Use color palette:
- coreColor: "#ff6600" (orange)
- rimColor: "#ffaa00" (gold)
- shockwaveColor: "#ffcc00" (yellow)
- bloomColor: "#ff8800" (dark orange)
```

### Energy Green

```
Use color palette:
- coreColor: "#00ff00" (green)
- rimColor: "#88ff88" (light green)
- shockwaveColor: "#aaffaa" (pale green)
- bloomColor: "#ccffcc" (very pale green)
```

## Motion Pattern Prompts

### Radial Burst

```
Use motionPattern: "radialBurst"
- Particles explode outward in all directions
- Even distribution around 360 degrees
- High initial speed, decelerates
- Best for: explosions, impacts, bursts
```

### Spiral

```
Use motionPattern: "spiral"
- Particles follow spiral path outward
- Creates swirling, dynamic motion
- More interesting than pure radial
- Best for: large explosions, special abilities
```

### Chaotic

```
Use motionPattern: "chaotic"
- Random directions with turbulence
- Creates organic, unpredictable motion
- High visual interest
- Best for: complex explosions, exotic effects
```

## Timing Curve Prompts

### Quick Snap

```
Use timing:
- coreExpandTime: 0.08 (very fast)
- shockwaveExpandTime: 0.12 (fast)
- fadeOutTime: 0.2 (quick fade)
- easeIn: "easeOut" (snap in)
- easeOut: "linear" (sharp cut)
```

### Smooth Bloom

```
Use timing:
- coreExpandTime: 0.15 (moderate)
- shockwaveExpandTime: 0.25 (slower)
- fadeOutTime: 0.4 (long fade)
- easeIn: "easeOut" (smooth start)
- easeOut: "easeIn" (smooth end)
```

### Dramatic Build

```
Use timing:
- coreExpandTime: 0.2 (slow build)
- shockwaveExpandTime: 0.3 (delayed)
- fadeOutTime: 0.5 (long sustain)
- easeIn: "easeInOut" (smooth curve)
- easeOut: "easeIn" (gradual fade)
```

## Example Complete Prompt

```
Generate a Nova Drift-style plasma explosion effect.

The effect should be:
- Large explosion (spriteSize: 128, frames: 16)
- Hot orange/red color palette (coreColor: "#ff6600", rimColor: "#ffaa00", shockwaveColor: "#ffcc00")
- High energy with intense core glow (intensity: 4.0)
- Double shockwave rings (ringCount: 2)
- Turbulent distortion field (distortionType: "turbulent", distortionStrength: 0.06)
- Voronoi noise (noiseType: "voronoi", noiseSpeed: 1.5)
- Spiral particle motion (motionPattern: "spiral", burstCount: 40)
- Chromatic aberration enabled
- Smooth timing (coreExpandTime: 0.15, shockwaveExpandTime: 0.25, fadeOutTime: 0.4)

Output JSON matching the Nova Drift FX registry schema.
Return only valid JSON, no additional text.
```

## Integration with Ollama

```python
def generate_fx_with_ai(prompt_template, model="llama3.2"):
    """Generate FX profile using AI"""
    import subprocess
    
    full_prompt = f"""
    {prompt_template}
    
    Output JSON matching this schema:
    {json.dumps(schema_example, indent=2)}
    """
    
    result = subprocess.run(
        ["ollama", "run", model, full_prompt],
        capture_output=True,
        text=True
    )
    
    # Parse JSON from response
    # ... extract and validate JSON ...
    
    return fx_profile
```

