# Space Whale Asset Generator Settings

## Settings File: `SpaceWhaleAssetGenerator_Settings.json`

This file contains all default settings for the Space Whale Asset Generator. Edit this file to customize defaults without modifying the script.

## Default Settings

### `defaults` Section

| Setting | Default | Description |
|---------|---------|-------------|
| `registryPath` | `"space_whale_ship_example.json"` | Path to ship registry file |
| `outputDir` | `"Output/SpaceWhaleAssets"` | Output directory for generated assets |
| `shipId` | `""` | Ship ID to generate (empty = all ships in registry) |
| `ollamaModel` | `""` | Ollama model to use (empty = auto-detect via dual-model router) |
| `useControlRoom` | `true` | Launch Control Room GUI for progress tracking |
| `skipVisualLanguage` | `false` | Skip visual language generation |
| `skipFX` | `false` | Skip FX assets generation |
| `skipAudio` | `false` | Skip audio assets generation |
| `skipSpritesheet` | `false` | Skip spritesheet generation |

### Model Selection

The `ollamaModel` setting in `defaults` is a general override. For task-specific models, use the `models` section below.

### Task-Specific Models (`models` Section)

Configure which model to use for different task types:

| Setting | Default | Description |
|---------|---------|-------------|
| `codeModel` | `""` | Model for code generation tasks (empty = auto-detect) |
| `visualModel` | `""` | Model for visual/orchestration tasks (empty = auto-detect) |
| `xmlModel` | `""` | Model for XML generation (empty = uses codeModel) |
| `audioModel` | `""` | Model for audio generation (empty = uses visualModel) |
| `useDualModelRouter` | `true` | Enable auto-detection via dual-model router |

**Model Selection Options:**
- **Empty string (`""`)** = Auto-detect via dual-model router (if enabled)
  - CodeLlama-34B for code/XML tasks
  - WizardLM for visual tasks
- **`"codellama:34b"`** = Force CodeLlama-34B
- **`"wizardlm-uncensored:latest"`** = Force WizardLM
- **Any other model name** = Use that specific model

**Examples:**

```json
{
  "models": {
    "codeModel": "codellama:34b",
    "visualModel": "wizardlm-uncensored:latest",
    "xmlModel": "",
    "audioModel": "",
    "useDualModelRouter": true
  }
}
```

This will:
- Use CodeLlama-34B for code tasks
- Use WizardLM for visual tasks
- Auto-detect XML model (uses codeModel)
- Auto-detect audio model (uses visualModel)
- Still use router for auto-detection when models are empty

### Control Room Settings

- **`useControlRoom: true`** = Launch Control Room GUI window
- **`useControlRoom: false`** = Run without GUI (command-line only)

### Skip Options

- **`true`** = Skip this asset type (don't generate)
- **`false`** = Generate this asset type

## Advanced Settings

### `advanced` Section

| Setting | Default | Description |
|---------|---------|-------------|
| `controlRoomMaxCores` | `32` | Maximum CPU cores for Control Room |
| `controlRoomWatchDirectory` | `""` | Custom watch directory (empty = use outputDir) |
| `controlRoomAssetType` | `"Ship"` | Asset type for Control Room |
| `controlRoomExportTargets` | `"Transcendence"` | Export target platform |
| `controlRoomAutoExport` | `true` | Enable auto-export in Control Room |

## Usage

1. **Edit the settings file** to change defaults
2. **Run the script** - it will use your settings automatically
3. **Command-line parameters override settings** - you can still override any setting via command-line

## Example: Change Default Output Directory

```json
{
  "defaults": {
    "outputDir": "MyCustomOutput/SpaceWhaleAssets",
    ...
  }
}
```

## Example: Disable Control Room by Default

```json
{
  "defaults": {
    "useControlRoom": false,
    ...
  }
}
```

## Example: Use Specific Model

```json
{
  "defaults": {
    "ollamaModel": "codellama:34b",
    ...
  }
}
```

## Notes

- Settings file is optional - if it doesn't exist, the script uses hardcoded defaults
- Command-line parameters always override settings file values
- Settings file must be valid JSON (use a JSON validator if you get errors)
- The script will show a warning if it can't load the settings file

