# AI Image Post-Processing Guide

## Overview

**All AI-generated images should be post-processed with ImageMagick** to ensure:
- Consistent format and quality
- Game compatibility
- Optimal file sizes
- Proper color space and bit depth
- Standardized dimensions

## When to Use ImageMagick Post-Processing

### ✅ Always Process:
- **AI-generated images** (Ollama, DALL-E, Stable Diffusion, etc.)
- **Procedurally generated images** (C++ backend, Python generators)
- **Template-based variants** (color modifications, animations)
- **Exported images** from any source that need game compatibility

### ⚠️ Exceptions (Still Consider Processing):
- **3D model exports** (ships, mechs) - May still benefit from format optimization
- **Pre-existing game assets** - Only if reformatting for compatibility
- **Already processed images** - Skip if already in correct format

## Standard Workflow

### 1. Generate Image (AI/Procedural)
```powershell
# AI generates image → saves to output.png
```

### 2. Post-Process with ImageMagick
```powershell
# Import post-processor module
Import-Module ".\Shared\ImageMagickPostProcessor.psm1"

# Process the generated image
Process-AIGeneratedImage `
    -InputPath "output.png" `
    -OutputPath "output_processed.png" `
    -GameType "Starbound" `
    -Quality "high"
```

### 3. Use Processed Image
```powershell
# Use the processed image in game
```

## Integration Points

### In PowerShell Scripts

After any image generation, add:

```powershell
# Load post-processor module
$postProcessorPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\ImageMagickPostProcessor.psm1"
if (Test-Path $postProcessorPath) {
    Import-Module $postProcessorPath -Force
    
    # Process all generated images
    $generatedImages = Get-ChildItem -Path $OutputDir -Filter "*.png" -Recurse
    foreach ($image in $generatedImages) {
        Process-AIGeneratedImage `
            -InputPath $image.FullName `
            -GameType "Starbound" `
            -Quality "high"
    }
}
```

### In C++ Backend

After image generation, call PowerShell post-processor:

```cpp
// After generating image
std::string imagePath = "generated.png";
std::string command = "powershell -Command \"Import-Module 'Tools\\Shared\\ImageMagickPostProcessor.psm1'; Process-AIGeneratedImage -InputPath '" + imagePath + "' -GameType 'Starbound'\"";
system(command.c_str());
```

### In Python Scripts

```python
import subprocess
import os

def post_process_image(image_path, game_type="Starbound"):
    """Post-process AI-generated image with ImageMagick"""
    tools_root = r"D:\games\Steam\steamapps\common\Transcendence\Tools"
    module_path = os.path.join(tools_root, "Shared", "ImageMagickPostProcessor.psm1")
    
    cmd = [
        "powershell",
        "-Command",
        f"Import-Module '{module_path}'; Process-AIGeneratedImage -InputPath '{image_path}' -GameType '{game_type}' -Quality 'high'"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

# After generating image
post_process_image("ai_output.png", "Starbound")
```

## Game-Specific Requirements

### Starbound
- **Format**: PNG, 8-bit depth
- **Max Size**: 2048x2048
- **Colorspace**: sRGB
- **Compression**: ZIP (level 9)

### Qud (Caves of Qud)
- **Format**: PNG, 8-bit depth
- **Max Size**: 512x512
- **Colorspace**: sRGB
- **Compression**: ZIP

### Terraria
- **Format**: PNG, 8-bit depth
- **Max Size**: 1024x1024
- **Colorspace**: sRGB

### CDDA
- **Format**: PNG, 8-bit depth
- **Max Size**: 32x32
- **Colorspace**: sRGB

## Quality Levels

- **low**: 60% quality, fast compression (for testing)
- **medium**: 75% quality, medium compression (for development)
- **high**: 90% quality, ZIP compression (for production) ⭐ **Recommended**
- **ultra**: 100% quality, ZIP compression (for final assets)

## Batch Processing

Process multiple images at once:

```powershell
$images = Get-ChildItem -Path ".\generated\" -Filter "*.png" -Recurse
$imagePaths = $images | ForEach-Object { $_.FullName }

Process-AIGeneratedImages `
    -InputPaths $imagePaths `
    -GameType "Starbound" `
    -Quality "high"
```

## Benefits

1. **Consistency**: All images follow same format standards
2. **Compatibility**: Ensures game engine compatibility
3. **Quality**: Optimized compression and color space
4. **Size**: Reduced file sizes without quality loss
5. **Metadata**: Stripped for privacy and smaller files

## Examples

### Example 1: Post-Process After AI Generation
```powershell
# Generate with Ollama
& ".\StarboundOllamaAssetGenerator.ps1" -AssetType "Icon" -AssetName "magic_orb"

# Post-process generated images
Import-Module ".\Shared\ImageMagickPostProcessor.psm1"
$outputDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets"
Get-ChildItem -Path $outputDir -Filter "*magic_orb*.png" -Recurse | ForEach-Object {
    Process-AIGeneratedImage -InputPath $_.FullName -GameType "Starbound"
}
```

### Example 2: Template-Based Variants
```powershell
# Generate variants from template
& ".\GenerateSpellstoneVariants.ps1" -BaseImagePath "template.png" -Element "fire"

# Post-process all variants
Import-Module ".\Shared\ImageMagickPostProcessor.psm1"
Process-AIGeneratedImages `
    -InputPaths (Get-ChildItem -Path ".\variants\" -Filter "*.png").FullName `
    -GameType "Starbound"
```

### Example 3: C++ Backend Integration
```powershell
# C++ generates image → PowerShell post-processes
$cppOutput = ".\cpp_generated\sprite.png"
if (Test-Path $cppOutput) {
    Import-Module ".\Shared\ImageMagickPostProcessor.psm1"
    Process-AIGeneratedImage -InputPath $cppOutput -GameType "Starbound"
}
```

## Best Practices

1. **Always process AI-generated images** - Don't skip this step
2. **Use appropriate game type** - Ensures correct format requirements
3. **Use "high" quality for production** - Balance between quality and size
4. **Process immediately after generation** - Don't accumulate unprocessed images
5. **Batch process when possible** - More efficient for multiple images
6. **Verify processed images** - Check file size and format after processing

## Troubleshooting

### ImageMagick Not Found
```powershell
# Check if ImageMagick is available
Get-ImageMagickPath
Test-ImageMagickAvailable

# Install if needed
& ".\Starbound\Install-ImageMagick.ps1"
```

### Processing Fails
- Check ImageMagick installation: `E:\tools\ImageMagick\magick.exe`
- Verify input file exists and is readable
- Check output directory permissions
- Review ImageMagick error messages

### Quality Issues
- Use "ultra" quality for final assets
- Check original image quality (garbage in = garbage out)
- Verify color space conversion worked correctly

## Integration Checklist

- [ ] Import `ImageMagickPostProcessor.psm1` module
- [ ] Call `Process-AIGeneratedImage` after each image generation
- [ ] Use correct `GameType` parameter
- [ ] Set appropriate `Quality` level
- [ ] Verify processed images are correct format
- [ ] Update generation scripts to include post-processing
- [ ] Document exceptions (if any)

## Summary

**Rule**: All AI-generated images → ImageMagick post-processing → Game-ready assets

**Exceptions**: Only skip if image is already in perfect format and doesn't need optimization.

**Result**: Consistent, high-quality, game-compatible assets across all tools.
