# Elin Spell Asset Generator - Guide

Complete spell asset generation system for the game Elin, integrated with your AI and procedural texture pipeline.

## Overview

Generates Elin-compatible spell assets including:
- **Spell Icons** (32×32) - UI icons for menus, hotbars, spellbooks
- **Spell Effects/FX** (32×32 or 64×64, multi-frame) - Cast animations, AoE effects
- **Spell Projectiles** (32×32, 1-4 frames) - Projectile animations
- **Buff/Debuff Icons** (16×16) - Simplified status effect icons

## Elin Asset Requirements

- **Tile Grid**: 32×32 pixels (16×16 for buffs)
- **Style**: Painterly, high-contrast, soft edges, readable at 1× scale
- **Palette**: Limited colors per icon (typically 2-4)
- **Animation**: Horizontal strips for multi-frame effects
- **Format**: PNG with transparency

## Quick Start

### Generate All Asset Types

```powershell
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse: a burst of green life energy" -GenerateAll
```

### Generate Specific Asset Types

```powershell
# Icon and FX only
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Fireball spell" -GenerateIcon -GenerateFX -FXFrames 6

# Projectile with 4 frames
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Ice shard projectile" -GenerateProjectile -ProjectileFrames 4
```

### Using AI-Generated Specifications

```powershell
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Arachnomancy - Venom Web" -GenerateAll -UseAI -OllamaModel "wizardlm-uncensored:latest"
```

## Parameters

- **`-SpellDescription`** (Required) - Description of the spell
- **`-SpellName`** - Custom spell name (auto-generated if not provided)
- **`-OutputDir`** - Output directory (default: `ElinAssets`)
- **`-GenerateIcon`** - Generate 32×32 spell icon
- **`-GenerateFX`** - Generate spell effect animation
- **`-GenerateProjectile`** - Generate projectile frames
- **`-GenerateBuff`** - Generate 16×16 buff icon
- **`-GenerateAll`** - Generate all asset types
- **`-FXFrames`** - Number of FX frames (default: 4)
- **`-ProjectileFrames`** - Number of projectile frames (default: 2)
- **`-UseAI`** - Use Ollama to generate asset specifications
- **`-OllamaModel`** - Ollama model to use (default: auto-detected)

## Output Structure

```
ElinAssets/
├── icons/
│   └── spell_name.png          (32×32)
├── fx/
│   └── spell_name_fx.png       (32×32 × N frames, horizontal strip)
├── projectiles/
│   └── spell_name_proj.png     (32×32 × N frames, horizontal strip)
└── buffs/
    └── spell_name_buff.png     (16×16)
```

## Spell Taxonomy Integration

Perfect for your spell school system:

```powershell
# Nature Magic spells
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Leaf Shield" -GenerateAll
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Vine Whip" -GenerateAll
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Root Bind" -GenerateAll

# Arachnomancy spells
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Arachnomancy - Venom Strike" -GenerateAll
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Arachnomancy - Web Trap" -GenerateAll
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Arachnomancy - Spider Swarm" -GenerateAll
```

## Batch Processing

### Process Multiple Spells

```powershell
$spells = @(
    "Nature Magic - Verdant Pulse: a burst of green life energy",
    "Nature Magic - Leaf Shield: protective barrier of leaves",
    "Nature Magic - Vine Whip: attacking vine",
    "Arachnomancy - Venom Web: toxic web trap",
    "Arachnomancy - Spider Bite: single-target poison"
)

foreach ($spell in $spells) {
    .\ElinSpellAssetGenerator.ps1 -SpellDescription $spell -GenerateAll -OutputDir "ElinAssets"
}
```

### From File

```powershell
# spells.txt contains one description per line
$spells = Get-Content "spells.txt"

foreach ($spell in $spells) {
    if (-not [string]::IsNullOrWhiteSpace($spell)) {
        .\ElinSpellAssetGenerator.ps1 -SpellDescription $spell -GenerateAll
    }
}
```

## Integration with Existing Pipeline

### With Texture Generation

```powershell
# 1. Generate base textures
.\BatchBakeTextures.ps1 -MaterialList @("nature", "venom", "web") -OutputDir "Textures"

# 2. Generate spell assets (can reference textures or generate procedurally)
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic spell" -GenerateAll
```

### With AssetMakerAI

```powershell
# Generate spell name and description first
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Effect -InputData "healing nature spell"

# Then generate assets
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - [generated name]" -GenerateAll
```

## Asset Specifications

### Icon Generation

- **Size**: 32×32 pixels
- **Style**: High-contrast, painterly, soft edges
- **Shapes**: Spiral, burst, leaf, star/pentagram, custom
- **Colors**: 2-4 colors from specification
- **Effects**: Optional glow, rim lighting

### FX Generation

- **Size**: 32×32 or 64×64 (configurable)
- **Frames**: 2-6 frames (default: 4)
- **Layout**: Horizontal strip
- **Motion Types**: Expanding pulse, rotating, burst
- **Effects**: Glow, fade-out

### Projectile Generation

- **Size**: 32×32 pixels
- **Frames**: 1-4 frames (default: 2)
- **Layout**: Horizontal strip
- **Shapes**: Crystal shard, energy orb, custom
- **Effects**: Motion blur for animation

### Buff Icon Generation

- **Size**: 16×16 pixels
- **Style**: Simplified version of main icon
- **Enhancement**: Increased contrast for readability
- **Source**: Can be generated from base icon or independently

## AI Specification Format

When using `-UseAI`, the system generates JSON specifications:

```json
{
  "spellName": "Verdant Pulse",
  "icon": {
    "shape": "spiral leaf burst",
    "colors": ["#4caf50", "#81c784", "#2e7d32"],
    "contrast": "high",
    "lighting": "soft rim light"
  },
  "fx": {
    "frames": 4,
    "motion": "expanding pulse",
    "colors": ["#66bb6a", "#a5d6a7"],
    "glow": true,
    "size": 32
  },
  "projectile": {
    "shape": "leaf shard",
    "frames": 2,
    "colors": ["#4caf50", "#81c784"]
  },
  "buff": {
    "colors": ["#4caf50", "#81c784"],
    "simplified": true
  }
}
```

## Workflow Examples

### Rapid Prototyping

```powershell
# Generate placeholder assets for 20 spells in minutes
$spellSchools = @("Nature Magic", "Arachnomancy", "Fire Magic", "Ice Magic")
$spellTypes = @("Bolt", "Shield", "Heal", "Trap", "AoE")

foreach ($school in $spellSchools) {
    foreach ($type in $spellTypes) {
        $desc = "$school - $type spell"
        .\ElinSpellAssetGenerator.ps1 -SpellDescription $desc -GenerateAll -OutputDir "ElinAssets\$school"
    }
}
```

### Spell School Identity

```powershell
# Nature Magic: Green palette, organic shapes
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - [spell]" -GenerateAll

# Arachnomancy: Dark purple/black, web patterns
.\ElinSpellAssetGenerator.ps1 -SpellDescription "Arachnomancy - [spell]" -GenerateAll
```

## Design Principles

- **Placeholder-First**: Generate usable assets quickly
- **Taxonomy-Aligned**: Supports spell school system
- **Deterministic**: Same description = same assets
- **Modular**: Generate only what you need
- **Game-Ready**: Outputs match Elin's requirements exactly

## Troubleshooting

### Python/Pillow Not Found
- Install Python 3.x
- Install Pillow: `python -m pip install Pillow`
- Or use the auto-install feature in CrossGameSpritesheet.ps1

### Assets Too Simple
- Use `-UseAI` for more sophisticated specifications
- Adjust colors and shapes in the Python script
- Extend procedural generation functions

### Animation Issues
- Verify frame count matches game expectations
- Check horizontal strip layout
- Ensure frame timing matches game's animation system

## Future Enhancements

- [ ] Blender integration for 3D-rendered icons
- [ ] Custom shape libraries per spell school
- [ ] Animation timing configuration
- [ ] Batch processing from spell database
- [ ] Integration with spell XML generation
- [ ] Preview generation for asset review

## References

- Elin game modding documentation
- Spell asset style guide
- Animation frame requirements

