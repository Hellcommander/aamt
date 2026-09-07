# ExportModAssets Tool Guide

## Overview

The `ExportModAssets.ps1` tool helps modders create game assets (spritesheets, projectiles, ships, items) by using the official [TranscendenceArt repository](https://github.com/kronosaur/TranscendenceArt) as reference material. It automatically handles proper credits and attribution.

## Features

- **Automatic Repository Cloning**: Downloads the TranscendenceArt repository if not present
- **Asset Export**: Extracts images and models from specific folders
- **Spritesheet Generation**: Creates spritesheets from multiple images (requires ImageMagick)
- **Proper Attribution**: Automatically includes credits file with exported assets
- **Drag-and-Drop Support**: Easy folder selection via batch file

## Prerequisites

- **Git**: For cloning the repository (download from https://git-scm.com/)
- **ImageMagick** (Optional): For automatic spritesheet generation (download from https://imagemagick.org/)
  - Without ImageMagick, the tool creates a manifest file for manual spritesheet creation

## Usage

### Basic Usage

```powershell
# Clone repository and list available folders
.\ExportModAssets.ps1 -CloneRepo

# Export all assets
.\ExportModAssets.ps1 -AssetType All -OutputPath "MyMod\Assets"

# Export specific folder (e.g., "Items")
.\ExportModAssets.ps1 -SourceFolder "Items" -OutputPath "MyMod\Resources"

# Generate spritesheet from images
.\ExportModAssets.ps1 -SourceFolder "Items" -GenerateSpritesheet -OutputPath "MyMod\Resources"
```

### Examples

**Export Commonwealth Fleet assets:**
```powershell
.\ExportModAssets.ps1 -SourceFolder "Commonwealth Fleet" -OutputPath "MyMod\Resources\Ships" -IncludeCredits
```

**Create projectile spritesheet:**
```powershell
.\ExportModAssets.ps1 -AssetType Projectile -GenerateSpritesheet -OutputPath "MyMod\Resources" -TileWidth 32 -TileHeight 32
```

**Export all items with credits:**
```powershell
.\ExportModAssets.ps1 -AssetType Item -OutputPath "MyMod\Assets" -IncludeCredits
```

### Drag-and-Drop

1. Clone the repository first: `.\ExportModAssets.ps1 -CloneRepo`
2. Drag a folder from the repository onto `ExportModAssets.bat`
3. Assets will be exported to the default output directory

## Parameters

- **`-ArtRepoPath`**: Path to TranscendenceArt repository (default: `Tools\TranscendenceArt`)
- **`-OutputPath`**: Output directory for exported assets (default: `Tools\ExportedAssets`)
- **`-AssetType`**: Type of assets to process: `Spritesheet`, `Projectile`, `Ship`, `Item`, `All` (default: `All`)
- **`-SourceFolder`**: Specific folder in Art repo to process (e.g., "Commonwealth Fleet", "Items")
- **`-GenerateSpritesheet`**: Generate spritesheet from images
- **`-IncludeCredits`**: Include credits file with exported assets (recommended)
- **`-CloneRepo`**: Force clone/download of the repository

## Spritesheet Generation

### With ImageMagick (Automatic)

If ImageMagick is installed, the tool will:
1. Resize all images to the specified tile size
2. Arrange them in a grid
3. Create a single PNG spritesheet
4. Generate a metadata file with tile mappings

### Without ImageMagick (Manual)

The tool creates a detailed manifest file with:
- Image list and locations
- Tile coordinates (row, column)
- Instructions for manual spritesheet creation
- Tile index mapping for XML reference

## Credits and Attribution

The tool automatically includes proper attribution to the TranscendenceArt repository:

```
Transcendence Art Assets Reference
===================================

This mod uses assets created with reference to the official TranscendenceArt repository:
https://github.com/kronosaur/TranscendenceArt

Original 3D models and artwork:
Copyright (c) 2003-2019 by Kronosaur Productions, LLC.
https://transcendence.kronosaur.com
```

**Always include credits** when using assets derived from TranscendenceArt!

## Output Structure

```
ExportedAssets/
├── Items/
│   ├── image1.png
│   ├── image2.jpg
│   ├── spritesheet.png (if generated)
│   ├── spritesheet_metadata.txt
│   └── CREDITS_TranscendenceArt.txt
├── Commonwealth Fleet/
│   └── ...
└── ...
```

## Using Exported Assets in Your Mod

1. **Copy assets to your mod's Resources folder:**
   ```
   YourMod/
   ├── YourMod.xml
   └── Resources/
       ├── spritesheet.png
       └── ...
   ```

2. **Reference in XML:**
   ```xml
   <Image UNID="&rsMySprite;" bitmap="Resources\spritesheet.png" />
   ```

3. **Use tile coordinates from metadata:**
   - Tile 0 = Row 0, Col 0
   - Tile 1 = Row 0, Col 1
   - etc.

## Tips

- **Start with reference**: Use TranscendenceArt as reference, then create your own assets
- **Respect licenses**: Always include proper credits
- **Test in game**: Verify assets display correctly
- **Optimize**: Compress images appropriately for game performance
- **Documentation**: Keep the metadata files for future reference

## Troubleshooting

**Git not found:**
- Install Git from https://git-scm.com/
- Ensure Git is in your PATH

**ImageMagick not found:**
- Install from https://imagemagick.org/
- Or use the manifest file to create spritesheets manually

**Repository clone fails:**
- Check internet connection
- Verify Git is installed correctly
- Try cloning manually: `git clone https://github.com/kronosaur/TranscendenceArt.git`

## Related Tools

- **CompileApiFolder.ps1**: Compiles API source code
- **BuildReferenceArchive.ps1**: Creates reference archive of game assets
- **TranscendenceTlispXmlChecker.ps1**: Validates mod XML files

## Resources

- TranscendenceArt Repository: https://github.com/kronosaur/TranscendenceArt
- Transcendence Forums: https://forums.kronosaur.com/
- Game Website: https://transcendence.kronosaur.com/

