# Asset Generation Guide

The Qud Mod Fixer now includes **automatic asset generation** for mutations, creatures, and equipment!

## What Gets Generated

### **Mutation Assets**
- **Icons**: Visual icons for mutations (64x64 PNG)
- **Ability Markers**: Visual markers for activated abilities (32x32 PNG)
- **Special Visuals**: Custom visuals for mutations like Space-Time Vortex
  - Black hole singularity visuals
  - White hole rupture visuals
  - Warning markers for pre-spawn indicators

### **Creature Assets**
- **Tiles**: Creature sprites in Qud format (32x32 BMP)
- Supports multiple tiers (T1-T6)
- Color-coded based on ObjectBlueprints.xml
- Creature types: Ants, Beetles, Moths, Leeches, Generic Insects

### **Equipment Assets**
- **Tiles**: Equipment tiles for game world (32x32 BMP)
- **Icons**: UI icons for inventory/equipment screen (64x64 PNG)
- Special handling for unique items like the Broodling Sack

### **Audio Assets**
- **Attack Sounds**: Swing/strike sounds for creatures
- **Hit Sounds**: Impact/contact sounds (material-based)
- **Death Sounds**: Creature death sounds
- **Spawn Sounds**: Appear/summon sounds
- **Ambient/Idle Sounds**: Loopable background sounds
- **Walk/Run/Jump/Land Sounds**: Footstep sounds (surface-based)
- **Use Sounds**: Item activation sounds
- **Missile Fire Sounds**: Projectile launch sounds
- **Detonated Sounds**: Explosion sounds

## Usage

### **Automatic (via Mod Fixer)**
Assets are automatically generated when you run the mod fixer:

```bash
python qud_mod_fixer.py "Broodmother Mutation"
```

The fixer will:
1. Fix code issues
2. Generate Unity assets (.meta files)
3. **Generate visual assets** (mutations, creatures, equipment)

### **Standalone Generation**
Generate assets without running the full fixer:

```bash
# Generate all assets
python generate_mod_assets.py "Broodmother Mutation"

# Or use the batch file
GenerateModAssets.bat "Broodmother Mutation"
```

### **Selective Generation**
Generate only specific asset types:

```bash
# Only mutations
python generate_mod_assets.py "Space Time Vortex" --mutations-only

# Only creatures
python generate_mod_assets.py "Broodmother Mutation" --creatures-only

# Only equipment
python generate_mod_assets.py "Broodmother Mutation" --equipment-only

# Only audio
python generate_mod_assets.py "Broodmother Mutation" --audio-only

# All assets including audio
python generate_mod_assets.py "Broodmother Mutation" --include-audio
```

## Requirements

### **Pillow (PIL)**
The asset generators require Pillow for image manipulation:

```bash
pip install Pillow
```

If Pillow is not installed, the generators will gracefully skip with a warning.

### **numpy, soundfile (for Audio)**
Audio generation requires numpy and soundfile:

```bash
pip install numpy soundfile
```

If these are not installed, audio generation will be skipped with a warning.

## Generated File Structure

```
ModName/
├── Visuals/
│   ├── Mutations/
│   │   ├── SpaceTimeVortex_icon.png
│   │   ├── BlackHole_visual.png
│   │   └── WhiteHole_visual.png
│   ├── Creatures/
│   │   ├── BroodlingDrone_T1.bmp
│   │   ├── BroodlingBeetle_T2.bmp
│   │   └── ...
│   └── Equipment/
│       ├── Broodling_Sack_tile.bmp
│       └── Broodling_Sack_icon.png
├── Sounds/
│   ├── ModName_attack.ogg
│   ├── ModName_hit.ogg
│   ├── ModName_death.ogg
│   ├── ModName_spawn.ogg
│   ├── ModName_ambient.ogg
│   └── ModName_walk.ogg
└── Assets/
    └── Resources/
        └── (Unity resources if needed)
```

## How It Works

### **1. Analysis Phase**
- Parses `Mutations.xml` to find mutations
- Parses `ObjectBlueprints.xml` to find creatures and equipment
- Extracts color codes, render strings, and tile references

### **2. Generation Phase**
- Creates appropriate visual assets based on type
- Uses Qud color palette for consistency
- Generates in correct formats (BMP for tiles, PNG for icons)

### **3. Integration**
- Assets are placed in `Visuals/` directory
- Can be referenced in ObjectBlueprints.xml
- Works with Unity asset pipeline

## Customization

### **Mutation Icons**
Icons are generated based on mutation type:
- **Mental**: Blue color scheme
- **Physical**: Red color scheme
- **Defect**: Gray color scheme
- **Cybernetics**: Yellow color scheme

Symbols are auto-selected based on mutation name:
- "Vortex" → Singularity symbol (◉)
- "Brood" → Egg/sack symbol (●)
- "Teleport" → Lightning (↯)

### **Creature Tiles**
Creatures are generated based on:
- Base creature type (ant, beetle, moth, leech)
- Tier level (affects size and detail)
- Color from ObjectBlueprints.xml

### **Equipment Assets**
Equipment like the sack includes:
- Organic, bulging shape
- Internal bulges (representing contents)
- Opening/top detail
- Color matching mod theme

## Examples

### **Space-Time Vortex**
```bash
python generate_mod_assets.py "Improved and Rebalanced Space Time Vortex"
```

Generates:
- Mutation icon
- Black hole singularity visual
- White hole rupture visual
- Warning markers

### **Broodmother Mutation**
```bash
python generate_mod_assets.py "Broodmother Mutation"
```

Generates:
- Mutation icon
- All broodling creature tiles (T1-T6)
- Broodling sack tile and icon

## Troubleshooting

### **"Pillow not found"**
```bash
pip install Pillow
```

### **"No assets generated"**
- Check that `Mutations.xml` or `ObjectBlueprints.xml` exists
- Verify mod path is correct
- Check that objects have Render parts defined

### **"Assets look wrong"**
- Assets are procedurally generated
- For custom art, replace generated files manually
- Generated assets are placeholders for development

## Integration with Mod Fixer

The asset generators are automatically called during mod fixing:

```
[FIXING MOD: Broodmother Mutation]
  ...
  Generating visual assets...
    [Mutation Assets] Created 1 icons, 0 visuals
    [Creature Assets] Created 12 creature tiles
    [Equipment Assets] Created 1 tiles, 1 icons
```

This ensures your mod has all necessary visual assets!

## Future Enhancements

Planned improvements:
- AI-generated art using image models
- Style transfer from base game assets
- Animation support
- Particle effect generation
- Sound effect generation

