# Space Whale 120 Facings Rendering Scripts

## Overview

This collection provides comprehensive Blender rendering scripts for generating 120-facing spritesheets for all Space Whale ship variants in Transcendence.

## File Structure

```
Tools/Transcendence/
├── blender_space_whale_120_facings.py          # Generic/template renderer
├── blender_space_whale_main_120_facings.py     # Main whale ship (256x256)
├── blender_space_whale_segment_120_facings.py  # Whale segments (128x128)
├── blender_space_whale_drone_120_facings.py    # Whale drones (64x64)
├── render_all_120_facings.bat                  # Batch renderer for all ships
├── SpaceWhale120FacingsGenerator.ps1           # PowerShell orchestrator
└── SpaceWhale120FacingsGenerator.bat           # PowerShell wrapper
```

## Script Details

### 1. Main Space Whale Renderer
**File:** `blender_space_whale_main_120_facings.py`
**Ship ID:** `scSpaceWhale` (&scSpaceWhale; / 0xE1276000)
**Size:** 256x256 pixels per frame
**Features:**
- Large elongated whale-like bio-organic ship
- Complex multi-part geometry (head, body, tail, dorsal fins)
- Professional three-point lighting + ambient + glow lights
- Bio-luminescent material with subsurface scattering
- Procedural noise patterns for organic variation
- High-quality rendering (256 samples, denoising)

**Model Details:**
- Main body: 3.5x1.8x1.2 scale (elongated whale shape)
- Head section: Forward bulge with 1.8x1.3x1.0 scale
- Tail section: Tapered cone (4 units long)
- Dorsal fin: Vertical protrusion
- Subdivision level: 3 (smooth organic curves)

**Material:**
- Base color: Blue-grey (0.25, 0.45, 0.65)
- Emission: Blue glow (0.15, 0.5, 1.0) at 2.0 strength
- Metallic: 0.3, Roughness: 0.4
- Subsurface scattering: 0.15 weight for organic translucency

### 2. Space Whale Segment Renderer
**File:** `blender_space_whale_segment_120_facings.py`
**Ship ID:** `scSpaceWhaleSegment` (&scSpaceWhaleSegment; / 0xE1273800)
**Size:** 128x128 pixels per frame
**Features:**
- Cylindrical segment body with connecting joints
- Medium complexity (128 samples)
- Optimized for repetitive segment rendering
- Similar material to main ship but slightly varied

**Model Details:**
- Main segment: Cylindrical body (radius 0.8, length 2.5)
- Connecting joints: Spherical joints at both ends (0.6 radius)
- Organic deformation: Displacement modifier (0.15 strength)
- Subdivision level: 2

**Use Case:** 
Segments are attached to main ship to create articulated spine/tail system for organic whale-like movement.

### 3. Space Whale Drone Renderer
**File:** `blender_space_whale_drone_120_facings.py`
**Ship ID:** `scSpaceWhaleDrone` (&scSpaceWhaleDrone; / 0xE1273900)
**Size:** 64x64 pixels per frame
**Features:**
- Small organic pod with fins
- Fast rendering (96 samples)
- Strong glow for visibility at small size
- Minimal geometry for performance

**Model Details:**
- Main body: Ico sphere (0.5 radius) scaled 1.2x0.8x0.6
- Side fins: Two cone-shaped wings (perpendicular)
- Tail: Small tapered cone (0.5 length)
- Subdivision level: 2

**Material:**
- Strong emission (2.5 strength) for visibility
- Higher subsurface weight (0.2) for organic appearance
- Brighter blue glow (0.2, 0.6, 1.0)

### 4. Generic Template Renderer
**File:** `blender_space_whale_120_facings.py`
**Purpose:** Original comprehensive template script
**Features:**
- Model path loading (supports .blend, .obj, .fbx, .gltf/.glb)
- Texture directory integration
- Fallback procedural generation
- Configurable frame size
- Registry JSON integration

## Batch Rendering

### Quick Start
```batch
cd Tools\Transcendence
render_all_120_facings.bat
```

This will render all three ship types sequentially:
1. Main Space Whale (256x256)
2. Whale Segment (128x128)
3. Whale Drone (64x64)

### PowerShell Method
```powershell
.\SpaceWhale120FacingsGenerator.ps1 `
    -RegistryPath "space_whale_ship_example.json" `
    -OutputDir "Output/120Facings"
```

### Manual Blender Commands

**Main Whale:**
```bash
blender --background --python blender_space_whale_main_120_facings.py -- \
    --output-dir Output/120Facings \
    --ship-id scSpaceWhale \
    --frame-size 256
```

**Segment:**
```bash
blender --background --python blender_space_whale_segment_120_facings.py -- \
    --output-dir Output/120Facings \
    --ship-id scSpaceWhaleSegment \
    --frame-size 128
```

**Drone:**
```bash
blender --background --python blender_space_whale_drone_120_facings.py -- \
    --output-dir Output/120Facings \
    --ship-id scSpaceWhaleDrone \
    --frame-size 64
```

## Output Files

For each ship, two files are generated:

1. **Spritesheet PNG:** `{ship_id}_120facings.png`
   - 10 columns × 12 rows grid
   - Total dimensions: frame_size × 10 by frame_size × 12
   - RGBA format with transparency
   - Example: `scSpaceWhale_120facings.png` (2560×3072 pixels)

2. **Transparency Mask BMP:** `{ship_id}_120facingsMask.bmp`
   - Same dimensions as spritesheet
   - Binary mask: White = opaque, Black = transparent
   - RGB BMP format (Transcendence compatible)

## Technical Specifications

### 120 Facings Layout
- **Total facings:** 120 (10 columns × 12 rows)
- **Rotation step:** 3 degrees per facing (360° / 120)
- **Grid layout:** 
  ```
  Facing 0  = 0°   (ship facing right)
  Facing 1  = 3°
  Facing 2  = 6°
  ...
  Facing 119 = 357°
  ```

### Rendering Quality Settings

| Ship Type | Samples | Frame Size | Ortho Scale | Render Time (est.) |
|-----------|---------|------------|-------------|-------------------|
| Main Whale | 256 | 256×256 | 16.0 | ~30-60 min |
| Segment | 128 | 128×128 | 8.0 | ~15-30 min |
| Drone | 96 | 64×64 | 4.0 | ~10-20 min |

*Render times based on GPU rendering (CUDA/OPTIX). CPU rendering will be significantly slower.*

### Lighting Setup

All ships use consistent lighting:
- **Key Light:** Main directional (SUN) at 45° angle, warm white
- **Fill Light:** Secondary directional (SUN) opposite side, cool blue
- **Rim Light:** Edge definition (SUN) from back, blue tint
- **Ambient Light:** Soft overall illumination (POINT)
- **Glow Light:** Bio-luminescence accent (POINT), blue

### Material System

**Procedural Bio-Organic Shader:**
- Principled BSDF base (realistic PBR)
- Emission shader (bio-luminescence)
- Noise texture (organic variation)
- Color ramp (glow pattern control)
- Mix shader (blend based on noise)

**Key Parameters:**
- Base: Blue-grey with metallic sheen
- Emission: Blue glow (varies by ship size)
- Subsurface: Organic translucency
- Noise: Procedural variation patterns

## Requirements

### Software
- **Blender 3.0+** (tested with Blender 5.0)
- **Python 3.7+** (bundled with Blender)
- **Pillow (PIL):** For spritesheet compositing
  ```bash
  pip install Pillow
  ```

### Hardware Recommendations
- **GPU:** NVIDIA RTX series or equivalent (CUDA/OPTIX support)
- **RAM:** 8GB minimum, 16GB+ recommended
- **Storage:** 1GB free space per ship rendering

### Blender Setup
The scripts automatically detect and use:
1. GPU rendering if available (CUDA/OPTIX)
2. CPU rendering as fallback
3. Denoising for quality
4. Transparent film for alpha channel

## Integration with Transcendence

### XML Implementation

```xml
<ShipClass UNID="&scSpaceWhale;"
    class="&scSpaceWhale;"
    manufacturer="Bio-Organic"
    level="10"
    ...>
    
    <Image 
        imageID="&rsLargeShips1;" 
        imageX="0" 
        imageY="0" 
        imageWidth="256" 
        imageHeight="256" 
        imageFrameCount="120" 
        imageTicksPerFrame="0"
        rotationCount="120"
    />
    
</ShipClass>
```

**Key Image Attributes:**
- `imageFrameCount="120"` - Use all 120 facings
- `rotationCount="120"` - Smooth 120-degree rotation
- `imageWidth/Height` - Match rendered frame size
- Grid is automatically parsed as 10×12 layout

### Resource Registration

Add to resource file (.xrs or in XML):
```xml
<Image UNID="&rsSpaceWhaleShips;"
    bitmap="scSpaceWhale_120facings.png"
    bitmask="scSpaceWhale_120facingsMask.bmp"
    backColor="0x000000"
/>
```

## Customization

### Changing Ship Appearance

Edit the `create_*` methods in each script:
- Modify primitive scales for size/proportions
- Add/remove geometry parts
- Adjust subdivision levels (smoothness vs performance)
- Change displacement strength (organic deformation)

### Material Customization

Edit the `apply_*_material` methods:
- **Base Color:** Change `inputs['Base Color'].default_value`
- **Glow Color:** Change emission `inputs['Color']`
- **Glow Strength:** Adjust `inputs['Strength']`
- **Pattern Scale:** Modify noise `inputs['Scale']`

### Lighting Adjustments

Edit `setup_lighting` methods:
- **Brightness:** Change light `data.energy` values
- **Color Temperature:** Modify light `data.color` RGB
- **Position:** Update light `location` vectors
- **Angle:** Adjust `rotation_euler` values

## Troubleshooting

### "Blender not found"
- Update `BLENDER_PATH` in batch file
- Or add Blender to system PATH
- Check Blender installation directory

### "PIL/Pillow not available"
```bash
# Install Pillow for Python
pip install Pillow

# Or using Blender's Python:
D:\tools\Blender Foundation\Blender 5.0\5.0\python\bin\python.exe -m pip install Pillow
```

### Slow Rendering
- Enable GPU in Blender preferences
- Reduce samples (edit script `scene.cycles.samples`)
- Disable denoising (`scene.cycles.use_denoising = False`)
- Lower subdivision levels in geometry creation

### Memory Issues
- Render ships individually instead of batch
- Close other applications
- Reduce frame size (for testing)
- Lower subdivision levels

### Dark/Bright Output
- Adjust light energy values in `setup_lighting`
- Modify material emission strength
- Change camera exposure (add to setup_camera)

## Future Enhancements

Potential additions for evolved ship variants:
- Firefly (transport)
- Wolfen (gunship)
- Sapphire (yacht)
- Centurion (heavy gunship)
- Carrier (with constructs)
- Spectre (stealth)
- Hullbreaker (ramming)
- Viper (venom)
- Battery/Courser (broadside)
- Architect (construct deployer)
- Leviathan (disabled - multi-segment)

Each would follow the same pattern with size/style variations.

## Credits

Based on:
- **Transcendence:** Space Whale system
- **Nova Drift:** Ship design inspiration
- **Living Weapon System:** Evolved ships mod

## License

Compatible with Transcendence modding license.
