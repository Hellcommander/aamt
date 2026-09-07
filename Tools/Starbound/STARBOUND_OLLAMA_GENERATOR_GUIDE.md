# Starbound Ollama Asset Generator Guide

Generate Starbound assets using Ollama AI for creative descriptions and parameter suggestions.

## Prerequisites

1. **Install Ollama**: Download from [ollama.ai](https://ollama.ai)
2. **Start Ollama**: Run `ollama serve` in a terminal (or it will auto-start)
3. **Install a model**: `ollama pull llama3.2` (or another model)

### Shared Integration Module

The generator automatically uses the shared `OllamaIntegration.psm1` module if available (located in `../Shared/`). This provides:
- **Automatic Ollama startup** if not running
- **Model auto-selection** based on task type
- **Optimal thread usage** for performance
- **CPU throttling** to prevent system overload
- **Better error handling** and retry logic

If the shared module is not found, the generator falls back to a basic implementation.

## Quick Start

### Basic Usage

```powershell
# Generate a particle effect with AI assistance
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "magicportal" `
    -Prompt "purple swirling magical energy with sparkles"
```

### Generate Multiple Variations

```powershell
# Generate 3 variations of a texture
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Texture `
    -AssetName "runicstone" `
    -GenerateMultiple 3
```

### Using Different Models

```powershell
# Use a different Ollama model
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Icon `
    -AssetName "spellicon" `
    -OllamaModel "llama3.1" `
    -Prompt "arcane magic symbol"
```

## Asset Types

### Particle Effects

Generates particle effects with AI-suggested colors, velocities, and behaviors.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "firestorm" `
    -Prompt "intense fire particles with orange and red colors, rising upward"
```

**Output**: `.particle` files with AI-generated parameters

### Textures

Generates texture descriptions and parameters for procedural generation.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Texture `
    -AssetName "ancientrune" `
    -Prompt "weathered stone with glowing runic inscriptions"
```

**Output**: Texture parameters and `.frames` files

### Animations

Generates animation descriptions with frame count and timing suggestions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Animation `
    -AssetName "spellcast" `
    -Prompt "wizard casting spell with energy gathering effect"
```

**Output**: Animation parameters and metadata

### Icons

Generates icon descriptions with style and shape suggestions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Icon `
    -AssetName "manaorb" `
    -Prompt "glowing blue mana orb icon"
```

**Output**: Icon parameters and metadata

### Spells

Generates spell descriptions with type and effect suggestions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Spell `
    -AssetName "icebolt" `
    -Prompt "ice projectile spell that freezes enemies"
```

**Output**: Spell definitions and parameters

### Projectiles

Generates projectile descriptions with appearance and behavior.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Projectile `
    -AssetName "lightningbolt" `
    -Prompt "electric projectile with crackling energy trail"
```

**Output**: Projectile definitions and parameters

### Item Sprites

Generates sprites for items (weapons, tools, consumables, etc.) with AI-generated descriptions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType ItemSprite `
    -AssetName "magicsword" `
    -Prompt "magical sword with glowing blue blade and runic inscriptions"
```

**Output**: PNG sprite file and `.frames` metadata file in `assets/items/sprites/`

### Mech Sprites

Generates sprites for mechs (UI icons and previews) with AI-generated descriptions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType MechSprite `
    -AssetName "phoenix_icon" `
    -Prompt "phoenix mech icon with orange and red colors, robotic appearance"
```

**Output**: PNG sprite file and `.frames` metadata file in `assets/mechs/sprites/`

### General Sprites

Generates general-purpose sprites with AI-generated descriptions.

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Sprite `
    -AssetName "customsprite" `
    -Prompt "pixel art sprite with purple and blue colors"
```

**Output**: PNG sprite file and `.frames` metadata file in `assets/sprites/`

## Integration with Existing Tools

The Ollama generator integrates seamlessly with existing generators:

1. **Uses Ollama** to generate creative descriptions
2. **Extracts parameters** from descriptions using AI
3. **Feeds into** `StarboundAssetGenerator.ps1` for actual generation
4. **Supports C++ backend** with `-UseCppBackend` flag

## Using with Particle Generator

The `StarboundParticleGenerator.ps1` also supports Ollama directly:

```powershell
.\StarboundParticleGenerator.ps1 `
    -ParticleName "magicsparkle" `
    -UseAI `
    -Description "purple magical sparkles"
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-AssetType` | String | Required | Particle, Texture, Animation, Icon, Spell, Projectile, Sprite, ItemSprite, MechSprite |
| `-AssetName` | String | Required | Name of the asset |
| `-Prompt` | String | "" | Optional prompt for Ollama |
| `-OllamaModel` | String | "llama3.2" | Ollama model to use |
| `-OllamaUrl` | String | "http://localhost:11434" | Ollama API URL |
| `-OutputDir` | String | Mod assets folder | Output directory |
| `-UseCppBackend` | Switch | False | Use C++ backend for generation |
| `-GenerateMultiple` | Int | 1 | Number of variations to generate |

## Output Structure

Generated assets are placed in the mod's assets folder:

```
mods/Magi-Tech Arcane Alchemy and Sorcery/assets/
├── particles/
│   └── magicportal.particle
├── textures/
│   ├── runicstone.png
│   └── runicstone.frames
└── animations/
    └── spellcast/
```

## Workflow Example

### Complete Asset Generation Pipeline

```powershell
# 1. Generate particle effect with AI
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "portalenergy" `
    -Prompt "mystical portal energy with purple and blue swirls"

# 2. Generate matching texture
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Texture `
    -AssetName "portaltexture" `
    -Prompt "ethereal portal texture with energy patterns"

# 3. Generate icon
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Icon `
    -AssetName "portalicon" `
    -Prompt "portal icon with magical symbols"
```

## Tips

1. **Be specific in prompts**: More detail = better results
2. **Use multiple variations**: Generate several and pick the best
3. **Combine with presets**: Use presets as starting points, then enhance with AI
4. **Iterate**: Generate, review, adjust prompt, regenerate

## Troubleshooting

### Ollama Not Responding

```powershell
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve
```

### Model Not Found

```powershell
# List available models
ollama list

# Pull a model
ollama pull llama3.2
```

### Poor Quality Results

- Try a different model (e.g., `llama3.1`, `mistral`)
- Provide more detailed prompts
- Generate multiple variations and select the best

## Advanced Usage

### Custom Output Directory

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Particle `
    -AssetName "testparticle" `
    -OutputDir "C:\MyAssets\Starbound"
```

### Using C++ Backend

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType Texture `
    -AssetName "proceduraltexture" `
    -UseCppBackend `
    -Prompt "noise-based texture with organic patterns"
```

### Batch Generation

```powershell
$assets = @("fire", "ice", "lightning", "poison")
foreach ($asset in $assets) {
    .\StarboundOllamaAssetGenerator.ps1 `
        -AssetType Particle `
        -AssetName "$asset`effect" `
        -Prompt "$asset elemental effect"
}
```

## Related Tools

- `StarboundAssetGenerator.ps1` - Base asset generator
- `StarboundParticleGenerator.ps1` - Particle generator with AI support
- `StarboundCppBackendBridge.ps1` - C++ backend integration

---

*Compatible with Ollama 0.1+ and Starbound 1.4+*
