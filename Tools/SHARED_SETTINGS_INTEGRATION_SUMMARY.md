# Shared Settings Integration Summary

## Overview

All asset generation tools in the `D:\games\Steam\steamapps\common\Transcendence\Tools` directory now use a centralized shared settings file: `AssetGenerationSettings.ps1`

## Settings File Location

**Root Location**: `D:\games\Steam\steamapps\common\Transcendence\Tools\AssetGenerationSettings.ps1`

This file is accessible from all subdirectories using relative paths.

## Configuration

### ImageMagick
- **Path**: `E:\tools\ImageMagick`
- **Executable**: `E:\tools\ImageMagick\magick.exe`
- **Functions**: `Get-ImageMagickPath()`, `Test-ImageMagickAvailable()`

### Output Directories
- **Default**: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets`
- **Spellstone**: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets\items\spellstones`

### Ollama Configuration
- **URL**: `http://localhost:11434`
- **Default Model**: `codellama:7b-instruct`
- **Planning Model**: `llama3.2`
- **Visual Model**: `wizardlm-uncensored`

### Defaults
- **Variants**: `3`
- **Animation Frames**: `8`

## Integration Status

### Updated Scripts (155 total)
All scripts that use ImageMagick, OutputDir, Ollama, or default values have been updated to load the shared settings file.

**Categories Updated:**
- Root Tools scripts (AIImplementChanges, Apply-AIFixes, etc.)
- Common tools (ExportToSpritesheet, OrganizeTools, etc.)
- CDDA tools (CDDABeeSwarmGenerator, etc.)
- Elin tools (BatchAssetGenerator, CustomRaceClassCreator, etc.)
- Qud tools (BakeQudTile, ExportQudTiles, etc.)
- Soulash tools (SoulashAssetGenerator)
- **Starbound tools** (all 99+ generation scripts)
- Transcendence tools (TranscendenceAssetGenerator, etc.) - Note: Uses Transcendence art as reference source for ship generation

### Scripts Already Using Settings (52 total)
These scripts already had settings integration or don't need it.

## How Scripts Load Settings

### From Tools Root
```powershell
$settingsPath = Join-Path $PSScriptRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
```

### From Subdirectories (e.g., Starbound/)
```powershell
$settingsPath = Join-Path (Split-Path -Parent $PSScriptRoot) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
```

### Using Helper Function
```powershell
# Automatically finds settings file from any location
Load-AssetGenerationSettings
```

## Usage Examples

### Using ImageMagick
```powershell
# Load settings first
. $settingsPath

# Get ImageMagick path
$magickExe = Get-ImageMagickPath
if (Test-ImageMagickAvailable) {
    & $magickExe input.png -modulate 120,100,100 output.png
}
```

### Using Output Directories
```powershell
# Load settings first
. $settingsPath

# Use default output directory
$outputDir = $script:DefaultOutputDir

# Or use spellstone-specific directory
$spellstoneDir = $script:SpellstoneOutputDir
```

### Using Ollama Settings
```powershell
# Load settings first
. $settingsPath

# Use configured Ollama URL and models
$ollamaUrl = $script:OllamaUrl
$model = $script:OllamaModel
```

### Using Default Values
```powershell
# Load settings first
. $settingsPath

# Use default variants
$variants = $script:DefaultVariants  # 3

# Use default animation frames
$frames = $script:DefaultAnimationFrames  # 8
```

## Updating Settings

To change any configuration:

1. Edit `D:\games\Steam\steamapps\common\Transcendence\Tools\AssetGenerationSettings.ps1`
2. All scripts will automatically use the updated settings on their next run
3. No need to update individual scripts

## Testing

Run the test script to verify settings:
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools\Starbound"
.\Test-AssetGenerationSettings.ps1
```

Or from Tools root:
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Tools"
$settingsPath = ".\AssetGenerationSettings.ps1"
. $settingsPath
Test-ImageMagickAvailable
Get-ImageMagickPath
```

## Benefits

1. **Centralized Configuration**: All paths and settings in one place
2. **Easy Updates**: Change once, applies everywhere
3. **Consistency**: All tools use the same ImageMagick location and output directories
4. **Maintainability**: No need to update individual scripts when paths change
5. **Flexibility**: Scripts can override settings if needed via parameters

## Migration Notes

- Scripts that were already using hardcoded paths will now use shared settings
- Scripts can still accept `-OutputDir` parameters to override defaults
- ImageMagick detection automatically falls back to PATH if not found at `E:\tools\ImageMagick`
- All settings are optional - scripts will work even if settings file is missing (with fallbacks)
