# Line Drawing to Asset Pipeline Guide

## Overview

This pipeline transforms your **single-color, line-by-line, interconnected drawings** into **multicolor, textured, game-ready assets**. Your drawing style is perfect for this because your lines already encode clean silhouettes, flow, and structure—the hardest parts for procedural tools to invent.

## Your Drawing Style → Asset Pipeline

### Your Style
- **Single color** (black lines on white, or white on black)
- **Line-by-line** construction
- **Interconnected shapes** (lines connect to form regions)
- **Clean structure** (clear silhouettes and flow)

### What the Pipeline Does
1. **Extracts structure** from your lines (skeleton, regions, intersections)
2. **Maps lines to colors** using your registry palette
3. **Creates meshes** from line structure
4. **Applies procedural materials** for texture and detail
5. **Generates game-ready assets** (spritesheets, XML, etc.)
6. **Keeps everything editable** (node groups, meshes, materials)

## Quick Start

### Basic Usage

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -SketchPath "drawings\verdant_pulse.png" `
    -UseSketchAs "silhouette"
```

### With Line Drawing Processing

```powershell
# Use line drawing processor directly
blender --background --python line_drawing_processor.py -- \
    --lineDrawing "drawings\ship_lineart.png" \
    --registry "asset_registry.json" \
    --assetId "ship_scout" \
    --mappingStrategy "hierarchical" \
    --output "ship_scout.blend"
```

## Drawing Preparation

### Best Practices for Your Line Drawings

1. **High Contrast**
   - Black lines on white background (or white on black)
   - Clear separation between lines and background
   - No gray areas or gradients

2. **Clean Lines**
   - Solid, continuous strokes
   - Minimal gaps in lines
   - Clear intersections

3. **Proper Resolution**
   - 512×512 minimum for icons
   - 1024×1024+ for ships/projectiles
   - Higher resolution = better structure extraction

4. **Clear Structure**
   - Outer outline clearly defined
   - Internal lines connect logically
   - Regions are clearly separated

### Scanning/Photographing Tips

- Use good lighting (avoid shadows)
- High resolution (300+ DPI)
- Straight, flat scanning
- Clean background

## Color Mapping Strategies

### Hierarchical (Default)

Maps colors based on line hierarchy:
- **Outer lines** → Darker palette colors
- **Inner lines** → Mid-tone colors
- **Intersections** → Lighter colors
- **Regions** → Fill with gradients

**Best for:**
- Ships (hull outline → panel lines → details)
- Icons (outer shape → internal details)
- Complex structures

**Example:**
```powershell
--mappingStrategy "hierarchical"
```

### Distance-Based

Maps colors based on distance from center:
- **Center** → Lightest colors
- **Edges** → Darkest colors
- **Gradient** → Smooth transition

**Best for:**
- Radial patterns
- Circular icons
- Energy effects

**Example:**
```powershell
--mappingStrategy "distance"
```

### Region-Based

Maps colors based on closed regions:
- Each **closed region** gets a color
- **Adjacent regions** get different colors
- **Lines** get region-appropriate colors

**Best for:**
- Multi-part structures
- Segmented designs
- Panel-based ships

**Example:**
```powershell
--mappingStrategy "region"
```

### Thickness-Based

Maps colors based on line thickness:
- **Thick lines** → Darker colors
- **Thin lines** → Lighter colors
- **Variable thickness** → Gradient mapping

**Best for:**
- Calligraphic styles
- Variable-width strokes
- Artistic line art

**Example:**
```powershell
--mappingStrategy "thickness"
```

## Asset Type Workflows

### Ships (Transcendence)

**Your Drawing:**
- Top-down ship outline
- Internal panel lines
- Detail lines

**Pipeline Processing:**
1. Extract outer silhouette → Extrude to 3D hull
2. Map panel lines → Plating patterns
3. Map detail lines → Emissive channels
4. Apply procedural materials → Hull texture
5. Render rotations → Spritesheet
6. Export XML → Transcendence mod

**Registry Entry:**
```json
{
  "id": "ship_scout",
  "type": "ship",
  "visual": {
    "icon": {
      "palette": ["#4a90e2", "#7bb3f0", "#2c5aa0"],
      "style": "painterly"
    }
  },
  "generation": {
    "sketchSource": "drawings/ship_scout_lineart.png",
    "useSketchAs": "silhouette",
    "extrudeDepth": 0.2,
    "mappingStrategy": "hierarchical"
  }
}
```

### Projectiles

**Your Drawing:**
- Energy bolt shape
- Flow lines
- Core outline

**Pipeline Processing:**
1. Extract shape → Emission mask
2. Map flow lines → Distortion pattern
3. Map core → Bright emission
4. Animate → Frame sequence
5. Assemble → Horizontal strip

**Registry Entry:**
```json
{
  "id": "projectile_energy",
  "type": "projectile",
  "visual": {
    "projectile": {
      "palette": ["#00ffff", "#0088ff", "#0000ff"],
      "shape": "energy bolt"
    }
  },
  "generation": {
    "sketchSource": "drawings/energy_bolt.png",
    "useSketchAs": "mask",
    "mappingStrategy": "distance"
  }
}
```

### Icons (Elin, Terraria, Starbound)

**Your Drawing:**
- Icon shape
- Internal details
- Border lines

**Pipeline Processing:**
1. Extract shape → Mask
2. Map details → Color regions
3. Apply materials → Texture
4. Bake → 32×32 or 64×64
5. Export → Game formats

**Registry Entry:**
```json
{
  "id": "icon_spell",
  "type": "spell",
  "visual": {
    "icon": {
      "palette": ["#ff6b6b", "#ff8787", "#ffa8a8"],
      "size": 32,
      "style": "pixel"
    }
  },
  "generation": {
    "sketchSource": "drawings/spell_icon.png",
    "useSketchAs": "silhouette",
    "mappingStrategy": "hierarchical"
  }
}
```

### Spell FX

**Your Drawing:**
- Base frame shape
- Motion lines
- Energy flow

**Pipeline Processing:**
1. Extract base → Frame 0
2. Map motion lines → Animation path
3. Map energy → Glow mask
4. Generate frames → Animation sequence
5. Assemble → Spritesheet

## Registry Integration

### Line Drawing Fields

Add to your registry `generation` block:

```json
{
  "generation": {
    "sketchSource": "drawings/my_drawing.png",
    "useSketchAs": "silhouette",
    "extrudeDepth": 0.1,
    "bevelAmount": 0.01,
    "mappingStrategy": "hierarchical",
    "quality": "high"
  }
}
```

### Parameters

- **sketchSource**: Path to your line drawing
- **useSketchAs**: How to use the drawing ("silhouette", "displacement", "mask", "reference")
- **extrudeDepth**: How far to extrude (for 3D meshes)
- **bevelAmount**: Edge bevel amount
- **mappingStrategy**: Color mapping method ("hierarchical", "distance", "region", "thickness")
- **quality**: Quality tier ("draft", "standard", "high", "ultra")

## Pipeline Flow

### 1. Digitize & Preprocess

- Scan/photograph your drawing
- Convert to pure black/white (threshold)
- Clean edges (remove noise)
- Unify stroke width (optional)

### 2. Extract Structure

- Detect lines (Hough transform or edge detection)
- Extract skeleton (centerlines)
- Find intersections and endpoints
- Identify closed regions
- Build line graph

### 3. Map to Colors

- Use your registry palette
- Apply mapping strategy
- Assign colors to lines/regions
- Create color map

### 4. Create Mesh

- Convert lines to curves
- Extrude to 3D (if needed)
- Create region meshes
- Apply bevels

### 5. Apply Materials

- Use procedural material generator
- Enhance with line color mapping
- Apply quality-tiered detail
- Enable node groups (for editing)

### 6. Generate Assets

- Render/bake textures
- Assemble spritesheets
- Export to game formats
- Save editable .blend files

## Why This Works With Your Style

### Your Advantages

1. **Clean Structure**: Your lines naturally encode structure
2. **Clear Hierarchy**: Outer/inner lines create natural hierarchy
3. **Interconnected Design**: Lines connect logically
4. **Flow & Motion**: Line direction suggests motion
5. **Segmentation**: Lines create natural regions

### What the Pipeline Adds

1. **Color**: Maps your palette to line structure
2. **Texture**: Adds procedural detail
3. **Lighting**: Applies rim light, emission
4. **Animation**: Uses line flow for motion
5. **Export**: Formats for multiple games

## Best Practices

### Drawing Tips

1. **Start with Outline**: Draw outer shape first
2. **Add Internal Lines**: Connect logically
3. **Create Regions**: Use lines to define areas
4. **Maintain Contrast**: Keep lines clear and distinct
5. **Think in Layers**: Outer → Inner → Details

### Processing Tips

1. **Test Mapping Strategies**: Try different strategies to see what works
2. **Adjust Parameters**: Tune extrude depth, bevel amount
3. **Use Quality Tiers**: Start with draft, upgrade to high/ultra
4. **Enable Node Groups**: Keep materials editable
5. **Iterate**: Refine drawings based on results

### Workflow Tips

1. **Batch Process**: Process multiple drawings at once
2. **Save Variations**: Keep different mapping strategies
3. **Document**: Note which strategies work for which asset types
4. **Reuse**: Create templates for common patterns
5. **Integrate**: Use with your existing registry and pipeline

## Troubleshooting

### Lines Not Detected

- **Check contrast**: Ensure high contrast (pure black/white)
- **Increase resolution**: Use higher resolution images
- **Clean image**: Remove noise, artifacts
- **Try different methods**: Switch between extraction methods

### Colors Not Mapping Correctly

- **Try different strategy**: Switch mapping strategies
- **Adjust palette**: Use more/fewer colors
- **Check structure**: Verify lines are being extracted
- **Manual override**: Edit material in Blender

### Mesh Not Created

- **Check extrude depth**: May be too small/large
- **Verify structure**: Ensure lines form valid shapes
- **Try silhouette method**: Use simpler extraction
- **Check bevel amount**: May be causing issues

### Materials Not Applied

- **Verify registry**: Check visual block has palette
- **Check quality**: Ensure quality tier is supported
- **Enable node groups**: May help with debugging
- **Manual application**: Apply material manually in Blender

## Advanced Usage

### Custom Line Processing

After initial processing, you can:
1. Open .blend file in Blender
2. Edit line curves manually
3. Adjust color mapping
4. Refine materials
5. Re-export

### Batch Processing

```powershell
$drawings = @(
    @{Id="ship1"; Path="drawings/ship1.png"; Strategy="hierarchical"},
    @{Id="ship2"; Path="drawings/ship2.png"; Strategy="region"},
    @{Id="icon1"; Path="drawings/icon1.png"; Strategy="distance"}
)

foreach ($drawing in $drawings) {
    blender --background --python line_drawing_processor.py -- \
        --lineDrawing $drawing.Path \
        --registry "registry.json" \
        --assetId $drawing.Id \
        --mappingStrategy $drawing.Strategy \
        --output "output/$($drawing.Id).blend"
}
```

### Integration with Spritesheet Builder

```powershell
# 1. Process line drawing
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -SketchPath "drawings/scout.png" `
    -ExportNodeGroups

# 2. Render rotations (manual or scripted)

# 3. Assemble spritesheet
.\CrossGameSpritesheet.ps1 `
    -InputDir "GeneratedTextures\ship_scout" `
    -OutputDir "Spritesheets" `
    -GameFormat "Both"
```

## Next Steps

- Create a drawing library for your mod
- Build drawing templates for different asset types
- Document which mapping strategies work best
- Create batch processing workflows
- Integrate with your existing asset pipeline

