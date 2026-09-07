# Space Whale Texture Generation Guide

## Overview

Textures are generated specifically for the **rigging system** and are used when rendering the final 120 facings spritesheet. These textures are UV-mapped and compatible with Blender's bone deformation system.

## Texture Maps Generated

For each module (head, mid_section, belly_bay, tail, dorsal_crest), the following texture maps are created:

### 1. Diffuse (Base Color)
- **File**: `{module_name}_diffuse.png`
- **Purpose**: Base color texture with organic variation
- **Format**: RGB, 512×512
- **Content**: Dark navy base with subtle noise pattern for organic feel

### 2. Emission (Glow/Veins)
- **File**: `{module_name}_emission.png`
- **Purpose**: Bioluminescent vein network and glow patterns
- **Format**: RGB, 512×512
- **Content**: Bright cyan vein network that flows along the module surface

### 3. Normal (Surface Detail)
- **File**: `{module_name}_normal.png`
- **Purpose**: Surface detail and organic wrinkles
- **Format**: RGB (normal map), 512×512
- **Content**: Subtle surface variation for organic skin texture

### 4. Roughness (Smoothness)
- **File**: `{module_name}_roughness.png`
- **Purpose**: Surface smoothness (30% roughness = 70% smooth/glossy)
- **Format**: Grayscale, 512×512
- **Content**: Uniform smooth value for bioluminescent skin

### 5. Metallic (Material Type)
- **File**: `{module_name}_metallic.png`
- **Purpose**: Non-metallic organic material
- **Format**: Grayscale, 512×512
- **Content**: Black (0) = non-metallic organic material

## Texture Structure

```
Output/SpaceWhaleTextures/
├── texture_registry.json (master registry)
├── head/
│   ├── head_diffuse.png
│   ├── head_emission.png
│   ├── head_normal.png
│   ├── head_roughness.png
│   └── head_metallic.png
├── mid_section/
│   ├── mid_section_diffuse.png
│   ├── mid_section_emission.png
│   ├── mid_section_normal.png
│   ├── mid_section_roughness.png
│   └── mid_section_metallic.png
├── belly_bay/
│   └── ... (same structure)
├── tail/
│   └── ... (same structure)
└── dorsal_crest/
    └── ... (same structure)
```

## Usage in Blender

### 1. Load Textures

Use the Blender texture setup script:

```bash
blender --background --python blender_space_whale_texture_setup.py -- \
    --registry Output/SpaceWhaleTextures/texture_registry.json \
    --texture-dir Output/SpaceWhaleTextures
```

### 2. Apply to Materials

Textures are automatically applied to materials with:
- **Diffuse** → Base Color input
- **Emission** → Emission shader (intensity 3.5)
- **Normal** → Normal map input
- **Roughness** → Roughness input
- **Metallic** → Metallic input

### 3. Rigging Compatibility

Textures are designed to work with:
- **Bone deformation** - Textures stretch naturally with mesh
- **Weight painting** - Smooth transitions between bone influences
- **UV mapping** - Automatic UV unwrapping compatible
- **Animation** - Textures animate with breathing/tail sweep

## Integration with Spritesheet Generation

When rendering the 120 facings spritesheet:

1. **Load textures** using `blender_space_whale_texture_setup.py`
2. **Apply to modules** - Each module gets its texture set
3. **Rig with bones** - Use existing rigging system
4. **Render frames** - Textures deform naturally with bone movement
5. **Composite spritesheet** - Final result includes all texture details

## Texture Generation

### Command Line

```bash
python space_whale_texture_generator.py \
    --ship-registry space_whale_ship_example.json \
    --visual-registry space_whale_visual_language_registry.json \
    --skinning-registry space_whale_skinning_registry.json \
    --output Output/SpaceWhaleTextures \
    --texture-size 512 512
```

### From GUI

The comprehensive asset generator includes texture generation automatically.

## Texture Registry

The `texture_registry.json` contains:

```json
{
  "version": "1.0.0",
  "shipId": "leviathan_alpha",
  "textureSize": [512, 512],
  "modules": [
    {
      "module": "head",
      "type": "head",
      "textures": {
        "diffuse": "head/head_diffuse.png",
        "emission": "head/head_emission.png",
        "normal": "head/head_normal.png",
        "roughness": "head/head_roughness.png",
        "metallic": "head/head_metallic.png"
      },
      "uvMapping": {
        "method": "automatic",
        "seams": "minimal"
      }
    }
  ]
}
```

## Quality Standards

- **Resolution**: 512×512 (suitable for game use, can be upscaled)
- **Format**: PNG with proper color spaces
- **UV Mapping**: Automatic, minimal seams for clean deformation
- **Compatibility**: Works with Blender's Principled BSDF shader

## Next Steps

1. **Generate textures** using the texture generator
2. **Load in Blender** with texture setup script
3. **Apply rigging** using existing bone structure
4. **Render 120 facings** with textures applied
5. **Export spritesheet** with all visual details

Textures are now ready for rigging and final spritesheet generation! 🎨

