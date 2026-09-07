# Unity Integration Guide

This guide explains how to integrate generated assets into Unity projects for the Elin game mod.

## Overview

The Asset Generator creates Unity-compatible assets including:
- Textures with power-of-2 dimensions
- Unity `.meta` files for proper import settings
- **PBR skin sets** (diffuse / normal / roughness / metallic / metallicgloss / emission)
- Material presets (`.mat` files) that pull in skin maps when present
- Optional simple skinned meshes (FBX via Blender stub)
- Sprite atlases and spritesheets

Canonical layout for CustomRaceClassCreator:

```
[ModPath]/Assets/Resources/{SystemName}/
  Textures/          (+ Textures/Skins/{System}_*.png)
  Icons/
  Sprites/
  Materials/
  Prefabs/
  Meshes/             (FBX from GeneratePbrSkin.ps1 -ExportMesh; shapes: displaced/armor_panel/organic/...)
  SpellAssets/
  UI/
```

## Quick Start

### 1. Generate Assets for Unity

```powershell
.\OllamaAssetGenerator.ps1 -ModPath "C:\YourMod\Path" -AssetTypes "textures" -Quality "high"
```

Textures land under `Assets/Resources/{System}/Textures/` (not `Assets/Textures/`).  
Texture runs also write a PBR skin set under `Textures/Skins/`.

### PBR skins + optional mesh

```powershell
.\GeneratePbrSkin.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName DragonMagic -Theme "dragon scale armor" -Quality high
.\GeneratePbrSkin.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName DragonMagic -ExportMesh -Shape armor_panel
```

Uses the **exact** Unity Editor matched to the live Elin build (`2021.3.45f2` under `E:\tools\Unity_Editor`) when building materials / AssetBundles.

### 2. Import into Unity

1. Open your Unity project
2. Navigate to the mod's `Assets` folder in Unity's Project window
3. Unity will automatically import the textures and recognize the `.meta` files
4. Wait for Unity to finish importing (check the bottom-right progress bar)

### 3. Use in Materials

1. Create a new Material in Unity: `Assets > Create > Material`
2. Assign the generated texture to the material's Albedo slot
3. If normal/emission maps were generated, assign them to their respective slots
   - Or regenerate materials via CustomRaceClassCreatorAssetGenerator (auto-assigns `Textures/Skins/*`)

## Directory Structure

The generator creates the following Unity-compatible structure:

```
[ModPath]/
├── Assets/
│   ├── Resources/
│   │   └── [SystemName]/
│   │       ├── Textures/
│   │       │   ├── texture_name.png
│   │       │   ├── texture_name.png.meta
│   │       │   └── Skins/
│   │       │       ├── System_diffuse.png (+ normal/roughness/metallic/metallicgloss/emission + .meta)
│   │       │       └── System_pbr.json
│   │       ├── Materials/
│   │       ├── Prefabs/
│   │       ├── Meshes/
│   │       └── UI/
│   └── AssetBundles/
│       └── Windows/
```

> Older docs mentioned `Assets/Textures/{System}/`. Prefer **`Assets/Resources/{System}/...`** — that is what CustomRaceClassCreator and the asset checker expect.

## Steam Deck / Linux

Code-based mods need Proton `winhttp` override. See [`STEAM_DECK_LINUX.md`](./STEAM_DECK_LINUX.md).

## Texture Import Settings

The generated `.meta` files configure Unity with optimal settings:

### Standard Texture Settings
- **Texture Type**: Default (for textures) or Sprite (2D and UI) for icons/sprites
- **Max Size**: 2048 (configurable via quality settings)
- **Compression**: Automatic based on quality tier
- **Generate Mip Maps**: Enabled for textures
- **sRGB**: Enabled for color textures
- **Filter Mode**: Bilinear
- **Wrap Mode**: Repeat (for tileable textures)

### Quality-Based Settings

| Quality | Max Size | Compression | Format |
|---------|----------|-------------|--------|
| Low | 256 | ETC_RGB4 | Compressed |
| Medium | 512 | DXT5 | Compressed |
| High | 1024 | BC7 | Compressed |
| Ultra | 2048 | RGBA32 | Uncompressed |

## Material Presets

The generator can create material presets with pre-configured settings:

### Standard Material
- Uses the generated texture as Albedo
- Includes normal map if generated
- Includes emission map if generated
- Configured for Standard shader

### PBR Material (High/Ultra Quality)
- Physically Based Rendering setup
- Metallic/Smoothness maps
- Normal maps
- Emission maps for glow effects

## Using Generated Assets

### Textures

1. **Find the Texture**: Navigate to `Assets/Textures/[SystemName]/` in Unity
2. **Select the Texture**: Click on the texture file
3. **Configure Import Settings**: In the Inspector, adjust settings if needed:
   - **Texture Type**: Default, Sprite, or Normal Map
   - **Max Size**: Adjust based on your needs
   - **Compression**: Choose quality vs. file size
4. **Apply**: Click "Apply" to save settings

### Sprites

1. **Import as Sprite**: Set Texture Type to "Sprite (2D and UI)"
2. **Configure Sprite Settings**:
   - **Pixels Per Unit**: 100 (default, adjust as needed)
   - **Filter Mode**: Point (for pixel art) or Bilinear (for smooth)
   - **Compression**: None (for pixel art) or Automatic
3. **Sprite Editor**: Use Unity's Sprite Editor to slice spritesheets if needed

### Spritesheets

If you generated spritesheets:

1. **Import the Spritesheet**: The spritesheet PNG will be in the Sprites folder
2. **Set as Sprite**: Change Texture Type to "Sprite (2D and UI)"
3. **Open Sprite Editor**: Click "Sprite Editor" button
4. **Slice the Sheet**: 
   - Choose "Grid By Cell Count" or "Grid By Cell Size"
   - Enter the frame dimensions (from spritesheet metadata)
   - Click "Slice"
5. **Apply**: Save the sprite settings

### Material Presets

1. **Locate Material**: Find `.mat` files in `Assets/Materials/[SystemName]/`
2. **Assign to Object**: Drag the material onto a GameObject in the scene
3. **Customize**: Adjust material properties in the Inspector as needed

## Advanced Configuration

### Custom Import Settings

You can customize texture import settings by editing the `.meta` files or using Unity's Preset system:

1. **Create a Preset**: 
   - Configure a texture's import settings
   - Click the preset icon (three dots) in the Inspector
   - Select "Save current to..."
2. **Apply Preset**: 
   - Select multiple textures
   - Apply the preset to all selected

### Batch Import

For large numbers of assets:

1. **Select All Assets**: In Project window, select all textures in a folder
2. **Apply Settings**: Configure import settings once
3. **Reimport**: Right-click > Reimport (if needed)

### Asset Refresh

If you regenerate assets:

1. **Delete Old Assets**: Remove old textures from Unity (optional, Unity will update)
2. **Regenerate**: Run the asset generator
3. **Refresh in Unity**: Unity will detect new/changed files automatically
   - Or manually: `Assets > Refresh` (Ctrl+R)

## Troubleshooting

### Textures Not Appearing

**Problem**: Textures don't show up in Unity

**Solutions**:
- Check that files are in `Assets/Textures/` folder (not outside Assets)
- Verify `.meta` files exist alongside texture files
- Refresh Unity: `Assets > Refresh` (Ctrl+R)
- Check Unity Console for import errors

### Import Errors

**Problem**: Unity shows import errors in Console

**Solutions**:
- Verify texture dimensions are power-of-2 (generator handles this automatically)
- Check file permissions (ensure Unity can read the files)
- Verify PNG file integrity (try opening in an image viewer)
- Check Unity Console for specific error messages

### Materials Not Working

**Problem**: Materials don't display correctly

**Solutions**:
- Verify texture is assigned to the correct material slot
- Check shader compatibility (Standard shader for most cases)
- Ensure textures are imported (not still importing)
- Check material's rendering mode (Opaque, Transparent, etc.)

### Performance Issues

**Problem**: Too many high-resolution textures causing lag

**Solutions**:
- Use lower quality settings for non-essential textures
- Enable texture compression
- Use texture atlases/spritesheets instead of individual textures
- Reduce Max Size in import settings
- Use Mip Maps for distant objects

## Best Practices

### Organization

1. **Use Folders**: Organize by system/type in subfolders
2. **Naming Convention**: Use consistent naming (e.g., `system_assettype_name.png`)
3. **Keep Structure**: Maintain the generated folder structure

### Performance

1. **Quality vs. Size**: Use appropriate quality for each asset type
   - Icons: Low-Medium quality
   - UI Elements: Medium quality
   - Textures: High quality
   - Hero Assets: Ultra quality
2. **Compression**: Enable compression for most textures
3. **Atlases**: Use spritesheets for multiple related sprites

### Workflow

1. **Generate First**: Run generator before importing to Unity
2. **Test Import**: Import a few assets first to verify settings
3. **Batch Process**: Generate all assets, then import
4. **Version Control**: Commit `.meta` files to version control

## Configuration

### Quality Settings

Edit `AssetGeneration.config.json` to customize:

```json
{
  "qualityPresets": [
    {
      "name": "High",
      "textureSize": 1024,
      "textureFormat": "BC7",
      "generateMipmaps": true,
      "compressTextures": true
    }
  ]
}
```

### Unity-Specific Settings

The generator creates `.meta` files with Unity-optimized settings. To customize:

1. **Edit Meta Files**: Modify `.meta` files directly (advanced)
2. **Use Presets**: Create Unity import presets and apply
3. **Post-Import**: Adjust settings in Unity after import

## See Also

- `QUICK_START.md` - Basic usage guide
- `TEXTURE_FORMAT_GUIDE.md` - Detailed texture format information
- `TROUBLESHOOTING.md` - Common issues and solutions
- `AssetGeneration.config.json` - Configuration options

## Support

For issues or questions:
1. Check `TROUBLESHOOTING.md` for common solutions
2. Review Unity Console for error messages
3. Verify all dependencies are installed (Python, Pillow)
4. Check that paths don't contain special characters
