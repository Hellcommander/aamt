# Transcendence Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Transcendence toolset integrates with AAMT's unified tool detection and integration system.

## Integrated Scripts

Main Transcendence PowerShell scripts now use the unified tool detection system:

### ✅ TranscendenceAssetGenerator.ps1
- **Required Tools**: ImageMagick
- **Optional Tools**: Ollama, Blender, Python, StableDiffusion
- **Integration**: 
  - Uses unified tool detection
  - Auto-imports Ollama integration when available
  - Validates required tools at startup
- **Status**: Fully integrated

### ✅ AssetMakerAI.ps1
- **Required Tools**: Ollama
- **Optional Tools**: ImageMagick, Blender, Python, StableDiffusion
- **Integration**: 
  - Uses unified tool detection
  - Auto-imports Ollama integration when available
  - Find-Ollama function uses unified detection first, falls back to manual detection
  - Validates required tools at startup
- **Status**: Fully integrated

### ✅ NovaDriftFXGenerator.ps1
- **Required Tools**: Blender, Python, ImageMagick
- **Optional Tools**: Ollama
- **Integration**: 
  - Uses unified tool detection for Blender and Python
  - Auto-imports Ollama integration when available
  - Validates required tools at startup
- **Status**: Fully integrated

## Tool Requirements

### Required for Asset Generation
- **ImageMagick** - For image post-processing and format conversion

### Required for AI Features
- **Ollama** - For AI-assisted asset generation and description enhancement

### Required for FX Generation
- **Blender** - For 3D FX rendering
- **Python** - For particle choreography scripts
- **ImageMagick** - For image post-processing

### Optional Tools (Enhance Functionality)
- **Stable Diffusion 3** - For high-quality image generation
- **Blender** - For 3D asset generation (optional for most tools)
- **Python** - For Python-based asset generators

## Usage Examples

### Basic Asset Generation
```powershell
# TranscendenceAssetGenerator.ps1 automatically detects and uses available tools
.\TranscendenceAssetGenerator.ps1 -AssetType Ship -AssetName "scout_ship" -Description "A fast scout ship"
# If Ollama is available, it will be used automatically for enhancement
```

### AI-Enhanced Asset Generation
```powershell
# AssetMakerAI.ps1 requires Ollama
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "A fast scout ship"
# Automatically uses Ollama for AI features
```

### FX Generation
```powershell
# NovaDriftFXGenerator.ps1 requires Blender, Python, and ImageMagick
.\NovaDriftFXGenerator.ps1 -RegistryPath "fx_registry.json" -OutputDir "Output/FX"
# Automatically detects and uses all required tools
```

## Error Handling

All scripts now provide helpful error messages when tools are missing:

```
ERROR: Missing required tools for Transcendence asset generation

=== Transcendence Toolset - Tool Status ===

Required Tools:
  ImageMagick: ❌ Missing (Required)
    → Download from https://imagemagick.org/script/download.php#windows

Optional Tools (Enhance Functionality):
  Ollama: ⚠️  Not Available
  Blender: ⚠️  Not Available
  Python: ⚠️  Not Available
  StableDiffusion: ⚠️  Not Available
```

## Benefits of Integration

1. **Unified Detection**: All tools use the same detection logic
2. **Better Error Messages**: Clear installation hints when tools are missing
3. **Consistent Behavior**: All scripts handle missing tools the same way
4. **Easy Maintenance**: Tool detection logic is centralized
5. **Graceful Degradation**: Optional tools enhance but don't block execution
6. **Automatic Integration**: Ollama and Stable Diffusion modules are auto-imported when available

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## Integration with Existing Features

The unified tool detection integrates seamlessly with existing Transcendence features:
- **Ollama integration** - Auto-imports when Ollama is available
- **Stable Diffusion integration** - Auto-imports when SD3 server is running
- **ImageMagick post-processing** - Uses unified detection for magick.exe path
- **Blender rendering** - Uses unified detection for blender.exe path
- **Python scripts** - Uses unified detection for python.exe path

## Special Notes

### AssetMakerAI.ps1
- Has its own `Find-Ollama` function for backward compatibility
- Now uses unified detection first, falls back to manual detection
- Maintains all existing functionality while benefiting from unified detection

### Transcendence Asset Generation
- Uses Transcendence art as reference source for ship generation
- Can benefit from Ollama for description enhancement
- ImageMagick is required for all asset post-processing

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
