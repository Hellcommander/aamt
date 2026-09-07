# Quality-Aware AI Prompt Template Guide

## Overview

This guide explains how to use the quality-aware AI prompt template for generating procedural material specifications from your unified asset registry. The template is designed to be:

- **Deterministic**: Same registry entry → same output → same textures
- **Registry-Driven**: Reads directly from your asset registry JSON
- **Quality-Tiered**: Scales complexity based on quality level (draft → ultra)
- **Style-Aware**: Adapts to painterly, pixel, flat, procedural styles
- **Shape-Aware**: Adjusts patterns based on shape descriptions
- **Export-Aware**: Considers multi-game export requirements

## Quick Start

### Basic Usage

```powershell
.\GenerateMaterialSpec.ps1 -RegistryPath "asset_registry.json" -AssetId "nature_verdant_pulse"
```

### With Custom Output

```powershell
.\GenerateMaterialSpec.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -OutputPath "material_specs\verdant_pulse.json" `
    -Model "llama3.2"
```

### Direct JSON Input

```powershell
$visual = '{"icon":{"shape":"spiral leaf burst","palette":["#4caf50"],"style":"painterly"}}'
$gen = '{"quality":"high"}'

.\GenerateMaterialSpec.ps1 -VisualJson $visual -GenerationJson $gen
```

## Integration with Texture Pipeline

### Using AI-Generated Specs

The `GenerateAssetTextures.ps1` script can optionally use AI-generated material specifications:

```powershell
.\GenerateAssetTextures.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "nature_verdant_pulse" `
    -Quality "high" `
    -UseAI `
    -AIModel "llama3.2"
```

This will:
1. Generate an AI material specification from the registry entry
2. Use the AI spec to determine texture requirements
3. Generate textures using the Blender material generator

## Prompt Template Structure

The prompt template is built into `GenerateMaterialSpec.ps1` and includes:

### Input Blocks

1. **VISUAL_BLOCK**: Contains icon, FX, projectile visual specifications
2. **GENERATION_BLOCK**: Contains quality, complexity, hints
3. **EXPORT_BLOCK**: Contains export targets (Elin, Terraria, Starbound)

### Output Structure

The AI generates a JSON specification with:

```json
{
  "material": {
    "style": "painterly",
    "shape": "spiral leaf burst",
    "palette": [
      { "hex": "#4caf50", "usage": "primary base color" },
      { "hex": "#81c784", "usage": "highlight accent" }
    ],
    "contrast": "high",
    "lighting": "soft rim light",
    "quality": "high",
    "proceduralLayers": [
      {
        "type": "noise",
        "scale": 12.0,
        "detail": 5.0,
        "factor": 0.4,
        "purpose": "base"
      },
      {
        "type": "voronoi",
        "scale": 18.0,
        "detail": 0.0,
        "factor": 0.6,
        "purpose": "detail"
      }
    ]
  },
  "animation": {
    "frames": 4,
    "motion": "expanding pulse",
    "glow": true
  },
  "textures": {
    "baseColor": true,
    "normal": false,
    "roughness": false,
    "emission": true
  }
}
```

## Quality Tiers

### Draft
- **Layers**: 1-2 procedural layers
- **Detail**: Low detail values
- **Features**: No rim lighting, no micro-detail
- **Use Case**: Quick previews, iteration

### Standard
- **Layers**: 2-3 layers
- **Detail**: Moderate detail
- **Features**: Simple color ramp
- **Use Case**: Production assets, most use cases

### High
- **Layers**: 3-5 layers
- **Detail**: Enhanced detail noise
- **Features**: Rim lighting (if suggested), subtle emission
- **Use Case**: High-quality assets, hero items

### Ultra
- **Layers**: 5-8 layers
- **Detail**: Micro-detail noise
- **Features**: Curvature-like variation, strong rim lighting, emission shaping
- **Use Case**: Maximum quality, showcase assets

## Procedural Layer Types

The AI can specify these layer types:

- **noise**: Perlin noise for organic patterns
- **voronoi**: Voronoi cells for geometric patterns
- **gradient**: Color gradients
- **mix**: Blending operations
- **emission**: Self-illumination for glow effects

Each layer includes:
- **scale**: Size of the pattern
- **detail**: Detail level (higher = more complex)
- **factor**: Mixing factor (0-1)
- **purpose**: base, detail, highlight, glow

## Shape-Aware Generation

The AI interprets shape descriptions to adjust patterns:

- **spiral/swirl**: Lower noise scales, spiral patterns
- **burst/explosion**: Higher scales, radial patterns
- **leaf/organic**: Medium scales, organic patterns
- **shard/crystal**: High scales, geometric patterns
- **web/net**: Very low scales, network patterns
- **star/glyph**: Low scales, symbolic patterns

## Style Adaptation

The AI adapts to different styles:

- **painterly**: Soft gradients, noise, color ramp
- **pixel**: Sharper, less smoothing, chunky shapes
- **flat**: Simple, solid colors, minimal variation
- **procedural**: Complex node setups, multi-layer

## Integration Examples

### Example 1: Full Pipeline

```powershell
# 1. Generate AI material spec
.\GenerateMaterialSpec.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -OutputPath "specs\fireball.json"

# 2. Generate textures using AI spec
.\GenerateAssetTextures.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -Quality "high" `
    -UseAI
```

### Example 2: Batch Processing

```powershell
$assets = @("spell_fireball", "spell_ice_shard", "spell_lightning")

foreach ($asset in $assets) {
    Write-Host "Processing: $asset" -ForegroundColor Cyan
    
    .\GenerateMaterialSpec.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $asset `
        -OutputPath "specs\$asset.json"
    
    .\GenerateAssetTextures.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $asset `
        -Quality "standard" `
        -UseAI
}
```

### Example 3: Custom Visual Block

```powershell
$visual = @{
    icon = @{
        shape = "magical glyph"
        palette = @("#ff6b6b", "#ff8787", "#ffa8a8")
        style = "pixel"
        size = 32
        contrast = "high"
        glow = $true
    }
} | ConvertTo-Json -Compress

$gen = @{
    quality = "ultra"
    proceduralHints = "arcane symbols, mystical energy"
} | ConvertTo-Json -Compress

.\GenerateMaterialSpec.ps1 -VisualJson $visual -GenerationJson $gen
```

## Troubleshooting

### Ollama Not Running
```powershell
# Check if Ollama is running
ollama serve

# Or use the helper
.\AssetMakerAI.ps1 -CheckOllama
```

### Invalid JSON Response
- Check that your Ollama model supports JSON output
- Try a different model (llama3.2, mistral, etc.)
- Check the raw response in the console output

### Quality Not Applied
- Ensure `generation.quality` is set in registry
- Check that the quality value matches: draft, standard, high, ultra

### Missing Texture Maps
- Verify `textures` block in registry entry
- Check AI spec output for texture requirements
- Ensure material generator supports requested maps

## Best Practices

1. **Start with Draft**: Test quickly with draft quality, then upgrade
2. **Use Registry**: Prefer registry entries over direct JSON for consistency
3. **Save Specs**: Save AI-generated specs for reproducibility
4. **Iterate**: Adjust registry entries and regenerate specs
5. **Batch Process**: Process multiple assets in a loop
6. **Model Selection**: Use larger models (llama3.2+) for better JSON output

## Advanced Usage

### Custom System Prompt

Modify the system prompt in `GenerateMaterialSpec.ps1`:

```powershell
$systemPrompt = "You are an expert procedural texture designer specializing in [YOUR_STYLE]. Output ONLY valid JSON."
```

### Quality Override

Override quality in the prompt:

```powershell
$gen = '{"quality":"ultra","proceduralHints":"maximum detail"}'
.\GenerateMaterialSpec.ps1 -VisualJson $visual -GenerationJson $gen
```

### Multi-Asset Generation

Generate specs for all assets in a registry:

```powershell
$registry = Get-Content "registry.json" | ConvertFrom-Json

foreach ($entry in $registry.entries) {
    .\GenerateMaterialSpec.ps1 `
        -RegistryPath "registry.json" `
        -AssetId $entry.id `
        -OutputPath "specs\$($entry.id).json"
}
```

## Next Steps

- Integrate with your Blender material generator
- Create custom quality presets
- Extend with additional layer types
- Build batch processing workflows
- Create quality comparison tools

