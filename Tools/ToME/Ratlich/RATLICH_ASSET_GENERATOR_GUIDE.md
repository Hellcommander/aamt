# Ratlich Race Asset Generator Guide

## Overview

The Ratlich Asset Generator creates high-quality sprites for the Ratlich race mod, focusing on a proper paperdoll system that doesn't reuse enemy images.

## Features

- **High Quality**: Generates 50-100 variations per asset and automatically selects the best one
- **Paperdoll System**: Creates base body sprites (front & back) and equipment overlays
- **Complete Asset Set**: Includes map sprites, icons, and equipment overlays
- **AI Enhancement**: Optional AI-powered color palettes and descriptions

## Quick Start

### Option 1: GUI (Recommended)

1. **Launch the GUI:**
   ```bash
   python generate_ratlich_assets_gui.py
   ```
   Or double-click `LaunchRatlichAssetGenerator.bat`

2. **Configure:**
   - Set mod path (default: Ratlich race mod location)
   - Enable/disable AI enhancement
   - Click "Generate Assets"

3. **Wait for completion:**
   - Progress bars show generation status
   - Log shows detailed progress
   - Best variations are automatically selected

### Option 2: Command Line

```bash
python generate_ratlich_assets.py --mod-path "path/to/tome-ratlich-race"
```

## Generated Assets

The generator creates the following assets:

### Base Sprites
- **Base Body (Front)**: 100 variations → `data/gfx/actors/ratlich_body_front.png`
- **Base Body (Back)**: 100 variations → `data/gfx/actors/ratlich_body_back.png`
  - Used for paperdoll system (doll_back support)

### Equipment Overlays
- **Head Overlay**: 80 variations → `data/gfx/overlays/ratlich_head.png`
- **Body Overlay**: 80 variations → `data/gfx/overlays/ratlich_body.png`
- **Hands Overlay**: 60 variations → `data/gfx/overlays/ratlich_hands.png`
- **Tail Weapon Overlay**: 80 variations → `data/gfx/overlays/ratlich_tail_weapon.png`

### Map Display Sprites
- **32x32**: 100 variations → `data/gfx/actors/ratlich_32.png`
- **64x64**: 100 variations → `data/gfx/actors/ratlich_64.png`
- **128x128**: 100 variations → `data/gfx/actors/ratlich_128.png`

### Icon Sprites
- **32x32 Icon**: 100 variations → `data/gfx/icons/ratlich_32.png`
- **128x128 Icon**: 100 variations → `data/gfx/icons/ratlich_128.png`

### Talent Icons
- **Rat Lich Cunning**: 100 variations → `data/gfx/talents/rat_lich_cunning.png`
- **Illusory Guise**: 100 variations → `data/gfx/talents/rat_lich_illusory_guise.png`
- **Equip Tail Weapon**: 100 variations → `data/gfx/talents/rat_lich_equip_tail_weapon.png`
- **Dark Feed Rush**: 100 variations → `data/gfx/talents/rat_lich_dark_feed_rush.png`
- **Summon Undead Rats**: 100 variations → `data/gfx/talents/rat_lich_summon_undead_rats.png`

**Total**: ~1,500 variations across 15 asset types

## Quality Selection

Each asset type generates many variations, and the generator automatically selects the best one based on:
- **Balance Score**: Higher scores indicate better quality
- **Visual Consistency**: Consistent with Ratlich theme (undead rodent)
- **Technical Quality**: Proper sprite dimensions and metadata

## Paperdoll Configuration

After generation, a configuration file is created:
- `data/gfx/ratlich_paperdoll_config.json`

This file contains paths to all generated assets and can be used to update the race definition.

## Updating the Race Definition

After generating assets, update the race definition to use them:

```bash
python update_ratlich_race_assets.py --mod-path "path/to/tome-ratlich-race"
```

This script will:
- Update `image`, `image32`, and `image128` paths in race definition
- Add `doll_back` support for paperdoll system
- Update talent icon paths in `ratlich_talents.lua`
- Create backups of both files

## File Structure

After generation, your mod will have:

```
tome-ratlich-race/
├── data/
│   └── gfx/
│       ├── actors/
│       │   ├── ratlich_body_front.png
│       │   ├── ratlich_body_back.png
│       │   ├── ratlich_32.png
│       │   ├── ratlich_64.png
│       │   └── ratlich_128.png
│       ├── overlays/
│       │   ├── ratlich_head.png
│       │   ├── ratlich_body.png
│       │   ├── ratlich_hands.png
│       │   └── ratlich_tail_weapon.png
│       ├── icons/
│       │   ├── ratlich_32.png
│       │   └── ratlich_128.png
│       ├── talents/
│       │   ├── rat_lich_cunning.png
│       │   ├── rat_lich_illusory_guise.png
│       │   ├── rat_lich_equip_tail_weapon.png
│       │   ├── rat_lich_dark_feed_rush.png
│       │   └── rat_lich_summon_undead_rats.png
│       └── ratlich_paperdoll_config.json
└── ...
```

## Paperdoll System

The generated assets support a proper paperdoll system:

1. **Base Body Sprites**: Front and back views for the character
2. **Equipment Overlays**: Separate sprites for equipment that can be composited
3. **doll_back Support**: Back view sprite for equipment overlay rendering

This allows equipment to be visually displayed on the character, unlike the current static tile system.

## Notes

- **Generation Time**: With 1,500+ variations, generation can take 45-90 minutes depending on your system
- **AI Enhancement**: Enabling AI adds time but improves color palettes and visual quality
- **Storage**: Generated assets use ~50-100 MB of disk space
- **Backup**: The update script creates backups before modifying race files

## Troubleshooting

**Generation fails:**
- Check that the mod path is correct
- Ensure you have write permissions to the mod directory
- Check the log for specific error messages

**Assets not appearing in game:**
- Run `update_ratlich_race_assets.py` to update the race and talent definitions
- Verify asset paths in the config file
- Check that sprites are in the correct directories
- For talent icons, ensure they're in `data/gfx/talents/` directory

**Paperdoll not working:**
- Ensure `doll_back` is set in the equipdoll definition
- Check that base body sprites exist
- Verify equipment overlay paths are correct

## Advanced Usage

### Custom Variations

Edit `generate_ratlich_assets.py` to change the number of variations:

```python
'base_body_front': {
    'variations': 150,  # Increase for even higher quality
    ...
}
```

### Manual Asset Selection

The generator selects the best variation automatically, but you can manually choose by:
1. Checking the log for all variation scores
2. Finding the variation number with the highest score
3. Manually copying that variation's file

### Custom Shape Modules

Modify the shape modules used for each asset type in `generate_ratlich_assets.py`:

```python
'base_body_front': {
    'shapes': [ShapeModule.SPHERE, ShapeModule.CLOUD],  # Change shapes
    ...
}
```

