# Starbound Spritesheet Generation Improvements

## Issues Fixed

### 1. **Image Format (32-bit RGBA PNG)**
- **Problem**: Generated images may not be in the correct format Starbound requires
- **Fix**: All bitmaps are now created explicitly in `Format32bppArgb` format
- **Fix**: PNG files are saved with uncompressed encoding to ensure proper format
- **Location**: `StarboundAssetGenerator.ps1` - all `New-Object System.Drawing.Bitmap` calls

### 2. **Frame Size Mismatch in .frames Files**
- **Problem**: `.frames` files were using generation dimensions instead of final frame dimensions
- **Fix**: Animation spritesheet `.frames` files now use `$finalFrameWidth` and `$finalFrameHeight` instead of `$frameWidth` and `$frameHeight`
- **Location**: Line ~950 in `StarboundAssetGenerator.ps1`

### 3. **Sprite Quality Improvements**
- **Problem**: Sprites were just colored rectangles with minimal detail
- **Fix**: Implemented layered sprite generation (rim, middle, core, accent) similar to Terraria portal generator
- **Fix**: Added shape detection (Circle, Square, Hexagon, Tear, Ellipse) from descriptions
- **Fix**: Improved pattern generation for different styles (metallic, organic, energy)
- **Location**: Lines ~436-600 in `StarboundAssetGenerator.ps1`

### 4. **Graphics Quality Settings**
- **Problem**: Graphics objects didn't have optimal quality settings
- **Fix**: Added `PixelOffsetMode`, `CompositingMode`, and `CompositingQuality` settings for better rendering
- **Location**: All `[System.Drawing.Graphics]::FromImage` calls

## Starbound Asset Requirements

### Image Format
- **Format**: 32-bit RGBA PNG (uncompressed)
- **Pixel Format**: `Format32bppArgb`
- **Compression**: None (uncompressed PNG)

### .frames File Format
```json
{
  "frameGrid": {
    "size": [width, height],  // Frame size in pixels
    "dimensions": [columns, rows]  // Grid layout (e.g., [8, 1] for 8 frames in a row)
  },
  "aliases": {
    "default": [0, 1, 2, ...]  // Frame indices for default animation
  }
}
```

### Frame Size Requirements
- **ItemSprite**: 16x16 per frame
- **MechSprite**: 48x48 per frame
- **Projectile**: 48x48 per frame
- **Particle**: 32x32 per frame
- **Icon**: 64x64 per frame

### Spritesheet Layout
- Frames are arranged horizontally (left to right)
- Each frame must be exactly the frame size
- Spritesheet width = frame width × frame count
- Spritesheet height = frame height

## Validation Checklist

Before considering an asset "complete", verify:

1. ✅ Image is 32-bit RGBA PNG format
2. ✅ `.frames` file exists and is valid JSON
3. ✅ `.frames` file `frameGrid.size` matches actual frame dimensions
4. ✅ `.frames` file `frameGrid.dimensions` matches spritesheet layout
5. ✅ Spritesheet width = frame width × frame count
6. ✅ Spritesheet height = frame height
7. ✅ Image contains actual sprite content (not just colored boxes)
8. ✅ Image has proper alpha channel (transparency where needed)

## Debugging Tips

1. **Open generated PNG in image viewer** - verify sprites are visible and correctly laid out
2. **Validate .frames JSON** - use a JSON validator to ensure format is correct
3. **Check Starbound logs** - look for asset loading errors in `starbound.log`
4. **Use asset viewer** - Starbound's asset viewer can help verify frame layout
5. **Compare with working assets** - check existing Starbound assets for reference format

## Next Steps

To further improve asset generation:

1. **Add segment-based packing** - Support combining multiple segment sprites (head, core, thruster, etc.)
2. **Add bin-packing algorithm** - Use MaxRects or similar for efficient spritesheet packing
3. **Add pivot point support** - Include pivot points in .frames or separate metadata
4. **Add animation metadata** - Generate .animation files with frame durations
5. **Add quality validation** - Automatically detect and reject "colored box" outputs
