# Caves of Qud Tile Export Guide

## Drawing-to-Tile Pipeline

This guide covers the complete pipeline for converting your **line-based drawings** into **Caves of Qud tiles** with procedural materials and full editability.

## Overview

This guide explains how to export assets from your unified registry as **Caves of Qud tiles**. Qud's format is simple and flexible: individual PNG files (32×32, 24×24, or 48×48) with optional animation frames and mod metadata.

## Why Qud Tiles Are Perfect for Your Pipeline

- **Simple format**: No atlas required, just individual PNG files
- **Flexible sizing**: 24×24, 32×32, or 48×48
- **Animation support**: Frame-by-frame or horizontal strips
- **No complex metadata**: Just filename-based references
- **Works with your drawings**: Your line-by-line style fits Qud's aesthetic
- **Editable materials**: Node groups preserved for tweaking

## Quick Start

### Basic Drawing-to-Tile Bake

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
    -Quality "high"
```

### Full Registry Export

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -OutputDir "QudTiles"
```

### With Animation

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "spell_fireball" `
    -OutputDir "QudTiles" `
    -Animated `
    -FrameCount 8 `
    -TileSize 32
```

### With Registry Entry

Add to your registry:

```json
{
  "id": "nature_verdant_pulse",
  "export": {
    "qud": {
      "enabled": true,
      "tileSize": 32,
      "animated": false,
      "metadataFormat": "xml"
    }
  }
}
```

Then run:

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse"
```

## Qud Tile Sizes

### 24×24 (Classic)
- Original Qud tileset size
- Retro aesthetic
- Smaller file size
- **Use for**: Classic-style mods, low-res assets

### 32×32 (Default)
- Modern Qud tileset size
- Good balance of detail and performance
- Most common size
- **Use for**: Standard mods, most assets

### 48×48 (High-Res)
- High-resolution tiles
- Maximum detail
- Larger file size
- **Use for**: High-quality mods, showcase assets

## Animation Support

### Frame-by-Frame
Each frame is a separate PNG file:
```
tile_frame00.png
tile_frame01.png
tile_frame02.png
tile_frame03.png
```

### Horizontal Strip (Optional)
All frames in a single horizontal strip:
```
tile_strip.png
```

## Mod Metadata

### XML Format

```xml
<Tile Name="nature_verdant_pulse" Path="assets/textures/tiles/nature_verdant_pulse.png" />
```

For animated tiles:

```xml
<Tile Name="spell_fireball" Animated="true" Frames="8">
    <Frame Index="0" Path="assets/textures/tiles/spell_fireball_frame00.png" />
    <Frame Index="1" Path="assets/textures/tiles/spell_fireball_frame01.png" />
    <!-- ... more frames ... -->
</Tile>
```

### JSON Format

```json
{
  "tile": {
    "name": "nature_verdant_pulse",
    "path": "assets/textures/tiles/nature_verdant_pulse.png"
  }
}
```

For animated tiles:

```json
{
  "tile": {
    "name": "spell_fireball",
    "animated": true,
    "frames": [
      {"index": 0, "path": "assets/textures/tiles/spell_fireball_frame00.png"},
      {"index": 1, "path": "assets/textures/tiles/spell_fireball_frame01.png"}
    ]
  }
}
```

## Registry Integration

### Qud Export Configuration

Add to your registry `export.qud` block:

```json
{
  "export": {
    "qud": {
      "enabled": true,
      "tileSize": 32,
      "animated": false,
      "frameCount": 4,
      "useHorizontalStrip": false,
      "metadataFormat": "xml"
    }
  }
}
```

### Parameters

- **enabled**: Enable Qud tile export (default: false)
- **tileSize**: Tile size in pixels (24, 32, or 48)
- **animated**: Generate animation frames (default: false)
- **frameCount**: Number of frames if animated (1-16)
- **useHorizontalStrip**: Use horizontal strip instead of individual frames
- **metadataFormat**: Mod metadata format ("xml" or "json")

## Pipeline Flow

### 1. Generate Material
Your existing pipeline generates the material:
- From registry visual block
- With procedural materials
- Quality-tiered detail
- Node groups (if enabled)

### 2. Bake to Qud Size
Material is baked to Qud tile size:
- 24×24, 32×32, or 48×48
- High-quality rendering
- Transparency preserved

### 3. Generate Animation (Optional)
If animated:
- Generate multiple frames
- Frame-by-frame or strip
- Consistent styling

### 4. Create Metadata
Generate mod metadata:
- XML or JSON format
- Tile references
- Animation info (if applicable)

## Usage Examples

### Example 1: Static Tile

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "icon_spell" `
    -OutputDir "QudTiles" `
    -TileSize 32
```

**Output:**
- `icon_spell.png` (32×32)
- `icon_spell.xml` (metadata)

### Example 2: Animated Tile

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -OutputDir "QudTiles" `
    -Animated `
    -FrameCount 8 `
    -TileSize 32
```

**Output:**
- `spell_fireball_frame00.png` through `frame07.png`
- `spell_fireball.xml` (with animation metadata)

### Example 3: Classic Size

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "item_potion" `
    -OutputDir "QudTiles" `
    -TileSize 24
```

**Output:**
- `item_potion.png` (24×24)
- `item_potion.xml` (metadata)

### Example 4: High-Res Tile

```powershell
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "creature_dragon" `
    -OutputDir "QudTiles" `
    -TileSize 48
```

**Output:**
- `creature_dragon.png` (48×48)
- `creature_dragon.xml` (metadata)

## Integration with Drawing Pipeline

### Line Drawing → Qud Tile

```powershell
# 1. Process line drawing
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -SketchPath "drawings\scout_lineart.png" `
    -ProcessAsLineDrawing `
    -MappingStrategy "hierarchical"

# 2. Export as Qud tile
.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -OutputDir "QudTiles" `
    -TileSize 32
```

## Direct Blender Usage

You can also use the Blender script directly:

```bash
blender --background --python qud_tile_exporter.py -- \
    --material "MyMaterial" \
    --tileName "my_tile" \
    --outputDir "output" \
    --size 32 \
    --animated \
    --frameCount 4
```

## File Structure

### Output Directory Structure

```
QudTiles/
├── nature_verdant_pulse/
│   ├── nature_verdant_pulse.png
│   └── nature_verdant_pulse.xml
├── spell_fireball/
│   ├── spell_fireball_frame00.png
│   ├── spell_fireball_frame01.png
│   ├── spell_fireball_frame02.png
│   ├── spell_fireball_frame03.png
│   └── spell_fireball.xml
└── ...
```

## Best Practices

### Tile Size Selection

- **24×24**: Use for classic-style mods, simple icons
- **32×32**: Use for most assets, standard mods
- **48×48**: Use for high-quality mods, detailed creatures

### Animation Guidelines

- **4 frames**: Simple animations (pulse, glow)
- **8 frames**: Standard animations (rotation, movement)
- **16 frames**: Complex animations (detailed motion)

### Naming Conventions

- Use lowercase with underscores
- Be descriptive but concise
- Match registry asset IDs
- Avoid special characters

### Metadata Format

- **XML**: More common, easier to read
- **JSON**: More flexible, better for automation

## Troubleshooting

### Tile Not Generated

- Check material exists in Blender
- Verify output directory is writable
- Check Blender console for errors
- Ensure registry entry is valid

### Wrong Size

- Verify `tileSize` parameter
- Check registry `export.qud.tileSize`
- Ensure size is 24, 32, or 48

### Animation Not Working

- Verify `--Animated` flag is set
- Check `frameCount` is > 1
- Ensure material supports animation
- Check Blender console for errors

### Metadata Not Generated

- Verify `--noMetadata` is not set
- Check output directory permissions
- Ensure metadata format is valid

## Advanced Usage

### Batch Export

```powershell
$assets = @("spell_fireball", "spell_ice", "spell_lightning")

foreach ($asset in $assets) {
    .\ExportQudTiles.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $asset `
        -OutputDir "QudTiles" `
        -TileSize 32
}
```

### Custom Tile Sizes

While Qud supports 24, 32, and 48, you can use any size:

```bash
blender --background --python qud_tile_exporter.py -- \
    --material "MyMaterial" \
    --tileName "custom_tile" \
    --outputDir "output" \
    --size 64
```

### Integration with Mod Build

```powershell
# Export all Qud-enabled assets
$registry = Get-Content "registry.json" | ConvertFrom-Json

foreach ($entry in $registry.entries) {
    if ($entry.export.qud -and $entry.export.qud.enabled) {
        .\ExportQudTiles.ps1 `
            -RegistryPath "registry.json" `
            -AssetId $entry.id `
            -OutputDir "QudMod\assets\textures\tiles"
    }
}
```

## Next Steps

- Create Qud mod structure
- Integrate with mod build system
- Set up batch processing
- Create tile preview tools
- Document your Qud mod conventions

