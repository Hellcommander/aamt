# Export to Spritesheet Tool

## Overview

The `ExportToSpritesheet.ps1` tool allows you to export previously generated source assets (Blender renders, textures) to spritesheets. It preserves high-quality source files and allows re-exporting with different settings.

## Features

- **Preserves Source Files**: Automatically organizes Blender renders, textures, and models into a `Source` subdirectory
- **Removes Low-Quality Files**: Cleans up intermediate low-quality files (previews, thumbnails, drafts)
- **Re-export Capability**: Export to spritesheets multiple times with different settings
- **Organized Structure**: Source files are organized by type (Blender, Textures, Models)

## Usage

### Basic Usage

```powershell
.\ExportToSpritesheet.ps1 -InputDir "Output\SpaceWhaleAssets" -AssetName "SpaceWhale" -Columns 10
```

### With Custom Settings

```powershell
.\ExportToSpritesheet.ps1 `
    -InputDir "Output\SpaceWhaleAssets" `
    -OutputDir "Output\SpaceWhaleAssets\Spritesheets" `
    -AssetName "SpaceWhale" `
    -Columns 10 `
    -Rows 12 `
    -FrameWidth 150 `
    -FrameHeight 150 `
    -OutputFormat "PNG"
```

### Parameters

- **InputDir** (Required): Directory containing source assets (Blender renders, textures)
- **OutputDir** (Optional): Output directory for spritesheets (defaults to InputDir)
- **AssetName** (Optional): Name of the asset (used for output filenames)
- **Columns** (Optional): Number of columns in spritesheet (default: 10)
- **Rows** (Optional): Number of rows (auto-calculated if not specified)
- **FrameWidth** (Optional): Width of each frame in pixels (default: 150)
- **FrameHeight** (Optional): Height of each frame in pixels (default: 150)
- **OutputFormat** (Optional): Output format - PNG, JPG, or BMP (default: PNG)
- **KeepSourceFiles** (Switch): Keep source files after export (default: true)
- **CleanLowQuality** (Switch): Remove lower quality intermediate files (default: true)

## Source File Organization

The tool automatically organizes source files into a `Source` subdirectory:

```
Output/
├── AssetName_spritesheet.png    (Final spritesheet)
├── Source/
│   ├── Blender/                 (Blender render frames)
│   │   ├── frame_0001.png
│   │   ├── frame_0002.png
│   │   └── ...
│   ├── Textures/                (Texture files)
│   │   ├── diffuse.png
│   │   ├── normal.png
│   │   └── ...
│   └── Models/                  (3D model files)
│       ├── model.obj
│       └── model.blend
```

## Low-Quality File Cleanup

The tool automatically removes low-quality intermediate files matching these patterns:
- `*_low.png`, `*_low.jpg`
- `*_preview.png`, `*_preview.jpg`
- `*_thumb.png`, `*_thumb.jpg`
- `*_temp.png`, `*_temp.jpg`
- `*_tmp.png`, `*_tmp.jpg`
- `*_draft.png`, `*_draft.jpg`

## Integration with Asset Generators

Asset generators (like `TranscendenceAssetGenerator.ps1`) now automatically preserve source files:

1. **Blender Renders**: Individual render frames are saved to `Source/Blender/`
2. **Models**: `.obj` and `.blend` files are saved to `Source/Models/`
3. **Textures**: Texture files are saved to `Source/Textures/`

This allows you to:
- Re-export spritesheets with different settings
- Edit source files and regenerate
- Keep high-quality source assets for future use

## Examples

### Export from Existing Source Files

```powershell
# Export a spritesheet from previously generated Blender renders
.\ExportToSpritesheet.ps1 `
    -InputDir "Output\SpaceWhaleAssets\Source\Blender" `
    -AssetName "SpaceWhale" `
    -Columns 10 `
    -Rows 12
```

### Re-export with Different Settings

```powershell
# Export with different frame size
.\ExportToSpritesheet.ps1 `
    -InputDir "Output\SpaceWhaleAssets\Source\Blender" `
    -AssetName "SpaceWhale_Large" `
    -Columns 8 `
    -FrameWidth 200 `
    -FrameHeight 200
```

## Requirements

- PowerShell 5.1 or later
- Python (for spritesheet assembly)
- Pillow library (`pip install Pillow`)
- CrossGameSpritesheet.ps1 tool (included in Tools/Common/)

## Notes

- Source files are copied (not moved) to preserve originals
- The tool uses the CrossGameSpritesheet tool for actual spritesheet assembly
- Files are sorted by name to ensure correct frame order
- Low-quality files are removed from the main directory but preserved in Source if they're actual source files

