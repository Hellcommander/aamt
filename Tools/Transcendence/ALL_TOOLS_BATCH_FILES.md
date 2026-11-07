# All Tools - Batch Files Reference

## Quick Access

All batch files are in the `Tools` directory. Double-click any `.bat` file to run it - no console commands needed!

## Testing

### ✅ `TestTranscendenceImages.bat` (shortcut: "Transcendence Image Tester" on the Desktop and in the game folder)
**Engine-rule image / facing tester** (`tx_image_tester.py`)
- Rules mirrored from the engine source (cited in the script): column-major rotation layout,
  frame 0 nose-up turning clockwise, required sheet size, mask size/bit depth, module-relative paths
- Flags frames clipped by the cell edge and ShipClasses below 120 facings (`--inventory`)
- No arguments: tests ZZZ_CrossModCompatibility. Drop any extension folder or XML onto it to test that
- Report + contact strips (0/90/180/270 deg): `Tools\Transcendence\Logs\image_tester\`
- Calibrated on vanilla Svarog / Viking sheets (pass)

### ✅ `tx_apply_mod_patches.py` (re-apply your own fixes after a third-party mod updates)
- One folder per mod in `mod_patches/` (`patch.json` + the XML fragment to insert): entities to declare, root attributes to drop, overrides to add
- `python tx_apply_mod_patches.py` reports; `--write` patches (backup `.bak_<stamp>_modpatch`); safe to run again, already-patched mods report OK
- Current: `corporate_command_ep_addon` (EI7000 Chimera hull, Thorin 300 fireRate 21, unidHumanSpaceLibrary, loads in every adventure)

### ✅ `tx_fix_obsolete_images.py` (mod issue: "Unknown image: <unid>" stops the game loading)
**Finds mod ships that still use retired TransCore ship images** (old sprite sheets with `obsoleteVersion`)
- `python tx_fix_obsolete_images.py <extension folder>` reports; add `--write` to patch (each file backed up `.bak_<stamp>_obsimg`)
- Swaps in the image vanilla uses today: same-UNID override, `scFooNPC`/`scDSFoo` named after `scFoo`, or the vanilla
  ship that used that old sheet cell (map `data\obsolete_ship_image_map.json`, built from upstream TransCore 2017 + current)
- "MANUAL" lines have no vanilla equivalent and need an image chosen by hand

## Main Generators

### 🚀 `StartSpaceWhaleAssetGeneration.bat`
**Complete asset generation with monitor**
- Generates all asset types
- Launches optional monitor GUI
- Full automation

### 🎨 `GenerateComprehensiveAssets.bat`
**Main comprehensive asset generator**
- Visual Language (150 variations)
- FX Assets (150 variations)
- Audio Assets (150 variations)
- Textures for Rigging
- 120 Facings Spritesheet
- Quality Reports

### 🖼️ `GenerateVisualLanguage.bat`
**Visual language assets only**
- Color palettes
- Materials
- Textures
- Animations
- Uses Ollama for AI generation

### ✨ `GenerateFXAssets.bat`
**FX effects only**
- 150 variations per effect
- Quality assessment
- Best selections
- Placeholder registry

### 🔊 `GenerateAudioAssets.bat`
**Audio assets only**
- Procedural audio generation
- 150 variations per sound
- EM/Plasma/Acoustic/Mechanical channels

### 🎨 `GenerateTextures.bat`
**Textures for rigging**
- Diffuse maps
- Emission maps
- Normal maps
- Roughness maps
- Metallic maps

### 🎬 `GenerateSpritesheet120Facings.bat`
**120 rotation facings spritesheet**
- Blender-based rendering
- Uses generated textures
- Full rotation animation

### 🔧 `GenerateRigging.bat`
**Blender rigging setup**
- Armature creation
- Bone structure
- Weight painting
- Blender integration

## Export & Integration

### 📄 `ExportToTranscendenceXML.bat`
**Export to Transcendence XML format**
- Converts generated assets to XML
- Ready for mod integration
- Transcendence-compatible format

### ✅ `CheckQuality.bat`
**Quality assessment**
- Checks all generated assets
- Reports low-quality items (score < 8.0)
- Detailed quality report

## GUI & Monitoring

### 🖥️ `LaunchControlRoom.bat`
**Control Room Monitor GUI**
- Real-time asset preview
- Image grid display
- XML content preview
- Progress tracking
- Log output

### 🎛️ `LaunchAssetGeneratorGUI.bat`
**Full GUI-based generator**
- Interactive controls
- Visual progress
- Real-time logs
- Preview of generated assets

## Testing

### 🧪 `TestDualModelSystem.bat`
**Test dual-model routing**
- Verifies CodeLlama-34B detection
- Verifies WizardLM-uncensored detection
- Tests task-based routing

### 🧪 `TestMinimalSpaceWhale.bat`
**Quick functionality test**
- Multithreading test
- GUI display test
- ~15 seconds

### 🧪 `TestGUI.bat`
**GUI display test**
- Launches monitor
- Verifies images display
- Verifies XML display

### 🧪 `RunAllTests.bat`
**Run all tests**
- Dual model test
- Minimal space whale test

## Workflow Examples

### Complete Generation (Recommended)
```
1. StartSpaceWhaleAssetGeneration.bat
   (or StartSpaceWhaleAssetGeneration_WithGUI.bat)
```

### Step-by-Step Generation
```
1. GenerateVisualLanguage.bat
2. GenerateFXAssets.bat
3. GenerateAudioAssets.bat
4. GenerateTextures.bat
5. GenerateSpritesheet120Facings.bat
6. CheckQuality.bat
7. ExportToTranscendenceXML.bat
```

### Monitoring Existing Generation
```
1. LaunchControlRoom.bat
   (in separate window while generation runs)
```

## Prerequisites

### Required
- ✅ Python 3.8+ (in PATH)
- ✅ PowerShell 5.1+ (Windows 10/11)

### Optional
- ✅ Ollama (for AI generation)
  - Models: `codellama:34b`, `wizardlm-uncensored:latest`
- ✅ Blender (for spritesheet/rigging)
  - Set `BLENDER_PATH` environment variable

## Configuration

Most batch files use default settings. To customize:

1. Right-click the `.bat` file
2. Select "Edit"
3. Modify the variables at the top:
   ```batch
   set "OUTPUT_DIR=Your\Custom\Path"
   set "SHIP_ID=your_ship_id"
   set "VARIATIONS=150"
   ```
4. Save and run

## Troubleshooting

### "Python is not installed"
- Install Python 3.8+ from python.org
- Add to system PATH

### "Ollama models not detected"
```bash
ollama pull codellama:34b
ollama pull wizardlm-uncensored:latest
```

### "Blender not found"
- Install Blender
- Set `BLENDER_PATH` environment variable
- Or edit batch file to specify Blender path

### "GUI not showing images"
- Check that files exist in output directory
- Verify GUI is watching correct directory
- Check log for image loading errors

## File Locations

- **Batch Files**: `Transcendence\Tools\*.bat`
- **Output**: `Transcendence\Tools\Output\`
- **Logs**: Shown in console/GUI

## Quick Reference

| Tool | Batch File | Purpose |
|------|------------|---------|
| **Complete Generation** | `StartSpaceWhaleAssetGeneration.bat` | Everything |
| **Visual Language** | `GenerateVisualLanguage.bat` | Colors, materials |
| **FX Effects** | `GenerateFXAssets.bat` | Visual effects |
| **Audio** | `GenerateAudioAssets.bat` | Sound effects |
| **Textures** | `GenerateTextures.bat` | Texture maps |
| **Spritesheet** | `GenerateSpritesheet120Facings.bat` | Rotation frames |
| **Rigging** | `GenerateRigging.bat` | Blender setup |
| **Quality Check** | `CheckQuality.bat` | Assessment |
| **XML Export** | `ExportToTranscendenceXML.bat` | Mod integration |
| **Monitor** | `LaunchControlRoom.bat` | Real-time preview |
| **GUI Generator** | `LaunchAssetGeneratorGUI.bat` | Interactive |

