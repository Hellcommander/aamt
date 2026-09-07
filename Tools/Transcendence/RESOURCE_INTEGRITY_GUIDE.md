# Resource Integrity Checker - User Guide

## Overview

The Resource Integrity Checker validates resource files (images, sounds) before runtime. It catches issues that would only appear when the game loads, saving you debugging time.

## What It Does

### 1. Image Validation 🖼️

**Checks**:
- Image files exist (bitmap/bitmask)
- Image dimensions match declared sizes
- Spritesheet frame counts are correct
- Spritesheet layouts are valid (columns/rows)
- Image formats are valid

**Validates**:
- `imageWidth` / `imageHeight` match actual image
- `imageFrameCount` matches spritesheet layout
- `rotationColumns` divides evenly into image width
- Bitmap and bitmask files exist

### 2. Sound Validation 🔊

**Checks**:
- Sound files exist
- File formats are supported (.wav, .mp3, .ogg)
- File paths are correct

**Validates**:
- `fileName` or `filename` attributes
- File existence
- Format compatibility

### 3. Resource Entry Validation 📁

**Checks**:
- /Resources entries exist
- Referenced files are found
- Paths are correct

## How to Use

### Run Resource Integrity Check

1. Go to **Project Health** tab
2. Enter mod folder path
3. Click **Resource Integrity** button
4. Review issues in report

### Understanding Results

**Error Severity**:
- **❌ Error**: Critical issues that will cause runtime failures
  - Missing image files
  - Image size mismatches
  - Missing sound files
  
- **⚠ Warning**: Potential issues that may cause problems
  - Missing bitmask files
  - Invalid image formats
  - Unsupported sound formats

**Issue Codes**:
- `MISSING_IMAGE`: Image file not found
- `IMAGE_SIZE_MISMATCH`: Declared size doesn't match actual
- `SPRITESHEET_FRAME_MISMATCH`: Frame count/layout error
- `INVALID_IMAGE_FORMAT`: Image can't be read
- `MISSING_SOUND`: Sound file not found
- `INVALID_SOUND_FORMAT`: Unsupported format
- `MISSING_RESOURCE_ENTRY`: Resource file not found

## Example Issues

### Image Size Mismatch

```
❌ MyMod.xml:45
   Image width mismatch: declared 128, actual 256
   Resource: Resources/ship.jpg
```

**Fix**: Update `imageWidth` attribute or resize image

### Spritesheet Frame Error

```
❌ MyMod.xml:67
   Spritesheet dimensions don't divide evenly: 512 x 256 with 8 columns
   Resource: Resources/ship_rotations.jpg
```

**Fix**: Adjust image size or column count

### Missing Sound File

```
❌ MyMod.xml:89
   Sound file not found: Resources/explosion.wav
   Resource: Resources/explosion.wav
```

**Fix**: Add missing sound file or correct path

## Use Cases

### Before Release
- Validate all resources are present
- Check image dimensions are correct
- Verify spritesheets are properly configured

### Debugging
- Find missing resource files
- Identify size mismatches
- Check spritesheet calculations

### Quality Assurance
- Ensure all resources are valid
- Verify file formats are supported
- Check resource paths are correct

## Technical Details

### Image Reading
- Uses .NET `System.Drawing.Image`
- Reads actual image dimensions
- Validates file can be opened

### Path Resolution
1. Tries relative to file directory
2. Tries relative to mod root
3. Reports if not found

### Spritesheet Validation
- Calculates expected frame layout
- Validates dimensions divide evenly
- Checks frame count matches layout

## Tips

- **Image Sizes**: Always match declared dimensions
- **Spritesheets**: Ensure dimensions divide evenly by columns
- **Sound Formats**: Use .wav for best compatibility
- **Paths**: Use relative paths from mod root
- **Bitmasks**: Optional but recommended for transparency

---

The Resource Integrity Checker catches runtime errors before they happen!

