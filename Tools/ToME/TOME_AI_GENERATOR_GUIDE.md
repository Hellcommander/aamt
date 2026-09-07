# ToME AI-Enhanced Asset Generator Guide

## Overview

The AI-Enhanced ToME Asset Generator uses **Ollama** for text/prompts and **local SD3.5** for real sprites:

- **Ollama** (`http://localhost:11434`) — lore, flavor, palettes, SD prompts (`wizardlm-uncensored` / code models)
- **SD3.5** (`http://127.0.0.1:1338`) — icon/sprite pixels via `tome_sd_pipeline.py` + `Shared\sd_http_client.py`
- Pillow procedural art remains a last-resort fallback only when `use_sd=False`

## Features

### AI-Powered Content Generation

- **Sprites / Icons** - Ollama prompt → SD3.5 → 64×64 RGBA cut-out (`tome_sd_pipeline.py`)
- **Lore Text** - Atmospheric, engaging lore entries
- **Flavor Text** - Evocative descriptions for talents/items
- **Achievement Descriptions** - Creative achievement text
- **Quest Descriptions** - Engaging quest narratives
- **NPC Descriptions** - Atmospheric NPC descriptions
- **Color Palettes** - Themed color schemes for spells/effects

### Dual-Model System

- **Code Model**: Lua stubs / code tasks
- **Visual Model (WizardLM)**: Creative text, descriptions, SD prompts

### Automatic Model Detection

The generator automatically detects available Ollama models and routes tasks appropriately.
Start SD with `Tools\Start-StableDiffusionServer.ps1` before sprite runs.

## Installation

### Requirements

1. **Ollama** installed and running:
   ```bash
   # Install Ollama
   # https://ollama.ai
   
   # Start Ollama
   ollama serve
   
   # Pull recommended models
   ollama pull codellama:34b
   ollama pull wizardlm-uncensored:13b
   ```

2. **Python dependencies**:
   ```bash
   pip install Pillow requests
   ```

3. **Model Router**:
   - `ollama_model_router.py` (from Space Whale generator)
   - Automatically detects and routes to best models

## Quick Start

### Generate Spell with AI Descriptions

```bash
python tomegen_ai_cli.py generate \
  --template spell \
  --shapes ring,ink_bleed \
  --seed 12345 \
  --out ./mods/ai_mod
```

### Generate Achievement with AI Description

```bash
python tomegen_ai_cli.py extended \
  --asset-type achievement \
  --seed 12345 \
  --category "My Category" \
  --out ./mods/ai_mod
```

### Disable AI (Use Fallback)

```bash
python tomegen_ai_cli.py generate \
  --template spell \
  --seed 12345 \
  --no-ai
```

## How It Works

### Model Routing

The generator uses `ollama_model_router.py` to:

1. **Detect available models** from Ollama
2. **Assign CodeLlama-34B** for code tasks
3. **Assign WizardLM** for visual/creative tasks
4. **Fallback gracefully** if Ollama unavailable

### AI Generation Process

1. **Check Ollama availability** - Verifies connection
2. **Route to appropriate model** - Code vs Visual
3. **Generate content** - AI creates descriptions/text
4. **Fallback if needed** - Uses predefined templates if AI unavailable

### Example AI Prompts

**Lore Generation:**
```
Generate a short lore entry for Tales of Maj'Eyal in the history category.
The entry should be 2-4 paragraphs, atmospheric, and fit the game's fantasy setting.
```

**Flavor Text:**
```
Generate a short, atmospheric flavor text (1-2 sentences) for a spell in Tales of Maj'Eyal.
Make it mysterious and evocative.
```

**Color Palette:**
```
Suggest a color palette for a fire themed spell/effect in Tales of Maj'Eyal.
Return only a JSON array of 3 RGB color tuples.
```

## Configuration

### Ollama URL

Default: `http://localhost:11434`

Override:
```bash
--ollama-url http://localhost:11434
```

### Model Selection

The generator auto-detects models. To use specific models:

1. Ensure models are pulled in Ollama
2. Model router will detect and use them
3. Priority: CodeLlama-34B > CodeLlama-13B > WizardLM

## Programmatic API

```python
from tome_asset_generator_ai import AIEnhancedToMEGenerator
from tome_asset_generator import AssetType, ShapeModule
from tome_asset_generator_extended import ExtendedAssetType

# Create AI-enhanced generator
generator = AIEnhancedToMEGenerator(
    output_dir="./mods/ai_mod",
    mod_name="ai_mod",
    mod_author="Your Name",
    use_ai=True  # Enable AI
)

# Generate base asset with AI descriptions
spell = generator.generate(
    template=AssetType.SPELL,
    shapes=[ShapeModule.RING],
    seed=12345
)

# Generate extended asset with AI descriptions
achievement = generator.generate_extended(
    asset_type=ExtendedAssetType.ACHIEVEMENT,
    seed=12346,
    category="My Category"
)

# Check AI status
if generator.use_ai:
    print(f"Code Model: {generator.code_model}")
    print(f"Visual Model: {generator.visual_model}")
```

## AI vs Fallback

### With AI Enabled

- **Lore**: AI-generated atmospheric text
- **Flavor Text**: Creative, evocative descriptions
- **Achievements**: Engaging achievement descriptions
- **Quests**: Narrative quest descriptions
- **NPCs**: Atmospheric NPC descriptions
- **Color Palettes**: Themed color schemes

### With AI Disabled (`--no-ai`)

- Uses predefined templates
- Faster generation
- No Ollama dependency
- Consistent but less creative

## Troubleshooting

### Ollama Not Available

**Symptoms:**
- Warnings about Ollama connection
- Fallback to templates

**Solutions:**
1. Start Ollama: `ollama serve`
2. Check connection: `curl http://localhost:11434/api/tags`
3. Use `--no-ai` to disable AI

### Model Not Found

**Symptoms:**
- Falls back to default model
- Warnings about model detection

**Solutions:**
1. Pull required models:
   ```bash
   ollama pull codellama:34b
   ollama pull wizardlm-uncensored:13b
   ```
2. Check available models: `ollama list`

### Slow Generation

**Causes:**
- Large models (34B parameters)
- Network latency
- Multiple AI calls

**Solutions:**
1. Use smaller models (13B, 7B)
2. Use `--no-ai` for faster generation
3. Generate in batches

## Comparison with Space Whale Generator

The ToME AI generator uses the same dual-agent system:

| Feature | Space Whale | ToME Generator |
|---------|------------|----------------|
| Code Model | CodeLlama-34B | CodeLlama-34B |
| Visual Model | WizardLM | WizardLM |
| Model Router | ✅ | ✅ |
| Auto-Detection | ✅ | ✅ |
| Fallback | ✅ | ✅ |
| Task Routing | Code/Visual | Code/Visual |

## Best Practices

1. **Start Ollama First**: Ensure Ollama is running before generation
2. **Use Appropriate Models**: CodeLlama for code, WizardLM for creative
3. **Monitor Generation**: Check console for AI status
4. **Review AI Output**: AI-generated text may need editing
5. **Use Fallback When Needed**: `--no-ai` for faster generation

## Examples

### Complete Mod with AI

```bash
# Generate base assets
python tomegen_ai_cli.py generate \
  --template spell \
  --shapes ring \
  --seed 10001 \
  --out ./mods/complete_ai_mod

# Generate extended assets
python tomegen_ai_cli.py extended \
  --asset-type achievement \
  --seed 20001 \
  --category "Generated" \
  --out ./mods/complete_ai_mod

python tomegen_ai_cli.py extended \
  --asset-type lore \
  --seed 20002 \
  --out ./mods/complete_ai_mod
```

## See Also

- `TOME_ASSET_GENERATOR_README.md` - Base generator docs
- `TOME_EXTENDED_ASSETS_GUIDE.md` - Extended assets docs
- `ollama_model_router.py` - Model routing system
- [Ollama Documentation](https://ollama.ai/docs)

