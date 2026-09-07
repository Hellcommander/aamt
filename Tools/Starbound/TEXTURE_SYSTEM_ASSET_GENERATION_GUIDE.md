# MeshTextureGenerator Asset Generation Guide

Generate palette files and material templates for the MeshTextureGenerator system.

## Quick Start

```powershell
# Generate all texture system assets
.\GenerateTextureSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateTextureSystemAssets.ps1 -UseCppBackend

# Or generate everything including texture system assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Color Palette Files (3 palettes)

1. **starbound_default.json** - Default 32-color Starbound palette
2. **starbound_warm.json** - Warm 24-color palette (browns, oranges, yellows)
3. **starbound_cool.json** - Cool 24-color palette (blues, purples, teals)

### Material Texture Templates (6 templates)

1. **material_metal** - Metal material texture
2. **material_wood** - Wood material texture
3. **material_stone** - Stone material texture
4. **material_fabric** - Fabric material texture
5. **material_glass** - Glass material texture
6. **material_emissive** - Emissive material texture

### Example Baked Texture References (3 examples)

1. **baked_example_8dir** - 8-direction baked atlas example
2. **baked_example_4dir** - 4-direction baked atlas example
3. **baked_example_1dir** - Single-direction baked atlas example

## Total: ~12 Assets

## Output Structure

```
assets/
├── textures/
│   ├── palettes/
│   │   ├── starbound_default.json
│   │   ├── starbound_warm.json
│   │   └── starbound_cool.json
│   ├── materials/
│   │   ├── material_metal.png
│   │   ├── material_wood.png
│   │   ├── material_stone.png
│   │   ├── material_fabric.png
│   │   ├── material_glass.png
│   │   └── material_emissive.png
│   └── baked_examples/
│       ├── baked_example_8dir.png
│       ├── baked_example_4dir.png
│       └── baked_example_1dir.png
```

## Integration

### Loading Palettes

```lua
-- Load palette from JSON file
MeshTexture.loadPalette("starbound_default", "/textures/palettes/starbound_default.json")

-- Or load from JSON string
local paletteJson = [[{"name":"custom","colors":[...]}]]
MeshTexture.loadPaletteFromJSON("custom", paletteJson)
```

### Using Palettes in Baking

```lua
local settings = TextureUtils.createBakeSettings({
    resolution = 64,
    directions = 8,
    paletteName = "starbound_default",
    useDithering = true,
    useAmbientOcclusion = true
})

local result = MeshTexture.bakeOffline("/meshes/example.obj", settings)
if result.success then
    MeshTexture.exportAtlasAsPNG(result.atlas, "/textures/baked/example.png")
end
```

### Material Templates

Material templates can be used as reference textures when baking meshes:

```lua
-- Use material template as reference
local materialPath = "/textures/materials/material_metal.png"
-- ... apply to mesh before baking ...
```

## Palette Formats

### JSON Palette Format

```json
{
  "name": "palette_name",
  "colorCount": 32,
  "isIndexed": false,
  "colors": [
    {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0},
    {"r": 0.2, "g": 0.2, "b": 0.2, "a": 1.0},
    ...
  ]
}
```

### Indexed Palette Format

For indexed palettes, include an `indices` array:

```json
{
  "name": "indexed_palette",
  "colorCount": 256,
  "isIndexed": true,
  "colors": [...],
  "indices": [0, 1, 2, ...]
}
```

## Bake Settings

### Resolution

- **64x64**: Fast, low quality
- **128x128**: Balanced
- **256x256**: High quality, slower

### Directions

- **1**: Single direction (front view)
- **4**: Four directions (N, E, S, W)
- **8**: Eight directions (N, NE, E, SE, S, SW, W, NW)

### Baking Options

- **useDithering**: Apply dithering for smoother color transitions
- **useAmbientOcclusion**: Include AO in baked texture
- **useEmissive**: Include emissive maps
- **useNormalMaps**: Include normal maps

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateTextureSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Load Palettes

Load palettes into the MeshTextureGenerator system.

### Step 3: Configure Bake Settings

Create bake settings with desired resolution, directions, and options.

### Step 4: Bake Meshes

Bake meshes using the loaded palettes and settings.

### Step 5: Export Results

Export baked atlases as PNG or JSON files.

## Advanced Options

### Custom Palettes

Create custom palette JSON files:

```json
{
  "name": "custom_palette",
  "colorCount": 16,
  "isIndexed": false,
  "colors": [
    {"r": 1.0, "g": 0.0, "b": 0.0, "a": 1.0},
    ...
  ]
}
```

### Custom Material Templates

Add custom material templates to the `$materialTemplates` array in the script.

### Custom Bake Examples

Add custom baked texture examples to the `$bakedExamples` array.

## Tips

1. **Palette size**: Use 16-32 colors for best performance
2. **Resolution**: Start with 64x64, increase if needed
3. **Directions**: Use 8 directions for smooth rotation
4. **Dithering**: Enable for smoother color transitions
5. **AO**: Enable ambient occlusion for better depth

## Troubleshooting

### Palettes Not Loading

- Check JSON file format is correct
- Verify file paths are correct
- Ensure colors are in RGBA format (0.0-1.0)

### Baking Fails

- Check mesh file exists and is valid
- Verify bake settings are valid
- Ensure palette is loaded

### Exported Textures Look Wrong

- Check palette matches mesh colors
- Verify resolution is appropriate
- Try enabling/disabling dithering

---

*Part of the Starbound Ollama Asset Generator suite*
