# CustomRaceClassCreator Asset Generator - Guide

## Overview

Comprehensive asset generator for the CustomRaceClassCreator mod that generates proper textures, icons, sprites, and other assets using AI and procedural tools. **Specifically designed to replace default Unity textures with proper game-ready textures.**

## Quick Start - Texture Generation

### Generate All Missing Textures

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -AssetTypes "textures" -UseAI
```

### Scan for Missing Textures Only

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -AssetTypes "textures" -ScanOnly
```

### Generate Textures for Specific Systems

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -AssetTypes "textures" -Systems "DragonMagic,BloodMagic,Necromancy" -UseAI
```

## Features

### ✅ Procedural Texture Generation

- **System-Specific Patterns**: Each magic system gets appropriate texture patterns
  - Fire systems: Gradient fire textures with noise
  - Ice systems: Crystalline ice patterns
  - Earth/Geomancy: Stone/rock noise textures
  - Water/River: Wave patterns
  - Nature/Druidic: Organic plant patterns
  - Blood/Necromancy: Dark swirling patterns
  - Magic/Arcane: Energy wave patterns

- **Proper Sizes**: Generates textures in appropriate sizes (256×256, 512×512, 1024×1024)

- **Color Theming**: Uses system-appropriate color palettes

- **No Placeholders**: Generates actual procedural textures, not default Unity textures

### ✅ AI-Powered Specifications

- Uses Ollama AI to generate texture specifications
- Automatically selects appropriate AI model per asset type
- Generates JSON specs with colors, patterns, and properties

### ✅ Progress Tracking

- Real-time progress bar
- Detailed status messages
- Summary report at completion

### ✅ Missing Asset Detection

- Scans for placeholder/default textures
- Detects empty texture folders
- Identifies systems with materials but no textures

### ✅ AssetBundle Integration

- **Automatic Bundle Scanning**: Checks Unity AssetBundles for existing high-quality assets
- **Smart Asset Reuse**: Uses existing bundle assets instead of generating new ones
- **Quality Assessment**: Evaluates bundle size and content to determine asset quality
- **Extraction Support**: Automatically extracts assets if AssetStudio is available
- **Skip Option**: Can skip generation entirely if high-quality bundle assets exist

## Asset Types Supported

| Type | Description | Default Size | Priority |
|------|-------------|--------------|----------|
| **textures** | Procedural textures for materials | 256-1024px | **HIGH** |
| icons | System icons | 32×32 | Medium |
| sprites | Character/object sprites | 32-64px | Medium |
| feat_icons | Feat ability icons | 32×32 | Medium |
| spell_icons | Spell icons | 32×32 | Medium |
| materials | Unity material files | N/A | Low |
| prefabs | Unity prefab files | N/A | Low |

## Texture Generation Details

### Texture Patterns by System

**Fire Systems** (DragonMagic, ElementMagic - Fire):
- Vertical gradient (fire rises)
- Noise-based variation
- Red/orange/yellow color palette

**Ice Systems** (ElementMagic - Ice):
- Crystalline angular patterns
- Blue/cyan color palette
- Reflective appearance

**Earth Systems** (Geomancy, TerrainMagic):
- Noise-based stone texture
- Brown/gray color palette
- Rough, organic appearance

**Water Systems** (RiverMagic):
- Wave patterns
- Blue/aqua color palette
- Flowing appearance

**Nature Systems** (DruidicMagic, Nature):
- Organic noise patterns
- Green color palette
- Natural, varied appearance

**Dark Systems** (BloodMagic, Necromancy):
- Swirling dark patterns
- Dark red/purple color palette
- Mystical appearance

**Magic Systems** (Arcane, general Magic):
- Energy wave patterns
- Purple/magenta color palette
- Energetic appearance

### Texture Naming

Textures are named based on the system:
- `DragonMagic` → `dragon_texture.png`
- `BloodMagic` → `blood_texture.png`
- `Necromancy` → `necromancy_texture.png`

## Usage Examples

### Example 1: Generate All Missing Textures

```powershell
# Scan first to see what's missing
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" -AssetTypes "textures" -ScanOnly

# Generate all missing textures with AI
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" -AssetTypes "textures" -UseAI
```

### Example 2: Generate Textures for Specific Magic Systems

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -Systems "DragonMagic,BloodMagic,Necromancy,Geomancy" `
    -UseAI
```

### Example 3: Improve Existing Placeholder Textures

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -ImproveExisting `
    -UseAI
```

### Example 4: Use Bundle Assets as References to Generate Improved Versions

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -UseAI `
    -UseBundlesAsReference
```

This will:
- Find bundle assets
- Analyze their style (colors, patterns, quality)
- Generate improved versions using AI based on the reference style
- Create assets that match or exceed the reference quality

### Example 5: Generate All Asset Types

```powershell
.\CustomRaceClassCreatorAssetGenerator.bat "E:\...\CustomRaceClassCreator" `
    -AssetTypes "all" `
    -UseAI
```

## Parameters

### Required
- **`-ModPath`** - Path to CustomRaceClassCreator mod directory

### Optional
- **`-AssetTypes`** - Comma-separated list or "all" (default: "all")
- **`-Systems`** - Comma-separated list or "all" (default: "all")
- **`-ScanOnly`** - Only scan, don't generate
- **`-ImproveExisting`** - Improve placeholder assets
- **`-UseAI`** - Use Ollama AI for specifications
- **`-OllamaModel`** - Specific Ollama model (default: auto-select)
- **`-ForceRegenerate`** - Regenerate even if assets exist
- **`-SkipIfBundleExists`** - Skip generation if high-quality bundle assets found
- **`-UseBundlesAsReference`** - Use bundle assets as style references to generate improved versions (requires -UseAI)

## Output Locations

Generated textures are placed in:
```
Assets/Resources/[SystemName]/Textures/
```

For example:
- `Assets/Resources/DragonMagic/Textures/dragon_texture.png`
- `Assets/Resources/BloodMagic/Textures/blood_texture.png`
- `Assets/Resources/Necromancy/Textures/necromancy_texture.png`
```

## AssetBundle Integration

The generator automatically scans Unity AssetBundles for existing high-quality assets before generating new ones.

### Bundle Locations Scanned

- `Assets/AssetBundles/Windows/` (and Linux/macOS variants)
- `Assets/UI/AssetBundles/Windows/`

### Quality Assessment

- **High Quality**: Bundle size > 1MB (likely contains substantial assets)
- **Medium Quality**: Bundle size 100KB - 1MB (may contain some assets)
- **Low Quality**: Bundle size < 100KB (likely minimal content)

### Asset Reuse Behavior

- **Default**: Checks bundles first, uses existing assets if found, generates if not
- **-SkipIfBundleExists**: Skips generation entirely if high-quality bundle assets found
- **-ForceRegenerate**: Ignores bundle assets and always generates new ones
- **-UseBundlesAsReference**: Uses bundle assets as style references to generate **improved versions** (requires -UseAI)

### Extraction Support

- **Automatic**: If AssetStudio CLI is installed, automatically extracts assets from bundles
- **Manual**: If AssetStudio not available, shows bundle info for manual extraction
- **Resources**: Already-extracted assets in Resources folders are automatically detected and used

### Reference-Based Enhancement

When using `-UseBundlesAsReference` with `-UseAI`:

1. **Extracts Reference Assets**: Automatically extracts assets from bundles
2. **Analyzes Style**: Uses image analysis to extract:
   - Dominant color palette
   - Pattern type (gradient, textured, complex)
   - Brightness and contrast levels
   - Quality metrics
3. **AI Enhancement**: Uses AI to generate improved specifications based on reference:
   - Enhanced color palettes (more vibrant/magical)
   - Improved patterns
   - Higher quality settings
   - Theme-appropriate enhancements
4. **Generates Better Assets**: Creates improved versions that match or exceed reference quality

### Benefits

- **Faster**: Reuses existing quality assets instead of regenerating
- **Better Quality**: Uses professionally created assets from bundles when available
- **Enhanced Generation**: Creates improved versions based on reference style
- **Flexible**: Can still generate new assets when bundles don't have what's needed

## Requirements

- **Python 3.x** with PIL/Pillow installed
- **Ollama** (optional, for AI specifications)
- **PowerShell 5.1+** or PowerShell Core
- **AssetStudio CLI** (optional, for automatic bundle extraction)

### Installing Dependencies

```powershell
# Install Pillow for Python
python -m pip install Pillow

# Or use python3
python3 -m pip install Pillow
```

## Integration with Unity

After generating textures:

1. **Import into Unity**: Textures are automatically detected if placed in `Assets/Resources/`
2. **Assign to Materials**: Update Unity materials to use the new textures
3. **Update Prefabs**: Prefabs using materials will automatically use new textures

## Troubleshooting

### Textures Not Generating

**Check Python installation:**
```powershell
python --version
python -m pip list | Select-String Pillow
```

**Check file permissions:**
- Ensure write access to mod directory
- Check antivirus isn't blocking file creation

### AI Not Working

**Check Ollama:**
```powershell
# Test Ollama connection
Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
```

**Use without AI:**
- Omit `-UseAI` flag to use default procedural generation

### Wrong Colors/Patterns

**Specify system explicitly:**
- Use `-Systems` parameter to target specific systems
- Colors are auto-selected based on system name

**Customize colors:**
- Edit the `Get-SystemDefaultColors` function in the script
- Or use AI with detailed prompts

## Best Practices

1. **Scan First**: Always run with `-ScanOnly` first to see what's missing
2. **Generate in Batches**: Generate textures for a few systems at a time
3. **Use AI**: Enable `-UseAI` for better, system-appropriate textures
4. **Review Results**: Check generated textures in Unity before committing
5. **Backup First**: Backup your mod before generating many assets

## Advanced Usage

### Custom Texture Sizes

Edit the script's `$script:AssetConfigs["textures"].Size` array to change default sizes.

### Custom Color Palettes

Edit the `Get-SystemDefaultColors` function to add/modify system color palettes.

### Custom Texture Patterns

Edit the `Generate-TextureAsset` function's Python script to add new texture patterns.

## See Also

- `ElinSpellAssetGenerator.ps1` - For spell-specific assets
- `ElinTextureGenerator.ps1` - For general Elin textures
- CustomRaceClassCreator mod documentation

---

**Version**: 1.0  
**Last Updated**: 2024-12-26  
**Focus**: Texture generation to replace default Unity textures

