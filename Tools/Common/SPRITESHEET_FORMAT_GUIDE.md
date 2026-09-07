# Spritesheet Format Guide

Guide to spritesheet formats for different games and asset types.

## Game-Specific Format Requirements

### Transcendence

**Ships:**
- **Format**: JPG (JPEG)
- **Mask**: Separate BMP file for transparency
- **Example**: `ShipName.jpg` + `ShipNameMask.bmp`
- **Reason**: Ships use JPG for smaller file size, with separate mask for transparency

**Items/Weapons/Projectiles:**
- **Format**: PNG
- **Transparency**: Built-in alpha channel
- **Example**: `ItemName_icon.png`
- **Reason**: Items need transparency, PNG supports alpha channel

**Spritesheets:**
- **Format**: PNG (for items/weapons), JPG (for ships)
- **Layout**: Grid-based (e.g., 10×12 for 120 facings)
- **Transparency**: PNG with alpha, or JPG + separate mask

### Terraria (tModLoader)

**All Assets:**
- **Format**: PNG
- **Transparency**: Built-in alpha channel
- **Tile Size**: 16×16 or 32×32 pixels
- **Spritesheets**: PNG with grid layout

### Starbound

**All Assets:**
- **Format**: PNG
- **Transparency**: Built-in alpha channel
- **Spritesheets**: PNG with `.frames` metadata file
- **Layout**: Grid-based with frame definitions

## Format Selection

The generator automatically selects the appropriate format:

```powershell
# Ship (Transcendence) - Uses JPG
.\TranscendenceAssetGenerator.ps1 -AssetType Ship -AssetName "MyShip" -GameFormat Transcendence
# Output: MyShip.jpg + MyShipMask.bmp

# Item (Transcendence) - Uses PNG
.\TranscendenceAssetGenerator.ps1 -AssetType Item -AssetName "MyItem" -GameFormat Transcendence
# Output: MyItem_icon.png

# Spritesheet (Terraria) - Uses PNG
.\TranscendenceAssetGenerator.ps1 -AssetType Spritesheet -AssetName "MySheet" -GameFormat Terraria
# Output: MySheet_spritesheet.png

# Spritesheet (Starbound) - Uses PNG
.\TranscendenceAssetGenerator.ps1 -AssetType Spritesheet -AssetName "MySheet" -GameFormat Starbound
# Output: MySheet_spritesheet.png + MySheet.frames
```

## Blender Export Formats

When using Blender for spritesheet generation:

### Transcendence Ships
```bash
blender --background --python blender_ship_spritesheet_export.py -- \
    --model "ship.blend" \
    --output "ship.jpg" \
    --game-format Transcendence \
    --output-format JPG \
    --facings 120 \
    --columns 10 \
    --rows 12
```

### Transcendence Items
```bash
blender --background --python blender_asset_spritesheet_export.py -- \
    --model "item.blend" \
    --output "item_spritesheet.png" \
    --game-format Transcendence \
    --output-format PNG \
    --asset-type item \
    --facings 1 \
    --columns 8 \
    --rows 8
```

### Terraria/Starbound
```bash
blender --background --python blender_asset_spritesheet_export.py -- \
    --model "asset.blend" \
    --output "asset_spritesheet.png" \
    --game-format Terraria \
    --output-format PNG \
    --asset-type item
```

## Format Conversion

The Blender scripts automatically handle format conversion:

1. **Renders frames as PNG** (for compositing with transparency)
2. **Composites into spritesheet** (maintaining transparency)
3. **Converts to final format**:
   - **JPG**: Converts RGBA → RGB, saves as JPEG
   - **PNG**: Keeps RGBA, saves as PNG
   - **BMP**: Converts RGBA → RGB, saves as BMP

## Mask Generation

For Transcendence ships using JPG format, masks are generated separately:

- **Format**: BMP
- **Content**: Black (transparent) and white (opaque)
- **Method**: Extracted from alpha channel of rendered frames
- **Usage**: Game engine uses mask for transparency on JPG spritesheets

## Best Practices

1. **Use PNG for items/weapons** - Better transparency support
2. **Use JPG for ships** - Smaller file size, separate mask for transparency
3. **Always generate masks** for JPG spritesheets
4. **Test in-game** to ensure format compatibility
5. **Check file sizes** - JPG is smaller, PNG preserves quality

## File Size Considerations

- **JPG**: ~70% smaller than PNG (for ships)
- **PNG**: Better quality, supports transparency
- **BMP**: Largest, but maximum compatibility

Choose format based on:
- **File size**: JPG for large spritesheets
- **Quality**: PNG for detailed assets
- **Transparency**: PNG or JPG+BMP mask
- **Game requirements**: Follow game-specific format needs

