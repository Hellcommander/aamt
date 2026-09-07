# Elin Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Elin toolset integrates with AAMT's unified tool detection and integration system.

## Overview

The Elin toolset generates assets for the Elin game mods, with extensive AI-assisted generation using Ollama. The toolset has been integrated with AAMT's unified tool detection system for consistent tool management.

## Integrated Scripts

### ✅ OllamaAssetGenerator.ps1
- **Purpose**: Enhanced Ollama-powered asset generator for Elin mods
- **Required Tools**: None (all tools optional)
- **Optional Tools**: Ollama, Python, ImageMagick
- **Integration**: 
  - Uses `Initialize-ToolsetTools` to check for optional tools
  - Uses `Use-OllamaIfAvailable` for Ollama integration
  - Displays tool status with `Show-ToolsetStatus`
  - Graceful degradation if Ollama is unavailable
- **Status**: Fully integrated

### ✅ ElinSpellAssetGenerator.ps1
- **Purpose**: Generates spell assets (icons, FX, projectiles, buffs) for Elin
- **Required Tools**: Python
- **Optional Tools**: Ollama, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check for Python (required)
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Displays tool status with `Show-ToolsetStatus`
  - Exits if Python is missing
- **Status**: Fully integrated

### ✅ ElinSpellAudioGenerator.ps1
- **Purpose**: Generates spell sound effects (cast, impact, loop) for Elin
- **Required Tools**: Python
- **Optional Tools**: Ollama (for AI specifications), librosa/torch (for quality assessment)
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check for Python (required)
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Integrates with shared audio quality assessment system
  - Displays tool status with `Show-ToolsetStatus`
  - Exits if Python is missing
- **Status**: Fully integrated

### ✅ ElinTextureGenerator.ps1
- **Purpose**: Generates texture files for Elin mods
- **Required Tools**: None (uses built-in .NET graphics)
- **Optional Tools**: Python, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Displays tool status with `Show-ToolsetStatus`
  - Works without external dependencies
- **Status**: Fully integrated

### ✅ CustomRaceClassCreatorAssetGenerator.ps1
- **Purpose**: Comprehensive asset generator for CustomRaceClassCreator mod
- **Required Tools**: None (all tools optional)
- **Optional Tools**: Ollama, Python, Blender, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Displays tool status with `Show-ToolsetStatus`
  - Uses unified Python detection (replaces manual `Get-Command python`)
- **Status**: Fully integrated

### ✅ MagicUIElementGenerator.ps1
- **Purpose**: Generates magic-themed UI elements for CustomRaceClassCreator
- **Required Tools**: None
- **Optional Tools**: Ollama, Python, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Displays tool status with `Show-ToolsetStatus`
- **Status**: Fully integrated

### ✅ SlotMagicAssetGenerator.ps1
- **Purpose**: Generates slot machine UI elements for SlotMagic system
- **Required Tools**: None
- **Optional Tools**: Ollama, Python, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Displays tool status with `Show-ToolsetStatus`
- **Status**: Fully integrated

### ✅ BatchAssetGenerator.ps1
- **Purpose**: Batch processes all mod assets using OllamaAssetGenerator
- **Required Tools**: None
- **Optional Tools**: Ollama, Python, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Displays tool status with `Show-ToolsetStatus`
  - Calls OllamaAssetGenerator.ps1 which has its own tool detection
- **Status**: Fully integrated

### ✅ CustomRaceClassCreatorModChecker.ps1
- **Purpose**: AI-guided mod checker for CustomRaceClassCreator
- **Required Tools**: None
- **Optional Tools**: Ollama, Python
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Displays tool status with `Show-ToolsetStatus`
  - Works without Ollama (reduced functionality)
- **Status**: Fully integrated

## Tool Requirements

### OllamaAssetGenerator.ps1
- **Required**: None
- **Optional**: 
  - Ollama (for AI-powered specifications)
  - Python (for Python-based utilities)
  - ImageMagick (for image post-processing)

### ElinSpellAssetGenerator.ps1
- **Required**: Python (for running `elin_spell_assets.py`)
- **Optional**: 
  - Ollama (for AI-assisted spell design)
  - ImageMagick (for image post-processing)

### ElinSpellAudioGenerator.ps1
- **Required**: Python (for running `elin_spell_audio.py`)
- **Optional**: 
  - Ollama (for AI-assisted audio specifications)
  - librosa, torch, transformers (for advanced audio quality assessment)
  - openai-whisper (for transcription in quality assessment)

### ElinTextureGenerator.ps1
- **Required**: None (uses built-in .NET System.Drawing)
- **Optional**: 
  - Python (for any Python-based utilities)
  - ImageMagick (for image post-processing)

### CustomRaceClassCreatorAssetGenerator.ps1
- **Required**: None
- **Optional**: 
  - Ollama (for AI-powered asset specifications)
  - Python (for Python-based asset generation)
  - Blender (for 3D asset generation)
  - ImageMagick (for image post-processing)

### MagicUIElementGenerator.ps1
- **Required**: None
- **Optional**: 
  - Ollama (for AI-powered UI design)
  - Python (for Python-based utilities)
  - ImageMagick (for image post-processing)

### SlotMagicAssetGenerator.ps1
- **Required**: None
- **Optional**: 
  - Ollama (for AI-powered symbol design)
  - Python (for Python-based utilities)
  - ImageMagick (for image post-processing)

### CustomRaceClassCreatorModChecker.ps1
- **Required**: None
- **Optional**: 
  - Ollama (for AI-powered code analysis and fixes)
  - Python (for Python-based utilities)

## Usage Examples

### Generate Assets with Ollama
```powershell
.\OllamaAssetGenerator.ps1 `
    -ModPath "E:\...\CustomRaceClassCreator" `
    -AssetTypes "textures,icons" `
    -UseOllama
```

### Generate Spell Assets
```powershell
.\ElinSpellAssetGenerator.ps1 `
    -SpellDescription "Nature Magic - Verdant Pulse" `
    -GenerateAll `
    -UseAI
```

### Generate Spell Audio
```powershell
.\ElinSpellAudioGenerator.ps1 `
    -SpellDescription "Nature Magic - Verdant Pulse" `
    -GenerateAll `
    -UseAI `
    -AssessQuality
```

### Generate Textures
```powershell
.\ElinTextureGenerator.ps1 `
    -TextureName "my_item" `
    -TextureType Item `
    -Preset Basic
```

## Integration Benefits

1. **Unified Detection**: All tools use the same detection logic
2. **Clear Error Messages**: Installation hints when tools are missing
3. **Consistent Behavior**: All toolsets handle missing tools the same way
4. **Python Path Detection**: Unified detection finds Python even if not in PATH
5. **Ollama Status**: Clear indication when Ollama is available for AI features
6. **Graceful Degradation**: Optional tools enhance but don't block execution

## Error Handling

### Missing Python (ElinSpellAssetGenerator)
- Script will exit with error
- Clear installation instructions are displayed
- Other scripts work without Python

### Missing Ollama
- Scripts continue without AI features
- Warning message is displayed
- User can choose to continue or install Ollama

### Missing Optional Tools
- Scripts continue with reduced functionality
- Clear status messages indicate missing tools
- Installation hints are provided

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## Related Scripts

### Python Scripts
- `elin_spell_assets.py` - Core Python script for spell asset generation
- `elin_spell_audio.py` - Core Python script for spell audio generation
- `generate_asset_image.py` - Asset image generation utility
- `generate_spritesheet.py` - Spritesheet generation utility

### Batch Files
- `OllamaAssetGenerator.bat` - Wrapper for OllamaAssetGenerator.ps1
- `ElinSpellAssetGenerator.bat` - Wrapper for ElinSpellAssetGenerator.ps1
- `ElinSpellAudioGenerator.bat` - Wrapper for ElinSpellAudioGenerator.ps1
- `CustomRaceClassCreatorAssetGenerator.bat` - Wrapper for CustomRaceClassCreatorAssetGenerator.ps1

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
- **[Ollama Asset Generator Guide](./OLLAMA_ASSET_GENERATOR_GUIDE.md)** - Detailed guide for OllamaAssetGenerator
- **[Elin Spell Audio Guide](./ELIN_SPELL_AUDIO_GUIDE.md)** - Detailed guide for ElinSpellAudioGenerator
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Audio quality assessment system
