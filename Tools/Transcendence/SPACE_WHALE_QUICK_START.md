# Space Whale Asset Generation - Quick Start Guide

## Overview

This guide helps you quickly start generating all Space Whale assets with multithreading support.

## Quick Launch Options

### Option 1: Complete Setup (Recommended)

**`StartSpaceWhaleAssetGeneration.bat`**

Launches everything needed:
- ✅ Control Room Monitor (optional GUI)
- ✅ Comprehensive Asset Generator (multithreaded)
- ✅ Automatic configuration
- ✅ Progress monitoring

**Usage:**
```batch
StartSpaceWhaleAssetGeneration.bat
```

### Option 2: GUI Mode

**`StartSpaceWhaleAssetGeneration_WithGUI.bat`**

Launches the full GUI-based generator:
- ✅ Visual progress bars
- ✅ Real-time logs
- ✅ Interactive controls
- ✅ Preview of generated assets

**Usage:**
```batch
StartSpaceWhaleAssetGeneration_WithGUI.bat
```

### Option 3: Monitor Only

**`StartSpaceWhaleAssetGeneration_MonitorOnly.bat`**

Launches only the monitor to watch existing generation:
- ✅ Real-time file detection
- ✅ Progress tracking
- ✅ Preview of generated assets
- ✅ Detailed logs

**Usage:**
```batch
StartSpaceWhaleAssetGeneration_MonitorOnly.bat
```

### Option 4: Quick Launch (No Prompts)

**`StartSpaceWhaleAssetGeneration_Quick.bat`**

Quick launcher with default settings, no prompts:
- ✅ Fast startup
- ✅ Default configuration
- ✅ All features enabled

**Usage:**
```batch
StartSpaceWhaleAssetGeneration_Quick.bat
```

## Prerequisites

### Required
- ✅ Python 3.8+ (in PATH)
- ✅ PowerShell 5.1+ (Windows 10/11)

### Optional (for full features)
- ✅ Ollama (for AI-generated variations)
  - Install: https://ollama.ai
  - Start: `ollama serve`
- ✅ Blender (for spritesheet generation)
  - Set `BLENDER_PATH` environment variable

## Configuration

### Default Settings

The batch files use these default settings:
- **Output Directory**: `Output\SpaceWhaleAssets`
- **Ship ID**: `leviathan_alpha`
- **Ollama Models**: 
  - Code Generation: `codellama:34b` (auto-detected)
  - Visual/Orchestration: `wizardlm-uncensored:latest` (auto-detected)
  - **Dual-model support enabled** - tasks automatically routed to best model
- **Variations**: `150` per asset type
- **Max Cores**: `32` (automatic detection)

### Customizing Settings

Edit the batch file to change:
```batch
set "OUTPUT_DIR=Your\Custom\Path"
set "SHIP_ID=your_ship_id"
set "OLLAMA_MODEL=your_model"
set "VARIATIONS=150"
```

## What Gets Generated

### 1. Visual Language Assets
- 150 color palette variations
- Material definitions
- Texture patterns
- Animation guidelines

### 2. FX Assets
- 150 variations per effect (10 effects)
- Best selection (1 per effect)
- Quality placeholders (10 per effect)
- Quality assessment reports

### 3. Audio Assets
- 150 variations per sound (11 sounds)
- EM channel sounds
- Plasma channel sounds
- Acoustic channel sounds
- Mechanical channel sounds

### 4. Textures for Rigging
- Diffuse maps (base color)
- Emission maps (glow)
- Normal maps (detail)
- Roughness maps (surface)
- Metallic maps (reflection)

### 5. Quality Reports
- Detailed quality scores
- Low-quality asset details (< 8.0)
- Recommendations

## Generation Time

### Before (Sequential)
- **~30+ hours** for all assets

### After (Multithreaded, 32 cores)
- **~1 hour** for all assets
- **~30x speedup**

## Output Structure

```
Output/
└── SpaceWhaleAssets/
    ├── VisualLanguage/
    │   └── ollama_palette_variations.json
    ├── FX/
    │   ├── space_whale_fx_registry_best.json
    │   ├── space_whale_fx_registry_placeholders.json
    │   └── SPACE_WHALE_FX_QUALITY_ASSESSMENT.md
    ├── Audio/
    │   └── *.ogg (audio files)
    ├── Textures/
    │   ├── texture_registry.json
    │   └── [module_name]/
    │       ├── *_diffuse.png
    │       ├── *_emission.png
    │       ├── *_normal.png
    │       ├── *_roughness.png
    │       └── *_metallic.png
    └── QUALITY_REPORT_LOW_SCORES.md
```

## Monitoring Progress

### Control Room Monitor Features

- **Real-time file detection**: See files as they're generated
- **Progress bars**: Visual progress tracking
- **Preview window**: See generated images immediately
- **Detailed logs**: All generation output
- **File list**: Track all generated files

### Launch Monitor Separately

If generation is already running, launch the monitor separately:

```batch
StartSpaceWhaleAssetGeneration_MonitorOnly.bat
```

Or:

```powershell
powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1 -WatchDirectory "Output"
```

## Troubleshooting

### Python Not Found

**Error**: `Python is not installed or not in PATH`

**Solution**:
1. Install Python 3.8+ from https://www.python.org
2. Check "Add Python to PATH" during installation
3. Restart command prompt

### Ollama Not Running

**Warning**: `Ollama does not appear to be running`

**Solution**:
1. Install Ollama: https://ollama.ai
2. Start Ollama: `ollama serve`
3. Verify: `curl http://localhost:11434/api/tags`

### Generation Takes Too Long

**Check**:
- CPU usage should be high (multithreading working)
- Check task manager for Python processes
- Verify thread count matches CPU cores

**Optimize**:
- Reduce variations (edit batch file)
- Close other applications
- Use SSD for output directory

### Monitor Not Showing Files

**Check**:
- Monitor is watching correct directory
- Files are being generated (check output directory)
- File extensions are supported (.png, .json, .xml, .ogg)
- GUI is displaying visual elements (not just text)

**Solution**:
- Restart monitor with correct watch directory: `powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1 -WatchDirectory "Output"`
- Check file permissions
- Verify STA mode is enabled (required for WPF GUI)
- Test with `TestMonitorGUI.ps1` to verify GUI is working

### GUI Rendering Issues

**Issue**: Window shows only text, no colors or progress bars

**Solution**:
1. Ensure script runs with `-STA` flag (required for WPF)
2. Check that WPF assemblies are loaded (automatic)
3. Verify window shows dark blue background (#1a2a3a)
4. Test with `TestMonitorGUI.ps1` to verify WPF is working

### Blender Script Errors

**Error**: `Failed to render ship: [error]`

**Common Issues**:
- **Missing Path import**: Fixed in latest version
- **Invalid registry JSON**: Check JSON syntax
- **Missing texture directory**: Script will continue without textures
- **Blender not found**: Ensure Blender is in PATH or use `--SkipBlender`

**Error Messages Now Include**:
- Detailed error context
- File paths for debugging
- Success/failure counts
- Per-ship error tracking

**Solutions**:
- Check registry file format and syntax
- Verify ship data has required fields (`visual`, `export.unid`, etc.)
- Check Blender installation and PATH
- Review error output for specific issues

### XML Export Errors

**Error**: `Failed to export ship: [error]`

**Common Issues**:
- **Missing required fields**: Ship data must have `id`, `export.unid`
- **Invalid UNID format**: UNID must be valid after cleaning
- **File write errors**: Check output directory permissions

**Error Messages Now Include**:
- Which field is missing
- File paths for debugging
- Success/failure counts
- Per-ship error tracking

**Solutions**:
- Verify ship registry has all required fields
- Check output directory exists and is writable
- Review error messages for specific missing fields

## Next Steps

After generation completes:

1. **Review Quality Reports**
   - Check `QUALITY_REPORT_LOW_SCORES.md`
   - Review quality scores for all assets

2. **Select Best Variations**
   - Use best selections from registries
   - Or choose from quality placeholders

3. **Generate Spritesheets**
   - Use Blender scripts for 120 facings
   - Apply generated textures
   - **Note**: Scripts now include improved error handling
   - Run: `SpaceWhale120FacingsGenerator.ps1 --registry space_whale_ship_example.json`

4. **Export to Transcendence**
   - Use XML exporter scripts
   - **Note**: Scripts now validate all required fields
   - Run: `python transcendence_space_whale_exporter.py --registry registry.json --output-dir Output/XML`
   - Integrate into mod

## Recent Improvements

### GUI Enhancements (✅ Complete)
- Fixed WPF window rendering (colors, borders, progress bars now visible)
- Improved progress bar visibility and styling
- Enhanced image preview loading with better error handling
- Added validation and error messages for debugging

### Error Handling (✅ Complete)
- **Blender Script**: Added comprehensive error handling, validation, and per-ship error tracking
- **XML Exporter**: Added field validation, error messages, and success/failure reporting
- **PowerShell Wrapper**: Improved error handling for registry loading and Blender execution
- All scripts now provide detailed error messages with context

### Script Improvements
- Fixed missing `Path` import in Blender script
- Added input validation for all parameters
- Added graceful error recovery (continues with next ship on failure)
- Added KeyboardInterrupt handling
- Improved exit codes and error reporting

## Support

For issues or questions:
- Check `SPACE_WHALE_MULTITHREADING_GUIDE.md` for technical details
- Review logs in `Output\SpaceWhaleAssets\`
- Check individual generator scripts for specific errors

## Summary

**Quick Start:**
```batch
StartSpaceWhaleAssetGeneration.bat
```

**With GUI:**
```batch
StartSpaceWhaleAssetGeneration_WithGUI.bat
```

**Monitor Only:**
```batch
StartSpaceWhaleAssetGeneration_MonitorOnly.bat
```

All generators are **fully multithreaded** and **thread-safe**! 🚀

