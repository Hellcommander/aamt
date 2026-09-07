# Glutton Remade Asset Generation Guide

## Overview

The ToME Asset Generator GUI now supports generating assets for the **Glutton Remade** mod, in addition to the Smog Devil Class mod.

## Quick Start

1. **Launch the GUI:**
   ```bash
   python tome_asset_generator_gui.py
   ```

2. **Select the Mod:**
   - Use the "Mod" dropdown at the top
   - Select `glutton-remade` for Glutton Remade
   - Select `smog-devil-class` for Smog Devil Class

3. **Configure Settings:**
   - Mod path and output path are auto-filled based on selection
   - Set variations per asset (default: 20)
   - Enable/disable AI enhancement

4. **Select Assets:**
   - **Main Assets tab**: Select weapon/effect assets (optional for Glutton)
   - **Talent Icons tab**: Select which talents to generate icons for
   - Use "Select All Talents" to quickly select all 193 talents

5. **Generate:**
   - Click "Generate Assets"
   - Watch progress bars and log output
   - Best variations are automatically selected and copied to mod directory

## Glutton Remade Talents

The mod has **193 talents** across multiple categories:

- **Amalgam Core** (4 talents): Core resource system
- **Corpse Larder** (7 talents): Corpse management
- **Digestion** (5 talents): Devour and digest mechanics
- **Gluttony** (16 talents): Core glutton abilities
- **Corruptions** (100+ talents): Corrupted versions of various talents
  - Boss abilities, celestial, debuffs, healing
  - NPC spells, techniques, psionic
  - Spell types (arcane, fire, ice, lightning)
  - Techniques (melee, ranged)
  - Wildgift, summoning, utility
- **Escort Powers** (16 talents): Unique escort abilities
- **And more...**

## Talent Icon Generation

Talent icons are automatically themed based on talent names:

- **Acid/Bile**: Acid-themed icons
- **Digest/Consume/Devour/Maw**: Dark-themed icons
- **Corrupt/Void/Horror**: Dark-themed icons
- **Lightning/Thunder**: Lightning-themed icons
- **Fire/Flame/Inferno**: Fire-themed icons
- **Ice/Frost/Cold**: Ice-themed icons
- **Heal/Regeneration**: Healing-themed icons
- **Summon/Tentacle**: Dark-themed icons
- **Default**: Dark-themed icons

## File Locations

Generated assets are placed in:
- **Talent Icons**: `mod/data/gfx/talents/`
- **Main Assets**: `mod/data/gfx/objects/` or `mod/data/gfx/effects/`

Icons use ToME naming convention: `{talent_id_lowercase}.png`
- Example: `GLUTTON_DEVOUR` → `glutton_devour.png`

## Asset Cleanup

When "Remove old/lower quality assets" is enabled:
- Only the best variation (highest balance score) is kept
- Old talent icons matching generated talent IDs are removed
- This ensures clean, high-quality assets

## Notes

- The Glutton Remade mod uses `short_name` for talent IDs (e.g., `GLUTTON_DEVOUR`)
- All 193 talents are extracted and available for icon generation
- Main assets (weapons/effects) are optional - you can uncheck them if not needed
- AI enhancement provides better color palettes and descriptions

## Troubleshooting

**Talent list not found:**
- Run `extract_glutton_talents.py` to extract talents from the mod
- Ensure the mod path is correct

**Icons not appearing in game:**
- Check that icons are in `mod/data/gfx/talents/`
- Verify talent IDs match exactly (case-sensitive in Lua, lowercase for filenames)
- Ensure mod is properly loaded in ToME

**Generation takes too long:**
- Reduce variations per asset (try 10 instead of 20)
- Disable AI enhancement for faster generation
- Generate talents in smaller batches

