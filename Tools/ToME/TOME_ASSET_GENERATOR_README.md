# ToME Asset Generator

A deterministic, mod-friendly asset generator for **Tales of Maj'Eyal (T-Engine4)** that produces ready-to-drop mod packages.

## Overview

The ToME Asset Generator creates complete mod packages including:
- **Animated spritesheets** (PNG) with metadata (.meta.json)
- **Lua stubs** for talents, items, and entities
- **VFX/particle metadata** for visual effects
- **Localization files** (locale/en/*.lua)
- **Manifest.json** with balance scoring and export hashes
- **Preview assets** (PNG + HTML viewer)

## Installation

### Requirements

- Python 3.7+
- Pillow (PIL) for sprite generation:
  ```bash
  pip install Pillow
  ```

### Setup

1. Place `tome_asset_generator.py` and `tomegen_cli.py` in your tools directory
2. Make scripts executable (Linux/Mac):
   ```bash
   chmod +x tomegen_cli.py
   ```

## Quick Start

### Generate a Single Asset

```bash
python tomegen_cli.py generate \
  --template spell \
  --shapes ring,ink_bleed \
  --seed 12345 \
  --out ./mods/tomegen_mod
```

### Preview Generated Assets

```bash
python tomegen_cli.py preview \
  --manifest mods/tomegen_mod/manifest.json
```

### Batch Generation from CSV

Create a CSV file (`seeds.csv`):
```csv
template,shapes,seed,variant
spell,ring,12345,
spell,bolt,12346,
actor,,12347,
item,,12348,
```

Then run:
```bash
python tomegen_cli.py batch \
  --csv seeds.csv \
  --out ./mods/batch_mod
```

## Command Reference

### `generate` - Generate Single Asset

Generate one asset with specified template, shapes, and seed.

**Options:**
- `--template` (required): Asset template (`spell`, `actor`, `item`, `vfx`, `projectile`)
- `--shapes` (optional): Comma-separated shape modules (`ring`, `ink_bleed`, `bolt`, `nova`, `beam`, etc.)
- `--seed` (required): Integer seed for deterministic generation
- `--variant` (optional): Variant identifier string
- `--out` (default: `./mods/tomegen_mod`): Output directory
- `--mod-name` (default: `tomegen_mod`): Mod name

**Example:**
```bash
python tomegen_cli.py generate \
  --template spell \
  --shapes ring,ink_bleed \
  --seed 12345 \
  --variant fire \
  --out ./mods/my_mod
```

### `preview` - Preview Assets

View generated assets from a manifest file.

**Options:**
- `--manifest` (required): Path to manifest.json

**Example:**
```bash
python tomegen_cli.py preview --manifest mods/tomegen_mod/manifest.json
```

### `batch` - Batch Generation

Generate multiple assets from a CSV file.

**CSV Format:**
- Columns: `template`, `shapes`, `seed`, `variant`
- `shapes` and `variant` are optional
- One asset per row

**Options:**
- `--csv` (required): Path to CSV file
- `--out` (default: `./mods/batch_mod`): Output directory
- `--mod-name` (default: `batch_mod`): Mod name

**Example:**
```bash
python tomegen_cli.py batch \
  --csv assets.csv \
  --out ./mods/my_batch_mod
```

## Asset Types

### Templates

- **`spell`**: Spell/talent effects with damage, range, cooldown, mana
- **`actor`**: Animated character/NPC sprites
- **`item`**: Static item sprites
- **`vfx`**: Visual effects and particles
- **`projectile`**: Projectile sprites

### Shape Modules

Shape modules modify base template parameters:

- **`ring`**: Area effect (increases radius, reduces damage)
- **`ink_bleed`**: Damage over time (adds duration, reduces damage)
- **`bolt`**: Single target (increases range, increases damage)
- **`nova`**: Large area effect (increases radius significantly)
- **`beam`**: Long-range beam (increases range)
- **`wall`**: Linear effect
- **`cloud`**: Lingering area effect
- **`sphere`**: 3D sphere effect
- **`cube`**: Cubic area effect
- **`spiral`**: Spiral pattern

## Output Structure

Generated mods follow ToME's standard mod structure:

```
mods/tomegen_mod/
  data/
    gfx/
      sprites/
        gen_spell_12345.png
        gen_spell_12345.meta.json
        icon_gen_spell_12345_64.png
    lua/
      talents/
        gen_spell_12345.lua
      entities/
        gen_actor_12347.lua
      items/
        gen_item_12348.lua
    locale/
      en/
        gen_spell_12345.lua
  manifest.json
  preview/
    gen_spell_12345_preview.png
    preview.html
```

## Spritesheet Metadata

Each sprite includes a `.meta.json` file:

```json
{
  "frame_width": 64,
  "frame_height": 64,
  "frames": 8,
  "fps": 12,
  "anchor_x": 32,
  "anchor_y": 48,
  "loop": true
}
```

## Lua Stub Safety

All generated Lua stubs are **safe** and follow ToME conventions:

- Use `loadPrevious(...)` for mod compatibility
- Only call preapproved engine functions
- No arbitrary code execution
- Sanitized names and parameters
- Validated numeric values

**Example Talent Stub:**
```lua
local _M = loadPrevious(...)

newTalent{
  name = "Gen: Hollow Star Bolt",
  short_name = "GEN_HOLLOW_BOLT",
  type = {"spell/arcane", 1},
  points = 5,
  cooldown = 10,
  mana = 18,
  tactical = { ATTACK = 2 },
  action = function(self, t)
    -- Safe, validated action
    local proj = game.zone:makeEntityByName(game.level, "projectile", "GEN_HOLLOW_BOLT_proj")
    if proj then
      proj.x, proj.y = self.x, self.y
      game:playSoundNear(self, "talents/spell_generic")
      game.zone:addEntity(game.level, proj)
    end
    return true
  end,
  info = function(self, t)
    return ([[Generated spell talent. Damage: 45.0, Range: 6]])
  end,
}
```

## Balance Scoring

Each generated asset includes a balance score calculated from:
- **Damage**: Normalized damage value (0-1)
- **Area**: Area of effect (0-1)
- **Duration**: Effect duration (0-1)
- **Control**: Control effects (0-1)
- **Cost**: Resource cost (mana + cooldown) (0-1)

**Total Score**: Weighted average (0-1)
- Assets with scores outside 0.1-0.9 are flagged as warnings

## Validation & Safety

The generator includes built-in validation:

### Engine Limits (Hard Caps)
- Max frames: 32
- Max sprite size: 256px
- Max damage: 1000 (warning threshold)
- Max radius: 10 (warning threshold)
- Max duration: 20 (warning threshold)

### Safety Rules
- No arbitrary Lua code
- Sanitized filenames and identifiers
- Validated numeric parameters
- Balance score warnings for outliers

### Preview Gating
Assets flagged as outliers (balance score < 0.1 or > 0.9) require manual review.

## Determinism

The generator is **fully deterministic**:
- Same template + shapes + seed = identical output
- Reproducible across runs
- Shareable seeds for collaboration

## Testing Checklist

Before shipping a mod:

- [ ] **Determinism**: Same seed produces identical files
- [ ] **Engine Load**: Mod loads in ToME without errors
- [ ] **Talent Lists**: Talents appear in talent lists
- [ ] **Sprite Alignment**: Frames align with anchor points
- [ ] **Animation FPS**: Animations play at intended speed
- [ ] **Balance Sweep**: Sample 1000 seeds, check balance distribution
- [ ] **Localization**: Generated locale files load and display correctly

## Advanced Usage

### Programmatic API

```python
from tome_asset_generator import ToMEAssetGenerator, AssetType, ShapeModule

generator = ToMEAssetGenerator("./mods/my_mod", "my_mod")

asset = generator.generate(
    template=AssetType.SPELL,
    shapes=[ShapeModule.RING, ShapeModule.INK_BLEED],
    seed=12345,
    variant="fire"
)

# Generate manifest and preview
manifest = generator.generate_manifest()
preview = generator.generate_preview_html()

# Check validation warnings
if generator.validation_warnings:
    print("Warnings:", generator.validation_warnings)
```

### Custom Templates

Extend the generator by:
1. Adding new `AssetType` enum values
2. Implementing `_draw_<type>_frame()` methods
3. Adding template-specific parameter generation in `_generate_parameters()`

## Troubleshooting

### PIL/Pillow Not Available
```bash
pip install Pillow
```

### Sprite Generation Fails
- Check PIL installation
- Verify output directory permissions
- Check disk space

### Lua Stubs Don't Load
- Verify ToME mod folder structure
- Check for syntax errors in generated Lua
- Ensure `loadPrevious(...)` is present

### Balance Scores All High/Low
- Adjust parameter ranges in `_generate_parameters()`
- Modify balance score weights in `_calculate_balance_score()`

## License

This tool is provided as-is for mod development. Generated assets and code follow ToME's modding guidelines.

## Contributing

When extending the generator:
1. Maintain determinism (seed-based RNG)
2. Keep Lua stubs safe (no arbitrary code)
3. Follow ToME mod conventions
4. Add validation for new parameters
5. Update documentation

## See Also

- [ToME Modding Guide](https://te4.org/wiki/Modding)
- [T-Engine4 Documentation](https://te4.org/wiki/T-Engine4)
- [ToME Forums](https://forums.te4.org/)

