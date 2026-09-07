# Drawing to Qud Tile Pipeline Guide

## Overview

This guide explains the complete pipeline for converting your **line-based drawings** into **Caves of Qud tiles** with procedural materials, node groups, and full editability.

## Your Drawing Style → Qud Tiles

### Your Style
- **Single color** (black lines on white, or white on black)
- **Line-by-line** construction
- **Interconnected shapes**
- **Clean structure**

### What the Pipeline Does
1. **Imports your drawing** as a mask
2. **Builds procedural material** using your registry palette
3. **Applies your drawing** as shape/detail source
4. **Bakes to Qud tile size** (24×24, 32×32, or 48×48)
5. **Saves editable .blend** with node groups
6. **Outputs standalone PNG** (exactly what Qud expects)

## Quick Start

### Basic Usage

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\spell_icon.png" `
    -OutputPath "QudTiles\spell_icon.png" `
    -TileSize 32
```

### With Registry

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\ship_scout.png" `
    -OutputPath "QudTiles\ship_scout.png" `
    -RegistryPath "asset_registry.json" `
    -AssetId "ship_scout" `
    -ExportNodeGroups
```

### With Custom Palette

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\spell_fireball.png" `
    -OutputPath "QudTiles\spell_fireball.png" `
    -Palette "#ff6b6b,#ff8787,#ffa8a8" `
    -Style "painterly" `
    -Quality "high" `
    -TileSize 32
```

## Pipeline Flow

### 1. Import Drawing
Your line drawing is imported as a mask:
- **White areas** = Apply color/material
- **Black areas** = Background/negative space
- **Gray areas** = Partial application

### 2. Build Procedural Material
Material is built using:
- **Your registry palette** (or custom palette)
- **Style** (painterly, pixel, flat, procedural)
- **Contrast** (low, medium, high)
- **Quality tier** (draft, standard, high, ultra)

### 3. Apply Drawing as Mask
Your drawing drives the material:
- **Mask alpha** → Color ramp factor
- **Line structure** → Detail distribution
- **Shape** → Material boundaries

### 4. Bake to Qud Size
Material is baked to Qud tile size:
- **24×24**: Classic tileset
- **32×32**: Default (most common)
- **48×48**: High-resolution

### 5. Export
Outputs:
- **PNG tile** (standalone, no atlas)
- **.blend file** (with node groups, if enabled)

## Registry Integration

### Registry Entry Example

```json
{
  "id": "spell_fireball",
  "name": "Fireball",
  "type": "spell",
  "visual": {
    "icon": {
      "palette": ["#ff6b6b", "#ff8787", "#ffa8a8"],
      "style": "painterly",
      "contrast": "high"
    }
  },
  "generation": {
    "quality": "high",
    "exportNodeGroups": true
  },
  "export": {
    "qud": {
      "enabled": true,
      "tileSize": 32
    }
  }
}
```

### Using Registry

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\spell_fireball.png" `
    -OutputPath "QudTiles\spell_fireball.png" `
    -RegistryPath "asset_registry.json" `
    -AssetId "spell_fireball"
```

The script will automatically:
- Load palette from registry
- Use style and contrast settings
- Apply quality tier
- Enable node groups if specified

## Drawing Preparation

### Best Practices

1. **High Contrast**
   - Pure black lines on white background
   - Or white lines on black background
   - Clear separation

2. **Clean Lines**
   - Solid, continuous strokes
   - Minimal gaps
   - Clear intersections

3. **Proper Resolution**
   - 512×512 minimum
   - Higher resolution = better results
   - Square aspect ratio recommended

4. **Clear Structure**
   - Outer outline clearly defined
   - Internal lines connect logically
   - Regions are separated

### Scanning Tips

- Good lighting (avoid shadows)
- High resolution (300+ DPI)
- Straight, flat scanning
- Clean background

## Material Styles

### Painterly (Default)
- Soft gradients
- Noise-based detail
- Color ramp blending
- **Best for**: Organic shapes, spell icons

### Pixel
- Sharper edges
- Less smoothing
- Chunky patterns
- **Best for**: Retro-style tiles, classic Qud aesthetic

### Flat
- Simple, solid colors
- Minimal variation
- Clean shapes
- **Best for**: Simple icons, UI elements

### Procedural
- Complex node setups
- Multi-layer detail
- Advanced patterns
- **Best for**: Complex assets, high-quality mods

## Quality Tiers

### Draft
- Fast processing
- Minimal detail
- 1-2 material layers
- **Use for**: Quick previews, iteration

### Standard
- Balanced detail
- 2-3 material layers
- Good quality
- **Use for**: Production assets, most tiles

### High
- Enhanced detail
- 3-5 material layers
- Rim lighting
- **Use for**: Hero assets, important tiles

### Ultra
- Maximum detail
- 5-8 material layers
- Micro-detail
- **Use for**: Showcase assets, final exports

## Node Groups (Editable Materials)

### Enable Node Groups

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\spell_icon.png" `
    -OutputPath "QudTiles\spell_icon.png" `
    -ExportNodeGroups `
    -BlendOutput "Materials\spell_icon.blend"
```

This creates:
- **Editable node groups** in the .blend file
- **Tweakable parameters** (scale, detail, colors)
- **Reusable components** (palette ramp, noise layers)
- **Full control** over every aspect

### Editing in Blender

1. Open the `.blend` file
2. Go to **Shading** workspace
3. Select the material
4. **Double-click** node groups to edit
5. **Tweak parameters** as needed
6. **Re-bake** or export

## Usage Examples

### Example 1: Simple Icon

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\icon_potion.png" `
    -OutputPath "QudTiles\icon_potion.png" `
    -Palette "#4a90e2,#7bb3f0" `
    -TileSize 32
```

### Example 2: Ship Tile

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\ship_scout.png" `
    -OutputPath "QudTiles\ship_scout.png" `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -Quality "high" `
    -ExportNodeGroups
```

### Example 3: Spell Effect

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\spell_fireball.png" `
    -OutputPath "QudTiles\spell_fireball.png" `
    -Palette "#ff6b6b,#ff8787,#ffa8a8" `
    -Style "painterly" `
    -Quality "ultra" `
    -TileSize 32
```

### Example 4: Classic Size

```powershell
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\item_sword.png" `
    -OutputPath "QudTiles\item_sword.png" `
    -TileSize 24 `
    -Style "pixel"
```

## Direct Blender Usage

You can also use the Blender script directly:

```bash
blender --background --python qud_tile_baker.py -- \
    --drawing "drawings/spell_icon.png" \
    --size 32 \
    --palette "#4caf50,#81c784,#2e7d32" \
    --output "QudTiles/spell_icon.png" \
    --exportNodeGroups \
    --blendOutput "Materials/spell_icon.blend"
```

## Batch Processing

### Process Multiple Drawings

```powershell
$drawings = @(
    @{Drawing="drawings\spell1.png"; Output="QudTiles\spell1.png"; Palette="#ff6b6b,#ff8787"},
    @{Drawing="drawings\spell2.png"; Output="QudTiles\spell2.png"; Palette="#4a90e2,#7bb3f0"},
    @{Drawing="drawings\spell3.png"; Output="QudTiles\spell3.png"; Palette="#4caf50,#81c784"}
)

foreach ($drawing in $drawings) {
    .\BakeQudTile.ps1 `
        -DrawingPath $drawing.Drawing `
        -OutputPath $drawing.Output `
        -Palette $drawing.Palette `
        -TileSize 32 `
        -ExportNodeGroups
}
```

### Process All Registry Entries

```powershell
$registry = Get-Content "registry.json" | ConvertFrom-Json

foreach ($entry in $registry.entries) {
    if ($entry.generation -and $entry.generation.sketchSource) {
        $drawingPath = $entry.generation.sketchSource
        $outputPath = "QudTiles\$($entry.id).png"
        
        if (Test-Path $drawingPath) {
            .\BakeQudTile.ps1 `
                -DrawingPath $drawingPath `
                -OutputPath $outputPath `
                -RegistryPath "registry.json" `
                -AssetId $entry.id `
                -ExportNodeGroups
        }
    }
}
```

## Integration with Other Tools

### Complete Workflow

```powershell
# 1. Process line drawing
.\BakeQudTile.ps1 `
    -DrawingPath "drawings\ship_scout.png" `
    -OutputPath "QudTiles\ship_scout.png" `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -ExportNodeGroups

# 2. (Optional) Edit in Blender
# Open Materials/ship_scout.blend
# Tweak node groups
# Re-bake if needed

# 3. Generate mod metadata
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -OutputDir "QudMod\assets\textures\tiles"
```

## Troubleshooting

### Drawing Not Imported

- Check file path is correct
- Verify file format (PNG, JPG supported)
- Ensure file is readable
- Check Blender console for errors

### Material Not Applied

- Verify palette is valid (hex colors)
- Check registry entry has visual block
- Ensure material generator is available
- Check Blender console for errors

### Tile Not Baked

- Verify output directory is writable
- Check Blender has write permissions
- Ensure material was created successfully
- Check Blender console for errors

### Node Groups Not Saved

- Verify `--ExportNodeGroups` flag is set
- Check `--BlendOutput` path is valid
- Ensure Blender can write to output location
- Check Blender console for errors

## Best Practices

### Drawing Tips

1. **Start with outline**: Draw outer shape first
2. **Add internal lines**: Connect logically
3. **Create regions**: Use lines to define areas
4. **Maintain contrast**: Keep lines clear
5. **Think in layers**: Outer → Inner → Details

### Processing Tips

1. **Test with draft**: Start with draft quality
2. **Try different styles**: See what works best
3. **Adjust palette**: Fine-tune colors
4. **Use node groups**: Keep materials editable
5. **Iterate**: Refine based on results

### Workflow Tips

1. **Batch process**: Process multiple drawings
2. **Save variations**: Keep different versions
3. **Document**: Note what works
4. **Reuse**: Create templates
5. **Integrate**: Use with your registry

## Next Steps

- Create drawing library for your mod
- Build drawing templates
- Set up batch processing
- Create Qud mod structure
- Integrate with mod build system

