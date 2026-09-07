# Asset Maker AI - Guide

AI-powered asset creation tool for Transcendence mods using [Ollama](https://ollama.ai/) local AI models.

## Features

- **Generate Asset Names**: Create thematic names for ships, items, weapons, etc.
- **Generate Descriptions**: Write engaging descriptions for game assets
- **Create XML Configurations**: Generate valid Transcendence XML code
- **Optimize Assets**: Get AI suggestions for improving asset metadata
- **Generate Credits**: Create professional credits text for mods
- **Generate 3D Models**: Create 3D models from text descriptions using Ollama + Blender

## Prerequisites

1. **Ollama** - Download from [https://ollama.ai/download](https://ollama.ai/download)
   - Or use the latest release: [v0.13.5](https://github.com/ollama/ollama/releases/tag/v0.13.5)
   - Install and ensure it's in your PATH or detected by the script

2. **AI Model** - Pull a model (recommended: `llama3.2`)
   ```powershell
   ollama pull llama3.2
   ```

## Quick Start

### 1. Check Ollama Installation
```powershell
.\AssetMakerAI.ps1 -CheckOllama
```

### 2. List Available Models
```powershell
.\AssetMakerAI.ps1 -ListModels
```

### 3. Generate Asset Name
```powershell
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "A fast scout ship with advanced sensors"
```

### 4. Generate Description
```powershell
.\AssetMakerAI.ps1 -Action GenerateDescription -AssetType Ship -InputData "SwiftScout"
```

### 5. Create XML Configuration
```powershell
.\AssetMakerAI.ps1 -Action CreateXML -AssetType Ship -InputData "SwiftScout"
```

### 6. Optimize Asset Metadata
```powershell
.\AssetMakerAI.ps1 -Action OptimizeAsset -InputData "MyMod\Assets\ship_metadata.json"
```

### 7. Generate Credits
```powershell
.\AssetMakerAI.ps1 -Action GenerateCredits -InputData "MyAwesomeMod"
```

### 8. Generate 3D Model from Description
```powershell
.\AssetMakerAI.ps1 -Action Generate3DModel -InputData "a simple low-poly fantasy tree" -ModelFormat OBJ -DetailLevel LowPoly
```

### 9. Generate Ship Model
```powershell
.\AssetMakerAI.ps1 -Action Generate3DModel -InputData "a sleek space fighter with twin engines and forward-swept wings" -ModelFormat FBX -DetailLevel Medium -OutputPath "MyMod\Models\fighter.fbx"
```

### 10. Generate Procedural Texture
```powershell
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "cracked stone texture, low contrast" -TextureMethod Procedural -TextureSize 256
```

### 11. Generate Texture and Add to Spritesheet
```powershell
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "rusty metal texture" -TextureMethod Procedural -SpritesheetPath "MyMod\Resources\spritesheet.png" -TileSize 128 -SpritesheetColumns 8
```

### 12. Batch Generate Textures
```powershell
# Create a text file with descriptions (one per line)
# textures.txt:
# cracked stone texture
# rusty metal texture
# smooth marble texture

.\AssetMakerAI.ps1 -Action BatchTextures -InputData "textures.txt" -TextureMethod Procedural -SpritesheetPath "MyMod\Resources\spritesheet.png"
```

### 13. Assemble Existing Textures into Spritesheet
```powershell
.\AssetMakerAI.ps1 -Action AssembleSpritesheet -InputData "MyMod\Textures" -SpritesheetPath "MyMod\Resources\spritesheet.png" -TileSize 128 -SpritesheetColumns 8
```

## Parameters

- **`-Action`**: Action to perform
  - `GenerateName` - Generate asset name
  - `GenerateDescription` - Generate description
  - `CreateXML` - Generate XML configuration
  - `OptimizeAsset` - Optimize asset metadata
  - `GenerateCredits` - Generate credits text
  - `Generate3DModel` - Generate 3D model from description (requires Blender)
  - `GenerateTexture` - Generate texture from description (requires Blender for Procedural)
  - `AssembleSpritesheet` - Assemble existing textures into a spritesheet
  - `BatchTextures` - Batch generate multiple textures from a list

- **`-AssetType`**: Type of asset
  - `Ship`, `Item`, `Weapon`, `Station`, `Projectile`, `Effect`, `Other`

- **`-InputData`**: Input for AI processing
  - For `GenerateName`: Description of the asset
  - For `GenerateDescription`: Asset name
  - For `CreateXML`: Asset name or JSON file path
  - For `OptimizeAsset`: File path to metadata
  - For `GenerateCredits`: Mod name

- **`-Model`**: Ollama model to use (default: auto-detected)
  - Examples: `llama3.2`, `llama3.1`, `mistral`, `phi3`

- **`-OutputPath`**: Output directory or file path (default: `AI_Generated_Assets`)

- **`-OllamaPath`**: Path to Ollama executable (auto-detected if not provided)

- **`-BlenderPath`**: Path to Blender executable (auto-detected if not provided, required for Generate3DModel)

- **`-ModelFormat`**: 3D model export format (for Generate3DModel)
  - `OBJ`, `FBX`, `GLB`, `GLTF`, `STL`, `PLY` (default: `OBJ`)

- **`-DetailLevel`**: Level of detail for 3D models (for Generate3DModel)
  - `LowPoly` - Minimal vertices, game-ready
  - `Medium` - Balanced quality/performance
  - `HighDetail` - Fine features, close-up renders
  - `Procedural` - Procedural generation techniques (default: `Medium`)

- **`-TextureMethod`**: Method for texture generation (for GenerateTexture)
  - `Procedural` - Generate using Blender procedural nodes (default)
  - `Diffusion` - Use local Stable Diffusion (not yet implemented)
  - `Hybrid` - Combine procedural and diffusion (not yet implemented)

- **`-TextureSize`**: Size of generated textures in pixels (default: `256`)

- **`-TileSize`**: Size of tiles in spritesheet (default: `128`)

- **`-SpritesheetColumns`**: Number of columns in spritesheet grid (default: `8`)

- **`-SpritesheetPath`**: Path to spritesheet file (optional, will create if doesn't exist)

- **`-CheckOllama`**: Check if Ollama is installed and running

- **`-ListModels`**: List available Ollama models

## Examples

### Generate a Ship Name
```powershell
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "A heavily armored battleship designed for frontline combat"
```

### Generate Full Ship Configuration
```powershell
# Step 1: Generate name
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "Fast interceptor" -OutputPath "MyShip"

# Step 2: Generate description (use the generated name)
.\AssetMakerAI.ps1 -Action GenerateDescription -AssetType Ship -InputData "Thunderbolt" -OutputPath "MyShip"

# Step 3: Create XML
.\AssetMakerAI.ps1 -Action CreateXML -AssetType Ship -InputData "Thunderbolt" -OutputPath "MyShip"
```

### Batch Processing
```powershell
# Generate multiple names
$descriptions = @(
    "Fast scout ship",
    "Heavy battleship",
    "Cargo freighter"
)

foreach ($desc in $descriptions) {
    .\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData $desc -OutputPath "BatchOutput"
}
```

## Integration with ExportModAssets.ps1

You can combine AI generation with asset export:

```powershell
# 1. Export assets from TranscendenceArt
.\ExportModAssets.ps1 -AssetType Ship -ExportAll -OutputPath "MyMod\Assets"

# 2. Generate names and descriptions using AI
.\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "Commonwealth fleet ship" -OutputPath "MyMod\Assets"

# 3. Create XML configurations
.\AssetMakerAI.ps1 -Action CreateXML -AssetType Ship -InputData "MyMod\Assets\generated_name.txt" -OutputPath "MyMod"

# 4. Generate placeholder textures
.\AssetMakerAI.ps1 -Action BatchTextures -InputData "texture_descriptions.txt" -TextureMethod Procedural -SpritesheetPath "MyMod\Resources\spritesheet.png"

# 5. Assemble all textures into spritesheet
.\AssetMakerAI.ps1 -Action AssembleSpritesheet -InputData "MyMod\Textures" -SpritesheetPath "MyMod\Resources\spritesheet.png"
```

## Texture Generation Workflow

### Placeholder Art Generation

Perfect for rapid prototyping and placeholder assets:

```powershell
# Generate textures for spell icons
$spellTextures = @(
    "nature magic leaf icon, green",
    "nature magic vine icon, dark green",
    "arachnomancy spider web icon, black",
    "arachnomancy venom drop icon, purple"
)

foreach ($desc in $spellTextures) {
    .\AssetMakerAI.ps1 -Action GenerateTexture -InputData $desc -TextureMethod Procedural -TextureSize 128 -SpritesheetPath "MyMod\Resources\spell_icons.png" -TileSize 128
}
```

### Batch Processing

Create a text file with descriptions and generate all at once:

```powershell
# textures.txt contains:
# cracked stone texture, low contrast
# rusty metal texture, orange-brown
# smooth marble texture, white with gray veins
# wooden planks texture, brown

.\AssetMakerAI.ps1 -Action BatchTextures -InputData "textures.txt" -OutputPath "MyMod\Textures" -TextureMethod Procedural -SpritesheetPath "MyMod\Resources\spritesheet.png"
```

### Spritesheet Management

The tool automatically:
- Finds the first empty slot in the spritesheet
- Resizes textures to match tile size
- Creates new spritesheets if they don't exist
- Maintains consistent grid layout

For manual control, use the Python script:
```powershell
python spritesheet_assembly.py --tile "texture.png" --sheet "spritesheet.png" --tileSize 128 --columns 8
```

## Troubleshooting

### Ollama Not Found
- Install Ollama from [https://ollama.ai/download](https://ollama.ai/download)
- Or specify path: `-OllamaPath "C:\Path\To\Ollama\ollama.exe"`

### Ollama Service Not Running
- The script will try to start it automatically
- Or run manually: `ollama serve`

### Model Not Found
- Pull a model: `ollama pull llama3.2`
- Or specify a different model: `-Model mistral`

### Slow Responses
- Use smaller models (e.g., `phi3` instead of `llama3.2`)
- Ensure Ollama is using GPU acceleration if available

## Recommended Models

- **`llama3.2`** (Default) - Good balance of quality and speed
- **`llama3.1`** - Higher quality, slower
- **`mistral`** - Fast and efficient
- **`phi3`** - Very fast, smaller model
- **`gemma2`** - Google's model, good for structured output

## Notes

- All AI-generated content should be reviewed and edited as needed
- XML output may need manual adjustments for your specific mod
- Generated names and descriptions are suggestions - customize to fit your mod's style
- The tool uses local AI models - no data is sent to external servers

## References

- [Ollama GitHub](https://github.com/ollama/ollama)
- [Ollama Latest Release (v0.13.5)](https://github.com/ollama/ollama/releases/tag/v0.13.5)
- [Transcendence Modding Forums](https://forums.kronosaur.com/)

