# Broodmother Mutation Asset Generator

High-quality asset generation for the Broodmother Mutation mod using Ollama AI tools with built-in quality control.

## Features

- **Always uses AI tools**: All asset generation uses Ollama AI for high-quality results
- **Quality control**: Built-in quality scoring and retry logic
- **Comprehensive coverage**: Generates icons, equipment tiles, creature tiles, and preview images
- **Automatic validation**: Ensures all generated assets meet quality standards

## Requirements

1. **Ollama must be installed and running**
   - Download from: https://ollama.ai
   - Start Ollama before running the generator

2. **Python dependencies**:
   ```bash
   pip install pillow requests
   ```

3. **Ollama integration module**:
   - Located in `../Shared/ollama_integration.py`
   - Must be available for the script to run

## Usage

### Quick Start (Windows)

1. Double-click `GenerateBroodmotherAssets.bat`
2. Wait for asset generation to complete
3. Check the `Textures/` folder in your mod directory

### Command Line

```bash
python generate_broodmother_assets_ollama.py "C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"
```

### Options

```bash
python generate_broodmother_assets_ollama.py <mod_path> [--ollama-url URL] [--model MODEL_NAME]
```

- `--ollama-url`: Ollama server URL (default: http://localhost:11434)
- `--model`: Specific Ollama model to use (default: auto-detect wizardlm-uncensored)

## Generated Assets

The generator creates:

1. **Mutation Icon** (`Broodmother_icon.png`)
   - 96x96 pixels
   - High-quality organic sack design
   - Magenta/purple color scheme

2. **Equipment Tiles**
   - `Broodling_Sack_tile.png` (64x64) - In-game equipment tile
   - `Broodling_Sack_icon.png` (96x96) - UI icon

3. **Creature Tiles** (64x64 each)
   - `BroodlingCrystal_T4.png`
   - `BroodlingPhantom_T5.png`
   - `BroodlingBombardier_T4.png`
   - `BroodlingSymbiote_T3.png`
   - `BroodlingTunneler_T3.png`

4. **Preview Image** (`preview.png`)
   - 512x512 pixels
   - Workshop preview image

## Quality Control (critique → correct → retry)

Default mode is **`police`**: after SD drafts, a cheap heuristic gate catches broken near-black/flat/empty images, then one Ollama critic (`wizardlm-uncensored`) reviews keepers. Failures get **correction text** baked into refined prompts/negatives and are **batch-regenerated on SD** (SD and Ollama never share the GPU in the same phase).

| Mode | Flag / menu | Speed | Behavior |
|------|-------------|-------|----------|
| `police` | default / menu **POLICE** / `GenerateBroodmotherAssets-Police.bat` | medium | Heuristic + one critic + SD retry |
| `draft` | `--quality-mode draft` / menu **Draft only** | fast | SD only — broken drafts kept |
| `full` | `--quality-mode full` / MultiAgent bat | slow | Sequential LLaVA → Qwen-VL → heuristic → creative refine + SD retry |

Implementation: [`broodmother_quality_loop.py`](broodmother_quality_loop.py) + [`generate_broodmother_assets_ollama.py`](generate_broodmother_assets_ollama.py). Report: `DesignDrafts/quality_loop_report.json`.

**Tradeoff:** police/full are vastly slower than one-shot SD (model load/unload + stop/start SD). That cost is what stops shipping broken drafts.

**Vortex-like thrift:** like the Space-Time Vortex generator, these modes are **slow but not resource-thrashing** — only one GPU owner at a time (SD *or* Ollama), so an overnight run can finish while you sleep without pinning CPU+GPU+pagefile. After drafts/exports land, later toolkit advances (export polish, Unity bridge, prompt packs) can improve the same assets without regenerating everything.

## AI Model Selection

The Broodmother generator **forces `wizardlm-uncensored:latest`** for prompt packs and art-director calls (no content filters — required for biomutation / organic body-horror descriptions).

Override if needed:

```powershell
& ".\GenerateBroodmotherAssets.ps1" -ModPath "<mod>" -OllamaModel "wizardlm-uncensored:latest"
# or python:
python generate_broodmother_assets_ollama.py "<mod>" --model wizardlm-uncensored:latest
```

Shared router preference lists also put `wizardlm-uncensored:latest` first for `visual` and `dark_tone` tiers.

## Integration with Mutation Asset Generator

### "Ollama is not available"
- Make sure Ollama is installed and running
- Check that `ollama serve` is running
- Verify connection at http://localhost:11434

### "Ollama integration module not found"
- Ensure `../Shared/ollama_integration.py` exists
- Check that the Shared directory is accessible

### "Quality score too low"
- The AI may need better prompts
- Try a different model: `--model llama3:latest`
- Check Ollama logs for errors

### "JSON parse error"
- The AI response may be malformed
- The generator will retry automatically
- If it persists, try a different model

## Integration with Mutation Asset Generator

The main `mutation_asset_generator.py` has been updated to:
- Check for Ollama availability
- Use AI tools when available
- Fall back to procedural generation if AI is unavailable
- Always prefer AI generation for better quality

## File Structure

```
Broodmother Mutation/
├── Textures/
│   ├── Broodmother_icon.png
│   ├── Equipment/
│   │   ├── Broodling_Sack_tile.png
│   │   └── Broodling_Sack_icon.png
│   └── Creatures/
│       ├── BroodlingCrystal_T4.png
│       ├── BroodlingPhantom_T5.png
│       └── ...
└── preview.png
```

## Best Practices

1. **Always use AI tools**: The generator is designed to always use Ollama
2. **Check quality**: Review generated assets before committing
3. **Regenerate if needed**: Run the generator again if quality is insufficient
4. **Keep Ollama updated**: Use the latest models for best results

## Credits

- Uses Ollama AI for asset generation
- Quality control system ensures consistent results
- Integrated with Caves of Qud modding standards
