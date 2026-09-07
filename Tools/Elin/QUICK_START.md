# Elin Tools - Quick Start

## Ollama Asset Generator

### Basic Usage

### Generate All Assets

```batch
OllamaAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"
```

### Generate Specific Asset Types

```batch
OllamaAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" "textures,icons"
```

### Generate for Specific Systems

```batch
OllamaAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" "textures" "DragonMagic,BloodMagic" "high"
```

### Generate with Spritesheets

```batch
OllamaAssetGenerator.bat "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" "all" "all" "high" --GenerateSpritesheets
```

## Parameters

1. **ModPath** (Required) - Path to your mod directory
2. **AssetTypes** (Optional) - Comma-separated list: `textures`, `icons`, `sprites`, `spell_assets`, or `all` (default: `all`)
3. **Systems** (Optional) - Comma-separated list of magic systems or `all` (default: `all`)
4. **Quality** (Optional) - Quality level: `low`, `medium`, `high`, or `ultra` (default: `high`)
5. **Options** (Optional) - Flags:
   - `--GenerateSpritesheets` - Generate spritesheets for batch assets
   - `--UseOllama` - Use Ollama for AI specifications (enabled by default)

## Examples

### Example 1: Quick Test (Low Quality)

```batch
OllamaAssetGenerator.bat "E:\...\CustomRaceClassCreator" "icons" "DragonMagic" "low"
```

### Example 2: Production Quality with Spritesheets

```batch
OllamaAssetGenerator.bat "E:\...\CustomRaceClassCreator" "all" "all" "high" --GenerateSpritesheets
```

### Example 3: Ultra Quality Textures Only

```batch
OllamaAssetGenerator.bat "E:\...\CustomRaceClassCreator" "textures" "all" "ultra"
```

## Output Location

Generated assets are saved to:
```
[ModPath]/GeneratedAssets/
├── Textures/
├── Icons/
├── Sprites/
└── SpellAssets/
```

## Troubleshooting

### Window Closes Immediately
- The batch file now includes a pause - if it still closes, check for PowerShell errors

### "Script not found" Error
- Ensure `OllamaAssetGenerator.ps1` is in the same directory as the batch file

### No Assets Generated
- Check that Ollama is running: `ollama serve`
- Verify Python and Pillow are installed: `python -m pip install Pillow`
- Check the output for error messages

### Ollama Not Available
- Install Ollama from https://ollama.com
- Start Ollama: `ollama serve`
- Install a model: `ollama pull wizardlm-uncensored:latest`

## Spell Audio Generator

### Generate Spell Sound Effects

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse: a burst of green life energy" -GenerateAll
```

Or using batch file:

```batch
ElinSpellAudioGenerator.bat -SpellDescription "Nature Magic - Verdant Pulse: a burst of green life energy" -GenerateAll
```

### Generate with Quality Assessment

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Fire Magic - Fireball" -GenerateAll -AssessQuality
```

### Generate Specific Sound Types

```powershell
.\ElinSpellAudioGenerator.ps1 -SpellDescription "Ice Magic - Frost Bolt" -GenerateCast -GenerateImpact
```

## See Also

### Core Documentation
- `OLLAMA_ASSET_GENERATOR_GUIDE.md` - Complete documentation for Ollama Asset Generator
- `UNITY_INTEGRATION_GUIDE.md` - How to integrate generated assets into Unity
- `TEXTURE_FORMAT_GUIDE.md` - Texture formats, compression, and quality settings
- `TROUBLESHOOTING.md` - Common issues and solutions
- `STEAM_DECK_LINUX.md` - Proton launch options so BepInEx code mods load on Steam Deck / Linux

### Specialized Guides
- `ELIN_SPELL_AUDIO_GUIDE.md` - Complete documentation for Spell Audio Generator
- `ELIN_SPELL_ASSETS_GUIDE.md` - Complete documentation for Spell Asset Generator
- `ELIN_TEXTURE_GENERATOR_GUIDE.md` - Elin-specific texture generation

### Scripts
- `OllamaAssetGenerator.ps1` - PowerShell script (can be run directly)
- `ElinSpellAudioGenerator.ps1` - PowerShell script (can be run directly)
