# Asset Generator Control Room - Universal Guide

## Overview

The **Asset Generator Control Room** is a universal real-time GUI that provides:

- **Live preview** of all generated assets (tiles, textures, models, spritesheets, icons, FX, projectiles)
- **Real-time chat** with Ollama for prompt-based generation
- **On-demand regeneration** with iterative refinement
- **Auto-export** to game formats (Qud, Elin, Terraria, Starbound, Transcendence)
- **Automatic launching** when AI generation starts from other scripts
- **File watching** for automatic preview updates

## Features

### Universal Asset Support
- **Tiles**: Qud-compatible tiles (24×24, 32×32, 48×48)
- **Textures**: Procedural textures with multiple maps
- **Models**: 3D models (OBJ, FBX, GLB, STL)
- **Spritesheets**: Cross-game spritesheet assembly
- **Icons**: Spell/item icons
- **FX**: Spell effect animations
- **Projectiles**: Projectile sprites

### Live Preview
- **Left panel**: Shows assets as they're generated
- **Automatic updates**: Watches output folder for new files
- **Real-time feedback**: See results immediately

### AI Chat Interface
- **Right panel**: Chat with Ollama
- **Prompt history**: Maintains conversation context
- **JSON output**: Generates material/model specifications
- **Iterative refinement**: Tweak and regenerate

### Auto-Export
- **Multiple targets**: Export to Qud, Elin, Terraria, Starbound, Transcendence
- **Automatic**: Export after generation if enabled
- **Format-specific**: Each game gets appropriate format

### Automatic Launching
- **From AssetMakerAI**: Launches automatically when `-LaunchControlRoom` is used
- **From other scripts**: Can be launched with watch directory
- **Background process**: Doesn't block main script execution

## Quick Start

### Manual Launch

```powershell
.\AssetGeneratorControlRoom.ps1
```

Or double-click:
```
AssetGeneratorControlRoom.bat
```

### With Parameters

```powershell
.\AssetGeneratorControlRoom.ps1 `
    -AssetType "Texture" `
    -DrawingPath "drawings\stone.png" `
    -ExportTargets @("Terraria", "Starbound") `
    -AutoExport
```

### Automatic Launch from AssetMakerAI

```powershell
# Generate texture with control room
.\AssetMakerAI.ps1 `
    -Action GenerateTexture `
    -InputData "cracked stone texture" `
    -LaunchControlRoom `
    -ControlRoomWatchDir "C:\MyMod\Assets\Temp"
```

```powershell
# Generate 3D model with control room
.\AssetMakerAI.ps1 `
    -Action Generate3DModel `
    -InputData "a sleek space fighter" `
    -LaunchControlRoom
```

## Usage Examples

### Example 1: Tile Generation

1. Select asset type: **Tile**
2. Select drawing: `drawings\spell_icon.png`
3. Set size: 32
4. Prompt: "Use this sketch as a silhouette. Make it painterly style with green palette."
5. Click "Send to AI"
6. Click "Generate Asset"
7. Enable auto-export: Check "Auto-Export"
8. Select export targets: Qud, Terraria
9. Review preview
10. Click "Save Final"

### Example 2: Texture Generation

1. Select asset type: **Texture**
2. Set size: 512
3. Prompt: "Cracked stone texture with moss, high detail, normal map"
4. Click "Send to AI"
5. Click "Generate Asset"
6. Enable auto-export: Check "Auto-Export"
7. Select export targets: Terraria, Starbound
8. Review preview
9. Refine: "More contrast, darker cracks"
10. Click "Send to AI" → "Generate Asset"
11. Save when satisfied

### Example 3: Model Generation

1. Select asset type: **Model**
2. Prompt: "A sleek space fighter with twin engines"
3. Click "Send to AI"
4. Click "Generate Asset"
5. Model is generated in background
6. Preview updates when model is rendered
7. Enable auto-export for game formats
8. Save final model

### Example 4: Automatic Launch

```powershell
# In your asset generation script
.\AssetMakerAI.ps1 `
    -Action GenerateTexture `
    -InputData "wooden texture" `
    -LaunchControlRoom `
    -ControlRoomWatchDir "C:\MyMod\Temp"
```

The control room will:
- Launch automatically
- Watch the specified directory
- Show previews as assets are generated
- Auto-export if enabled

## GUI Layout

### Header
- **Title**: "Asset Generator Control Room"
- **Asset Type Selector**: Dropdown to choose asset type

### Left Panel: Live Preview
- Shows generated assets in real-time
- Updates automatically when new assets are created
- Black background for contrast
- Placeholder text when no preview available

### Right Panel: AI Chat & Controls

**Top Section: Prompt Input**
- Multi-line text box for your prompts
- Accepts return for multi-line prompts
- Scrollable for long prompts

**Middle Section: Control Buttons**
- **Send to AI**: Sends prompt to Ollama
- **Generate Asset**: Renders asset using current spec
- **Regenerate**: Re-runs last prompt
- **Save Final**: Saves asset to output directory

**Bottom Section: AI Response**
- Shows Ollama's JSON response
- Read-only display
- Scrollable for long responses

**Settings Expander**
- Drawing path selector
- Size dropdown (varies by asset type)
- Ollama model selector
- Export targets checkboxes
- Auto-export checkbox
- Output path selector

### Bottom: Status & Log

**Status Bar**
- Current operation status
- Error messages
- Ready state

**Log Panel**
- Timestamped log entries
- Console-style output (black background, green text)
- Scrollable
- Auto-scrolls to latest entries

## Asset Type Details

### Tiles
- **Sizes**: 24, 32, 48
- **Export**: Qud format (PNG + metadata)
- **Use**: Caves of Qud mods

### Textures
- **Sizes**: 64, 128, 256, 512
- **Export**: Multiple game formats
- **Maps**: Base color, normal, roughness, emission
- **Use**: Material textures for models

### Models
- **Formats**: OBJ, FBX, GLB, STL
- **Export**: Game-specific formats
- **Use**: 3D assets for games

### Spritesheets
- **Sizes**: Variable
- **Export**: Terraria, Starbound formats
- **Use**: Cross-game asset sharing

### Icons
- **Sizes**: 16, 32, 64
- **Export**: Elin format
- **Use**: Spell/item icons

### FX
- **Sizes**: 32, 64
- **Frames**: 4-16
- **Export**: Elin format
- **Use**: Spell effect animations

### Projectiles
- **Sizes**: 32, 64
- **Frames**: 2-8
- **Export**: Elin format
- **Use**: Projectile sprites

## Auto-Export

### Enabling Auto-Export

1. Check "Auto-Export" checkbox in settings
2. Select export targets (Qud, Elin, Terraria, Starbound, Transcendence)
3. Generate asset
4. Assets are automatically exported after generation

### Export Targets

- **Qud**: PNG tiles + XML/JSON metadata
- **Elin**: Spell assets (icons, FX, projectiles)
- **Terraria**: Spritesheets + JSON metadata
- **Starbound**: Spritesheets + .frames files
- **Transcendence**: Game-specific formats

### Export Locations

Exports are saved to:
- `{OutputPath}/{ExportTarget}Export/`
- Example: `GeneratedAssets/QudExport/`, `GeneratedAssets/TerrariaExport/`

## Integration with Other Scripts

### From AssetMakerAI

```powershell
.\AssetMakerAI.ps1 `
    -Action GenerateTexture `
    -InputData "stone texture" `
    -LaunchControlRoom `
    -ControlRoomWatchDir "C:\Temp\Assets"
```

### From AssetRegistry

```powershell
# Launch control room for registry generation
.\AssetRegistry.ps1 `
    -Action Generate `
    -GameFormat All `
    -LaunchControlRoom
```

### From Custom Scripts

```powershell
# Launch control room with watch directory
$watchDir = "C:\MyMod\Assets\Temp"
Start-Process -FilePath "pwsh" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "AssetGeneratorControlRoom.ps1",
    "-WatchDirectory", $watchDir,
    "-AssetType", "Texture",
    "-AutoExport"
)
```

## File Watching

The GUI automatically watches the specified directory for new files:

- **Automatic detection**: New files appear in preview immediately
- **No manual refresh**: Preview updates as assets are generated
- **Real-time feedback**: See results as they're created

### Watch Directory

- **Default**: Temporary directory
- **Custom**: Specify with `-WatchDirectory`
- **Shared**: Can watch a directory shared with other scripts

## Best Practices

### Workflow

1. **Launch control room** before starting generation
2. **Set asset type** and size
3. **Select export targets** if auto-exporting
4. **Generate with AI** to get spec
5. **Generate asset** to see preview
6. **Refine iteratively** with prompts
7. **Save final** when satisfied

### Prompt Writing

1. **Be specific**: "More contrast" not "better"
2. **Use context**: Reference the drawing/asset
3. **Iterate**: Build on previous prompts
4. **Test incrementally**: Small changes first

### Auto-Export

1. **Enable early**: Check auto-export before generation
2. **Select targets**: Choose appropriate game formats
3. **Review exports**: Check exported files after generation
4. **Organize**: Use output path to organize exports

## Troubleshooting

### Preview Not Updating

- Check that assets are being written to watch directory
- Verify file watcher is running (check log)
- Try manual refresh (close and reopen GUI)
- Check file permissions

### Ollama Not Responding

- Verify Ollama is running: `ollama serve`
- Check model name is correct
- Check Ollama API is accessible
- Review log for error messages

### Blender Not Found

- Specify `-BlenderPath` parameter
- Check Blender is installed
- Verify PATH includes Blender
- Check common installation paths

### Asset Not Generating

- Verify input file exists
- Check Blender console for errors
- Verify output directory is writable
- Check log for error messages

### Auto-Export Not Working

- Verify auto-export is enabled
- Check export targets are selected
- Verify export scripts exist
- Check log for export errors

## Advanced Usage

### Batch Processing

While the GUI is interactive, you can:

1. Generate multiple assets in sequence
2. Save each iteration
3. Compare results
4. Choose best version

### Custom Watch Directories

```powershell
# Watch a shared directory
.\AssetGeneratorControlRoom.ps1 `
    -WatchDirectory "C:\SharedAssets\Temp" `
    -AssetType "Texture"
```

### Integration with Build System

```powershell
# Launch control room as part of build process
$watchDir = Join-Path $buildDir "Assets\Temp"
Start-Process -FilePath "pwsh" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "AssetGeneratorControlRoom.ps1",
    "-WatchDirectory", $watchDir,
    "-AutoExport"
)

# Generate assets (they'll appear in control room)
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "texture1" -OutputPath $watchDir
.\AssetMakerAI.ps1 -Action GenerateTexture -InputData "texture2" -OutputPath $watchDir
```

## Next Steps

- Create prompt templates for common patterns
- Build a library of successful prompts
- Integrate with mod build system
- Create batch processing workflows
- Document your prompt patterns
- Set up watch directories for your projects

