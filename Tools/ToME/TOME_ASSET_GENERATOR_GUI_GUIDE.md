# ToME Asset Generator GUI Guide

## Overview

Graphical interface for generating ToME mod assets with:
- **Real-time progress indicators** (overall and per-asset)
- **Live generation log** with status updates
- **Asset selection** checkboxes
- **Automatic cleanup** of old assets
- **Drag & drop** mod folder support
- **AI enhancement** integration

## Quick Start

### Launch GUI

```bash
python tome_asset_generator_gui.py
```

Or double-click: `LaunchToMEAssetGeneratorGUI.bat`

### Generate Assets

1. **Set Mod Path**
   - Enter path to your ToME mod (e.g., `tome-smog-devil-class`)
   - Or drag & drop mod folder onto the path field

2. **Set Output Path**
   - Where to generate assets temporarily (default: `Output/SmogDevilAssets`)

3. **Configure Options**
   - **Use AI Enhancement**: Enable for AI-generated descriptions (requires Ollama)
   - **Variations per asset**: Number of variations to generate (default: 20)

4. **Select Assets**
   - Check which asset types to generate:
     - Steam Staff (Weapon)
     - Steam Overload (Effect)
     - Steam Mana Converter (Effect)
     - Steam Mana Symphony (Effect)
     - Smog Devil Apotheosis (Effect)

5. **Cleanup Options**
   - **Remove old assets**: Automatically removes old/lower quality assets after generation

6. **Click "Generate Assets"**
   - Watch progress bars and log in real-time
   - Assets are automatically copied to mod directory
   - Old assets are removed (if enabled)

## Progress Indicators

### Overall Progress
- Shows total progress across all assets
- Format: "Overall Progress: X / Y"
- Updates as each asset completes

### Current Asset Progress
- Shows progress for current asset type
- Format: "Current: Asset Name - X / Y"
- Updates for each variation

### Generation Log
- Real-time log of all operations
- Shows:
  - Asset generation status
  - Balance scores
  - File copy operations
  - Cleanup operations
  - Errors and warnings

## Features

### Real-Time Updates
- Progress bars update as assets generate
- Log updates immediately
- Status bar shows current operation

### Automatic File Management
- Generates assets in temporary directory
- Copies to mod directory automatically
- Removes old assets (if enabled)
- Preserves metadata files (.meta.json)

### Error Handling
- Continues on individual asset failures
- Logs all errors
- Shows summary at end

### Stop Generation
- Click "Stop" to cancel generation
- Current asset completes, then stops
- Partial results are saved

## Example Workflow

### Generate 20 Steam Staff Variations

1. Set mod path: `F:\...\tome-smog-devil-class`
2. Check "Steam Staff (Weapon)"
3. Set variations: 20
4. Enable "Remove old assets"
5. Click "Generate Assets"

**Result:**
- Generates 20 steam staff sprites
- Copies to `mod/data/gfx/objects/steam_staff_00.png` through `steam_staff_19.png`
- Removes any old `steam_staff*.png` files
- Creates metadata files for each sprite

## Asset Types

### Steam Staff (Item)
- **Type**: Item/Weapon
- **Output**: `data/gfx/objects/steam_staff_XX.png`
- **Shapes**: None (static item)

### Steam Overload (VFX)
- **Type**: Visual Effect
- **Output**: `data/gfx/effects/steam_overload_XX.png`
- **Shapes**: Nova, Spiral

### Steam Mana Converter (VFX)
- **Type**: Visual Effect
- **Output**: `data/gfx/effects/steam_mana_converter_XX.png`
- **Shapes**: Ring, Spiral

### Steam Mana Symphony (VFX)
- **Type**: Visual Effect
- **Output**: `data/gfx/effects/steam_mana_symphony_XX.png`
- **Shapes**: Ring, Cloud

### Smog Devil Apotheosis (VFX)
- **Type**: Visual Effect
- **Output**: `data/gfx/effects/smog_devil_apotheosis_XX.png`
- **Shapes**: Nova, Spiral

## File Structure

After generation, mod structure:

```
tome-smog-devil-class/
  data/
    gfx/
      objects/
        steam_staff_00.png
        steam_staff_00.meta.json
        steam_staff_01.png
        ...
      effects/
        steam_overload_00.png
        steam_overload_00.meta.json
        ...
```

## Tips

1. **Start Small**: Test with 1-2 variations first
2. **Monitor Progress**: Watch log for errors
3. **Check Balance Scores**: Higher scores = better balanced
4. **Review Assets**: Check preview images before using
5. **Backup First**: Backup mod before removing old assets

## Troubleshooting

### GUI Won't Launch
- Check Python installation
- Install dependencies: `pip install tkinterdnd2`

### No Progress Updates
- Check if generation thread is running
- Look for errors in log

### Assets Not Copying
- Check mod path is correct
- Verify write permissions
- Check log for errors

### AI Not Working
- Start Ollama: `ollama serve`
- Pull models: `ollama pull codellama:34b`
- Check connection in log

## See Also

- `TOME_ASSET_GENERATOR_README.md` - Base generator docs
- `TOME_AI_GENERATOR_GUIDE.md` - AI features
- `TOME_MOD_CHECKER_README.md` - Mod validation

