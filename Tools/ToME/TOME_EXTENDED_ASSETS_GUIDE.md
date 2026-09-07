# ToME Extended Asset Generator Guide

## Overview

The Extended Asset Generator adds support for additional ToME asset types beyond basic sprites and talents:

- **Achievements** - Unlockable achievements
- **Birth Descriptors** - Races and classes for character creation
- **NPCs** - Non-player characters and entities
- **Lore** - Story and world-building entries
- **Quests** - Quest definitions
- **Zones** - Level/dungeon definitions
- **Timed Effects** - Status effects and buffs/debuffs

## Installation

The extended generator requires the base generator:

```bash
# Both files should be in the same directory
tome_asset_generator.py
tome_asset_generator_extended.py
tomegen_extended_cli.py
```

## Quick Start

### Generate an Achievement

```bash
python tomegen_extended_cli.py generate \
  --asset-type achievement \
  --seed 12345 \
  --category "Generated" \
  --out ./mods/my_mod
```

### Generate a Birth Race

```bash
python tomegen_extended_cli.py generate \
  --asset-type birth_race \
  --seed 12346 \
  --out ./mods/my_mod
```

### Generate an NPC

```bash
python tomegen_extended_cli.py generate \
  --asset-type npc \
  --seed 12347 \
  --out ./mods/my_mod
```

## Supported Asset Types

### Achievements

Generates achievement definitions with tracking and completion logic.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type achievement \
  --seed 12345 \
  --category "My Category"
```

**Generated Structure:**
- `data/achievements/gen_achievement_12345.lua`

### Birth Races

Generates race descriptors for character creation.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type birth_race \
  --seed 12346
```

**Generated Structure:**
- `data/birth/races/gen_birth_race_12346.lua`

**Features:**
- Random stat bonuses
- Race type selection (humanoid, giant, undead, etc.)
- Safe descriptor structure

### Birth Classes

Generates class descriptors for character creation.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type birth_class \
  --seed 12347
```

**Generated Structure:**
- `data/birth/classes/gen_birth_class_12347.lua`

### NPCs

Generates NPC entity definitions.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type npc \
  --seed 12348
```

**Generated Structure:**
- `data/general/npcs/gen_npc_12348.lua`

**Features:**
- Base entity definition
- Variant entity with level range
- AI configuration
- Combat stats

### Lore

Generates lore/story entries.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type lore \
  --seed 12349 \
  --category "history"
```

**Generated Structure:**
- `data/lore/gen_lore_12349.lua`

**Categories:**
- history
- legend
- misc
- location
- person

### Quests

Generates quest definitions.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type quest \
  --seed 12350
```

**Generated Structure:**
- `data/quests/gen_quest_12350.lua`

**Quest Types:**
- kill
- collect
- explore
- escort
- deliver

### Zones

Generates zone/dungeon definitions.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type zone \
  --seed 12351
```

**Generated Structure:**
- `data/zones/gen_zone_12351/zone.lua`

**Zone Types:**
- dungeon
- wilderness
- town
- cave
- ruins

### Timed Effects

Generates status effect definitions.

**Example:**
```bash
python tomegen_extended_cli.py generate \
  --asset-type timed_effect \
  --seed 12352
```

**Generated Structure:**
- `data/timed_effects/gen_timed_effect_12352.lua`

**Effect Types:**
- physical
- magical
- mental
- other

## Batch Generation

Create a CSV file (`extended_assets.csv`):

```csv
asset_type,seed,variant,category
achievement,12345,,Generated
birth_race,12346,,
npc,12347,,
lore,12348,,history
quest,12349,,
zone,12350,,
timed_effect,12351,,
```

Run batch generation:

```bash
python tomegen_extended_cli.py batch \
  --csv extended_assets.csv \
  --out ./mods/my_extended_mod \
  --mod-name my_extended_mod \
  --mod-author "Your Name"
```

## Mod Structure

The extended generator creates a complete mod structure:

```
mods/my_mod/
  init.lua                    # Mod initialization
  manifest.json               # Asset manifest
  data/
    achievements/             # Achievement definitions
    birth/
      races/                  # Race descriptors
      classes/                # Class descriptors
    general/
      npcs/                   # NPC entities
      objects/                # Item definitions
      events/                 # Event definitions
      grids/                  # Grid definitions
      encounters/             # Encounter definitions
      traps/                  # Trap definitions
    lore/                     # Lore entries
    quests/                   # Quest definitions
    zones/                    # Zone definitions
      gen_zone_12351/
        zone.lua
        npcs.lua (optional)
        objects.lua (optional)
        grids.lua (optional)
    timed_effects/            # Status effects
    gfx/                      # Graphics (from base generator)
    lua/                      # Lua stubs (from base generator)
    locale/                   # Localization (from base generator)
```

## Mod Init File

The generator automatically creates `init.lua`:

```lua
-- Generated ToME Mod
-- Created by ToME Asset Generator

long_name = "My Mod"
short_name = "my_mod"
for_module = "tome"
version = {1, 7, 4}
addon_version = {1, 0, 0}
weight = 1
author = { "Your Name" }
homepage = "http://te4.org/"
description = [[Generated mod created by ToME Asset Generator.]]
overload = false
superload = false
hooks = false
data = true
```

## Programmatic API

```python
from tome_asset_generator_extended import (
    ExtendedToMEAssetGenerator,
    ExtendedAssetType
)

# Create generator
generator = ExtendedToMEAssetGenerator(
    output_dir="./mods/my_mod",
    mod_name="my_mod",
    mod_author="Your Name",
    mod_version="1.0.0"
)

# Generate an achievement
achievement = generator.generate_extended(
    asset_type=ExtendedAssetType.ACHIEVEMENT,
    seed=12345,
    category="My Category"
)

# Generate a birth race
race = generator.generate_extended(
    asset_type=ExtendedAssetType.BIRTH_RACE,
    seed=12346
)

# Generate mod init
init_path = generator.generate_mod_init()

# Generate manifest
manifest_path = generator.generate_extended_manifest()
```

## Combining Base and Extended Assets

You can use both generators together:

```python
from tome_asset_generator import ToMEAssetGenerator, AssetType, ShapeModule
from tome_asset_generator_extended import ExtendedToMEAssetGenerator, ExtendedAssetType

# Create extended generator (includes base functionality)
generator = ExtendedToMEAssetGenerator("./mods/combined_mod", "combined_mod")

# Generate base assets (spells, actors, etc.)
spell = generator.generate(
    template=AssetType.SPELL,
    shapes=[ShapeModule.RING],
    seed=10001
)

# Generate extended assets
achievement = generator.generate_extended(
    asset_type=ExtendedAssetType.ACHIEVEMENT,
    seed=20001
)

# Generate mod files
generator.generate_mod_init()
generator.generate_extended_manifest()
generator.generate_preview_html()
```

## Customization

All generated files are safe, validated Lua that follows ToME conventions. You can:

1. **Edit generated files** - Customize as needed
2. **Add additional logic** - Extend generated stubs
3. **Combine with manual assets** - Mix generated and hand-crafted content
4. **Use as templates** - Copy and modify for your own assets

## Safety & Validation

- All generated Lua is validated
- Names are sanitized to prevent code injection
- Follows ToME mod conventions
- Compatible with ToME's mod loading system

## Next Steps

1. Generate assets using the CLI
2. Review generated files
3. Customize as needed
4. Test in ToME
5. Package and share your mod

## See Also

- `TOME_ASSET_GENERATOR_README.md` - Base generator documentation
- `TOME_ASSET_GENERATOR_QUICK_START.md` - Quick start guide
- [ToME Modding Guide](https://te4.org/wiki/Modding)

