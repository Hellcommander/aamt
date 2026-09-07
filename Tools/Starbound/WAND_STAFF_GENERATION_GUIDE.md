# Runic Wand & Staff Sprite Generation Guide

Generate sprites for all Runic Wands and Staves defined in the mod's configuration files.

## Quick Start

```powershell
# Generate all wand and staff sprites
.\GenerateWandStaffSprites.ps1

# Use C++ backend for better quality
.\GenerateWandStaffSprites.ps1 -UseCppBackend

# Or generate everything including wands/staves
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Wand Types (3+ items)

1. **basic_wand** - Simple wand with basic capabilities
2. **advanced_wand** - More powerful wand with enhanced capabilities
3. **runic_runner** - Fast and efficient runic wand
4. **runic** - Classic runic wand with branching paths
5. **chronomancer** - Time-manipulating wand

### Staff Types (5+ items)

1. **basic_staff** - Simple staff with enhanced range and damage
2. **advanced_staff** - Powerful staff with multiple spellstone slots
3. **elemental_staff** - Staff specialized in elemental magic
4. **battle_staff** - Combat-focused staff with enhanced damage
5. **arcane_staff** - Staff focused on arcane magic and utility
6. **runic_staff** - Staff version of runic wand
7. **chronomancer_staff** - Time-manipulating staff
8. **elementalist_staff** - Enhanced elemental area effects
9. **battlemage_staff** - Devastating area damage staff

## Sprite Characteristics

### By Tier

| Tier | Visual Style |
|------|-------------|
| 1 | Simple design, basic magical glow |
| 2 | Refined design, enhanced runic patterns, stronger glow |
| 3 | Masterwork design, intricate runes, powerful energy aura |

### By Type

| Type | Visual Style |
|------|-------------|
| Wand | One-handed, shorter, compact design |
| Staff | Two-handed, longer, ornate design |

### By Element

| Element | Visual Style |
|---------|-------------|
| Fire | Red/orange colors, flickering flames |
| Ice | Blue/white colors, frost patterns |
| Lightning | Yellow/white colors, electrical arcs |
| Elemental | Rainbow colors, swirling energy |
| Arcane | Purple colors, swirling magical energy |
| Temporal | Clockwork patterns, time distortion effects |

## Output Structure

```
assets/
└── items/
    └── sprites/
        ├── basic_wand.png
        ├── basic_wand.frames
        ├── advanced_wand.png
        ├── advanced_wand.frames
        ├── basic_staff.png
        ├── basic_staff.frames
        └── ... (all other wands and staves)
```

## Configuration Files

The generator reads from:
- `cpp_backend/config/wandTemplates.json` - Wand templates
- `cpp_backend/config/staffTemplates.json` - Staff templates
- `cpp_backend/config/magitechWandTypes.json` - Magitech wand/staff types

## Integration

### Creating Item Definitions

After generating sprites, create `.item` files for each wand/staff:

```json
{
  "itemName": "basic_wand",
  "shortdescription": "Basic Wand",
  "description": "A simple wand with basic capabilities",
  "category": "weapon",
  "rarity": "Common",
  "twoHanded": false,
  "inventoryIcon": "basic_wand.png",
  "weapon": {
    "fireTime": 0.5,
    "projectileType": "spell_projectile"
  }
}
```

### For Staves

```json
{
  "itemName": "basic_staff",
  "shortdescription": "Basic Staff",
  "description": "A simple staff with enhanced range and damage",
  "category": "weapon",
  "rarity": "Common",
  "twoHanded": true,
  "inventoryIcon": "basic_staff.png",
  "weapon": {
    "fireTime": 0.7,
    "projectileType": "spell_projectile"
  }
}
```

## Workflow

### Step 1: Generate Sprites

```powershell
.\GenerateWandStaffSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Create Item Definitions

Create `.item` files in `items/weapons/wands/` and `items/weapons/staves/` directories.

### Step 3: Create Animations (Optional)

For animated wands/staves, create animation files:

```json
{
  "animatedParts": {
    "parts": {
      "wand": {
        "properties": {
          "image": "/items/weapons/wands/basic_wand.png"
        }
      }
    }
  }
}
```

### Step 4: Test in Game

Load the mod and verify wands/staves appear correctly.

## Advanced Options

### Custom Prompts

Edit `GenerateWandStaffSprites.ps1` to customize prompts for specific wands/staves.

### Tier-Based Generation

The generator automatically adjusts visual style based on tier:
- Tier 1: Simple, basic
- Tier 2: Refined, enhanced
- Tier 3: Masterwork, legendary

### Elemental Themes

Elemental staves get element-specific visual cues:
- Fire: Flames, red/orange
- Ice: Frost, blue/white
- Lightning: Arcs, yellow/white
- Arcane: Swirling energy, purple
- Temporal: Clockwork, time effects

## Tips

1. **Match descriptions**: Prompts are based on template descriptions
2. **Use tier information**: Higher tiers get more ornate designs
3. **Elemental themes**: Elemental staves get appropriate color schemes
4. **Two-handed design**: Staves are longer and more ornate than wands
5. **Runic patterns**: All wands/staves should have runic patterns

## Troubleshooting

### Sprites Not Generating

- Check configuration files exist
- Verify Ollama is running
- Check model is installed

### Poor Quality

- Use `-UseCppBackend` for better quality
- Provide more detailed descriptions in templates
- Generate multiple variations

### Missing Templates

- Ensure configuration files are in correct location
- Check JSON syntax is valid
- Verify template IDs are unique

---

*Part of the Starbound Ollama Asset Generator suite*
