# Soulash Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Soulash toolset integrates with AAMT's unified tool detection and integration system.

## Overview

The Soulash toolset generates asset definition files and placeholder images for Soulash mods. The toolset has been integrated with AAMT's unified tool detection system for consistent tool management.

## Integrated Scripts

### ✅ SoulashAssetGenerator.ps1
- **Purpose**: Generates asset definition files and placeholder images for Soulash mods
- **Required Tools**: None (uses built-in .NET System.Drawing)
- **Optional Tools**: Python, ImageMagick
- **Integration**: 
  - Uses `Initialize-ToolsetTools` to check for optional tools
  - Displays tool status with `Show-ToolsetStatus`
  - Works without external dependencies (uses System.Drawing for image generation)
- **Status**: Fully integrated

### ✅ SoulashAssetGenerator.bat
- **Purpose**: Drag-and-drop wrapper for `SoulashAssetGenerator.ps1`
- **Integration**: Added AAMT header comment
- **Status**: Updated

## Tool Requirements

### SoulashAssetGenerator.ps1
- **Required**: None (uses built-in .NET System.Drawing for placeholder generation)
- **Optional**: 
  - Python (for any Python-based utilities)
  - ImageMagick (for image post-processing)

## Usage Examples

### Generate Creature Asset
```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "demon" `
    -AssetType Creature `
    -Preset Demon `
    -GeneratePlaceholder
```

### Generate Item Asset
```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "health_potion" `
    -AssetType Item `
    -Preset Potion `
    -GeneratePlaceholder
```

### Generate Spritesheet
```powershell
.\SoulashAssetGenerator.ps1 `
    -AssetName "orc_warrior" `
    -AssetType Spritesheet `
    -Preset Humanoid `
    -SpriteWidth 32 `
    -SpriteHeight 32 `
    -AnimationFrames 4 `
    -Directions 4 `
    -GeneratePlaceholder
```

## Integration Benefits

1. **Unified Detection**: Uses the same detection logic as other toolsets
2. **Clear Error Messages**: Installation hints when tools are missing
3. **Consistent Behavior**: Handles missing tools the same way as other toolsets
4. **Optional Tools**: Python and ImageMagick enhance but don't block execution
5. **Self-Contained**: Works without external dependencies using built-in .NET graphics

## Error Handling

### Missing Optional Tools
- Script continues with built-in .NET graphics
- Clear status messages indicate missing tools
- Installation hints are provided for optional tools

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## Asset Types Supported

- **Creature**: Monsters, NPCs with spritesheets and portraits
- **Portrait**: Character face icons
- **Item**: Equipment, consumables, materials
- **Ability**: Skill/spell icons
- **Tile**: Ground, wall tiles
- **Building**: Structures
- **Effect**: Animated effects
- **Spritesheet**: Full spritesheet definitions

## Presets Available

### Creature Presets
- Demon, Undead, Beast, Humanoid, Elemental, Construct

### Item Presets
- Weapon, Armor, Potion, Book, Gem, Food, Tool

### Ability Presets
- Attack, Magic, Buff, Debuff, Passive

### Tile Presets
- Ground, Wall, Door, Container, Decoration

## Output Structure

The generator creates:
- JSON asset definition files
- Placeholder images (if `-GeneratePlaceholder` is used)
- Spritesheet layout guides (for creatures and spritesheets)
- Organized directory structure by asset type

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
- **[Soulash Asset Generator Guide](./SOULASH_ASSET_GENERATOR_GUIDE.md)** - Detailed guide for Soulash asset generation
