# Node Groups Export Mode Guide

## Overview

The Node Groups Export Mode transforms your generated materials from "black box" textures into **editable, non-destructive, artist-friendly shader kits**. Every procedural layer becomes a reusable, tweakable node group that modders can open in Blender and customize.

## Why Node Groups?

### Benefits

- **Editable**: Every layer can be tweaked without regenerating
- **Non-Destructive**: Changes don't require re-baking
- **Organized**: Clean, labeled building blocks
- **Reusable**: Node groups can be shared across materials
- **Modder-Friendly**: Clear visual hierarchy, no spaghetti nodes
- **Quality-Tiered**: Ultra quality = more node groups, Draft = fewer groups

### Use Cases

- **Manual Refinement**: Generate a base, then tweak in Blender
- **Consistent Styling**: Reuse node groups across spell schools or factions
- **Learning Tool**: See how procedural materials are built
- **Custom Variations**: Create variations without regenerating from scratch

## Quick Start

### Basic Usage

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -Quality "high" `
    -ExportNodeGroups
```

This will:
1. Generate textures as usual
2. Create a `.blend` file with editable node groups
3. Save the file to `GeneratedTextures\{AssetId}\{AssetId}_material.blend`

### Custom Blend File Path

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -ExportNodeGroups `
    -BlendOutputPath "Materials\verdant_pulse.blend"
```

## Node Group Structure

### Available Node Groups

Each procedural layer becomes a named, reusable node group:

#### **PaletteRampLayer**
- **Purpose**: Color palette ramping
- **Inputs**: `Factor` (float)
- **Outputs**: `Color` (color)
- **Tweakable**: Palette colors, ramp positions

#### **BaseNoiseLayer**
- **Purpose**: Base noise pattern
- **Inputs**: `Scale` (float), `Detail` (float)
- **Outputs**: `Fac` (float)
- **Tweakable**: Noise scale, detail level

#### **DetailNoiseLayer**
- **Purpose**: Detail noise overlay (high/ultra quality)
- **Inputs**: `Scale` (float), `Detail` (float)
- **Outputs**: `Mask` (float)
- **Tweakable**: Detail intensity, scale

#### **VoronoiLayer**
- **Purpose**: Voronoi pattern generation
- **Inputs**: `Scale` (float)
- **Outputs**: `Distance` (float)
- **Tweakable**: Pattern scale, cell size

#### **RimLightLayer**
- **Purpose**: Rim lighting effects
- **Inputs**: `BaseColor` (color), `RimColor` (color), `Strength` (float)
- **Outputs**: `Color` (color)
- **Tweakable**: Rim color, strength, blend mode

#### **EmissionLayer**
- **Purpose**: Glow and emission effects
- **Inputs**: `Color` (color), `Strength` (float)
- **Outputs**: `Emission` (color)
- **Tweakable**: Emission color, intensity

## Material Structure

When node groups are enabled, the material structure looks like:

```
[BaseNoiseLayer] → [VoronoiLayer] → [Pattern Mix] → [PaletteRampLayer] → [DetailNoiseLayer] → [RimLightLayer] → [Principled BSDF] → [Output]
                                                                         ↓
                                                                    [EmissionLayer]
```

Each node group is:
- **Labeled**: Clear names for easy identification
- **Parameterized**: Only essential inputs exposed
- **Organized**: Logical layout and connections
- **Reusable**: Can be copied to other materials

## Quality Tiers and Node Groups

### Draft
- **Groups**: BaseNoiseLayer, VoronoiLayer, PaletteRampLayer
- **Complexity**: Minimal, fast to edit
- **Use Case**: Quick iterations

### Standard
- **Groups**: BaseNoiseLayer, VoronoiLayer, PaletteRampLayer, Pattern Mix
- **Complexity**: Moderate, balanced
- **Use Case**: Production assets

### High
- **Groups**: All standard + DetailNoiseLayer, RimLightLayer (if needed)
- **Complexity**: Enhanced detail, more layers
- **Use Case**: High-quality assets

### Ultra
- **Groups**: All high + additional detail layers, emission shaping
- **Complexity**: Maximum detail, full control
- **Use Case**: Showcase assets, final exports

## Editing Node Groups in Blender

### Opening the Material

1. Open the `.blend` file in Blender
2. Go to **Shading** workspace
3. Select the material (named after your asset ID)
4. View the node tree

### Tweaking Parameters

Each node group exposes key parameters:

- **Scale**: Pattern size
- **Detail**: Detail level
- **Factor**: Mixing strength
- **Color**: Color inputs
- **Strength**: Effect intensity

### Editing Node Groups

1. **Double-click** a node group to enter it
2. **Edit** internal nodes
3. **Add/Remove** nodes as needed
4. **Exit** by clicking the material name breadcrumb

### Reusing Node Groups

1. **Copy** a node group (Shift+D)
2. **Paste** into another material
3. **Adjust** parameters for variation
4. **Save** as a new material

## Integration Examples

### Example 1: Generate and Tweak

```powershell
# 1. Generate with node groups
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -Quality "high" `
    -ExportNodeGroups

# 2. Open in Blender and tweak
# - Adjust palette colors
# - Modify rim light strength
# - Change noise scales
# - Save as new material

# 3. Bake tweaked material
# Use Blender's bake tools or re-run with modified .blend
```

### Example 2: Batch with Node Groups

```powershell
$assets = @("spell_fireball", "spell_ice_shard", "spell_lightning")

foreach ($asset in $assets) {
    .\GenerateAssetTextures.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $asset `
        -Quality "standard" `
        -ExportNodeGroups
}
```

### Example 3: Custom Blend Location

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "nature_verdant_pulse" `
    -ExportNodeGroups `
    -BlendOutputPath "D:\Mods\Materials\verdant_pulse.blend"
```

## Direct Blender Usage

You can also use the Blender script directly:

```bash
blender --background --python bake_texture.py -- \
    --registry "asset_registry.json" \
    --assetId "nature_verdant_pulse" \
    --quality "high" \
    --exportNodeGroups \
    --blendOutput "material.blend"
```

## Node Group Best Practices

### 1. Start with Generated Base
- Generate materials with node groups enabled
- Use as a starting point, not final result

### 2. Tweak Incrementally
- Make small changes to one group at a time
- Test each change before moving on

### 3. Save Variations
- Save tweaked materials as new `.blend` files
- Name them descriptively (e.g., `verdant_pulse_bright.blend`)

### 4. Reuse Groups
- Copy node groups between materials
- Create a library of reusable groups

### 5. Document Changes
- Note what you changed and why
- Keep a changelog for your materials

## Troubleshooting

### Node Groups Not Created
- Ensure `--exportNodeGroups` flag is set
- Check that material generator supports node groups
- Verify Blender version (3.0+ recommended)

### Blend File Not Saved
- Check output directory permissions
- Verify `--blendOutput` path is valid
- Check Blender console for errors

### Node Groups Not Editable
- Ensure you're in Shading workspace
- Select the material in the material list
- Double-click node groups to enter them

### Missing Node Groups
- Check quality tier (draft has fewer groups)
- Verify visual block has required data
- Check that glow/rim lighting are enabled if needed

## Advanced Usage

### Custom Node Group Library

Create a library of reusable node groups:

1. Generate materials with node groups
2. Extract node groups you like
3. Save them in a separate `.blend` file
4. Append them to new materials as needed

### Material Variations

Generate multiple variations:

```powershell
# Base material
.\GenerateAssetTextures.ps1 -RegistryPath "registry.json" -AssetId "spell_base" -ExportNodeGroups

# Open in Blender, tweak, save as:
# - spell_bright.blend
# - spell_dark.blend
# - spell_glowing.blend
```

### Batch Material Creation

Generate materials for an entire spell school:

```powershell
$spells = @("nature_verdant", "nature_growth", "nature_heal")

foreach ($spell in $spells) {
    .\GenerateAssetTextures.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $spell `
        -Quality "standard" `
        -ExportNodeGroups `
        -BlendOutputPath "Materials\Nature\$spell.blend"
}
```

## Next Steps

- Create a node group library for your mod
- Build material presets for different spell schools
- Share node groups with other modders
- Document your custom node group setups
- Build a material variation workflow

