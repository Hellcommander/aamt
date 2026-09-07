# ToME Asset Generator - Complete Summary

## Overview

A comprehensive asset generation system for **Tales of Maj'Eyal (T-Engine4)** that produces ready-to-drop mod packages with both visual and data assets.

## Components

### 1. Base Generator (`tome_asset_generator.py`)

Generates core visual and gameplay assets:

- **Spritesheets** (PNG) with metadata (.meta.json)
- **Lua stubs** for talents, items, entities
- **VFX/particle metadata**
- **Localization files**
- **Balance scoring**
- **Preview assets** (PNG + HTML)

**CLI:** `tomegen_cli.py`

### 2. Extended Generator (`tome_asset_generator_extended.py`)

Adds support for additional ToME asset types:

- **Achievements** - Unlockable achievements
- **Birth Descriptors** - Races and classes
- **NPCs** - Non-player characters
- **Lore** - Story entries
- **Quests** - Quest definitions
- **Zones** - Level/dungeon definitions
- **Timed Effects** - Status effects
- **Mod init.lua** - Mod initialization file

**CLI:** `tomegen_extended_cli.py`

## Quick Start

### Base Assets

```bash
# Generate a spell
python tomegen_cli.py generate \
  --template spell \
  --shapes ring,ink_bleed \
  --seed 12345 \
  --out ./mods/my_mod
```

### Extended Assets

```bash
# Generate an achievement
python tomegen_extended_cli.py generate \
  --asset-type achievement \
  --seed 12345 \
  --category "My Category" \
  --out ./mods/my_mod
```

## File Structure

```
mods/my_mod/
  init.lua                    # Mod initialization (extended)
  manifest.json               # Asset manifest
  data/
    # Base Assets
    gfx/sprites/              # Spritesheets + metadata
    lua/talents/              # Talent stubs
    lua/entities/              # Entity stubs
    lua/items/                # Item stubs
    locale/en/                 # Localization
    
    # Extended Assets
    achievements/              # Achievement definitions
    birth/
      races/                   # Race descriptors
      classes/                 # Class descriptors
    general/
      npcs/                    # NPC entities
      objects/                 # Item definitions
      events/                  # Event definitions
      grids/                   # Grid definitions
      encounters/              # Encounter definitions
      traps/                   # Trap definitions
    lore/                      # Lore entries
    quests/                    # Quest definitions
    zones/                     # Zone definitions
    timed_effects/             # Status effects
    
  preview/                     # Preview assets
    preview.html
    *_preview.png
```

## Asset Types

### Base Asset Types

- `spell` - Spell/talent effects
- `actor` - Animated characters
- `item` - Static items
- `vfx` - Visual effects
- `projectile` - Projectile sprites

### Extended Asset Types

- `achievement` - Achievements
- `birth_race` - Character races
- `birth_class` - Character classes
- `npc` - NPC entities
- `lore` - Story entries
- `quest` - Quest definitions
- `zone` - Zone/dungeon definitions
- `timed_effect` - Status effects

## Shape Modules

Modify base template parameters:

- `ring` - Area effect
- `ink_bleed` - Damage over time
- `bolt` - Single target
- `nova` - Large area
- `beam` - Long-range beam
- `wall` - Linear effect
- `cloud` - Lingering area
- `sphere` - 3D sphere
- `cube` - Cubic area
- `spiral` - Spiral pattern

## Features

### Deterministic Generation
- Same seed = identical output
- Reproducible across runs
- Shareable seeds

### Safe Lua
- Validated code
- No arbitrary execution
- Follows ToME conventions

### Balance Scoring
- Automatic balance calculation
- Warnings for outliers
- Designer-friendly metrics

### Validation
- Engine limit checks
- Safety rules
- Preview gating

## Documentation

- `TOME_ASSET_GENERATOR_README.md` - Base generator full docs
- `TOME_ASSET_GENERATOR_QUICK_START.md` - Quick start guide
- `TOME_EXTENDED_ASSETS_GUIDE.md` - Extended assets guide
- `example_tomegen_usage.py` - Base generator example
- `example_tomegen_extended_usage.py` - Extended generator example

## Examples

### Generate Complete Mod

```python
from tome_asset_generator_extended import (
    ExtendedToMEAssetGenerator,
    ExtendedAssetType
)
from tome_asset_generator import AssetType, ShapeModule

# Create generator
generator = ExtendedToMEAssetGenerator(
    "./mods/complete_mod",
    "complete_mod",
    "Your Name",
    "1.0.0"
)

# Base assets
generator.generate(
    AssetType.SPELL,
    [ShapeModule.RING],
    seed=10001
)

# Extended assets
generator.generate_extended(
    ExtendedAssetType.ACHIEVEMENT,
    seed=20001,
    category="My Category"
)

# Generate mod files
generator.generate_mod_init()
generator.generate_extended_manifest()
generator.generate_preview_html()
```

## Batch Generation

### Base Assets CSV

```csv
template,shapes,seed,variant
spell,ring,12345,
spell,bolt,12346,
actor,,12347,
```

### Extended Assets CSV

```csv
asset_type,seed,variant,category
achievement,12345,,Generated
birth_race,12346,,
npc,12347,,
lore,12348,,history
```

## Testing Checklist

- [ ] Determinism: Same seed produces identical files
- [ ] Engine Load: Mod loads without errors
- [ ] Talents: Appear in talent lists
- [ ] Sprites: Display correctly
- [ ] Balance: Scores within normal range
- [ ] Localization: Text displays correctly
- [ ] Achievements: Track properly
- [ ] NPCs: Spawn correctly
- [ ] Quests: Start and complete
- [ ] Zones: Load and generate

## Requirements

- Python 3.7+
- Pillow: `pip install Pillow`

## License

Provided as-is for mod development. Generated assets follow ToME modding guidelines.

## See Also

- [ToME Modding Guide](https://te4.org/wiki/Modding)
- [T-Engine4 Documentation](https://te4.org/wiki/T-Engine4)
- [ToME Forums](https://forums.te4.org/)

