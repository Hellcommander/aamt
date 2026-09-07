# Mod Sprite Generation Guide

Automatically generate sprites for all spellstones and unique items in the Magi-Tech mod.

## Quick Start

```powershell
# Generate all spellstone and item sprites
.\GenerateModSprites.ps1

# Use C++ backend for better quality
.\GenerateModSprites.ps1 -UseCppBackend

# Use specific Ollama model
.\GenerateModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Spellstone Cores
- **spellstone_core_common** - Arcane Core (Common)
- **spellstone_core_refined** - Refined Core (Rare)
- **spellstone_core_arcane** - Arcane Core (Epic)
- **spellstone_core_apex** - Apex Core (Legendary)

### Elemental Spellstones
- **spellstone_fire** - Fire Spellstone
- **spellstone_ice** - Frost Spellstone
- **spellstone_lightning** - Storm Spellstone
- **spellstone_nature** - Nature Spellstone
- **spellstone_arcane** - Arcane Spellstone
- **spellstone_void** - Void Spellstone
- **spellstone_cosmic** - Cosmic Spellstone
- **spellstone_temporal** - Temporal Spellstone

### Unique Items
- **alchemical_grenade_launcher** - Alchemical Grenade Launcher

## Output Structure

Generated sprites are saved to:
```
mods/Magi-Tech Arcane Alchemy and Sorcery/assets/items/sprites/
├── spellstone_core_common.png
├── spellstone_core_common.frames
├── spellstone_core_refined.png
├── spellstone_core_refined.frames
├── spellstone_fire.png
├── spellstone_fire.frames
└── ... (all other spellstones)
```

## Sprite Characteristics

### By Rarity

**Common Spellstones:**
- Simple translucent crystal
- Basic magical glow
- 32x32 pixels

**Rare Spellstones:**
- Faceted crystal with enhanced glow
- Refined appearance
- 32x32 pixels

**Epic Spellstones:**
- Pulsating crystal with animated runes
- Powerful arcane energy
- 64x64 pixels

**Legendary Spellstones:**
- Radiant crystal with rotating inner shards
- Pure magical power
- 64x64 pixels

### By Element

- **Fire**: Red/orange colors, flickering flames
- **Ice**: Blue/white colors, frost patterns
- **Lightning**: Yellow/white colors, electrical arcs
- **Nature**: Green colors, vine patterns
- **Arcane**: Purple colors, swirling energy
- **Void**: Black/dark colors, smoky trails
- **Cosmic**: Star-like particles, galaxy colors
- **Temporal**: Clockwork patterns, time effects

## Integration

After generation, update item JSON files to reference new sprites:

```json
{
  "asset": {
    "primary": "/items/sprites/spellstone_fire.png",
    "source": "magi_tech_custom",
    "license": "MIT"
  }
}
```

## Batch Processing

The script processes all items sequentially. For large batches:

1. **Run in background**: Use `Start-Job` for parallel processing
2. **Generate in stages**: Run for specific item types
3. **Use C++ backend**: Better quality but slower

## Customization

### Add More Items

Edit `GenerateModSprites.ps1` and add to `$uniqueItems` array:

```powershell
$uniqueItems = @(
    @{
        Id = "my_custom_item"
        Name = "My Custom Item"
        Description = "Description here"
        Prompt = "detailed prompt for sprite generation"
    }
)
```

### Modify Prompts

The script automatically creates prompts based on:
- Item description
- Rarity level
- Elemental affinity (for spellstones)

You can customize the prompt generation logic in the script.

## Troubleshooting

### Sprites Not Generating

- Check Ollama is running: `ollama serve`
- Verify model is installed: `ollama list`
- Check output directory permissions

### Poor Quality

- Use `-UseCppBackend` flag
- Provide more detailed prompts
- Generate multiple variations

### Missing Items

- Verify spellstone_items.json exists
- Check JSON structure is correct
- Ensure item definitions are valid

## Performance

- **Generation time**: ~20-30 seconds per sprite (with Ollama)
- **Total time**: ~5-10 minutes for all spellstones
- **With C++ backend**: Slower but higher quality

## Next Steps

After generating sprites:

1. **Review generated sprites** in `assets/items/sprites/`
2. **Update item JSON files** to reference new sprites
3. **Test in-game** to verify appearance
4. **Regenerate** if needed with adjusted prompts

---

*Part of the Starbound Ollama Asset Generator suite*
