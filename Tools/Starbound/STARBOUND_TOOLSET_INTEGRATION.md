# Starbound Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Starbound toolset integrates with AAMT's unified tool detection and integration system.

## Integrated Scripts

All main Starbound PowerShell scripts now use the unified tool detection system:

### ✅ StarboundOllamaAssetGenerator.ps1
- **Required Tools**: ImageMagick
- **Optional Tools**: Ollama, StableDiffusion, Python, Blender
- **Integration**: 
  - Uses unified tool detection
  - Auto-imports Ollama integration when available
  - Validates required tools at startup
- **Status**: Fully integrated

### ✅ StarboundAssetGenerator.ps1
- **Required Tools**: ImageMagick
- **Optional Tools**: Ollama, StableDiffusion, Python, Blender
- **Integration**: 
  - Uses unified tool detection
  - Auto-imports Ollama integration when available
  - Validates required tools at startup
- **Status**: Fully integrated

### ✅ OllamaImageGenerator.ps1
- **Required Tools**: ImageMagick
- **Optional Tools**: Ollama, StableDiffusion
- **Integration**: 
  - Uses unified tool detection
  - Auto-imports Ollama and Stable Diffusion integration when available
  - Validates required tools at startup
  - Gracefully degrades if optional tools are missing
- **Status**: Fully integrated

### ✅ StarboundSoundGenerator.ps1
- **Purpose**: Generates sound effects for Starbound mods
- **Required Tools**: Python (for `generate_sound.py` or `starbound_audio_generator.py`)
- **Optional Tools**: Ollama (for AI-assisted descriptions), librosa/torch (for quality assessment)
- **Integration**:
  - Uses existing `generate_sound.py` or enhanced `starbound_audio_generator.py`
  - Can use Ollama for AI-generated descriptions
  - Supports multiple sound types (Impact, Charge, Ambient, Magic, Mechanical, Organic, Explosion, Whoosh, Roar)
  - Can integrate with shared audio quality assessment system
- **Status**: Integrated (can be enhanced with quality assessment)

## Tool Requirements

### Required for All Starbound Tools
- **ImageMagick** - For image post-processing and format conversion

### Optional Tools (Enhance Functionality)
- **Ollama** - For AI-assisted asset generation and description enhancement
- **Stable Diffusion 3** - For high-quality image generation
- **Python** - For Python-based asset generators (required for sound generation)
- **Blender** - For 3D asset generation (some tools)
- **librosa, torch, transformers** - For advanced audio quality assessment

## Usage Examples

### Basic Asset Generation
```powershell
# StarboundAssetGenerator.ps1 automatically detects and uses available tools
.\StarboundAssetGenerator.ps1 -AssetType Texture -AssetName "magicportal"
# If Ollama is available, it will be used automatically for enhancement
```

### AI-Enhanced Asset Generation
```powershell
# StarboundOllamaAssetGenerator.ps1 uses Ollama if available
.\StarboundOllamaAssetGenerator.ps1 -AssetType Particle -AssetName "magicportal" -Prompt "purple swirling energy"
# Automatically uses Ollama for description enhancement
```

### High-Quality Image Generation
```powershell
# OllamaImageGenerator.ps1 uses both Ollama and Stable Diffusion if available
.\OllamaImageGenerator.ps1 -Description "A magical portal" -UseStableDiffusion
# Workflow: Ollama enhances description → SD3 generates high-quality image
```

### Sound Effect Generation
```powershell
# StarboundSoundGenerator.ps1 generates sound effects
.\StarboundSoundGenerator.ps1 -SoundName "magicImpact" -Preset Magic
# Uses Python script for procedural audio generation
```

## Error Handling

All scripts now provide helpful error messages when tools are missing:

```
ERROR: Missing required tools for Starbound asset generation

=== Starbound Toolset - Tool Status ===

Required Tools:
  ImageMagick: ❌ Missing (Required)
    → Download from https://imagemagick.org/script/download.php#windows

Optional Tools (Enhance Functionality):
  Ollama: ⚠️  Not Available
  StableDiffusion: ⚠️  Not Available
  Python: ⚠️  Not Available
  Blender: ⚠️  Not Available
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

The unified tool detection integrates seamlessly with existing Starbound features:
- **Ollama integration** - Auto-imports when Ollama is available
- **Stable Diffusion integration** - Auto-imports when SD3 server is running
- **ImageMagick post-processing** - Uses unified detection for magick.exe path
- **C++ backend** - Can use Ollama for enhanced generation when available

## Related Scripts

### Python Scripts
- `generate_sound.py` - Basic sound generation script
- `starbound_audio_generator.py` - Enhanced audio generator with more sound types and features

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Ollama Integration](OLLAMA_INTEGRATION.md)** - How Ollama enhances Starbound assets
- **[Starbound Audio Generator Guide](STARBOUND_AUDIO_GENERATOR_GUIDE.md)** - Sound effect generation guide
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Audio quality assessment system
- **[Main README](../README_AAMT.md)** - Overview of AAMT
