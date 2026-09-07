# Spritesheet Tool Recommendations for OpenStarbound Asset Pipeline

## Executive Summary

Based on your PowerShell-based asset generation pipeline, **Aseprite CLI** is the top recommendation for automated spritesheet generation. It offers:
- Direct `.frames` file output compatible with Starbound
- Robust CLI that integrates seamlessly with PowerShell
- Power-of-two packing and precise frame slicing
- Cross-platform support (Windows, macOS, Linux)
- Open-source (with paid binaries, but CLI works with source builds)

**Alternative:** If Aseprite is not available, **Free Texture Packer** (CLI) or **Python-based tools** (SpriteSheet Maker, kipuki/sprite-sheet-tools) are excellent alternatives that can be called from PowerShell.

---

## Recommended Tool: Aseprite CLI

### Why Aseprite for Your Pipeline

1. **Native `.frames` Support**: Aseprite can export directly to Starbound-compatible `.frames` format
2. **PowerShell Integration**: CLI can be called directly from PowerShell scripts
3. **Precise Control**: Padding, trimming, power-of-two constraints, and pivot points
4. **Batch Processing**: Supports batch operations for multiple assets
5. **Proven in Modding**: Widely used in Starbound and OpenStarbound modding communities

### Installation

**Option 1: Paid Binary (Recommended for Production)**
- Download from: https://www.aseprite.org/
- Install normally, CLI is included in installation

**Option 2: Build from Source (Free)**
- Source code: https://github.com/aseprite/aseprite
- Requires Skia library and build tools
- More complex but free for commercial use

### CLI Usage for OpenStarbound

```powershell
# Pack individual frames into a spritesheet with .frames metadata
aseprite -b `
    --sheet "output.png" `
    --data "output.frames" `
    --format json-array `
    --sheet-width 512 `
    --sheet-height 512 `
    --size-constraints POT `
    --shape-padding 2 `
    --border-padding 2 `
    --trim `
    --extrude 1 `
    frame1.png frame2.png frame3.png ...
```

**Key Flags:**
- `--sheet`: Output spritesheet path
- `--data`: Output `.frames` metadata file
- `--format json-array`: Starbound-compatible JSON format
- `--size-constraints POT`: Power-of-two atlas size
- `--shape-padding`: Padding between frames (prevents bleeding)
- `--border-padding`: Padding around entire atlas
- `--trim`: Remove transparent edges
- `--extrude`: Extend edge pixels (prevents filtering artifacts)

---

## Alternative Tools

### 1. Free Texture Packer (CLI)

**Pros:**
- Completely free and open-source
- Cross-platform
- CLI and build tool plugins (Gulp, Grunt, Webpack)
- Supports power-of-two packing

**Cons:**
- Requires Node.js installation
- `.frames` format may need custom conversion

**Installation:**
```powershell
npm install -g free-tex-packer-cli
```

**Usage:**
```powershell
free-tex-packer-cli `
    --input "./frames/*.png" `
    --output "./atlas" `
    --format json `
    --pot `
    --padding 2 `
    --trim `
    --multipack
```

### 2. Python-Based Tools

**SpriteSheet Maker** or **kipuki/sprite-sheet-tools** can be called from PowerShell:

```powershell
python sprite_sheet_generator.py `
    --input "./frames/*.png" `
    --output "./sheet.png" `
    --grid_size (4,4) `
    --sprite_padding (2,2) `
    --metadata "./sheet.frames"
```

**Pros:**
- Easy to customize and extend
- Can generate Starbound `.frames` format directly
- No external dependencies beyond Python

**Cons:**
- Requires Python installation
- May need custom `.frames` format conversion

---

## Integration with Your Current Pipeline

### Current State

Your `StarboundAssetGenerator.ps1` currently:
1. Generates individual frames using System.Drawing
2. Manually packs frames into horizontal strips
3. Manually creates `.frames` JSON files

### Recommended Enhancement

Replace manual spritesheet packing with Aseprite CLI (or alternative) for:
- **Better packing efficiency** (MaxRects algorithm vs. simple horizontal strip)
- **Automatic power-of-two sizing**
- **Consistent padding and trimming**
- **Reduced code complexity**

### Integration Points

1. **After Frame Generation**: Instead of manually drawing frames onto a spritesheet, save individual frames as PNGs
2. **Call Aseprite CLI**: Use PowerShell to invoke Aseprite CLI to pack frames
3. **Use Generated `.frames` File**: Aseprite outputs the `.frames` file directly

---

## Implementation Plan

### Phase 1: Add Aseprite CLI Support (Recommended)

1. **Check for Aseprite Installation**
   ```powershell
   function Test-AsepriteAvailable {
       $asepritePath = Get-Command aseprite -ErrorAction SilentlyContinue
       return $null -ne $asepritePath
   }
   ```

2. **Create PowerShell Wrapper Function**
   - See `StarboundSpritesheetPacker.ps1` (created below)
   - Handles frame collection, Aseprite invocation, and `.frames` file validation

3. **Update `Generate-AnimationSprite`**
   - Optionally use Aseprite CLI instead of manual packing
   - Fall back to current method if Aseprite unavailable

### Phase 2: Batch Processing Enhancement

1. **Collect All Frames**: Generate all frames first, save as individual PNGs
2. **Batch Pack**: Use Aseprite CLI to pack multiple animations in one pass
3. **Validate Output**: Check `.frames` files match spritesheet dimensions

### Phase 3: Advanced Features

1. **Multipack Support**: Split large frame sets across multiple atlases
2. **Pivot Point Support**: Extract pivot points from frame metadata
3. **Animation Duration**: Include frame durations in `.frames` files

---

## Comparison: Manual vs. Tool-Based Packing

| Feature | Current (Manual) | Aseprite CLI | Free Texture Packer |
|---------|------------------|--------------|---------------------|
| Packing Algorithm | Horizontal strip | MaxRects (optimal) | Bin-packing |
| Power-of-Two | Manual calculation | Automatic | Automatic |
| Padding Control | Manual | Automatic | Automatic |
| Trimming | Manual | Automatic | Automatic |
| `.frames` Output | Manual JSON | Direct export | Custom conversion needed |
| Code Complexity | High | Low (CLI call) | Low (CLI call) |
| Performance | Good | Excellent | Good |

---

## Next Steps

1. **Install Aseprite** (or alternative tool)
2. **Test CLI Integration**: Run sample commands to verify output format
3. **Create PowerShell Wrapper**: See `StarboundSpritesheetPacker.ps1` below
4. **Integrate into Pipeline**: Update `StarboundAssetGenerator.ps1` to use tool-based packing
5. **Validate Output**: Test generated spritesheets in OpenStarbound

---

## References

- **Aseprite Documentation**: https://www.aseprite.org/docs/cli/
- **Free Texture Packer**: https://github.com/odrick/free-tex-packer
- **Starbound Asset Format**: See `SPRITESHEET_GENERATION_IMPROVEMENTS.md`
