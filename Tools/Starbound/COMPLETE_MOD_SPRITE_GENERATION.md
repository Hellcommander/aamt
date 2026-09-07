# Complete Mod Sprite Generation Guide

Generate sprites for **ALL** mod content using Ollama AI: spellstones, ingredients, reagents, weapons, projectiles, objects, and monsters.

## Quick Start

```powershell
# Generate sprites for everything
.\GenerateAllModSprites.ps1

# Skip existing sprites (faster for re-runs)
.\GenerateAllModSprites.ps1 -SkipExisting

# Use C++ backend for better quality
.\GenerateAllModSprites.ps1 -UseCppBackend

# Update JSON files to reference new sprites
.\UpdateItemSprites.ps1
```

## What Gets Generated

### 1. Spellstones (12 items)
- **Base Cores**: common, refined, arcane, apex
- **Elemental Variants**: fire, ice, lightning, nature, arcane, void, cosmic, temporal

### 2. Spell Ingredients (~50+ items)

**Basic Elements** (9 items):
- fire_ruby, ice_crystal, lightning_core, earth_core, water_pearl, air_wisp, shadow_wisp, light_prism, nature_seed, cosmic_dust

**Crystals** (5 items):
- mana_crystal, focus_crystal, resonance_crystal, prismatic_crystal, chaos_crystal

**Catalysts** (5 items):
- stability_catalyst, power_amplifier, resonance_tuner, mana_conductor, elemental_focus

**Rare Components** (~10 items):
- salamander_scale, frost_essence, and more...

**Exotic Materials** (~5 items):
- phoenix_feather, dimensional_anchor, and more...

### 3. Reagent Items (6 items)
- reagent_fireessence
- reagent_icecrystal
- reagent_oilpowder
- reagent_poisoncloud
- reagent_catalyst
- reagent_vial

### 4. Unique Weapons
- alchemical_grenade_launcher

### 5. Projectiles (3 items)
- chemicalgrenade
- magitech_bolt
- magitech_burst

### 6. Objects (2 items)
- deviceworkbench
- magitechspellcraftingstation

### 7. Animation Spritesheets (5+ items)
- magitech_device (6 frames, device activation)
- spell_cast (8 frames, spell casting)
- magic_aura (4 frames, status effect)
- alchemical_reaction (10 frames, chemical mixing)
- portal_opening (12 frames, portal formation)

## Total: ~85+ Unique Sprites + Animation Spritesheets

## Generation Process

For each item, the generator:

1. **Extracts metadata** from JSON/item files
2. **Creates AI prompt** based on:
   - Item description
   - Rarity level (common → legendary)
   - Element type (fire, ice, etc.)
   - Category (crystal, organic, catalyst, etc.)
3. **Generates sprite** using Ollama + procedural/C++ backend
4. **Creates .frames file** for Starbound compatibility

## Sprite Characteristics

### By Rarity

| Rarity | Visual Style |
|--------|-------------|
| Common | Simple appearance, basic magical glow |
| Uncommon | Refined appearance, enhanced glow |
| Rare | Faceted crystal with animated runes, powerful energy |
| Epic | Pulsating crystal with swirling energy, epic appearance |
| Legendary | Radiant crystal with rotating inner shards, legendary power |

### By Category

| Category | Visual Style |
|----------|-------------|
| Crystal | Crystalline structure, gem-like appearance |
| Organic | Organic material, living essence |
| Elemental | Pure elemental energy, glowing core |
| Catalyst | Manufactured catalyst, synthetic compound |
| Exotic | Exotic otherworldly material, unique appearance |

### By Element

- **Fire**: Red/orange colors, flickering flames
- **Ice**: Blue/white colors, frost patterns
- **Lightning**: Yellow/white colors, electrical arcs
- **Nature**: Green colors, vine patterns
- **Arcane**: Purple colors, swirling energy
- **Void**: Black/dark colors, smoky trails
- **Cosmic**: Star-like particles, galaxy colors
- **Temporal**: Clockwork patterns, time effects

## Output Structure

```
assets/
├── items/
│   └── sprites/
│       ├── spellstone_core_common.png
│       ├── spellstone_core_common.frames
│       ├── fire_ruby.png
│       ├── fire_ruby.frames
│       ├── reagent_fireessence.png
│       ├── reagent_fireessence.frames
│       └── ... (all other sprites)
├── animations/
│   ├── magitech_device/
│   │   ├── magitech_device.png
│   │   ├── magitech_device.animation
│   │   └── magitech_device.frames
│   ├── spell_cast/
│   │   ├── spell_cast.png
│   │   ├── spell_cast.animation
│   │   └── spell_cast.frames
│   └── ... (all other animations)
```

## Workflow

### Step 1: Generate All Sprites

```powershell
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

This will:
- Process all spellstones
- Process all spell ingredients
- Process all reagent items
- Process all unique weapons
- Process all projectiles
- Process all objects
- Process all animation spritesheets

**Time**: ~25-35 minutes for all items (depending on Ollama speed)

### Step 1b: Generate Animation Spritesheets (Optional)

```powershell
.\GenerateAnimationSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

Generate animation spritesheets separately if needed.

### Step 2: Update JSON References

```powershell
.\UpdateItemSprites.ps1
```

This automatically updates:
- `spellstone_items.json` - All spellstone asset references
- `basic_elements.json` - All ingredient icon paths
- `crystals.json` - All crystal icon paths
- `catalysts.json` - All catalyst icon paths
- `rare_components.json` - All rare component icon paths
- `exotic_materials.json` - All exotic material icon paths
- Reagent `.item` files - All inventoryIcon references
- Weapon JSON files - All weapon asset references

### Step 3: Test in Game

Load the mod in Starbound and verify sprites appear correctly.

## Advanced Options

### Skip Existing Sprites

```powershell
.\GenerateAllModSprites.ps1 -SkipExisting
```

Only generates sprites that don't already exist. Useful for:
- Adding new items without regenerating everything
- Fixing failed generations
- Updating specific items

### Use C++ Backend

```powershell
.\GenerateAllModSprites.ps1 -UseCppBackend
```

Uses the C++ backend for higher quality sprites (slower but better).

### Custom Model

```powershell
.\GenerateAllModSprites.ps1 -OllamaModel "llama3.1"
```

Use a different Ollama model for generation.

## Batch Processing Tips

### Generate in Stages

```powershell
# Stage 1: Spellstones only
.\GenerateModSprites.ps1

# Stage 2: Ingredients
# (Modify GenerateAllModSprites.ps1 to only process ingredients)

# Stage 3: Everything else
.\GenerateAllModSprites.ps1 -SkipExisting
```

### Parallel Processing

For faster generation, you can run multiple instances targeting different categories (requires script modification).

## Troubleshooting

### Some Sprites Failed

- Check Ollama is running
- Verify model is installed
- Check output directory permissions
- Re-run with `-SkipExisting` to only generate failed ones

### Poor Quality Sprites

- Use `-UseCppBackend` for better quality
- Provide more detailed descriptions in source JSON
- Generate multiple variations and select best

### JSON Not Updated

- Run `UpdateItemSprites.ps1` after generation
- Check file paths are correct
- Verify JSON structure matches expected format

## Integration Checklist

- [ ] Generate all sprites with `GenerateAllModSprites.ps1`
- [ ] Update JSON references with `UpdateItemSprites.ps1`
- [ ] Test sprites in-game
- [ ] Verify all items display correctly
- [ ] Check inventory icons work
- [ ] Verify tooltips show sprites
- [ ] Test crafting stations display correctly

## File Locations

**Generated Sprites**:
```
mods/Magi-Tech Arcane Alchemy and Sorcery/assets/items/sprites/
```

**Updated JSON Files**:
```
mods/Magi-Tech Arcane Alchemy and Sorcery/
├── items/spellstones/spellstone_items.json
├── spellIngredients/*.json
├── items/consumable/reagents/*.item
└── items/weapons/*/*.json
```

## Next Steps

After generating all sprites:

1. **Review** generated sprites in `assets/items/sprites/`
2. **Update** any items that need better prompts
3. **Regenerate** specific items if needed
4. **Test** in-game to verify appearance
5. **Commit** to version control

---

*Complete sprite generation system for Magi-Tech Arcane Alchemy and Sorcery mod*
