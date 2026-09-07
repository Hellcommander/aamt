# Deprecated Vortex Generator Scripts

This directory contains **deprecated** vortex asset generator scripts that have been superseded by the unified generator.

## ⚠️ DEPRECATED - DO NOT USE

These scripts are kept for reference only. **All improvements have been merged into the unified generator.**

## Unified Generator

**Use this instead:** `generate_vortex_professional.py`

The unified generator (`generate_vortex_professional.py`) contains all features and improvements from these deprecated scripts:

- ✅ 4x supersampling with LANCZOS anti-aliasing
- ✅ 16-frame ultra-smooth animations
- ✅ Multi-AI support (math AI + visual AI)
- ✅ HSV color space for vibrant gradients
- ✅ Multiple layered effects (5+ layers per frame)
- ✅ High-resolution support (64x64, 96x96) for tile scaling mods
- ✅ Audio generation support (white hole sounds)
- ✅ Model router integration
- ✅ Quality assessment integration
- ✅ All asset types (icons, animations, particles, overlays, ability icons, warning markers)
- ✅ Performance optimizations (caching, memory management)
- ✅ Enhanced error handling with retry logic

## Deprecated Scripts

### `generate_vortex_assets_ollama.py`
- **Status:** Superseded by unified generator
- **Original Features:** Basic generator with 8 frames, standard resolution, audio support
- **Replaced By:** `generate_vortex_professional.py` (includes all features + improvements)

### `generate_vortex_enhanced_assets.py`
- **Status:** Superseded by unified generator
- **Original Features:** Enhanced assets, additional icons, model router integration
- **Replaced By:** `generate_vortex_professional.py` (includes all features + improvements)

### `generate_vortex_premium_assets.py`
- **Status:** Superseded by unified generator
- **Original Features:** Premium quality rendering, 16 frames
- **Replaced By:** `generate_vortex_professional.py` (includes all features + improvements)

## Migration Guide

**Old Usage:**
```bash
python generate_vortex_assets_ollama.py "MOD_PATH"
python generate_vortex_enhanced_assets.py "MOD_PATH"
python generate_vortex_premium_assets.py "MOD_PATH"
```

**New Usage (Unified Generator):**
```bash
python generate_vortex_professional.py "MOD_PATH"
```

**Or use the entry points:**
```batch
GenerateVortexAssets.bat
```

```powershell
.\GenerateVortexAssets.ps1 -ModPath "MOD_PATH" -QualityAssessmentDepth "full"
```

## Why These Scripts Were Deprecated

1. **Feature Duplication:** Multiple scripts with overlapping features
2. **Maintenance Burden:** Hard to maintain and update multiple scripts
3. **Inconsistent Features:** Different scripts had different capabilities
4. **Unified Solution:** All improvements merged into one comprehensive generator

## Archive Date

These scripts were archived when the unified generator (`generate_vortex_professional.py`) was completed with all improvements integrated.

## Questions?

If you need features from these deprecated scripts, they are all available in `generate_vortex_professional.py`. If you find any missing features, please report them so they can be added to the unified generator.
