# Terraria Portal Asset Generator Guide

## Overview

The **Terraria Portal Generator** creates complete, ready-to-use portal assets for Terraria mods using tModLoader. It generates animated spritesheets, C# tile classes, and all necessary metadata files.

## Features

- **Animated Portal Spritesheets**: Horizontal frame strips (8+ frames) for smooth animation
- **tModLoader Integration**: Complete C# tile class with animation logic
- **Proper File Structure**: Organized mod directory ready for tModLoader
- **AI-Powered Generation**: Optional AI-assisted portal design
- **Glow Effects**: Built-in lighting and glow support
- **Customizable**: Easy to modify colors, animation speed, and effects

## Quick Start

### Basic Portal Generation

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "NetherPortal" `
    -PortalDescription "A swirling purple portal with energy particles" `
    -FrameCount 8 `
    -TileSize 16
```

### With AI Generation

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "CrystalPortal" `
    -PortalDescription "A crystalline blue portal with magical runes" `
    -UseAI `
    -OllamaModel "wizardlm-uncensored" `
    -FrameCount 12 `
    -TileSize 32
```

## Parameters

- **`-PortalName`** (Required): Name of the portal (e.g., "NetherPortal", "CrystalPortal")
- **`-PortalDescription`**: Description for AI generation or visual reference
- **`-OutputDir`**: Output directory (default: "TerrariaMods")
- **`-FrameCount`**: Number of animation frames (default: 8)
- **`-TileSize`**: Tile size in pixels - 16 or 32 (default: 16)
- **`-UseAI`**: Use AI to generate portal design
- **`-OllamaModel`**: Ollama model to use (default: "wizardlm-uncensored")

## Generated Files

The generator creates a complete mod structure:

```
PortalName/
├── Assets/
│   └── Textures/
│       └── Tiles/
│           └── PortalName.png          # Animated spritesheet
├── Content/
│   └── Tiles/
│       └── PortalNameTile.cs           # Tile class with animation
├── modinfo.json                        # Mod metadata
├── build.txt                           # tModLoader build config
└── README.md                           # Usage instructions
```

## Understanding Terraria Portal Assets

Based on the [Terraria source code](https://github.com/kran27/Terraria) and tModLoader documentation:

### Spritesheet Format

- **Horizontal Strip**: Animation frames arranged horizontally
- **Frame Size**: 16×16 or 32×32 pixels (must match tile size)
- **Frame Count**: Typically 4-16 frames for smooth animation
- **Format**: PNG with transparency

### Animation System

Terraria uses a frame-based animation system:
- Frames are arranged horizontally in the spritesheet
- Animation speed controlled by frame counter
- Each tile instance animates independently
- Frame height must match tile size

### Tile Properties

Portals typically have:
- `Main.tileSolid[Type] = false` - Not solid (players can pass through)
- `Main.tileLighted[Type] = true` - Emits light
- `Main.tileFrameImportant[Type] = true` - Frame-based animation
- `AnimationFrameHeight` - Height of each frame

## Customization

### Changing Colors

Edit the `ModifyLight` method in the generated `.cs` file:

```csharp
public override void ModifyLight(int i, int j, ref float r, ref float g, ref float b)
{
    r = 0.5f;  // Red component (0.0 - 1.0)
    g = 0.2f;  // Green component
    b = 1.0f;  // Blue component (purple glow)
}
```

### Adjusting Animation Speed

Modify the `AnimateTile` method:

```csharp
public override void AnimateTile(ref int frame, ref int frameCounter)
{
    frameCounter++;
    if (frameCounter >= 5)  // Lower = faster animation
    {
        frameCounter = 0;
        frame++;
        if (frame >= FrameCount)
        {
            frame = 0;
        }
    }
}
```

### Adding Teleportation

Add teleportation logic to the tile class:

```csharp
public override bool RightClick(int i, int j)
{
    // Teleport player to linked portal
    Player player = Main.LocalPlayer;
    // Your teleportation logic here
    return true;
}
```

## Integration with Asset Generator Control Room

You can use the Control Room to refine portal designs:

```powershell
# Generate portal with Control Room
.\AssetGeneratorControlRoom.ps1 `
    -AssetType "Texture" `
    -DrawingPath "portal_sketch.png" `
    -ExportTargets @("Terraria") `
    -AutoExport

# Then use generated texture in portal generator
.\TerrariaPortalGenerator.ps1 `
    -PortalName "CustomPortal" `
    -PortalDescription "Use the texture from Control Room"
```

## Examples

### Example 1: Nether Portal

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "NetherPortal" `
    -PortalDescription "A dark purple portal with swirling energy, nether-themed" `
    -FrameCount 10 `
    -TileSize 16
```

### Example 2: Crystal Portal (High-Res)

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "CrystalPortal" `
    -PortalDescription "A bright blue crystalline portal with magical runes" `
    -FrameCount 12 `
    -TileSize 32 `
    -UseAI
```

### Example 3: Fire Portal

```powershell
.\TerrariaPortalGenerator.ps1 `
    -PortalName "FirePortal" `
    -PortalDescription "A blazing orange-red portal with flames and embers" `
    -FrameCount 8 `
    -TileSize 16
```

## Installation in tModLoader

1. **Copy Mod Folder**:
   - Place the generated mod folder in: `Documents/My Games/Terraria/ModLoader/Mods/`

2. **Build Mod**:
   - Open tModLoader
   - Go to Mods menu
   - Click "Build All" or build your specific mod

3. **Enable Mod**:
   - Enable the mod in the Mods menu
   - Restart Terraria

4. **Test**:
   - Start a new world or load existing
   - Use a mod item editor or creative mode to place the portal tile
   - Verify animation works correctly

## Troubleshooting

### Animation Not Working

- Check that `AnimationFrameHeight` matches tile size
- Verify frame count in `AnimateTile` matches spritesheet
- Ensure `Main.tileFrameImportant[Type] = true`

### Portal Not Visible

- Check file path in `ModContent.Request<Texture2D>`
- Verify spritesheet is in correct location
- Ensure transparency is preserved in PNG

### Glow Not Showing

- Verify `ModifyLight` method is implemented
- Check that `Main.tileLighted[Type] = true`
- Ensure color values are in 0.0-1.0 range

### Build Errors

- Ensure tModLoader is installed
- Check that all required files are present
- Verify C# syntax is correct

## Advanced Features

### Multiple Portal Variants

Generate multiple portals with different themes:

```powershell
.\TerrariaPortalGenerator.ps1 -PortalName "FirePortal" -PortalDescription "Fire theme"
.\TerrariaPortalGenerator.ps1 -PortalName "IcePortal" -PortalDescription "Ice theme"
.\TerrariaPortalGenerator.ps1 -PortalName "VoidPortal" -PortalDescription "Void theme"
```

### Custom Spritesheet

If you have a custom spritesheet:

1. Place it in `Assets/Textures/Tiles/PortalName.png`
2. Update `FrameCount` in the tile class to match your frames
3. Adjust `AnimationFrameHeight` if needed

### Particle Effects

Add particle effects in `PostDraw` method:

```csharp
public override void PostDraw(int i, int j, SpriteBatch spriteBatch)
{
    // Existing glow code...
    
    // Add particles
    if (Main.rand.NextBool(10))
    {
        Dust.NewDust(
            new Vector2(i * 16, j * 16),
            16, 16,
            DustID.PurpleTorch,
            0f, 0f,
            100, default,
            1.5f
        );
    }
}
```

## Best Practices

1. **Frame Count**: Use 8-12 frames for smooth animation
2. **Tile Size**: 16×16 for standard, 32×32 for high-res
3. **Animation Speed**: 5-10 frame counter for good pacing
4. **Colors**: Use bright, saturated colors for visibility
5. **Transparency**: Preserve alpha channel for portal effects
6. **Testing**: Always test in-game before finalizing

## References

- **tModLoader Documentation**: https://tmodloader.org/docs/
- **Terraria Source**: https://github.com/kran27/Terraria (old version, for reference)
- **Terraria Forums**: Community support and examples

## Next Steps

1. Generate your portal asset
2. Customize the tile class for your needs
3. Add teleportation logic if desired
4. Test in tModLoader
5. Share your mod!

---

**Generated by**: Terraria Portal Asset Generator  
**Compatible with**: tModLoader  
**Terraria Version**: 1.4+

