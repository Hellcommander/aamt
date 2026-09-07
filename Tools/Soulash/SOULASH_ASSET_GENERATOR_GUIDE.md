# Soulash Asset Generator Guide

A PowerShell tool for generating Soulash mod asset definition files.

## Overview

Soulash uses various asset types:
- **Creatures** - Monsters/NPCs with spritesheets and portraits
- **Portraits** - Character face icons (64x64 typically)
- **Items** - Equipment, consumables, materials
- **Abilities** - Skill and spell icons
- **Tiles** - Ground and wall tiles
- **Buildings** - Structures and decorations
- **Effects** - Animated visual effects

## Quick Start

```powershell
# Generate a demon creature
.\SoulashAssetGenerator.ps1 -AssetName "fire_demon" -AssetType Creature -Preset Demon

# Generate a health potion
.\SoulashAssetGenerator.ps1 -AssetName "health_potion" -AssetType Item -Preset Potion

# Generate an attack ability
.\SoulashAssetGenerator.ps1 -AssetName "fireball" -AssetType Ability -Preset Magic
```

## Asset Types

### Creature

Full creature with spritesheet, portrait, and stats.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "demon_lord" `
    -AssetType Creature `
    -Preset Demon `
    -HasHorns -HasTail -HasWings `
    -ColorVariants 3 `
    -GeneratePlaceholder
```

**Presets:** Demon, Undead, Beast, Humanoid, Elemental, Construct

**Generated Files:**
- `creature/demon_lord.json` - Asset definition
- `creature/sprites/demon_lord.png` - Spritesheet (placeholder)
- `creature/portraits/demon_lord.png` - Portrait (placeholder)
- `creature/demon_lord_layout.md` - Spritesheet guide

### Portrait

Character face icons for UI.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "hero_portrait" `
    -AssetType Portrait `
    -PortraitSize 64 `
    -ColorVariants 4
```

### Item

Equipment, consumables, and materials.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "iron_sword" `
    -AssetType Item `
    -Preset Weapon `
    -ItemSlot "main_hand" `
    -Stats @{ "damage" = 10; "speed" = 5 }
```

**Presets:** Weapon, Armor, Potion, Book, Gem, Food, Tool

### Ability

Skills and spells.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "heal" `
    -AssetType Ability `
    -Preset Buff `
    -GeneratePlaceholder
```

**Presets:** Attack, Magic, Buff, Debuff, Passive

### Tile

Ground and wall tiles.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "stone_floor" `
    -AssetType Tile `
    -Preset Ground
```

**Presets:** Ground, Wall, Door, Container, Decoration

### Building

Structures with footprints.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "small_house" `
    -AssetType Building `
    -SpriteWidth 64 `
    -SpriteHeight 64
```

### Effect

Animated visual effects.

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "explosion" `
    -AssetType Effect `
    -AnimationFrames 8
```

## Parameters

### Basic Parameters

```powershell
-AssetName         # Required. Asset identifier
-AssetType         # Type of asset (see above)
-Preset            # Built-in preset to use
-OutputDir         # Output directory (default: "SoulashAssets")
-Description       # Asset description
```

### Sprite Parameters

```powershell
-SpriteWidth       # Width in pixels (default: 32)
-SpriteHeight      # Height in pixels (default: 32)
-PortraitSize      # Portrait dimensions (default: 64)
-AnimationFrames   # Number of animation frames (default: 4)
-Directions        # Number of directions (default: 4)
-ColorVariants     # Number of color variants (default: 1)
```

### Creature Parameters

```powershell
-HasTail           # Include tail body part
-HasWings          # Include wings body part
-HasHorns          # Include horns body part
```

### Item Parameters

```powershell
-ItemCategory      # weapon, armor, consumable, material, misc
-ItemSlot          # main_hand, off_hand, head, chest, etc.
-Stats             # Hashtable of stat bonuses
```

### Other

```powershell
-GeneratePlaceholder  # Create placeholder PNG images
```

## Generated JSON Format

### Creature Example

```json
{
  "id": "fire_demon",
  "name": "Fire Demon",
  "type": "creature",
  "description": "A demon creature.",
  "sprite": {
    "path": "sprites/fire_demon.png",
    "width": 32,
    "height": 32,
    "frames": 4,
    "directions": 4,
    "variants": 2
  },
  "portrait": {
    "path": "portraits/fire_demon.png",
    "width": 64,
    "height": 64
  },
  "body_parts": {
    "base": true,
    "head": true,
    "body": true,
    "horns": true,
    "tail": true,
    "wings": false
  },
  "stats": {
    "HP": 100,
    "Strength": 15,
    "Agility": 10,
    "Intelligence": 12
  },
  "category": "demon"
}
```

### Item Example

```json
{
  "id": "health_potion",
  "name": "Health Potion",
  "type": "item",
  "description": "A potion item.",
  "icon": {
    "path": "items/health_potion.png",
    "width": 32,
    "height": 32
  },
  "category": "consumable",
  "stackable": true,
  "max_stack": 10
}
```

## Spritesheet Layout

### Creature Spritesheet

```
Row 0: Idle (frames 0-3)
Row 1: Walk (frames 0-3)
Row 2: Attack (frames 0-3)
Row 3: Death (frames 0-3)
--- (repeat for each direction) ---
Row 4-7: Direction 2
Row 8-11: Direction 3
Row 12-15: Direction 4
--- (body parts if modular) ---
Row 16+: Horns
Row 17+: Tail
Row 18+: Wings
```

### Color Variants

For multiple color variants, add columns:
- Variant 1: Columns 0-3
- Variant 2: Columns 4-7
- etc.

## Integration with MultiAssetGenerator

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Soulash `
    -AssetType Creature `
    -AssetName "my_monster" `
    -Description "demon with horns"
```

## Tips

1. **Start with presets** - They set sensible defaults
2. **Use placeholders** - Test layouts before creating real art
3. **Check layout guides** - Generated .md files show expected format
4. **Modular parts** - Body parts can be mix-and-matched
5. **Color variants** - Use hue shifts for easy variations

## Common Patterns

### Monster with Color Variants

```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "slime" `
    -AssetType Creature `
    -Preset Beast `
    -ColorVariants 5 `
    -Description "Gelatinous creature in various colors"
```

### Equipment Set

```powershell
# Weapon
.\SoulashAssetGenerator.ps1 -AssetName "iron_sword" -AssetType Item -Preset Weapon -ItemSlot "main_hand"

# Armor pieces
.\SoulashAssetGenerator.ps1 -AssetName "iron_helm" -AssetType Item -Preset Armor -ItemSlot "head"
.\SoulashAssetGenerator.ps1 -AssetName "iron_chest" -AssetType Item -Preset Armor -ItemSlot "chest"
.\SoulashAssetGenerator.ps1 -AssetName "iron_boots" -AssetType Item -Preset Armor -ItemSlot "feet"
```

### Skill Tree

```powershell
.\SoulashAssetGenerator.ps1 -AssetName "basic_attack" -AssetType Ability -Preset Attack
.\SoulashAssetGenerator.ps1 -AssetName "fireball" -AssetType Ability -Preset Magic
.\SoulashAssetGenerator.ps1 -AssetName "shield" -AssetType Ability -Preset Buff
```

