# Space Whale 120 Facings Guide

## Overview

Space Whale ships require **120 facings** (rotation frames) for complete 360-degree coverage. This provides smooth rotation at **3 degrees per frame** (360° / 120 = 3°).

## Spritesheet Layout

### Grid Structure
- **Total Facings**: 120
- **Columns**: 10
- **Rows**: 12
- **Layout**: 10×12 grid
- **Rotation**: 3° per frame

### Frame Order
```
Row 1:   0°   3°   6°   9°  12°  15°  18°  21°  24°  27°
Row 2:  30°  33°  36°  39°  42°  45°  48°  51°  54°  57°
Row 3:  60°  63°  66°  69°  72°  75°  78°  81°  84°  87°
...
Row 12: 330° 333° 336° 339° 342° 345° 348° 351° 354° 357°
```

## Generation

### Using Blender Script

```powershell
.\SpaceWhale120FacingsGenerator.ps1 -RegistryPath "space_whale_ship_example.json" -OutputDir "Output/120Facings"
```

This will:
- Render 120 rotation frames (one per 3°)
- Composite into 10×12 grid spritesheet
- Generate transparency mask (BMP)
- Output PNG spritesheet + BMP mask

### Manual Blender Command

```bash
blender --background --python blender_space_whale_120_facings.py -- \
    --registry space_whale_ship_example.json \
    --ship-id leviathan_alpha \
    --output-dir Output/120Facings \
    --columns 10 \
    --rows 12 \
    --animation-frames 16
```

## Output Files

### Spritesheet
- **File**: `{ship_id}_120facings.png`
- **Format**: PNG with alpha channel
- **Size**: `(frame_size × 10) × (frame_size × 12)`
- **Layout**: 10 columns × 12 rows

### Mask
- **File**: `{ship_id}_120facingsMask.bmp`
- **Format**: BMP (Transcendence requirement)
- **Content**: Black (transparent) / White (opaque)
- **Size**: Same as spritesheet

## Transcendence Integration

### XML Format

```xml
<Image UNID="&shLeviathanAlphaImage;">
    <ImageDesc
        bitmap="Resources/Ships/leviathan_alpha_120facings.png"
        bitmask="Resources/Ships/leviathan_alpha_120facingsMask.bmp"
        frameCount="120"
        rotationCount="120"
        ticksPerFrame="1"
    />
</Image>
```

### Ship Class

```xml
<ShipClass UNID="&shLeviathanAlpha;">
    <Image>&shLeviathanAlphaImage;</Image>
    <!-- ... other ship properties ... -->
</ShipClass>
```

## Frame Calculation

### Rotation Mapping
- **Facing 0**: 0° (facing right/east)
- **Facing 30**: 90° (facing up/north)
- **Facing 60**: 180° (facing left/west)
- **Facing 90**: 270° (facing down/south)
- **Facing 120**: 360° (back to 0°)

### Angle to Facing
```python
angle_degrees = 45.0
facing_index = int((angle_degrees / 360.0) * 120) % 120
# Result: facing_index = 15
```

### Facing to Angle
```python
facing_index = 15
angle_degrees = (facing_index / 120.0) * 360.0
# Result: angle_degrees = 45.0
```

## Performance Considerations

### File Size
- **120 facings × frame_size**: Large file
- **Recommendation**: 
  - Frame size: 256-512 pixels
  - Total spritesheet: ~2560×3072 to 5120×6144 pixels
  - File size: ~5-20 MB (PNG)

### Optimization
- Use **JPG + BMP mask** for smaller file size (Transcendence ships)
- Generate **mipmaps** for LOD
- Consider **compression** settings

## Animation Frames

### Per-Facing Animation
Each facing can have multiple animation frames:
- **Breathing**: 16 frames
- **Gill pulse**: 8 frames
- **Tail sweep**: 12 frames

### Total Frames
- **Base**: 120 facings × 1 frame = 120 frames
- **With breathing**: 120 facings × 16 frames = 1,920 frames
- **Spritesheet**: Organize as `(facings × animation_frames)` grid

## Testing

### Verify Facings
1. **Load spritesheet** in game
2. **Rotate ship** 360°
3. **Check smoothness**: No stuttering or jumps
4. **Verify alignment**: Ship should face correct direction

### Common Issues
- **Stuttering**: Missing frames or incorrect frame order
- **Wrong direction**: Frame 0 should face east (right)
- **Gaps**: Ensure all 120 facings are rendered
- **Mask issues**: Check BMP mask matches PNG alpha

## Files

- `blender_space_whale_120_facings.py` - 120 facings renderer
- `SpaceWhale120FacingsGenerator.ps1` - Generator script
- `SPACE_WHALE_120_FACINGS_GUIDE.md` - This guide

## Quick Start

1. **Prepare ship model** in Blender
2. **Run generator**:
   ```powershell
   .\SpaceWhale120FacingsGenerator.ps1 -RegistryPath "space_whale_ship_example.json"
   ```
3. **Wait for rendering** (120 frames takes time)
4. **Verify output**: Check PNG + BMP files
5. **Integrate**: Add to Transcendence XML

## Conclusion

The 120 facings system provides **smooth 360-degree rotation** with **3-degree precision**. All rendering scripts support this format! 🎨

