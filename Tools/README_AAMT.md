# AI-Assisted Modding Tools (AAMT)

**AI-Assisted Modding Tools (AAMT)** is a comprehensive multi-game modding toolkit that uses AI to assist with asset generation, code analysis, and mod development.

## Overview

AAMT provides AI-powered tools for modding multiple games including:
- **Starbound** - Asset generation, sprite creation, mod development
- **Elin** - Spell assets, texture generation, custom race/class creation
- **Caves of Qud** - Tile generation, character assets
- **Terraria** - Portal generation, asset creation
- **Tales of Maj'Eyal** - Asset generation
- **Transcendence** - Ship generation (uses Transcendence art as reference source)

## Core Features

### 🤖 AI Integration
- **Ollama** - Local LLM integration for prompt enhancement, code analysis, and creative assistance
- **Stable Diffusion 3 Medium** - High-quality image generation for game assets
- **Three-tier routing system** - Automatic escalation for content that might be blocked

### 🎨 Asset Generation
- Procedural and AI-generated textures, icons, sprites
- Spritesheet generation
- Multi-game asset pipelines
- Quality-aware generation (low to ultra)

### 🛠️ Development Tools
- Code analysis and fixes
- Mod checking and validation
- Asset registry and management
- Batch processing

## Quick Start

### Setup

**Repository bootstrap** (fresh clone — do this first):

```powershell
cd Tools
.\Copy-LocalSettings.ps1
# Edit TranscendenceTools.ini, AssetGenerationSettings.ps1, Qud\settings.json
.\Fetch-ThirdParty.ps1   # optional third-party clones
```

**Full setup guide**: See [`SETUP_REQUIRED_TOOLS.md`](SETUP_REQUIRED_TOOLS.md) for detailed installation instructions.

**Core Dependencies** (required for most tools):
1. **Python 3.8+** - Core runtime for many tools
2. **Ollama** - AI assistance (https://ollama.ai)
3. **Stable Diffusion 3** - Image generation (use `Install-CondaAndSetup.ps1`)

**Additional Dependencies** (tool-specific):
- **ImageMagick** - Image post-processing (required for most asset generation)
- **Blender** - 3D asset generation (required for Qud tiles, optional for others)
- **Python packages** - `requests`, `Pillow`, `typing-extensions`

**Quick Install**:
```powershell
# Install Python dependencies
cd Shared
python -m pip install requests typing-extensions Pillow

# Setup Stable Diffusion (includes Conda)
.\Install-CondaAndSetup.ps1
```

### Basic Usage

```powershell
# Generate assets with AI assistance
.\StarboundOllamaAssetGenerator.ps1 -AssetType Texture -AssetName "magicportal"

# Generate character images with SD3
.\UncensoredCharacterImageGenerator.ps1 -Description "..." -UseStableDiffusion
```

## Architecture

- **Shared Modules** (`Shared/`) - Reusable modules for all games
  - `ToolDetection.psm1` - Unified tool detection (Ollama, ImageMagick, Blender, Python, SD3)
  - `ToolsetIntegration.psm1` - Helper functions for toolset integration
  - `OllamaIntegration.psm1` - Ollama API integration
  - `StableDiffusionIntegration.psm1` - SD3 API integration
  - `ToolsetInfo.psm1` - Toolset branding and info
  - `ImageMagickPostProcessor.psm1` - Image post-processing
- **Game-Specific Tools** - Tools organized by game (Starbound/, Elin/, Qud/, etc.)
  - All toolsets can use shared modules via `ToolDetection` and `ToolsetIntegration`
- **Common Tools** - Cross-game utilities

## Toolset Integration

All game-specific toolsets can easily integrate with AAMT tools:

```powershell
# Import integration modules
Import-Module ".\Shared\ToolDetection.psm1"
Import-Module ".\Shared\ToolsetIntegration.psm1"

# Initialize tools for your toolset
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "Blender", "StableDiffusion")

# Use tools when available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    # Now use Ollama features
}
```

See **[Toolset Integration Guide](TOOLSET_INTEGRATION_GUIDE.md)** for complete documentation.

## Dependencies by Tool Type

| Tool Type | Ollama | SD3 | ImageMagick | Blender | Python |
|-----------|--------|-----|-------------|---------|--------|
| Character Image Gen | ✅ | ✅ | ✅ | ❌ | ✅ |
| Starbound Assets | ✅ | ⚠️ | ✅ | ⚠️ | ✅ |
| Qud Tiles | ❌ | ❌ | ✅ | ✅ | ❌ |
| Elin Assets | ✅ | ⚠️ | ✅ | ❌ | ✅ |
| General Post-Processing | ❌ | ❌ | ✅ | ❌ | ⚠️ |

✅ = Required | ⚠️ = Optional | ❌ = Not needed

## Documentation

- **[Setup Guide](SETUP_REQUIRED_TOOLS.md)** - Complete installation instructions
- **[Toolset Integration Guide](TOOLSET_INTEGRATION_GUIDE.md)** - How toolsets can use AAMT tools
- **[Ollama Integration](Starbound/OLLAMA_INTEGRATION.md)** - How Ollama enhances assets
- **[Image Post-Processing](AI_IMAGE_POST_PROCESSING_GUIDE.md)** - ImageMagick workflow
- **[Elin Asset Guide](Elin/OLLAMA_ASSET_GENERATOR_GUIDE.md)** - Elin-specific generation
- **[Uncensored Image Generator](UNCENSORED_IMAGE_GENERATOR_README.md)** - Character image generation

## License

Original AAMT code is **MIT** so it does not copyleft or relicense your mods.
Policy: repo-root `LICENSING.md`. Third-party clones and the Qud Lab simulator
are **not** in git — `Fetch-ThirdParty.ps1` and (if granted) `Qud/QudLab/Fetch-PrivatePack.ps1`.
