# Procedural Mech System Asset Generation Guide

Generate supporting assets for the procedural mech system including textures, icons, and preview sprites.

## Quick Start

```powershell
# Generate all mech assets
.\GenerateMechAssets.ps1

# Use C++ backend for better quality
.\GenerateMechAssets.ps1 -UseCppBackend

# Or generate everything including mech assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Mech Part Textures (6 textures)

1. **mech_metal** - Metallic mech texture
2. **mech_armor** - Armored mech texture
3. **mech_energy** - Energy mech texture
4. **mech_organic** - Organic mech texture
5. **mech_crystal** - Crystal mech texture
6. **mech_rust** - Rust mech texture

### Mech Part Icons (10 icons)

1. **mech_part_body** - Body part icon
2. **mech_part_head** - Head part icon
3. **mech_part_torso** - Torso part icon
4. **mech_part_arm** - Arm part icon
5. **mech_part_hand** - Hand part icon
6. **mech_part_leg** - Leg part icon
7. **mech_part_foot** - Foot part icon
8. **mech_part_wing** - Wing part icon
9. **mech_part_weapon** - Weapon part icon
10. **mech_part_shield** - Shield part icon

### Mech Preview Sprites (4 sprites)

1. **mech_preview_bipedal** - Bipedal mech preview
2. **mech_preview_quadruped** - Quadruped mech preview
3. **mech_preview_hover** - Hover mech preview
4. **mech_preview_tank** - Tank mech preview

## Total: ~20 Assets

## Output Structure

```
assets/
├── textures/
│   └── mech/
│       ├── mech_metal.png
│       ├── mech_armor.png
│       └── ... (all mech textures)
├── interface/
│   └── icons/
│       └── mech/
│           ├── mech_part_body.png
│           ├── mech_part_head.png
│           └── ... (all part icons)
└── mechs/
    └── previews/
        ├── mech_preview_bipedal.png
        ├── mech_preview_quadruped.png
        └── ... (all preview sprites)
```

## Integration

### Material Textures

Reference textures in mech part definitions:

```lua
local part = engine.createMechPart({
    id = "torso_part",
    type = "torso",
    materialId = "/textures/mech/mech_metal.png",
    metallic = 0.8,
    roughness = 0.2
})
```

### Part Icons

Use icons in UI for part selection:

```lua
local partIcon = "/interface/icons/mech/mech_part_torso.png"
```

### Preview Sprites

Use preview sprites for mech selection UI:

```lua
local mechPreview = "/mechs/previews/mech_preview_bipedal.png"
```

## Mech Part Types

### Core Parts
- **Body**: Main body/core structure
- **Head**: Cockpit/head unit
- **Torso**: Upper torso section

### Limbs
- **Arms**: Left/right arms
- **Hands**: Grippers/hands
- **Legs**: Left/right legs
- **Feet**: Ground contact points

### Optional Parts
- **Wings**: Wings/jets for flight
- **Weapons**: Weapon systems
- **Shields**: Shield systems
- **Accessories**: Additional components

## Mech Types

### Bipedal
- **Visual**: Humanoid mech, two legs, two arms
- **Use**: Standard combat mechs
- **Preview**: Side view, humanoid silhouette

### Quadruped
- **Visual**: Four-legged mech, animal-like
- **Use**: Fast ground movement
- **Preview**: Side view, four-legged silhouette

### Hover
- **Visual**: Floating mech, no ground contact
- **Use**: Aerial combat, mobility
- **Preview**: Side view, floating appearance

### Tank
- **Visual**: Tank-like mech, low profile
- **Use**: Heavy combat, defense
- **Preview**: Side view, tank silhouette

## Material Types

### Metal
- **Visual**: Gray/silver metal, industrial
- **Properties**: High metallic, low roughness
- **Use**: Standard mech parts

### Armor
- **Visual**: Reinforced plates, military
- **Properties**: High metallic, medium roughness
- **Use**: Defensive parts

### Energy
- **Visual**: Glowing energy panels, blue/purple
- **Properties**: Low metallic, high glow
- **Use**: Energy-based parts

### Organic
- **Visual**: Bio-mechanical, green/brown
- **Properties**: Low metallic, high roughness
- **Use**: Bio-mech parts

### Crystal
- **Visual**: Crystalline structure, faceted
- **Properties**: Medium metallic, low roughness
- **Use**: Crystal-based parts

### Rust
- **Visual**: Weathered metal, orange/brown
- **Properties**: Low metallic, high roughness
- **Use**: Damaged/weathered parts

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateMechAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Mech Parts

Use procedural mech generator to create parts with material references.

### Step 3: Assemble Mechs

Use mech assembly system to combine parts.

### Step 4: Configure Materials

Set material properties for each part type.

### Step 5: Test in Game

Load the mod and test mechs in-game.

## Advanced Options

### Custom Textures

Edit `GenerateMechAssets.ps1` to add custom texture types:

```powershell
@{
    Id = "custom_texture"
    Name = "Custom Texture"
    Description = "Custom texture description"
}
```

### Custom Part Icons

Add custom part icons to the `$mechPartIcons` array.

### Custom Previews

Add custom mech type previews to the `$mechPreviews` array.

## Tips

1. **Texture size**: Use 256x256 or 512x512 for textures
2. **Icon size**: Keep icons at 32x32 for UI consistency
3. **Preview size**: Use 64x64 or 128x128 for previews
4. **Seamless textures**: Ensure textures tile seamlessly
5. **Material properties**: Match textures to material properties

## Procedural Generation

**Note**: The mech system primarily generates meshes, skeletons, and animations procedurally. These assets are supporting materials for:
- Material textures for rendered mechs
- UI icons for part selection
- Preview sprites for mech selection

The actual mech geometry is generated by the `ProceduralMechGenerator` class.

## Troubleshooting

### Textures Not Appearing

- Check texture paths in part definitions
- Verify textures are in `assets/textures/mech/`
- Ensure material properties are set correctly

### Icons Not Showing

- Verify icon paths in UI code
- Check icons are in `assets/interface/icons/mech/`
- Ensure icon size is 32x32

### Previews Not Loading

- Check preview paths in mech definitions
- Verify previews are in `assets/mechs/previews/`
- Ensure preview size is appropriate

---

*Part of the Starbound Ollama Asset Generator suite*
