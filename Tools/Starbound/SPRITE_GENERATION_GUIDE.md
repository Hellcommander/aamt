# Sprite Generation Guide

The Ollama asset generator now supports creating sprites for items and mechs, generating unique assets instead of reusing existing ones.

## Overview

Sprite generation creates:
- **PNG sprite images** with procedural generation or C++ backend
- **`.frames` files** for Starbound animation metadata
- **AI-generated descriptions** for creative sprite designs
- **Automatic parameter extraction** from descriptions

## Asset Types

### ItemSprite

Generates sprites for items (weapons, tools, consumables, materials, etc.).

**Default Size**: 32x32 pixels (configurable: 16x16, 32x32, 64x64)

**Output Location**: `assets/items/sprites/`

**Example**:
```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType ItemSprite `
    -AssetName "alchemical_grenade" `
    -Prompt "green glass grenade with glowing chemical liquid inside"
```

### MechSprite

Generates sprites for mechs (UI icons, previews, thumbnails).

**Default Size**: 64x64 pixels (configurable: 32x32, 64x64, 128x128)

**Output Location**: `assets/mechs/sprites/`

**Example**:
```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType MechSprite `
    -AssetName "phoenix_mech_icon" `
    -Prompt "phoenix mech icon with orange flames and metallic body"
```

### Sprite

General-purpose sprite generation.

**Default Size**: 64x64 pixels

**Output Location**: `assets/sprites/`

## Generation Process

1. **AI Description Generation**: Ollama generates a creative description based on your prompt
2. **Parameter Extraction**: AI extracts sprite parameters (size, colors, frame count)
3. **Sprite Creation**: 
   - Uses C++ backend if available (better quality)
   - Falls back to procedural PowerShell generation
4. **Frames File**: Automatically creates `.frames` file for Starbound

## Procedural Generation

When C++ backend is not available, the generator creates procedural sprites using:

- **Magical items**: Gradient backgrounds with sparkles
- **Weapons/Tools**: Metallic look with highlights
- **Default**: Colored rectangles with borders and patterns

## Using Generated Sprites

### In Item JSON

```json
{
  "itemName": "Alchemical Grenade",
  "asset": {
    "primary": "/items/sprites/alchemical_grenade.png",
    "source": "magi_tech_custom"
  }
}
```

### In Mech Definitions

```yaml
name: phoenix_mk2
icon: "/mechs/sprites/phoenix_mech_icon.png"
```

### In Lua Code

```lua
local itemConfig = {
    name = "magicsword",
    image = "/items/sprites/magicsword.png"
}
```

## Parameters

The generator automatically extracts these parameters from AI descriptions:

- **Width/Height**: Sprite dimensions (16-128 pixels)
- **FrameCount**: Number of animation frames (1-16)
- **ColorPalette**: Array of RGB colors for the sprite
- **ItemType/MechType**: Type classification for better generation

## Customization

### Specify Size

The generator will use AI-suggested sizes, but you can override:

```powershell
# Generate with specific parameters
$params = @{
    Width = 64
    Height = 64
    FrameCount = 4
    ColorPalette = @(@(255, 0, 0), @(200, 0, 0), @(150, 0, 0))
}

.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType ItemSprite `
    -AssetName "redsword" `
    -Parameters $params
```

### Using C++ Backend

For better quality sprites, use the C++ backend:

```powershell
.\StarboundOllamaAssetGenerator.ps1 `
    -AssetType ItemSprite `
    -AssetName "highquality_weapon" `
    -UseCppBackend `
    -Prompt "detailed magical weapon sprite"
```

## Batch Generation

Generate multiple sprites at once:

```powershell
$items = @("sword", "shield", "staff", "wand", "orb")
foreach ($item in $items) {
    .\StarboundOllamaAssetGenerator.ps1 `
        -AssetType ItemSprite `
        -AssetName "$item`_sprite" `
        -Prompt "$item with magical properties"
}
```

## Output Structure

```
assets/
├── items/
│   └── sprites/
│       ├── magicsword.png
│       ├── magicsword.frames
│       ├── alchemical_grenade.png
│       └── alchemical_grenade.frames
├── mechs/
│   └── sprites/
│       ├── phoenix_icon.png
│       └── phoenix_icon.frames
└── sprites/
    └── (general sprites)
```

## Tips

1. **Be specific in prompts**: More detail = better sprite generation
2. **Use color descriptions**: "blue glowing", "red metallic", etc.
3. **Specify style**: "pixel art", "hand-drawn", "procedural"
4. **Generate variations**: Use `-GenerateMultiple` to create several versions
5. **Use C++ backend**: Better quality for final assets

## Troubleshooting

### Sprites Not Generating

- Check if C++ backend path is correct
- Verify output directory has write permissions
- Check Ollama connection

### Poor Quality Sprites

- Use `-UseCppBackend` for better quality
- Provide more detailed prompts
- Generate multiple variations and select best

### Missing .frames Files

- Frames files are created automatically
- Check output directory structure
- Verify JSON serialization is working

## Integration with Existing Items

To replace existing item sprites:

1. Generate new sprite with Ollama
2. Update item JSON to reference new sprite path
3. Test in-game to verify appearance
4. Adjust prompt and regenerate if needed

---

*Part of the Starbound Ollama Asset Generator suite*
