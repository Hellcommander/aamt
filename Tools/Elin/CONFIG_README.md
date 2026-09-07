# Ollama Asset Generator - Configuration

## Quick Start

**Just double-click `OllamaAssetGenerator.bat`** - it will use settings from `OllamaAssetGenerator.config.json`!

## Configuration File

Edit `OllamaAssetGenerator.config.json` to customize settings:

```json
{
  "modPath": "E:\\SteamLibrary\\steamapps\\common\\Elin\\Package\\Mod\\CustomRaceClassCreator",
  "assetTypes": "all",
  "systems": "all",
  "quality": "high",
  "generateSpritesheets": true,
  "useOllama": true,
  "outputDir": ""
}
```

### Settings

- **modPath**: Path to your mod directory (defaults to your mod location)
- **assetTypes**: `"all"` or comma-separated: `"textures,icons,sprites,spell_assets"`
- **systems**: `"all"` or comma-separated: `"DragonMagic,BloodMagic,Necromancy"`
- **quality**: `"low"`, `"medium"`, `"high"`, or `"ultra"` (default: `"high"`)
- **generateSpritesheets**: `true` or `false` (default: `true`)
- **useOllama**: `true` or `false` (default: `true`)
- **outputDir**: Leave empty to use default `GeneratedAssets` folder

## Usage

### Default (Double-Click)
Just double-click `OllamaAssetGenerator.bat` - uses all settings from config file.

### Override Mod Path
```batch
OllamaAssetGenerator.bat "E:\...\OtherMod"
```

### Override Multiple Settings
```batch
OllamaAssetGenerator.bat "E:\...\Mod" "textures,icons" "DragonMagic" "ultra"
```

## Examples

### Generate Everything (Default)
Just double-click the batch file!

### Generate Only Textures
Edit config:
```json
{
  "assetTypes": "textures",
  ...
}
```

### Generate for Specific Systems
Edit config:
```json
{
  "systems": "DragonMagic,BloodMagic,Necromancy",
  ...
}
```

### Ultra Quality
Edit config:
```json
{
  "quality": "ultra",
  ...
}
```

## Notes

- Config file uses double backslashes (`\\`) for Windows paths
- Settings in config file are defaults - command line arguments override them
- If config file is missing, it will use hardcoded defaults
