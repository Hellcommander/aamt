# Texture Format Guide

This guide explains the texture formats, compression options, and quality settings available in the Asset Generator.

## Supported Formats

### Output Formats

| Format | Extension | Use Case | Quality | File Size |
|--------|-----------|----------|---------|-----------|
| PNG | `.png` | General purpose, transparency | Lossless | Large |
| JPEG | `.jpg` | Photos, no transparency needed | Lossy | Small |
| TGA | `.tga` | High quality, Unity compatible | Lossless | Large |
| EXR | `.exr` | HDR textures, professional | Lossless | Very Large |

### Unity Texture Formats

The generator creates Unity `.meta` files that specify these internal formats:

| Format | Platform | Quality | Compression | Use Case |
|--------|----------|---------|-------------|----------|
| RGBA32 | All | Highest | None | UI, Icons, Critical textures |
| BC7 | DX11+ | High | 4:1 | Standard textures (recommended) |
| DXT5 | DX9+ | Medium | 4:1 | Older hardware, compatibility |
| ETC_RGB4 | Android | Medium | 4:1 | Mobile/Android |
| ASTC | Mobile | High | Variable | Modern mobile devices |

## Quality Presets

### Low Quality
- **Texture Size**: 256×256
- **Format**: ETC_RGB4 (mobile) or DXT5 (desktop)
- **Compression**: Maximum
- **Mip Maps**: Enabled
- **Use Case**: Icons, UI elements, distant objects
- **File Size**: ~64-128 KB per texture

### Medium Quality
- **Texture Size**: 512×512
- **Format**: DXT5 (desktop) or ETC_RGB4 (mobile)
- **Compression**: Balanced
- **Mip Maps**: Enabled
- **Use Case**: Standard game textures, most assets
- **File Size**: ~256-512 KB per texture

### High Quality
- **Texture Size**: 1024×1024
- **Format**: BC7 (desktop) or ASTC (mobile)
- **Compression**: Moderate
- **Mip Maps**: Enabled
- **Use Case**: Hero assets, important textures
- **File Size**: ~1-2 MB per texture

### Ultra Quality
- **Texture Size**: 2048×2048
- **Format**: RGBA32 (uncompressed) or BC7
- **Compression**: None/Minimal
- **Mip Maps**: Enabled
- **Use Case**: High-resolution textures, print quality
- **File Size**: ~8-16 MB per texture (uncompressed)

## Format Selection Guide

### By Asset Type

#### Icons (32×32 to 64×64)
- **Recommended**: Low-Medium quality
- **Format**: PNG with compression
- **Unity Format**: RGBA32 or DXT5
- **Why**: Small size, sharp edges, transparency support

#### Sprites (64×64 to 256×256)
- **Recommended**: Medium quality
- **Format**: PNG
- **Unity Format**: DXT5 or BC7
- **Why**: Balance between quality and performance

#### Textures (256×256 to 2048×2048)
- **Recommended**: High quality
- **Format**: PNG or TGA
- **Unity Format**: BC7 (desktop) or ASTC (mobile)
- **Why**: Detail preservation, tiling support

#### UI Elements
- **Recommended**: Low-Medium quality
- **Format**: PNG
- **Unity Format**: RGBA32
- **Why**: Sharp text, transparency, no compression artifacts

### By Platform

#### Desktop (Windows/Mac/Linux)
- **Best Format**: BC7 (DX11+) or DXT5 (DX9)
- **Quality**: High
- **Size**: 1024×1024 recommended

#### Mobile (Android/iOS)
- **Best Format**: ASTC (modern) or ETC2 (older)
- **Quality**: Medium-High
- **Size**: 512×512 to 1024×1024

#### WebGL
- **Best Format**: DXT5 or ASTC
- **Quality**: Medium
- **Size**: 512×512 (file size critical)

## Compression Options

### PNG Compression Levels

| Level | Quality | File Size | Generation Time |
|-------|---------|-----------|-----------------|
| 0 (None) | Highest | Largest | Fastest |
| 3 (Low) | High | Large | Fast |
| 6 (Medium) | Good | Medium | Medium |
| 9 (Maximum) | Good | Smallest | Slowest |

**Default**: Level 6 (balanced)

### JPEG Quality

| Quality | Visual Quality | File Size | Use Case |
|---------|----------------|-----------|----------|
| 90-100 | Excellent | Large | High quality exports |
| 80-89 | Very Good | Medium | Standard use |
| 70-79 | Good | Small | Web, thumbnails |
| 60-69 | Acceptable | Very Small | Low priority assets |
| <60 | Poor | Tiny | Not recommended |

**Default**: 85 (very good quality)

### Unity Compression

The generator configures Unity compression via `.meta` files:

- **None**: Uncompressed (RGBA32) - Best quality, largest size
- **Low**: Minimal compression - Good quality, large size
- **Normal**: Balanced - Good quality, medium size
- **High**: Maximum compression - Acceptable quality, small size

## Power-of-2 Dimensions

Unity works best with power-of-2 texture dimensions. The generator automatically ensures this:

### Standard Sizes

| Size | Pixels | Use Case |
|------|--------|----------|
| 32×32 | 1,024 | Icons, small sprites |
| 64×64 | 4,096 | Small sprites, UI elements |
| 128×128 | 16,384 | Medium sprites |
| 256×256 | 65,536 | Standard textures |
| 512×512 | 262,144 | High-quality textures |
| 1024×1024 | 1,048,576 | Very high quality |
| 2048×2048 | 4,194,304 | Maximum quality |

### Non-Power-of-2

While supported, non-power-of-2 textures may:
- Use more memory
- Have slower performance
- Not tile properly
- Cause compression issues

**Recommendation**: Always use power-of-2 dimensions.

## Special Texture Types

### Normal Maps
- **Format**: PNG or TGA
- **Unity Format**: BC5 or DXT5nm
- **Color Space**: Linear (not sRGB)
- **Compression**: Specialized normal map compression

### Emission Maps
- **Format**: PNG
- **Unity Format**: RGBA32 or BC7
- **Color Space**: sRGB
- **Use**: Glow effects, emissive materials

### Alpha Masks
- **Format**: PNG (with alpha channel)
- **Unity Format**: DXT5 (supports alpha)
- **Use**: Transparency, cutouts

## Configuration

### Custom Format Settings

Edit `AssetGeneration.config.json`:

```json
{
  "textureFormatsByQuality": {
    "Low": "ETC_RGB4",
    "Medium": "DXT5",
    "High": "BC7",
    "Ultra": "RGBA32"
  },
  "textureSizesByQuality": {
    "Low": 256,
    "Medium": 512,
    "High": 1024,
    "Ultra": 2048
  },
  "defaultOutputFormat": "PNG"
}
```

### Per-Asset Type Formats

```json
{
  "outputFormatsByType": {
    "Texture": "PNG",
    "Sprite": "PNG",
    "Icon": "PNG",
    "UI": "PNG"
  }
}
```

## File Size Guidelines

### Target Sizes by Quality

| Quality | Target Size (per texture) | Max Total (100 textures) |
|---------|---------------------------|--------------------------|
| Low | 64-128 KB | 6-12 MB |
| Medium | 256-512 KB | 25-50 MB |
| High | 1-2 MB | 100-200 MB |
| Ultra | 8-16 MB | 800 MB - 1.6 GB |

### Optimization Tips

1. **Use Appropriate Quality**: Don't use Ultra for icons
2. **Enable Compression**: Always compress except for critical assets
3. **Use Atlases**: Combine multiple textures into spritesheets
4. **Mip Maps**: Enable for textures viewed at distance
5. **Format Selection**: Choose format based on platform and use case

## Best Practices

### For Icons
- Size: 32×32 to 64×64
- Format: PNG, RGBA32 in Unity
- Quality: Low-Medium
- Compression: Minimal (sharp edges)

### For Textures
- Size: 512×512 to 1024×1024
- Format: PNG or TGA, BC7 in Unity
- Quality: Medium-High
- Compression: Moderate

### For Sprites
- Size: 64×64 to 256×256
- Format: PNG, DXT5 or BC7 in Unity
- Quality: Medium
- Compression: Balanced

### For UI
- Size: 32×32 to 128×128
- Format: PNG, RGBA32 in Unity
- Quality: Low-Medium
- Compression: Minimal

## Troubleshooting Format Issues

### Artifacts in Compressed Textures

**Problem**: Blocky artifacts, color banding

**Solutions**:
- Use higher quality setting
- Switch to BC7 format (better than DXT5)
- Use RGBA32 for critical textures
- Increase texture size

### Large File Sizes

**Problem**: Textures taking too much space

**Solutions**:
- Use lower quality preset
- Enable compression
- Use appropriate format (BC7 vs RGBA32)
- Reduce texture dimensions
- Use texture atlases

### Import Errors in Unity

**Problem**: Unity can't import texture

**Solutions**:
- Verify file is valid PNG/JPEG/TGA
- Check file isn't corrupted
- Ensure dimensions are power-of-2
- Check file permissions
- Verify `.meta` file exists

## See Also

- `UNITY_INTEGRATION_GUIDE.md` - How to use textures in Unity
- `TROUBLESHOOTING.md` - Common issues and solutions
- `AssetGeneration.config.json` - Configuration reference
- `QUICK_START.md` - Basic usage
