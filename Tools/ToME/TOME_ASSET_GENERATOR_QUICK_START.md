# ToME Asset Generator - Quick Start Guide

## Installation

```bash
pip install Pillow
```

## Basic Usage

### 1. Generate a Single Spell

```bash
python tomegen_cli.py generate \
  --template spell \
  --shapes ring,ink_bleed \
  --seed 12345 \
  --out ./mods/my_spell_mod
```

### 2. View Preview

Open `mods/my_spell_mod/preview/preview.html` in your browser.

### 3. Install Mod

Copy `mods/my_spell_mod` to ToME's `mods/` directory.

## Common Templates

- **Spell**: `--template spell`
- **Actor**: `--template actor`
- **Item**: `--template item`
- **VFX**: `--template vfx`

## Common Shapes

- **Ring** (area effect): `--shapes ring`
- **Bolt** (single target): `--shapes bolt`
- **Nova** (large area): `--shapes nova`
- **Ink Bleed** (DoT): `--shapes ink_bleed`
- **Multiple**: `--shapes ring,ink_bleed`

## Batch Generation

Create `assets.csv`:
```csv
template,shapes,seed,variant
spell,ring,12345,fire
spell,bolt,12346,ice
actor,,12347,
```

Run:
```bash
python tomegen_cli.py batch --csv assets.csv --out ./mods/batch_mod
```

## Output Structure

```
mods/my_spell_mod/
  data/
    gfx/sprites/     # PNG spritesheets + .meta.json
    lua/talents/      # Talent Lua stubs
    lua/entities/     # Entity Lua stubs
    lua/items/        # Item Lua stubs
    locale/en/        # Localization files
  manifest.json       # Mod manifest
  preview/            # Preview assets
```

## Tips

1. **Deterministic**: Same seed = same output
2. **Balance Scores**: Check `manifest.json` for balance scores (0.1-0.9 is normal)
3. **Validation**: Warnings appear in console for outliers
4. **Safe Lua**: All generated Lua is validated and safe

## Troubleshooting

**No sprites generated?**
- Install Pillow: `pip install Pillow`

**Lua errors?**
- Check ToME mod folder structure
- Verify `loadPrevious(...)` is present

**Balance scores extreme?**
- Adjust seed or shapes
- Check validation warnings

## Next Steps

- Read `TOME_ASSET_GENERATOR_README.md` for full documentation
- Check `example_tomegen_usage.py` for programmatic API
- Review generated Lua stubs and customize as needed

