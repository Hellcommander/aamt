# Shared Asset Generation Settings
**AI-Assisted Modding Tools (AAMT)**

All asset generation tools use a centralized settings file: `AssetGenerationSettings.ps1`

## Configuration File

**Location**: `AssetGenerationSettings.ps1`

This file contains all shared configuration for:
- ImageMagick installation path
- Output directories
- Ollama API settings
- Default values (variants, animation frames, etc.)

## Settings

### ImageMagick Configuration
- **Path**: `E:\tools\ImageMagick`
- **Executable**: `E:\tools\ImageMagick\magick.exe`

### Output Directories
- **Default**: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets`
- **Spellstone**: `F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\assets\items\spellstones`

### Ollama Configuration
- **URL**: `http://localhost:11434`
- **Default Model**: `codellama:7b-instruct`
- **Planning Model**: `llama3.2`
- **Visual Model**: `wizardlm-uncensored`

### Default Values
- **Variants**: `3` (number of variants per asset type)
- **Animation Frames**: `8` (frames per animation)

## Usage

All scripts automatically load this settings file. To use settings in a custom script:

```powershell
# Load shared settings
$settingsPath = Join-Path $PSScriptRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Use ImageMagick
$magickExe = Get-ImageMagickPath
if (Test-ImageMagickAvailable) {
    & $magickExe input.png output.png
}

# Use output directories
$outputDir = $script:SpellstoneOutputDir
```

## Testing

Run the test script to verify all settings:

```powershell
.\Test-AssetGenerationSettings.ps1
```

## Updating Settings

Simply edit `AssetGenerationSettings.ps1` to change any configuration. All scripts will automatically use the updated settings on their next run.

## Scripts Using Shared Settings

- `GenerateSpellstoneVariants.ps1` - Template-based variant generation
- `GenerateSpellstoneAssets.ps1` - Ollama-based asset generation
- `Install-ImageMagick.ps1` - Installation verification
