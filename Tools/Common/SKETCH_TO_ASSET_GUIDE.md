# 2D Sketch to Asset Pipeline Guide

## Overview

The 2D Sketch to Asset Pipeline transforms hand-drawn sketches into fully-generated, editable game assets. This system respects your workflow by:

- **Using sketches as shape input** (not final art)
- **Using procedural materials for style** (from your registry)
- **Keeping everything editable** (node groups, meshes, materials)
- **Integrating with your existing pipeline** (registry, quality tiers, exports)

## Philosophy

You're not trying to magically turn a sketch into a finished asset. Instead:

1. **Sketch defines the shape** - Your drawing provides the silhouette/outline
2. **Registry defines the style** - Palette, materials, quality come from your registry
3. **Blender creates the mesh** - Extrudes, bevels, and processes the sketch
4. **Procedural materials add detail** - Your material generator applies style
5. **Everything stays editable** - Node groups, meshes, and materials can be tweaked

This is exactly how professional studios work when turning concept art into production assets.

## Quick Start

### Basic Usage

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -SketchPath "sketches\verdant_pulse.png" `
    -UseSketchAs "silhouette"
```

### With Registry Entry

Add to your registry entry:

```json
{
  "id": "nature_verdant_pulse",
  "generation": {
    "sketchSource": "sketches/verdant_pulse.png",
    "useSketchAs": "silhouette",
    "extrudeDepth": 0.1,
    "bevelAmount": 0.01,
    "quality": "high"
  }
}
```

Then run:

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse"
```

## Sketch Methods

### Silhouette (Default)

Extrudes the sketch outline to create a 3D mesh.

**Best for:**
- Ship hulls
- Icons
- Projectiles
- Simple 3D shapes

**Parameters:**
- `extrudeDepth`: How far to extrude (default: 0.1)
- `bevelAmount`: Edge bevel amount (default: 0.01)

**Example:**
```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_hull" `
    -SketchPath "sketches\ship_topdown.png" `
    -UseSketchAs "silhouette"
```

### Displacement

Uses the sketch as a height map to displace a subdivided plane.

**Best for:**
- Terrain
- Surface details
- Organic shapes
- Height-based textures

**Parameters:**
- `displacementStrength`: Displacement amount (default: 0.1)

**Example:**
```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "terrain_detail" `
    -SketchPath "sketches\terrain_heightmap.png" `
    -UseSketchAs "displacement"
```

### Mask

Uses the sketch as an alpha mask for materials.

**Best for:**
- Glow effects
- Emission patterns
- Transparent areas
- Material masking

**Example:**
```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_glow" `
    -SketchPath "sketches\glow_mask.png" `
    -UseSketchAs "mask"
```

### Reference

Imports the sketch as a reference image (non-rendering).

**Best for:**
- Visual guides
- Manual modeling reference
- Concept art placement

**Example:**
```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "concept_reference" `
    -SketchPath "sketches\concept.png" `
    -UseSketchAs "reference"
```

### Heightmap

Similar to displacement but optimized for height-based meshes.

**Best for:**
- 3D terrain
- Depth-based shapes
- Topographic features

## Registry Integration

### Sketch Source in Registry

```json
{
  "id": "ship_scout",
  "name": "Scout Ship",
  "type": "ship",
  "visual": {
    "icon": {
      "shape": "streamlined fighter",
      "palette": ["#4a90e2", "#7bb3f0", "#2c5aa0"],
      "style": "painterly"
    }
  },
  "generation": {
    "sketchSource": "sketches/ship_scout_topdown.png",
    "useSketchAs": "silhouette",
    "extrudeDepth": 0.15,
    "bevelAmount": 0.02,
    "quality": "high"
  }
}
```

### Sketch Parameters

- **sketchSource**: Path to sketch image file (relative to registry or absolute)
- **useSketchAs**: Method to use ("silhouette", "displacement", "mask", "reference", "heightmap")
- **extrudeDepth**: Extrusion depth for silhouette method (Blender units)
- **bevelAmount**: Bevel amount for edges (Blender units)
- **displacementStrength**: Displacement strength for displacement method (Blender units)

## Pipeline Flow

### 1. Sketch Input

User provides a 2D sketch:
- Pencil drawing (scanned/photographed)
- Digital sketch
- Silhouette
- Rough shape
- Top-down ship outline
- Projectile concept

### 2. Blender Processing

Blender processes the sketch based on method:
- **Silhouette**: Traces outline → Extrudes → Bevels
- **Displacement**: Subdivides plane → Applies displacement
- **Mask**: Imports as alpha mask
- **Reference**: Imports as non-rendering reference

### 3. Material Application

Your procedural material generator applies:
- Palette colors from registry
- Style (painterly, pixel, flat)
- Quality-tiered detail
- Node groups (if enabled)

### 4. Rendering & Export

Depending on asset type:
- **Ships**: Render rotations → Spritesheet
- **Projectiles**: Render frames → Animation strip
- **Icons**: Bake to 32×32 or 64×64

## Integration Examples

### Example 1: Ship from Sketch

```powershell
# 1. Create registry entry with sketch
# registry.json:
{
  "id": "ship_scout",
  "generation": {
    "sketchSource": "sketches/scout_topdown.png",
    "useSketchAs": "silhouette",
    "extrudeDepth": 0.2
  }
}

# 2. Generate asset
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -Quality "high" `
    -ExportNodeGroups
```

### Example 2: Spell Icon from Sketch

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -SketchPath "sketches\fireball_icon.png" `
    -UseSketchAs "silhouette" `
    -TextureSize 64
```

### Example 3: Projectile with Displacement

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "projectile_energy" `
    -SketchPath "sketches\energy_bolt.png" `
    -UseSketchAs "displacement" `
    -Quality "ultra"
```

## Direct Blender Usage

You can also use the Blender script directly:

```bash
blender --background --python sketch_to_mesh.py -- \
    --sketch "sketches/ship.png" \
    --registry "asset_registry.json" \
    --assetId "ship_scout" \
    --output "ship_scout.blend"
```

Or with direct JSON:

```bash
blender --background --python sketch_to_mesh.py -- \
    --sketch "sketches/ship.png" \
    --visualJson '{"icon":{"palette":["#4a90e2"],"style":"painterly"}}' \
    --generationJson '{"useSketchAs":"silhouette","extrudeDepth":0.1}' \
    --output "ship.blend"
```

## Quality Tiers with Sketches

### Draft
- Fast silhouette extraction
- Minimal subdivision
- Quick material application
- **Use Case**: Rapid prototyping

### Standard
- Balanced processing
- Moderate detail
- Standard material quality
- **Use Case**: Production assets

### High
- Enhanced mesh detail
- Additional bevels/smoothing
- High-quality materials
- **Use Case**: Hero assets

### Ultra
- Maximum mesh detail
- Micro-bevels and smoothing
- Ultra-quality materials
- **Use Case**: Showcase assets

## Best Practices

### 1. Sketch Preparation

- **Clean outlines**: Use high contrast for silhouette extraction
- **Proper resolution**: 512×512 minimum for good results
- **Clear shapes**: Avoid overly complex details in sketch
- **Consistent style**: Match sketch style to intended asset type

### 2. Method Selection

- **Ships**: Use "silhouette" with moderate extrude depth
- **Terrain**: Use "displacement" or "heightmap"
- **Effects**: Use "mask" for glow patterns
- **Reference**: Use "reference" for manual modeling guides

### 3. Parameter Tuning

- **Start with defaults**: Test with default parameters first
- **Adjust incrementally**: Make small changes and test
- **Match asset scale**: Adjust extrude depth to match game scale
- **Consider bevels**: Add bevels for smoother edges

### 4. Material Integration

- **Use registry**: Define materials in registry, not in sketch
- **Enable node groups**: Use `-ExportNodeGroups` for tweakability
- **Quality tiers**: Match quality to asset importance
- **Test materials**: Verify materials work with sketch-derived mesh

## Troubleshooting

### Sketch Not Found
- Check path is correct (relative or absolute)
- Verify file exists and is readable
- Check file format (PNG, JPG supported)

### Mesh Not Created
- Verify sketch has clear contrast (for silhouette)
- Check extrude depth is appropriate
- Try different `useSketchAs` method

### Material Not Applied
- Verify registry entry has visual block
- Check material generator is available
- Ensure quality tier is supported

### Poor Results
- Try different sketch method
- Adjust extrude/displacement parameters
- Use higher quality sketch image
- Enable node groups for manual tweaking

## Advanced Usage

### Batch Processing

Process multiple sketches:

```powershell
$sketches = @(
    @{Id="ship1"; Path="sketches/ship1.png"},
    @{Id="ship2"; Path="sketches/ship2.png"}
)

foreach ($sketch in $sketches) {
    .\GenerateAssetTextures.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $sketch.Id `
        -SketchPath $sketch.Path `
        -UseSketchAs "silhouette"
}
```

### Custom Mesh Processing

After sketch processing, you can:
1. Open the `.blend` file in Blender
2. Edit the mesh manually
3. Adjust materials
4. Re-export or bake textures

### Integration with Spritesheet Builder

```powershell
# 1. Generate asset from sketch
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "ship_scout" `
    -SketchPath "sketches/scout.png" `
    -ExportNodeGroups

# 2. Render rotations in Blender (manual or scripted)

# 3. Assemble spritesheet
.\CrossGameSpritesheet.ps1 `
    -InputDir "GeneratedTextures\ship_scout" `
    -OutputDir "Spritesheets" `
    -GameFormat "Both"
```

## Next Steps

- Create sketch library for your mod
- Build sketch templates for different asset types
- Integrate with your spritesheet pipeline
- Create batch processing workflows
- Document your sketch conventions

