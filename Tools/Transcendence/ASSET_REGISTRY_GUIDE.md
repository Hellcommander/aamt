# Unified Asset Registry - Guide

Central registry system for managing and auto-generating assets across multiple games (Elin, Terraria, Starbound, Transcendence).

## Overview

The Unified Asset Registry is a JSON-based system that serves as a single source of truth for all mod assets. It drives automatic asset generation, spritesheet assembly, and game-specific exports.

## Key Features

- **Canonical IDs**: Stable identifiers across all pipelines
- **Visual Identity**: Centralized shape, palette, and style definitions
- **Generation Instructions**: AI/Blender hints for procedural generation
- **Multi-Game Export**: Toggle exports for different games
- **Taxonomy Support**: Perfect for spell school systems
- **Batch Processing**: Generate assets for entire schools or categories

## Quick Start

### Initialize Registry

```powershell
.\AssetRegistry.ps1 -Action Init -RegistryPath "my_mod_registry.json"
```

### Add Entry

```powershell
$entry = @{
    id = "nature_verdant_pulse"
    name = "Verdant Pulse"
    type = "spell"
    school = "Nature Magic"
    description = "A burst of green life energy"
    tags = @("healing", "nature")
    visual = @{
        icon = @{
            shape = "spiral leaf burst"
            palette = @("#4caf50", "#81c784", "#2e7d32")
            style = "painterly"
            size = 32
            contrast = "high"
            glow = $true
        }
        fx = @{
            frames = 4
            motion = "expanding pulse"
            glow = $true
        }
        projectile = @{
            shape = "leaf shard"
            frames = 2
        }
    }
    generation = @{
        complexity = "medium"
        useAI = $false
    }
    export = @{
        elin = $true
        terraria = $true
        starbound = $true
    }
}

.\AssetRegistry.ps1 -Action Add -EntryId "nature_verdant_pulse" -EntryData $entry
```

### List Entries

```powershell
# List all
.\AssetRegistry.ps1 -Action List

# Filter by school
.\AssetRegistry.ps1 -Action List -Filter @{school="Nature Magic"}

# Filter by type
.\AssetRegistry.ps1 -Action List -Filter @{type="spell"}

# Filter by tags
.\AssetRegistry.ps1 -Action List -Filter @{tags=@("healing")}
```

### Generate Assets

```powershell
# Generate all assets
.\AssetRegistry.ps1 -Action Generate -GameFormat All

# Generate for specific school
.\AssetRegistry.ps1 -Action Generate -Filter @{school="Nature Magic"} -GameFormat Elin

# Generate for specific game
.\AssetRegistry.ps1 -Action Generate -GameFormat Terraria
```

## Registry Schema

### Entry Structure

```json
{
  "id": "canonical_id",
  "name": "Human Readable Name",
  "type": "spell|item|projectile|effect|buff|debuff",
  "school": "Spell School or Category",
  "description": "Lore or gameplay description",
  "tags": ["tag1", "tag2"],
  "visual": {
    "icon": { ... },
    "fx": { ... },
    "projectile": { ... },
    "buff": { ... }
  },
  "generation": { ... },
  "export": { ... }
}
```

### Visual Specifications

#### Icon
- **shape**: Description (spiral, burst, leaf, star, etc.)
- **palette**: Array of hex colors (#RRGGBB)
- **style**: painterly, pixel, flat, procedural
- **size**: 16, 24, 32, 48, 64
- **contrast**: low, medium, high
- **lighting**: Description (soft rim light, etc.)
- **glow**: boolean

#### FX
- **frames**: 1-16
- **motion**: expanding, rotating, pulse, etc.
- **glow**: boolean
- **size**: 32, 48, 64, 96, 128
- **palette**: Array of hex colors

#### Projectile
- **shape**: shard, orb, bolt, etc.
- **frames**: 1-8
- **size**: 16, 24, 32, 48
- **palette**: Array of hex colors

#### Buff
- **size**: 16, 24
- **simplified**: boolean

### Generation Block

```json
{
  "generation": {
    "materialModel": "wood|stone|metal or Ollama model name",
    "proceduralHints": "Hints for procedural generation",
    "animationHints": "Hints for animation",
    "complexity": "simple|medium|complex",
    "useAI": true|false
  }
}
```

### Export Block

```json
{
  "export": {
    "elin": true,
    "terraria": true,
    "starbound": true,
    "transcendence": false,
    "custom": ["future_game1", "future_game2"]
  }
}
```

## Workflow Examples

### Spell School Setup

```powershell
# Initialize registry
.\AssetRegistry.ps1 -Action Init -RegistryPath "nature_magic_registry.json"

# Add multiple Nature Magic spells
$spells = @(
    @{id="nature_verdant_pulse"; name="Verdant Pulse"; ...},
    @{id="nature_leaf_shield"; name="Leaf Shield"; ...},
    @{id="nature_vine_whip"; name="Vine Whip"; ...}
)

foreach ($spell in $spells) {
    .\AssetRegistry.ps1 -Action Add -RegistryPath "nature_magic_registry.json" -EntryId $spell.id -EntryData $spell
}
```

### Batch Asset Generation

```powershell
# Generate all Elin assets
.\AssetRegistry.ps1 -Action Generate -RegistryPath "nature_magic_registry.json" -GameFormat Elin

# Generate for specific school
.\AssetRegistry.ps1 -Action Generate -Filter @{school="Nature Magic"} -GameFormat All

# Generate healing spells only
.\AssetRegistry.ps1 -Action Generate -Filter @{tags=@("healing")} -GameFormat Elin
```

### Taxonomy-Driven Generation

```powershell
# Generate assets for all Nature Magic spells
.\AssetRegistry.ps1 -Action Generate -Filter @{school="Nature Magic"} -GameFormat All -OutputDir "NatureMagicAssets"

# Generate assets for all Arachnomancy spells
.\AssetRegistry.ps1 -Action Generate -Filter @{school="Arachnomancy"} -GameFormat All -OutputDir "ArachnomancyAssets"
```

## Integration with Existing Tools

### With ElinSpellAssetGenerator

The registry automatically calls `ElinSpellAssetGenerator.ps1` when generating Elin assets:

```powershell
# Registry entry with export.elin = true automatically generates:
# - icons/spell_name.png
# - fx/spell_name_fx.png
# - projectiles/spell_name_proj.png
# - buffs/spell_name_buff.png
```

### With CrossGameSpritesheet

For Terraria/Starbound exports, the registry can drive spritesheet generation:

```powershell
# Future integration will automatically:
# - Generate textures from registry specs
# - Assemble into game-specific spritesheets
# - Generate metadata files
```

### With AssetMakerAI

Use AI to generate registry entries:

```powershell
# 1. Generate spell name/description with AI
$name = .\AssetMakerAI.ps1 -Action GenerateName -AssetType Effect -InputData "nature healing spell"
$desc = .\AssetMakerAI.ps1 -Action GenerateDescription -AssetType Effect -InputData $name

# 2. Create registry entry
$entry = @{
    name = $name
    description = $desc
    # ... visual specs
}

# 3. Add to registry
.\AssetRegistry.ps1 -Action Add -EntryId "nature_heal" -EntryData $entry
```

## Advanced Usage

### Update Entry

```powershell
$update = @{
    visual = @{
        icon = @{
            palette = @("#newcolor1", "#newcolor2")
        }
    }
}

.\AssetRegistry.ps1 -Action Update -EntryId "nature_verdant_pulse" -EntryData $update
```

### Remove Entry

```powershell
.\AssetRegistry.ps1 -Action Remove -EntryId "nature_verdant_pulse"
```

### Validate Registry

```powershell
.\AssetRegistry.ps1 -Action Validate -RegistryPath "my_registry.json"
```

## Design Principles

- **Single Source of Truth**: All asset definitions in one place
- **Deterministic**: Same registry = same assets
- **Extensible**: Easy to add new games, asset types, or fields
- **Taxonomy-Friendly**: Perfect for spell school systems
- **Pipeline-Driven**: Automatically generates assets from specs

## Future Enhancements

- [ ] JSON Schema validation
- [ ] Import from existing game files
- [ ] Export to game-specific formats
- [ ] Version control integration
- [ ] Diff/merge tools
- [ ] Web UI for registry management
- [ ] Automatic asset updates when registry changes

## References

- JSON Schema: `asset_registry_schema.json`
- Elin Asset Generator: `ElinSpellAssetGenerator.ps1`
- Cross-Game Spritesheet: `CrossGameSpritesheet.ps1`
- Asset Maker AI: `AssetMakerAI.ps1`

