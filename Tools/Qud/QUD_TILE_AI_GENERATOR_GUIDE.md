# Qud Tile AI Generator - Control Room Guide

## Overview

The **Qud Tile AI Generator** is a real-time GUI control room that provides:

- **Live preview** of generated tiles as they're created
- **Real-time chat** with Ollama for prompt-based generation
- **On-demand regeneration** with iterative refinement
- **File watching** for automatic preview updates
- **Full integration** with your Blender tile baker

## Features

### Live Preview
- **Left panel**: Shows tiles as they're generated
- **Automatic updates**: Watches output folder for new files
- **Real-time feedback**: See results immediately

### AI Chat Interface
- **Right panel**: Chat with Ollama
- **Prompt history**: Maintains conversation context
- **JSON output**: Generates material specifications
- **Iterative refinement**: Tweak and regenerate

### Controls
- **Send to AI**: Generate material spec from prompt
- **Bake Tile**: Render tile using current spec
- **Regenerate**: Re-run last prompt with refinements
- **Save Final**: Save tile to output directory

### Settings
- **Drawing path**: Select your line drawing
- **Tile size**: 24×24, 32×32, or 48×48
- **Ollama model**: Choose AI model
- **Output path**: Where to save final tiles

## Quick Start

### Launch GUI

```powershell
.\QudTileAIGenerator.ps1
```

Or double-click:
```
QudTileAIGenerator.bat
```

### Basic Workflow

1. **Select Drawing**
   - Click "Browse..." next to Drawing path
   - Select your line drawing image

2. **Set Tile Size**
   - Choose 24, 32, or 48 from dropdown

3. **Type Prompt**
   - Enter your request (e.g., "Make it more crystalline, cooler palette, strong rim light")
   - Click "Send to AI"

4. **Review AI Response**
   - Check the AI Response box for the generated JSON spec
   - Verify it looks correct

5. **Bake Tile**
   - Click "Bake Tile"
   - Watch the preview update automatically

6. **Refine**
   - Type feedback (e.g., "Increase contrast, darker background")
   - Click "Send to AI" again
   - Click "Bake Tile" to see changes

7. **Save Final**
   - When satisfied, click "Save Final"
   - Tile is copied to output directory

## Usage Examples

### Example 1: Basic Generation

1. Select drawing: `drawings\spell_icon.png`
2. Set tile size: 32
3. Prompt: "Use this sketch as a silhouette. Make it painterly style with green palette."
4. Click "Send to AI"
5. Click "Bake Tile"
6. Review preview
7. Click "Save Final"

### Example 2: Iterative Refinement

1. Initial prompt: "Make it crystalline with cool colors"
2. Bake and review
3. Refine: "More contrast, darker background, add glow"
4. Bake again
5. Refine: "Softer edges, warmer highlights"
6. Bake again
7. Save when satisfied

### Example 3: With Registry

```powershell
.\QudTileAIGenerator.ps1 `
    -DrawingPath "drawings\ship_scout.png" `
    -RegistryPath "asset_registry.json" `
    -AssetId "ship_scout"
```

The GUI will:
- Load palette from registry
- Use style and quality settings
- Pre-fill drawing path
- Use registry asset ID for naming

## GUI Layout

### Left Panel: Live Preview
- Shows generated tiles in real-time
- Updates automatically when new tiles are baked
- Black background for contrast
- Placeholder text when no preview available

### Right Panel: AI Chat & Controls

**Top Section: Prompt Input**
- Multi-line text box for your prompts
- Accepts return for multi-line prompts
- Scrollable for long prompts

**Middle Section: Control Buttons**
- **Send to AI**: Sends prompt to Ollama
- **Bake Tile**: Renders tile using current spec
- **Regenerate**: Re-runs last prompt
- **Save Final**: Saves tile to output directory

**Bottom Section: AI Response**
- Shows Ollama's JSON response
- Read-only display
- Scrollable for long responses

**Settings Expander**
- Drawing path selector
- Tile size dropdown
- Ollama model selector
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

## AI Prompt Examples

### Shape & Style
```
Use this sketch as a silhouette. Make it more crystalline, cooler palette, strong rim light.
```

### Color Adjustments
```
Increase contrast, darker background, more glow in the core. Use warmer highlights.
```

### Detail Refinement
```
Add more detail noise, softer edges, enhance rim lighting. Make the center brighter.
```

### Style Changes
```
Switch to pixel style, higher contrast, sharper edges. Use a red-orange palette.
```

### Quality Upgrades
```
Upgrade to ultra quality, add micro-detail, enhance emission. Make it more magical.
```

## File Watching

The GUI automatically watches the temp directory for new PNG files:

- **Automatic detection**: New files appear in preview immediately
- **No manual refresh**: Preview updates as Blender writes files
- **Real-time feedback**: See results as they're generated

## Prompt History

The GUI maintains a prompt history:

- **Context preservation**: Each prompt includes previous context
- **Iterative refinement**: Build on previous requests
- **Regenerate**: Re-run last prompt with modifications

## Integration with Pipeline

### With Registry

```powershell
.\QudTileAIGenerator.ps1 `
    -RegistryPath "asset_registry.json" `
    -AssetId "spell_fireball"
```

### With Drawing

```powershell
.\QudTileAIGenerator.ps1 `
    -DrawingPath "drawings\spell_icon.png" `
    -TileSize 32
```

### With Custom Model

```powershell
.\QudTileAIGenerator.ps1 `
    -OllamaModel "mistral" `
    -DrawingPath "drawings\ship.png"
```

## Troubleshooting

### Preview Not Updating

- Check that Blender is writing to temp directory
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

### Tile Not Baking

- Verify drawing file exists
- Check Blender console for errors
- Verify output directory is writable
- Check log for error messages

### AI Response Invalid

- Check Ollama model supports JSON output
- Try a different model
- Verify prompt is clear
- Check log for parsing errors

## Best Practices

### Prompt Writing

1. **Be specific**: "More contrast" not "better"
2. **Use context**: Reference the drawing
3. **Iterate**: Build on previous prompts
4. **Test incrementally**: Small changes first

### Workflow

1. **Start simple**: Basic prompt first
2. **Review AI response**: Check JSON is valid
3. **Bake and preview**: See results
4. **Refine incrementally**: Small tweaks
5. **Save when satisfied**: Don't over-iterate

### Settings

1. **Use registry**: Pre-fill settings from registry
2. **Choose appropriate size**: Match your mod's style
3. **Select right model**: Larger models = better JSON
4. **Set output path**: Organize your tiles

## Advanced Usage

### Batch Processing

While the GUI is interactive, you can:

1. Generate multiple tiles in sequence
2. Save each iteration
3. Compare results
4. Choose best version

### Custom Prompts

Build complex prompts:

```
Use this sketch as a silhouette. Apply a crystalline material with:
- Cool blue-green palette (#4a90e2, #7bb3f0, #2c5aa0)
- High contrast
- Strong rim lighting
- Ultra quality with micro-detail
- Emission glow in the core
```

### Integration with Other Tools

```powershell
# 1. Generate in GUI
# 2. Export final tile
# 3. Use in mod

.\ExportQudTiles.ps1 `
    -RegistryPath "registry.json" `
    -AssetId "spell_fireball" `
    -OutputDir "QudMod\assets\textures\tiles"
```

## Next Steps

- Create prompt templates for common patterns
- Build a library of successful prompts
- Integrate with mod build system
- Create batch processing workflows
- Document your prompt patterns

