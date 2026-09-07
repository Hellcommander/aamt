# Caves of Qud Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the Caves of Qud toolset integrates with AAMT's unified tool detection and integration system.

## Integrated Scripts

All Qud PowerShell scripts now use the unified tool detection system:

### ✅ BakeQudTile.ps1
- **Required Tools**: Blender, ImageMagick
- **Optional Tools**: None
- **Integration**: Uses `Get-BlenderPath` from ToolDetection module
- **Status**: Fully integrated

### ✅ ExportQudTiles.ps1
- **Required Tools**: Blender, ImageMagick
- **Optional Tools**: None
- **Integration**: Uses unified Blender detection
- **Status**: Fully integrated

### ✅ QudTileAIGenerator.ps1
- **Required Tools**: Blender, ImageMagick
- **Optional Tools**: Ollama (for AI assistance)
- **Integration**: Uses unified detection for all tools, imports Ollama integration when available
- **Status**: Fully integrated

### ✅ GenerateVortexAssets.ps1
- **Required Tools**: Ollama, Python
- **Optional Tools**: ImageMagick
- **Integration**: Uses unified detection, imports Ollama integration
- **Status**: Fully integrated

### ✅ QudModFixer.ps1
- **Required Tools**: Ollama, Python
- **Optional Tools**: None
- **Integration**: Uses unified detection, imports Ollama integration
- **Status**: Fully integrated

### ✅ QudAudioGenerator.ps1
- **Purpose**: Generates sound effects for Qud mods (attack, hit, death, spawn, ambient, walk, use, etc.)
- **Required Tools**: Python
- **Optional Tools**: Ollama (for AI specifications), librosa/torch (for quality assessment)
- **Integration**:
  - Uses `Initialize-ToolsetTools` to check for Python (required)
  - Uses `Use-OllamaIfAvailable` when `-UseAI` is specified
  - Integrates with shared audio quality assessment system
  - Displays tool status with `Show-ToolsetStatus`
  - Exits if Python is missing
- **Status**: Fully integrated

## Tool Requirements

### Required for All Qud Tools
- **Blender** - For 3D tile baking and rendering
- **ImageMagick** - For image post-processing and format conversion

### Required for AI-Enhanced Tools
- **Ollama** - For AI-assisted asset generation and code analysis
- **Python** - For running Python-based asset generators

### Required for Audio Generation
- **Python** - For running audio generation scripts
- **numpy, soundfile** - For audio processing (install with: `pip install numpy soundfile`)

### Optional for Audio Quality Assessment
- **librosa, torch, transformers** - For advanced audio quality assessment
- **openai-whisper** - For transcription in quality assessment

## Usage Examples

### Basic Tile Baking
```powershell
# BakeQudTile.ps1 automatically detects Blender and ImageMagick
.\BakeQudTile.ps1 -DrawingPath "drawing.png" -OutputPath "tile.png"
```

### AI-Enhanced Tile Generation
```powershell
# QudTileAIGenerator.ps1 uses Ollama if available
.\QudTileAIGenerator.ps1 -DrawingPath "drawing.png" -OutputPath "tile.png"
# If Ollama is available, AI features are automatically enabled
```

### Vortex Asset Generation
```powershell
# GenerateVortexAssets.ps1 requires Ollama and Python
.\GenerateVortexAssets.ps1 -ModPath "C:\Path\To\Mod"
# Automatically checks for required tools and provides helpful error messages
```

### Audio Generation
```powershell
# QudAudioGenerator.ps1 requires Python
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all"
# With quality assessment
.\QudAudioGenerator.ps1 -ModName "Broodmother Mutation" -SoundTypes "all" -AssessQuality
```

## Error Handling

All scripts now provide helpful error messages when tools are missing:

```
ERROR: Missing required tools for Qud tile generation

=== Caves of Qud Toolset - Tool Status ===

Required Tools:
  Blender: ❌ Missing (Required)
    → Download from https://www.blender.org/download/
  ImageMagick: ❌ Missing (Required)
    → Download from https://imagemagick.org/script/download.php#windows
```

## Benefits of Integration

1. **Unified Detection**: All tools use the same detection logic
2. **Better Error Messages**: Clear installation hints when tools are missing
3. **Consistent Behavior**: All scripts handle missing tools the same way
4. **Easy Maintenance**: Tool detection logic is centralized
5. **Graceful Degradation**: Optional tools enhance but don't block execution

## Tool Detection Details

The unified system automatically searches for tools in:
- System PATH
- Environment variables (e.g., `BLENDER_PATH`)
- Common installation paths
- User-specified paths (via parameters)

## Related Scripts

### Python Scripts
- `qud_audio_generator.py` - Core Python script for audio generation
- `generate_mod_assets.py` - Asset generation (now includes audio support)
- `mutation_asset_generator.py` - Mutation asset generation
- `creature_asset_generator.py` - Creature asset generation
- `equipment_asset_generator.py` - Equipment asset generation

### Batch Files
- `QudAudioGenerator.bat` - Wrapper for QudAudioGenerator.ps1
- `GenerateModAssets.bat` - Wrapper for generate_mod_assets.py

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Qud Audio Generator Guide](./QUD_AUDIO_GENERATOR_GUIDE.md)** - Detailed guide for QudAudioGenerator
- **[Shared Audio Quality Assessment](../Shared/AUDIO_QUALITY_ASSESSMENT_README.md)** - Audio quality assessment system
- **[Asset Generation Guide](./ASSET_GENERATION_GUIDE.md)** - Complete asset generation documentation
- **[ApiMigrator](./ApiMigrator.md)** - Obsolete-API migrate / CP437 / chargen XML (Launch-ApiMigrator.bat)
- **[Folder index](./README.md)** - Every Qud tool in this directory
