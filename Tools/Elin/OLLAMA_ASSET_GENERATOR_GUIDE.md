# Ollama Asset Generator Guide
**AI-Assisted Modding Tools (AAMT)**

Complete guide for generating high-quality assets and spritesheets using Ollama AI. Part of the AI-Assisted Modding Tools (AAMT) suite.

## Overview

The Ollama Asset Generator uses AI-powered specifications to create game-ready assets including:
- **Textures** - Material textures for 3D objects (256-1024px)
- **Icons** - UI icons for menus and interfaces (32px)
- **Sprites** - Character and object sprites (64px)
- **Spell Assets** - Spell icons, effects, and projectiles (32px)

## Features

### ✅ AI-Powered Specifications
- Uses Ollama to generate detailed asset specifications
- System-specific color palettes and themes
- Quality-aware generation (low to ultra)
- Automatic pattern and style selection

### ✅ High-Quality Generation
- Procedural image generation with multiple patterns
- Visual effects (glow, rim-light, shadows)
- Style options (painterly, pixel-art, stylized)
- Quality levels from placeholder to ultra-high

### ✅ Spritesheet Support
- Automatic spritesheet generation for batch assets
- Efficient grid layouts
- Configurable spacing and columns

### ✅ Integration
- Uses Shared Ollama integration module for optimal performance
- Compatible with existing asset generators
- Python-based image generation for quality

## Quick Start

### Generate All Assets

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" `
    -AssetTypes "all" `
    -Quality "high" `
    -UseOllama
```

### Generate Specific Asset Types

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures,icons" `
    -Systems "DragonMagic,BloodMagic" `
    -Quality "high"
```

### Generate with Spritesheets

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "icons,sprites" `
    -GenerateSpritesheets `
    -Quality "high"
```

### Batch Processing

```powershell
.\BatchAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -Quality "high" `
    -GenerateSpritesheets
```

## Parameters

### OllamaAssetGenerator.ps1

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-ModPath` | Path to mod directory | **Required** |
| `-AssetTypes` | Comma-separated types or "all" | "all" |
| `-Systems` | Comma-separated systems or "all" | "all" |
| `-OutputDir` | Output directory | `GeneratedAssets` |
| `-UseOllama` | Use Ollama for AI specs | `$true` |
| `-GenerateSpritesheets` | Generate spritesheets | `$false` |
| `-Quality` | Quality level (low/medium/high/ultra) | "high" |

### Quality Levels

| Level | Size | Colors | Detail | Use Case |
|-------|------|--------|--------|----------|
| **low** | 128px | 2 | basic | Placeholders, testing |
| **medium** | 256px | 4 | standard | Standard gameplay |
| **high** | 512px | 6 | enhanced | Production quality |
| **ultra** | 1024px | 8 | ultra | High-end assets |

## Asset Types

### Textures
- **Size**: 256-1024px (based on quality)
- **Patterns**: Gradient, noise, organic, geometric
- **Use**: Material textures for 3D objects
- **Output**: `GeneratedAssets/Textures/[System]/[system]_texture.png`

### Icons
- **Size**: 32px (standard UI size)
- **Patterns**: Geometric, organic, stylized
- **Use**: UI icons for menus and interfaces
- **Output**: `GeneratedAssets/Icons/[System]/[system]_icons.png`

### Sprites
- **Size**: 64px (character/object size)
- **Patterns**: Stylized, painterly
- **Use**: Character and object sprites
- **Output**: `GeneratedAssets/Sprites/[System]/[system]_sprites.png`

### Spell Assets
- **Size**: 32px (spell icon size)
- **Patterns**: Magical, glowing, themed
- **Use**: Spell icons, effects, projectiles
- **Output**: `GeneratedAssets/SpellAssets/[System]/[system]_spell_assets.png`

## AI Specification Format

When using Ollama, the generator creates detailed JSON specifications:

```json
{
  "colors": ["#ff4444", "#ff8844", "#ffaa44", "#ffcc44"],
  "pattern": "gradient",
  "style": "stylized",
  "effects": ["glow", "rim-light"],
  "theme": "DragonMagic",
  "size": 512,
  "details": ["fire", "scales", "energy"]
}
```

## Spritesheet Generation

Enhanced spritesheet generation based on Transcendence patterns with:
- **Configurable Grid Layouts** - Fixed or auto-calculated columns/rows
- **Frame-Based Layouts** - Fixed frame sizes for consistent sprites
- **Metadata Generation** - JSON metadata and info text files
- **Multiple Formats** - PNG (default) or JPG support
- **Proper Spacing** - Configurable spacing between sprites
- **Asset Type Support** - Optimized layouts per asset type

Spritesheets combine multiple assets into a single image for efficient loading:

```
GeneratedAssets/
└── Icons/
    └── DragonMagic/
        ├── dragonmagic_icons.png
        ├── dragonmagic_icons_2.png
        ├── DragonMagic_icons_spritesheet.png  ← Spritesheet
        ├── DragonMagic_icons_spritesheet.json ← Metadata
        └── DragonMagic_icons_spritesheet.info.txt ← Info file
```

### Spritesheet Layout

```
┌─────┬─────┬─────┬─────┐
│  1  │  2  │  3  │  4  │
├─────┼─────┼─────┼─────┤
│  5  │  6  │  7  │  8  │
├─────┼─────┼─────┼─────┤
│  9  │ 10  │ 11  │ 12  │
└─────┴─────┴─────┴─────┘
```

### Spritesheet Features

**Grid Configuration:**
- Auto-calculated: Optimally sized grid based on asset count
- Fixed columns: Specify exact column count
- Fixed rows: Specify exact row count
- Fixed frames: Specify exact frame dimensions

**Metadata Files:**
- `.json` - Complete spritesheet metadata (dimensions, grid, assets list)
- `.info.txt` - Human-readable info file (Transcendence-style)

**Format Support:**
- PNG (default) - With alpha channel support
- JPG - For non-transparent spritesheets

## System-Specific Themes

The generator automatically applies system-appropriate themes:

| System | Colors | Pattern | Style |
|--------|--------|---------|-------|
| **DragonMagic** | Red/Orange/Yellow | Fire gradient | Glowing |
| **BloodMagic** | Dark Red | Swirling | Mystical |
| **Necromancy** | Gray/Black | Dark patterns | Shadowy |
| **DruidicMagic** | Green | Organic | Natural |
| **ElementMagic** | Blue | Energy waves | Energetic |
| **Geomancy** | Brown/Gray | Stone texture | Rough |

## Workflow Examples

### Example 1: Generate All Textures

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -Quality "high" `
    -UseOllama
```

### Example 2: Generate Icons for Specific Systems with Spritesheets

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "icons" `
    -Systems "DragonMagic,BloodMagic,Necromancy" `
    -Quality "high" `
    -GenerateSpritesheets
```

This generates:
- Individual icon files per system
- Spritesheets combining all icons per system
- Metadata JSON files with grid information
- Info text files (Transcendence-style)

### Example 3: Ultra-Quality Assets

```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures,icons" `
    -Quality "ultra" `
    -UseOllama
```

### Example 4: Batch Processing All Assets

```powershell
.\BatchAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -Quality "high" `
    -GenerateSpritesheets
```

## Integration with Existing Tools

### With CustomRaceClassCreatorAssetGenerator

The Ollama generator complements the existing asset generator:

```powershell
# 1. Generate base assets with existing generator
.\CustomRaceClassCreatorAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -UseAI

# 2. Enhance with Ollama generator
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures" `
    -Quality "ultra" `
    -UseOllama
```

### With ElinSpellAssetGenerator

```powershell
# Generate spell assets with Ollama
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "spell_assets" `
    -Systems "Nature Magic,Arachnomancy" `
    -Quality "high"
```

## Requirements

### Required
- **PowerShell 5.1+** or PowerShell Core
- **Python 3.x** with PIL/Pillow
- **Ollama** (for AI specifications)

### Optional
- **Shared Ollama Integration** (for optimal performance)
- **AssetStudio CLI** (for bundle extraction)

### Installing Dependencies

```powershell
# Install Pillow for Python
python -m pip install Pillow

# Or use python3
python3 -m pip install Pillow
```

## Troubleshooting

### Ollama Not Available

**Check Ollama:**
```powershell
# Test connection
Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
```

**Start Ollama:**
```powershell
ollama serve
```

**Install Models:**
```powershell
ollama pull wizardlm-uncensored:latest
ollama pull llama3.2:3b
```

### Python/Pillow Not Found

**Check Python:**
```powershell
python --version
python -m pip list | Select-String Pillow
```

**Install Pillow:**
```powershell
python -m pip install Pillow
```

### Assets Not Generating

1. **Check file permissions** - Ensure write access to mod directory
2. **Check antivirus** - May block file creation
3. **Check Python script** - Verify `generate_asset_image.py` exists
4. **Check output directory** - Verify path is correct

### Low Quality Assets

1. **Increase quality level** - Use `-Quality "ultra"`
2. **Enable Ollama** - Use `-UseOllama` for better specs
3. **Check specifications** - Review generated JSON specs
4. **Customize patterns** - Edit Python generator for custom patterns

## Advanced Usage

### Custom Spritesheet Layouts

Generate spritesheets with custom grid layouts:

```powershell
# Direct Python call for custom layouts
python generate_spritesheet.py `
    --assets "icon1.png,icon2.png,icon3.png" `
    --output "custom_sheet.png" `
    --columns 5 `
    --rows 3 `
    --frame-width 32 `
    --frame-height 32 `
    --spacing 4 `
    --type "icons"
```

### Custom Quality Settings

Edit `OllamaAssetGenerator.ps1` to customize quality settings:

```powershell
$script:QualitySettings = @{
    "custom" = @{ Size = 2048; Detail = "ultra"; Colors = 10 }
}
```

### Custom Patterns

Edit `generate_asset_image.py` to add custom pattern generators:

```python
def generate_custom_pattern(size, colors):
    # Your custom pattern logic
    pass
```

### System-Specific Customization

Edit the `Get-DefaultAssetSpec` function to add custom system themes:

```powershell
$systemColors = @{
    "CustomSystem" = @("#color1", "#color2", "#color3")
}
```

### Spritesheet Metadata

Access spritesheet metadata programmatically:

```powershell
# Load metadata JSON
$metadata = Get-Content "DragonMagic_icons_spritesheet.json" | ConvertFrom-Json
Write-Host "Grid: $($metadata.columns)x$($metadata.rows)"
Write-Host "Frame size: $($metadata.frame_width)x$($metadata.frame_height)"
Write-Host "Assets: $($metadata.asset_count)"
```

## Best Practices

1. **Start with Medium Quality** - Test with medium quality first
2. **Use Spritesheets** - Generate spritesheets for batch assets
3. **System-Specific** - Generate assets per system for consistency
4. **Review Results** - Check generated assets before committing
5. **Backup First** - Backup mod before generating many assets
6. **Use Ollama** - Enable Ollama for better, themed assets

## Output Structure

```
GeneratedAssets/
├── Textures/
│   ├── DragonMagic/
│   │   ├── dragonmagic_texture.png
│   │   └── DragonMagic_textures_spritesheet.png
│   └── BloodMagic/
│       └── bloodmagic_texture.png
├── Icons/
│   ├── DragonMagic/
│   │   └── dragonmagic_icons.png
│   └── BloodMagic/
│       └── bloodmagic_icons.png
├── Sprites/
│   └── ...
└── SpellAssets/
    └── ...
```

## See Also

- `CustomRaceClassCreatorAssetGenerator.ps1` - Base asset generator
- `ElinSpellAssetGenerator.ps1` - Spell-specific assets
- `Shared/OllamaIntegration.psm1` - Ollama integration module
- `Shared/ollama_integration.py` - Python Ollama integration

---

**Version**: 1.0  
**Last Updated**: 2024-12-26  
**Focus**: High-quality AI-powered asset generation with Ollama
