# StarboundShaderSuite Asset Generation Guide

Generate textures and assets for the StarboundShaderSuite shader system.

## Quick Start

```powershell
# Generate all shader assets
.\GenerateShaderAssets.ps1

# Use C++ backend for better quality
.\GenerateShaderAssets.ps1 -UseCppBackend

# Or generate everything including shader assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Noise Textures (4 textures)

1. **noise** - General purpose noise texture
2. **noise_cloud** - Cloud noise pattern
3. **noise_perlin** - Perlin noise pattern
4. **noise_voronoi** - Voronoi/cellular noise pattern

### Damage Textures (4 textures)

1. **damage_mask** - Damage mask (grayscale, white = damage)
2. **damage_decal** - Damage decal (red/orange burn marks)
3. **damage_crack** - Crack pattern
4. **damage_scorch** - Scorch marks

### Ripple Textures (3 textures)

1. **ripple** - Circular ripple pattern
2. **ripple_wave** - Wave ripple pattern
3. **ripple_distortion** - Distortion ripple pattern

### Emissive Maps (3 maps)

1. **emissive_glow** - General glow map
2. **emissive_pulse** - Pulsing glow pattern
3. **emissive_pattern** - Pattern-based glow

### Normal Maps (2 maps)

1. **normal_default** - Default neutral normal map
2. **normal_detail** - Detail normal map

## Total: ~16 Assets

## Output Structure

```
assets/
└── textures/
    └── shaders/
        ├── noise.png
        ├── noise_cloud.png
        ├── noise_perlin.png
        ├── noise_voronoi.png
        ├── damage_mask.png
        ├── damage_decal.png
        ├── damage_crack.png
        ├── damage_scorch.png
        ├── ripple.png
        ├── ripple_wave.png
        ├── ripple_distortion.png
        ├── emissive_glow.png
        ├── emissive_pulse.png
        ├── emissive_pattern.png
        ├── normal_default.png
        └── normal_detail.png
```

## Integration

### Using Noise Textures

```lua
-- Dissolve shader with noise texture
local dissolvePass = StarboundShaders.createDissolvePass(
    0.5,  -- threshold
    "/textures/shaders/noise.png"  -- noise texture
)
dissolvePass.execute()
```

### Using Damage Textures

```lua
-- Damage overlay shader
local damagePass = StarboundShaders.createDamageOverlayPass(
    "/textures/shaders/damage_mask.png",  -- damage mask
    "/textures/shaders/damage_decal.png", -- damage decal
    0.5  -- intensity
)
damagePass.execute()
```

### Using Ripple Textures

```lua
-- Water ripple shader
local ripplePass = StarboundShaders.createWaterRipplePass(
    0.0,  -- time
    "/textures/shaders/ripple.png"  -- ripple map
)
ripplePass.execute()
```

### Using Emissive Maps

```lua
-- Emissive glow shader
local emissivePass = StarboundShaders.createEmissiveGlowPass(0.0)
emissivePass.setTexture("emissiveMap", emissiveTexture, 0)
emissivePass.execute()
```

### Using Normal Maps

```lua
-- Cell shading shader with normal map
local cellPass = StarboundShaders.createCellShadingPass(
    glm.vec3(0.7, 0.7, 0.0),  -- light direction
    glm.vec3(1.0, 1.0, 1.0)   -- light color
)
cellPass.setTexture("normalTex", normalTexture, 1)
cellPass.setBool("useNormalMap", true)
cellPass.execute()
```

## Shader Usage

### Dissolve Shader

The dissolve shader uses noise textures to create a dissolving effect:

```lua
local dissolvePass = StarboundShaders.createDissolvePass(
    0.5,  -- threshold (0.0 to 1.0)
    "/textures/shaders/noise.png"  -- noise texture path
)
dissolvePass.setFloat("time", currentTime)
dissolvePass.setBool("animated", true)
dissolvePass.execute()
```

### Damage Overlay Shader

The damage overlay shader applies damage effects:

```lua
local damagePass = StarboundShaders.createDamageOverlayPass(
    "/textures/shaders/damage_mask.png",
    "/textures/shaders/damage_decal.png",
    0.5  -- intensity
)
damagePass.setVec3("damageTint", glm.vec3(0.8, 0.2, 0.1))
damagePass.execute()
```

### Water Ripple Shader

The water ripple shader creates water distortion effects:

```lua
local ripplePass = StarboundShaders.createWaterRipplePass(
    currentTime,  -- time
    "/textures/shaders/ripple.png"  -- ripple map
)
ripplePass.setFloat("rippleSpeed", 0.1)
ripplePass.setFloat("rippleStrength", 0.03)
ripplePass.execute()
```

### Emissive Glow Shader

The emissive glow shader creates glowing effects:

```lua
local emissivePass = StarboundShaders.createEmissiveGlowPass(currentTime)
emissivePass.setTexture("emissiveMap", emissiveTexture, 0)
emissivePass.setVec3("glowColor", glm.vec3(1.0, 0.5, 0.0))
emissivePass.setFloat("glowIntensity", 1.0)
emissivePass.execute()
```

### Cell Shading Shader

The cell shading shader creates toon-style shading:

```lua
local cellPass = StarboundShaders.createCellShadingPass(
    glm.vec3(0.7, 0.7, 0.0),  -- light direction
    glm.vec3(1.0, 1.0, 1.0)   -- light color
)
cellPass.setTexture("normalTex", normalTexture, 1)
cellPass.setBool("useNormalMap", true)
cellPass.setInt("shadingLevels", 3)
cellPass.execute()
```

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateShaderAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Load Textures

Load textures into your texture system.

### Step 3: Create Shader Passes

Create shader passes with the appropriate textures.

### Step 4: Execute Shaders

Execute shader passes in your rendering pipeline.

## Advanced Options

### Custom Noise Textures

Add custom noise textures to the `$noiseTextures` array in the script.

### Custom Damage Textures

Add custom damage textures to the `$damageTextures` array.

### Custom Ripple Textures

Add custom ripple textures to the `$rippleTextures` array.

## Tips

1. **Noise textures**: Use seamless textures for tiling
2. **Damage textures**: Grayscale masks work best
3. **Ripple textures**: Ensure textures are seamless
4. **Emissive maps**: White = glow, black = no glow
5. **Normal maps**: Use RGB format, blue tint for neutral

## Troubleshooting

### Shaders Not Compiling

- Check shader source files exist
- Verify texture paths are correct
- Ensure textures are loaded before use

### Textures Not Appearing

- Check texture file paths
- Verify textures are loaded into GPU
- Ensure texture units are set correctly

### Effects Not Working

- Check shader uniforms are set
- Verify texture bindings are correct
- Ensure shader passes are executed

---

*Part of the Starbound Ollama Asset Generator suite*
