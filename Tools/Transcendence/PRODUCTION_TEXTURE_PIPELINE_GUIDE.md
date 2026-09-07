# Production Texture Generation Pipeline

## Overview

This pipeline generates production-quality textures from your unified asset registry. It reads visual blocks, generates procedural materials with quality-appropriate detail, and bakes multiple texture maps (Base Color, Normal, Roughness, Emission) for use in models, spritesheets, and cross-game exports.

## Features

- **Quality Tiers**: Draft → Standard → High → Ultra
- **Multiple Texture Maps**: Base Color, Normal, Roughness, Emission, Metallic
- **Registry Integration**: Reads directly from your asset registry JSON
- **Shape-Aware Materials**: Automatically adjusts based on shape descriptions
- **Style Support**: Painterly, Pixel, Flat, Procedural

## Registry Schema Updates

### Quality Field

Add a `quality` field to the `generation` block:

```json
{
  "generation": {
    "quality": "high",
    "materialModel": "painterly",
    "proceduralHints": "leaf veins, soft gradients"
  }
}
```

**Quality Levels:**
- `draft`: Fast, minimal noise layers, low resolution (for quick previews)
- `standard`: Default settings, 1-2 noise layers, simple color ramp
- `high`: Multiple layers, detail noise, rim lighting, enhanced contrast
- `ultra`: Maximum detail, micro-detail layers, multi-pass baking, normal map generation

### Textures Field

Specify which texture maps to generate:

```json
{
  "textures": {
    "baseColor": true,
    "normal": true,
    "roughness": false,
    "emission": true,
    "metallic": false
  }
}
```

**Available Maps:**
- `baseColor`: Base color/diffuse texture (always recommended)
- `normal`: Normal map for 3D models
- `roughness`: Roughness map for PBR materials
- `emission`: Emission map for glow/FX effects
- `metallic`: Metallic map for PBR materials

## Usage

### PowerShell Script

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -Quality "high" `
    -TextureSize 512 `
    -Samples 1
```

### Parameters

- `-RegistryPath`: Path to your asset registry JSON file (required)
- `-AssetId`: Asset ID from the registry (required)
- `-Quality`: Quality level: `draft`, `standard`, `high`, `ultra` (default: `standard`)
- `-OutputDir`: Output directory for generated textures (default: `GeneratedTextures\{AssetId}`)
- `-BlenderPath`: Path to Blender executable (auto-detected if not provided)
- `-TextureSize`: Size of generated textures in pixels (default: 512)
- `-Samples`: Cycles render samples (default: 1 for fast, higher for quality)

### Direct Blender Usage

You can also call the Blender script directly:

```bash
blender --background --python bake_texture.py -- \
    --registry "asset_registry.json" \
    --assetId "nature_verdant_pulse" \
    --quality "high" \
    --size 512 \
    --outputDir "output" \
    --pass ALL \
    --samples 1
```

## Quality Tiers Explained

### Draft
- **Use Case**: Quick previews, iteration, testing
- **Settings**: Reduced noise scales (50%), minimal detail
- **Bake Time**: ~5-10 seconds per map
- **File Size**: Smallest

### Standard
- **Use Case**: Production assets, most use cases
- **Settings**: Default procedural settings, balanced detail
- **Bake Time**: ~10-20 seconds per map
- **File Size**: Medium

### High
- **Use Case**: High-quality assets, hero items, promotional materials
- **Settings**: Additional detail noise layer, enhanced rim lighting
- **Bake Time**: ~20-40 seconds per map
- **File Size**: Larger

### Ultra
- **Use Case**: Maximum quality, final exports, showcase assets
- **Settings**: Micro-detail layers, maximum noise detail, overlay blending
- **Bake Time**: ~40-80 seconds per map
- **File Size**: Largest

## Texture Maps

### Base Color
The main color texture. Always generated unless explicitly disabled.

**Output**: `baseColor.png`

### Normal Map
Surface detail for 3D models. Adds depth and detail without geometry.

**Output**: `normal.png`

**When to Use**: For 3D models that need surface detail, PBR workflows

### Roughness Map
Controls surface shininess. Darker = rougher, lighter = shinier.

**Output**: `roughness.png`

**When to Use**: PBR materials, realistic lighting

### Emission Map
Glow and self-illumination. Perfect for FX, magic effects, energy.

**Output**: `emission.png`

**When to Use**: Spell effects, glowing items, magical artifacts, FX

### Metallic Map
Controls metallic appearance. White = metallic, black = non-metallic.

**Output**: `metallic.png`

**When to Use**: Metal items, armor, weapons

## Integration with Other Tools

### For Models
Generate textures and apply to your 3D models:

```powershell
# Generate textures
.\GenerateAssetTextures.ps1 -RegistryPath "registry.json" -AssetId "my_asset" -Quality "high"

# Use in Blender model
# Import textures: baseColor.png, normal.png, roughness.png
```

### For Spritesheets
Generate textures and assemble into spritesheets:

```powershell
# Generate textures
.\GenerateAssetTextures.ps1 -RegistryPath "registry.json" -AssetId "spell_icon" -Quality "standard" -TextureSize 64

# Assemble into spritesheet
.\CrossGameSpritesheet.ps1 -InputDir "GeneratedTextures\spell_icon" -OutputDir "Spritesheets" -GameFormat "Both"
```

### For Elin Assets
Generate textures and convert to Elin format:

```powershell
# Generate textures
.\GenerateAssetTextures.ps1 -RegistryPath "registry.json" -AssetId "nature_verdant_pulse" -Quality "high"

# Generate Elin assets
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature spell" -SpellName "Verdant Pulse" -OutputDir "ElinAssets" -GenerateAll
```

## Example Registry Entry

```json
{
  "id": "nature_verdant_pulse",
  "name": "Verdant Pulse",
  "type": "spell",
  "school": "Nature Magic",
  "visual": {
    "icon": {
      "shape": "spiral leaf burst",
      "palette": ["#4caf50", "#81c784", "#2e7d32"],
      "style": "painterly",
      "size": 32,
      "contrast": "high",
      "glow": true
    },
    "fx": {
      "frames": 4,
      "motion": "expanding pulse",
      "glow": true,
      "size": 64
    }
  },
  "generation": {
    "quality": "high",
    "proceduralHints": "organic, flowing, nature-themed"
  },
  "textures": {
    "baseColor": true,
    "normal": false,
    "roughness": false,
    "emission": true
  },
  "export": {
    "elin": true,
    "terraria": true,
    "starbound": true
  }
}
```

## Troubleshooting

### Blender Not Found
- Install Blender or specify `-BlenderPath`
- Check environment variables: `BLENDER_PATH`, `BLENDER_DIR`, `BLENDER_HOME`

### Texture Generation Fails
- Check Blender version (5.0+ recommended)
- Verify registry JSON is valid
- Check output directory permissions
- Review Blender console output for errors

### Quality Issues
- Increase `-Samples` for better quality (slower)
- Use `-Quality "high"` or `"ultra"` for more detail
- Increase `-TextureSize` for higher resolution

### Missing Texture Maps
- Verify `textures` block in registry entry
- Check that requested maps are supported
- Ensure material supports the requested map type

## Performance Tips

1. **Use Draft for Iteration**: Test quickly with `-Quality "draft"`
2. **Batch Processing**: Process multiple assets in a loop
3. **Sample Count**: Use `-Samples 1` for speed, `-Samples 64+` for quality
4. **Texture Size**: Use appropriate size (64-512 for icons, 1024+ for models)
5. **Selective Baking**: Only bake maps you need (disable unused maps in registry)

## Next Steps

- Integrate with your model pipeline
- Set up batch processing for multiple assets
- Create custom material presets
- Extend with additional texture maps as needed

