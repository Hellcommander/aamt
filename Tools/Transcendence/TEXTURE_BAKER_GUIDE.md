# Blender Texture Baker - Guide

Production-ready procedural texture generation system for mod asset pipelines.

## Overview

The texture baker is a modular Blender Python script that:
- Creates procedural materials from predefined types or JSON definitions
- Bakes materials to PNG textures
- Works headless for batch processing
- Integrates with PowerShell automation
- Supports multiple bake passes (Diffuse, Roughness, Normal, etc.)

## Files

- **`bake_texture.py`** - Main Blender Python module
- **`BatchBakeTextures.ps1`** - PowerShell wrapper for batch processing
- **`AssetMakerAI.ps1`** - Integrated texture generation (uses baker when possible)

## Quick Start

### Single Texture

```powershell
# Using predefined material type
blender --background --python bake_texture.py -- --material wood --size 512 --output "wood.png"

# Using JSON definition
blender --background --python bake_texture.py -- --json material.json --size 512 --output "custom.png"
```

### Batch Processing

```powershell
# Batch bake multiple materials
.\BatchBakeTextures.ps1 -MaterialList @("wood", "stone", "metal") -OutputDir "Textures"

# From file
.\BatchBakeTextures.ps1 -MaterialList "materials.txt" -OutputDir "Textures"
```

### Via AssetMakerAI

```powershell
# Automatically uses texture baker when description matches known types
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "wooden texture" -TextureMethod Procedural
```

## Predefined Material Types

- **`wood`** - Procedural wood grain texture
- **`stone`** - Stone/brick texture with Voronoi patterns
- **`metal`** - Rusty metal texture
- **`rusty_metal`** - Alias for metal

## JSON Material Definitions

For AI-generated or custom materials, use JSON:

```json
{
  "name": "CustomMaterial",
  "noise": {
    "scale": 10.0
  },
  "colors": [
    [0.3, 0.2, 0.1],
    [0.5, 0.35, 0.2]
  ],
  "roughness": 0.7,
  "metallic": 0.0
}
```

## Bake Passes

- **`DIFFUSE`** - Base color (default)
- **`ROUGHNESS`** - Surface roughness map
- **`NORMAL`** - Normal map
- **`EMIT`** - Emission map
- **`COMBINED`** - Combined passes

## Parameters

### bake_texture.py

- `--material` - Material type name (wood, stone, metal)
- `--json` - Path to JSON material definition
- `--size` - Texture size in pixels (default: 512)
- `--output` - Output PNG path (required)
- `--pass` - Bake pass type (default: DIFFUSE)
- `--seamless` - Make texture tileable (future feature)
- `--samples` - Cycles render samples (default: 1 for speed)

### BatchBakeTextures.ps1

- `-MaterialList` - Array of material names or file path
- `-OutputDir` - Output directory (default: BakedTextures)
- `-BlenderPath` - Blender executable path (auto-detected)
- `-TextureSize` - Texture size (default: 512)
- `-BakePass` - Bake pass type (default: DIFFUSE)
- `-UseJSON` - Generate JSON definitions using Ollama

## Integration with AssetMakerAI

The `AssetMakerAI.ps1` script automatically uses the texture baker when:
- Description matches known material types (wood, stone, metal)
- `bake_texture.py` is available in the Tools directory

Otherwise, it falls back to Ollama-generated Blender Python code.

## Workflow Examples

### Placeholder Texture Generation

```powershell
# Generate textures for spell icons
$textures = @(
    "wood",
    "stone",
    "metal"
)

.\BatchBakeTextures.ps1 -MaterialList $textures -OutputDir "SpellIcons" -TextureSize 128
```

### Custom Material Pipeline

1. Generate JSON using Ollama:
```powershell
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "mossy stone with green tint" -TextureMethod Procedural
```

2. Or create JSON manually and bake:
```powershell
blender --background --python bake_texture.py -- --json mossy_stone.json --size 512 --output "mossy_stone.png"
```

### Spritesheet Assembly

```powershell
# 1. Batch bake textures
.\BatchBakeTextures.ps1 -MaterialList @("wood", "stone", "metal") -OutputDir "Textures"

# 2. Assemble into spritesheet
.\AssetMakerAI.ps1 -Action AssembleSpritesheet -InputData "Textures" -SpritesheetPath "spritesheet.png" -TileSize 128
```

## Extending Material Types

Add new material builders to `bake_texture.py`:

```python
def build_material_custom(name="CustomMaterial"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Your node setup here
    # ...
    
    return mat

# Register
MATERIAL_BUILDERS["custom"] = build_material_custom
```

## Design Principles

- **Minimal**: Single-purpose script, easy to understand
- **Deterministic**: Same inputs = same outputs
- **Headless-friendly**: Works without GUI
- **Extensible**: Easy to add new material types
- **Pipeline-integrated**: Works with PowerShell automation

## Troubleshooting

### Blender Not Found
- Install Blender or specify path: `-BlenderPath "C:\Path\To\Blender\blender.exe"`

### Bake Fails
- Check Blender version (tested with 5.0+)
- Ensure Cycles render engine is available
- Check output directory permissions

### Texture Not Saved
- Verify output path is writable
- Check Blender console for errors
- Ensure image node is active before baking

## Future Enhancements

- [ ] Seamless/tileable texture generation
- [ ] Multi-pass baking (combine Diffuse + Roughness + Normal)
- [ ] Ollama JSON generation integration
- [ ] Material library with presets
- [ ] UV unwrapping for complex shapes
- [ ] Texture variation system

## References

- [Blender Python API](https://docs.blender.org/api/current/)
- [Blender Baking Documentation](https://docs.blender.org/manual/en/latest/render/cycles/baking.html)

