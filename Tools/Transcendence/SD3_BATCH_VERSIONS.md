# SD3 Texture Generator - Batch File Versions

## Overview

Two batch file versions are available for SD3 texture generation:

1. **`SpaceWhaleSD3TextureGenerator.bat`** - FULL version (includes design drafts)
2. **`SpaceWhaleSD3TextureGenerator_Fast.bat`** - FAST version (skips design drafts)

## Version Comparison

### FULL Version (`SpaceWhaleSD3TextureGenerator.bat`)

**Includes:**
- ✅ Blender model textures (diffuse maps)
- ✅ Projectile textures (energy bolts, plasma, bio-missiles)
- ✅ Design drafts (concept art)

**Generation Time:**
- ~5-10 minutes per ship (3 variations each)
- ~10-20 minutes for all ships (2 ships)

**Use When:**
- You need concept art and design references
- Quality is more important than speed
- You want complete asset sets

### FAST Version (`SpaceWhaleSD3TextureGenerator_Fast.bat`)

**Includes:**
- ✅ Blender model textures (diffuse maps)
- ✅ Projectile textures (energy bolts, plasma, bio-missiles)
- ❌ Design drafts (SKIPPED)

**Generation Time:**
- ~3-6 minutes per ship (3 variations each)
- ~6-12 minutes for all ships (2 ships)

**Use When:**
- You need textures quickly
- Design drafts are not needed
- You're iterating on texture generation
- Speed is more important than completeness

## Usage

### Standalone Usage

```powershell
# FULL version (with design drafts)
.\SpaceWhaleSD3TextureGenerator.bat `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -Variations 3

# FAST version (without design drafts)
.\SpaceWhaleSD3TextureGenerator_Fast.bat `
    -ShipRegistry "space_whale_ship_example.json" `
    -VisualRegistry "space_whale_visual_language_registry.json" `
    -OutputDir "Output/Textures" `
    -Variations 3
```

### Quality Generator Integration

```bash
# FULL version (default, includes design drafts)
python space_whale_quality_asset_generator.py --use-sd3

# FAST version (skip design drafts)
python space_whale_quality_asset_generator.py --use-sd3 --sd3-fast
```

## Design Drafts as Reference

**Important:** Design drafts are used as reference images for other texture generation:

1. **Design drafts generated first** (if enabled)
2. **Design drafts used as reference** for Blender textures and other assets
3. **Better visual consistency** when design drafts are available

### Reference Image Priority

When generating textures, the system looks for reference images in this order:

1. **Design drafts** (if available) - Best reference for concept art
2. **Procedural textures** - Good reference for color and patterns
3. **Other matching textures** - Fallback reference

### Image-to-Image Benefits

Using design drafts as reference provides:

- ✅ **Better visual consistency** - Matches concept art style
- ✅ **Color accuracy** - Preserves color palette from design
- ✅ **Pattern preservation** - Maintains texture structure
- ✅ **Quality improvement** - Reference images provide superior guidance

## Performance Comparison

### Time Savings (FAST vs FULL)

| Scenario | FULL Version | FAST Version | Time Saved |
|----------|-------------|-------------|------------|
| 1 ship, 3 variations | ~5-10 min | ~3-6 min | ~2-4 min |
| 2 ships, 3 variations | ~10-20 min | ~6-12 min | ~4-8 min |
| 1 ship, 5 variations | ~8-15 min | ~5-10 min | ~3-5 min |

### Quality Trade-off

- **FULL version**: Complete asset set with design references
- **FAST version**: Production textures only, no concept art

## Recommendations

### Use FULL Version When:
- ✅ Generating assets for the first time
- ✅ Need concept art for documentation
- ✅ Want complete asset sets
- ✅ Quality is more important than speed

### Use FAST Version When:
- ✅ Iterating on texture generation
- ✅ Design drafts already exist
- ✅ Need textures quickly
- ✅ Speed is more important than completeness

## Integration with Pipeline

### Quality Generator Behavior

- **Default**: Uses FULL version (includes design drafts)
- **With `--sd3-fast`**: Uses FAST version (skips design drafts)
- **Automatic selection**: Chooses appropriate batch file based on flag

### Settings File

```json
{
  "useSd3": true,
  "sd3TextureType": "all",
  "sd3Variations": 3,
  "sd3IncludeDesignDrafts": true  // false for fast mode
}
```

## Summary

Two batch file versions provide flexibility:

✅ **FULL version** - Complete asset generation with design drafts
✅ **FAST version** - Production textures only, faster generation
✅ **Automatic selection** - Quality generator chooses based on flags
✅ **Design drafts as reference** - Better visual consistency when available

Choose the version that best fits your workflow and time constraints.
