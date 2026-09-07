# Terraria Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Terraria toolset integrates with AAMT's unified tool detection and integration system.

## Overview

The Terraria toolset generates portal assets for tModLoader mods, with optional AI-assisted generation using Ollama. The toolset has been integrated with AAMT's unified tool detection system for consistent tool management.

## Integrated Scripts

### ✅ TerrariaPortalOllamaGenerator.ps1
- **Purpose**: Generates animated portal spritesheets using Ollama for AI-assisted design
- **Required Tools**: Python, Ollama
- **Optional Tools**: ImageMagick
- **Integration**: 
  - Uses `Initialize-ToolsetTools` to check for Python and Ollama
  - Uses `Get-PythonPath` for Python executable detection
  - Uses `Get-OllamaInfo` for Ollama status
  - Displays tool status with `Show-ToolsetStatus`
  - Graceful fallback if Ollama is unavailable (with user confirmation)
- **Status**: Fully integrated

### ✅ TerrariaPortalGenerator.ps1
- **Purpose**: Generates complete portal effect packages (textures, JSON profiles, code templates)
- **Required Tools**: None (uses built-in .NET graphics)
- **Optional Tools**: Python, ImageMagick
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check optional tools
  - Displays tool status with `Show-ToolsetStatus`
  - Works without external dependencies (uses System.Drawing)
- **Status**: Fully integrated

### ✅ TerrariaPortalAudioGenerator.ps1
- **Purpose**: Generates portal sound effects (activation, ambient, teleport, deactivation)
- **Required Tools**: Python
- **Optional Tools**: Ollama (for AI specifications), librosa/torch (for quality assessment)
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check for Python (required)
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Integrates with shared audio quality assessment system
  - Displays tool status with `Show-ToolsetStatus`
  - Exits if Python is missing
- **Status**: Fully integrated

### ✅ TerrariaPortalOllamaGenerator.bat
- **Purpose**: Wrapper script for `TerrariaPortalOllamaGenerator.ps1`
- **Integration**: Added AAMT header comment
- **Status**: Updated

### ✅ TerrariaPortalGenerator.bat
- **Purpose**: Drag-and-drop wrapper for `TerrariaPortalGenerator.ps1`
- **Integration**: Added AAMT header comment
- **Status**: Updated

## Tool Requirements

### TerrariaPortalOllamaGenerator.ps1
- **Required**: 
  - Python (for running `terraria_portal_ollama_generator.py`)
  - Ollama (for AI-assisted portal design generation)
- **Optional**: 
  - ImageMagick (for image post-processing)

### TerrariaPortalGenerator.ps1
- **Required**: None (uses built-in .NET System.Drawing)
- **Optional**: 
  - Python (for any Python-based utilities)
  - ImageMagick (for image post-processing)

### TerrariaPortalAudioGenerator.ps1
- **Required**: Python (for running `terraria_portal_audio_generator.py`)
- **Optional**: 
  - Ollama (for AI-assisted audio specifications)
  - librosa, torch, transformers (for advanced audio quality assessment)
  - openai-whisper (for transcription in quality assessment)

## Usage Examples

### Generate Portal with Ollama
```powershell
.\TerrariaPortalOllamaGenerator.ps1 `
    -PortalName "VoidPortal" `
    -Description "A cold blue void portal with spacetime distortion" `
    -Preset Void `
    -TileSize 16 `
    -FrameCount 8
```

### Generate Portal Package (No AI)
```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "FirePortal" `
    -Preset Fire `
    -GeneratePlaceholders
```

### Generate Portal Audio
```powershell
.\TerrariaPortalAudioGenerator.ps1 `
    -PortalName "VoidPortal" `
    -Preset Void `
    -GenerateAll `
    -AssessQuality
```

## Integration Benefits

1. **Unified Detection**: All tools use the same detection logic
2. **Clear Error Messages**: Installation hints when tools are missing
3. **Consistent Behavior**: All toolsets handle missing tools the same way
4. **Python Path Detection**: Unified detection finds Python even if not in PATH
5. **Ollama Status**: Clear indication when Ollama is available for AI features
6. **Graceful Degradation**: Optional tools enhance but don't block execution

## Error Handling

### Missing Ollama
- `TerrariaPortalOllamaGenerator.ps1` will prompt the user to continue with fallback
- Fallback designs are generic and not recommended
- User can choose to exit and install Ollama

### Missing Python
- `TerrariaPortalOllamaGenerator.ps1` will exit with error
- Clear installation instructions are displayed
- `TerrariaPortalGenerator.ps1` works without Python

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## Related Scripts

### Python Scripts
- `terraria_portal_ollama_generator.py` - Core Python script for Ollama-based generation
- `terraria_portal_quality_checker.py` - Quality checking for generated portals
- `terraria_portal_audio_generator.py` - Core Python script for portal audio generation

### Batch Files
- `GenerateTerrariaPortals.bat` - Batch generation script
- `GenerateAllCrossModPortals.bat` - Cross-mod portal generation
- `terraria_portal_ollama_generator.bat` - Python script wrapper
- `TerrariaPortalAudioGenerator.bat` - Wrapper for TerrariaPortalAudioGenerator.ps1

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
- **[Terraria Portal Guide](./TERRARIA_PORTAL_GUIDE.md)** - Terraria-specific portal generation guide
- **[Terraria Portal Audio Guide](./TERRARIA_PORTAL_AUDIO_GUIDE.md)** - Portal audio generation guide
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Audio quality assessment system
