# Developer Documentation

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Function Documentation](#function-documentation)
3. [Extension Guide](#extension-guide)

---

## Architecture Overview

### System Design

The Asset Generator is a modular system that combines PowerShell orchestration with Python-based image generation, integrated with Ollama AI for intelligent asset specification. The architecture follows a clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    PowerShell Layer                         │
│  (OllamaAssetGenerator.ps1, ElinTextureGenerator.ps1)      │
│  - Parameter handling                                       │
│  - Workflow orchestration                                   │
│  - Tool detection and integration                           │
│  - Error handling and user feedback                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Shared Modules                            │
│  (../Shared/OllamaIntegration.psm1, etc.)                   │
│  - Ollama API integration                                   │
│  - Tool detection                                           │
│  - Unified toolset integration                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Layer                              │
│  (generate_asset_image.py, generate_spritesheet.py)        │
│  - Image generation algorithms                              │
│  - Pattern generation                                       │
│  - Spritesheet packing                                      │
│  - Preview generation                                       │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. PowerShell Scripts (Orchestration Layer)

**Main Scripts:**
- `OllamaAssetGenerator.ps1` - Primary asset generator with AI integration
- `ElinTextureGenerator.ps1` - Specialized texture generator for Elin mods
- `ElinSpellAssetGenerator.ps1` - Spell-specific asset generation
- `BatchAssetGenerator.ps1` - Batch processing capabilities

**Responsibilities:**
- Parameter validation and configuration
- Tool detection (Python, Ollama, ImageMagick)
- Workflow orchestration
- Error handling and user feedback
- Path normalization and file management
- Integration with Shared modules

#### 2. Python Scripts (Generation Layer)

**Core Scripts:**
- `generate_asset_image.py` - Procedural image generation from specifications
- `generate_spritesheet.py` - Spritesheet creation with bin-packing optimization
- `generate_previews.py` - Preview thumbnail and catalog generation

**Responsibilities:**
- Image manipulation using PIL/Pillow
- Pattern generation (gradients, noise, organic, geometric)
- Color interpolation and palette management
- Spritesheet layout optimization
- Asset validation and quality checks

#### 3. Shared Modules (Integration Layer)

**Modules:**
- `OllamaIntegration.psm1` - Unified Ollama API wrapper
- `ToolDetection.psm1` - Tool availability detection
- `ToolsetIntegration.psm1` - Cross-toolset integration

**Features:**
- Automatic model tier routing (visual, dark_tone, escalation)
- Dark tone content detection
- Model escalation on refusal
- Consistent error handling

#### 4. Configuration System

**Files:**
- `AssetGeneration.config.json` - Quality presets and format settings
- `OllamaAssetGenerator.config.json` - Script-specific configuration

**Configuration Structure:**
```json
{
  "qualityPresets": [
    {
      "name": "Medium",
      "textureSize": 512,
      "textureFormat": "DXT5",
      "generateMipmaps": true,
      "usePBR": true
    }
  ],
  "textureFormatsByQuality": {
    "Low": "ETC_RGB4",
    "Medium": "DXT5",
    "High": "BC7",
    "Ultra": "RGBA32"
  }
}
```

### Data Flow

1. **User Input** → PowerShell script receives parameters
2. **Tool Detection** → Shared modules check for Python, Ollama, etc.
3. **AI Specification** (if enabled) → Ollama generates JSON specification
4. **Specification Processing** → PowerShell creates temp JSON file
5. **Image Generation** → Python script reads spec and generates image
6. **Post-Processing** → Optional spritesheet generation, previews, Unity integration
7. **Output** → Assets saved to mod directory structure

### Key Design Patterns

#### 1. Fallback Pattern
- If Ollama is unavailable, falls back to default specifications
- If Python is unavailable, creates placeholder assets
- Graceful degradation at each layer

#### 2. Specification-Driven Generation
- All assets generated from JSON specifications
- Enables consistent styling and easy customization
- Supports both AI-generated and hardcoded specs

#### 3. Modular Tool Integration
- Shared modules provide consistent interfaces
- Easy to swap implementations (e.g., different AI providers)
- Tool detection ensures features degrade gracefully

#### 4. Path Normalization
- Handles paths with spaces and special characters
- Resolves relative to absolute paths
- Proper quoting for command-line arguments

---

## Function Documentation

### PowerShell Functions

#### Test-OllamaForAssets

**Purpose:** Tests Ollama connection and prepares for asset generation.

**Syntax:**
```powershell
Test-OllamaForAssets
```

**Returns:** `$true` if Ollama is available and ready, `$false` otherwise

**Behavior:**
- Checks if Ollama is enabled via `$script:UseOllama`
- Uses `Test-OllamaConnection` from Shared module if available
- Falls back to direct HTTP check if module not loaded
- Provides user feedback on connection status

**Example:**
```powershell
if (Test-OllamaForAssets) {
    Write-Host "Ollama ready for AI-powered generation"
}
```

---

#### Get-AIAssetSpecification

**Purpose:** Uses Ollama to generate detailed asset specifications in JSON format.

**Syntax:**
```powershell
Get-AIAssetSpecification -SystemName <string> -AssetType <string> [-Description <string>]
```

**Parameters:**
- `SystemName` - Magic system name (e.g., "DragonMagic", "BloodMagic")
- `AssetType` - Type of asset ("icons", "sprites", "textures", "spell_assets")
- `Description` - Optional additional description for the asset

**Returns:** PSCustomObject with specification properties:
- `colors` - Array of hex color strings
- `pattern` - Pattern type (gradient, noise, organic, geometric)
- `style` - Visual style (painterly, pixel-art, realistic, stylized)
- `effects` - Array of visual effects (glow, shadow, rim-light)
- `theme` - Theme elements specific to the system
- `size` - Recommended size in pixels
- `details` - Array of detail elements
- `tileable` - Boolean (for textures)

**Behavior:**
- Constructs detailed prompt for Ollama
- Uses Shared `Invoke-OllamaRequest` with `TaskType="visual"`
- Automatically routes to appropriate model tier
- Falls back to `Get-DefaultAssetSpec` if Ollama fails
- Parses JSON from AI response

**Example:**
```powershell
$spec = Get-AIAssetSpecification -SystemName "DragonMagic" -AssetType "textures"
# Returns: @{colors=@("#ff4444","#ff8844"); pattern="gradient"; ...}
```

---

#### Get-DefaultAssetSpec

**Purpose:** Returns default asset specification when AI is not available.

**Syntax:**
```powershell
Get-DefaultAssetSpec -SystemName <string> -AssetType <string>
```

**Parameters:**
- `SystemName` - Magic system name
- `AssetType` - Type of asset

**Returns:** Hashtable with default specification

**Behavior:**
- Uses system-specific color palettes when available
- Falls back to generic blue palette for unknown systems
- Respects quality settings from `$script:QualitySettings`
- Returns consistent structure matching AI-generated specs

**System Color Palettes:**
- DragonMagic: Red/orange/yellow gradient
- BloodMagic: Dark to bright red
- Necromancy: Grayscale
- DruidicMagic: Green nature tones
- ElementMagic: Blue tones
- Geomancy: Brown earth tones

---

#### Generate-Asset

**Purpose:** Generates a single asset using AI specifications.

**Syntax:**
```powershell
Generate-Asset -SystemName <string> -AssetType <string> -AssetName <string> -Specification <object>
```

**Parameters:**
- `SystemName` - Magic system name
- `AssetType` - Type of asset to generate
- `AssetName` - Name for the output file (without extension)
- `Specification` - PSCustomObject with asset specification

**Returns:** `$true` if generation succeeded, `$false` otherwise

**Behavior:**
- Determines output path based on asset type and mod structure
- Creates temporary JSON file with specification
- Calls Python `generate_asset_image.py` script
- Handles path normalization for spaces and special characters
- Provides detailed error messages with suggestions
- Falls back to placeholder if Python unavailable

**Output Paths:**
- Textures: `$ModPath/Assets/Textures/$SystemName/`
- Other assets: `$OutputDir/$AssetType/$SystemName/`

**Example:**
```powershell
$spec = Get-AIAssetSpecification -SystemName "DragonMagic" -AssetType "icons"
$success = Generate-Asset -SystemName "DragonMagic" -AssetType "icons" -AssetName "dragon_icon" -Specification $spec
```

---

#### Generate-Spritesheet

**Purpose:** Generates a spritesheet from multiple assets.

**Syntax:**
```powershell
Generate-Spritesheet -SystemName <string> -AssetType <string> -Assets <array> [-Columns <int>] [-Rows <int>] [-FrameWidth <int>] [-FrameHeight <int>] [-Spacing <int>]
```

**Parameters:**
- `SystemName` - Magic system name
- `AssetType` - Type of assets in spritesheet
- `Assets` - Array of asset objects with Path property
- `Columns` - Number of columns (0 = auto-calculate)
- `Rows` - Number of rows (0 = auto-calculate)
- `FrameWidth` - Width of each frame (0 = use default)
- `FrameHeight` - Height of each frame (0 = use default)
- `Spacing` - Pixels between frames (default: 2)

**Returns:** Nothing (void)

**Behavior:**
- Auto-calculates grid layout if columns/rows not specified
- Uses asset config defaults for frame size if not specified
- Calls Python `generate_spritesheet.py` script
- Handles path normalization for asset list
- Creates metadata JSON alongside spritesheet

**Grid Calculation:**
- If both columns and rows are 0: calculates square-ish grid
- If only columns specified: calculates rows to fit all assets
- If only rows specified: calculates columns to fit all assets

**Example:**
```powershell
$assets = @(
    @{Path="asset1.png"},
    @{Path="asset2.png"},
    @{Path="asset3.png"}
)
Generate-Spritesheet -SystemName "DragonMagic" -AssetType "icons" -Assets $assets -Columns 2
```

---

#### Normalize-PathForCommand

**Purpose:** Normalizes a path for use in command-line arguments, ensuring it works with spaces.

**Syntax:**
```powershell
Normalize-PathForCommand -Path <string>
```

**Parameters:**
- `Path` - Path to normalize

**Returns:** Normalized path string

**Behavior:**
- Resolves relative paths to absolute if path exists
- Preserves original format for non-existent paths (e.g., output paths)
- Handles paths with spaces correctly
- PowerShell automatically quotes paths when passed in arrays

**Example:**
```powershell
$normalized = Normalize-PathForCommand -Path "C:\My Folder\file.png"
# Returns: "C:\My Folder\file.png" (resolved if exists)
```

---

#### Join-PathArray

**Purpose:** Joins an array of paths with a delimiter, handling paths with spaces and special characters.

**Syntax:**
```powershell
Join-PathArray -Paths <array> [-Delimiter <string>]
```

**Parameters:**
- `Paths` - Array of path strings
- `Delimiter` - Delimiter to use (default: ",")

**Returns:** Joined path string

**Behavior:**
- Normalizes each path before joining
- Quotes paths that contain the delimiter character
- Used for passing multiple paths to Python scripts

**Example:**
```powershell
$paths = @("C:\Path1", "C:\Path 2", "C:\Path,3")
$joined = Join-PathArray -Paths $paths
# Returns: "C:\Path1,C:\Path 2,"C:\Path,3""
```

---

#### Test-PythonDependency

**Purpose:** Tests if Python is available and checks for required packages.

**Syntax:**
```powershell
Test-PythonDependency [-CheckPillow]
```

**Parameters:**
- `CheckPillow` - Switch to also check for Pillow (PIL) package

**Returns:** `$true` if Python (and Pillow if requested) is available, `$false` otherwise

**Behavior:**
- Checks for `python` or `python3` in PATH
- If `-CheckPillow` specified, verifies PIL import works
- Provides user-friendly error messages with installation instructions
- Writes status messages to console

**Example:**
```powershell
if (-not (Test-PythonDependency -CheckPillow)) {
    Write-Host "Python or Pillow missing - some features disabled"
}
```

---

#### Write-ErrorWithContext

**Purpose:** Writes an error message with additional context and suggestions.

**Syntax:**
```powershell
Write-ErrorWithContext -Message <string> [-Context <string>] [-Suggestions <string[]>]
```

**Parameters:**
- `Message` - Main error message
- `Context` - Additional context about the error
- `Suggestions` - Array of suggestion strings

**Returns:** Nothing (void)

**Behavior:**
- Formats error message in red
- Displays context in gray
- Lists suggestions in yellow with bullet points
- Provides consistent error reporting across the system

**Example:**
```powershell
Write-ErrorWithContext `
    -Message "Asset generation failed" `
    -Context "Exit code: 1, Type: textures" `
    -Suggestions @(
        "Check Python error output",
        "Verify Pillow is installed",
        "Check output directory permissions"
    )
```

---

### Python Functions

#### generate_asset_image.py

**Main Function:** `main()`

**Purpose:** Command-line entry point for asset image generation.

**Arguments:**
- `--spec` - Path to JSON specification file (required)
- `--output` - Path to output image file (required)
- `--type` - Asset type (icons, sprites, textures, spell_assets)
- `--size` - Image size in pixels (overrides spec if provided)

**Behavior:**
- Reads JSON specification from file
- Validates specification structure
- Generates image based on specification
- Saves to output path
- Returns exit code: 0=success, 1=dependencies, 2=arguments, 3=generation, 4=I/O

**Specification Format:**
```json
{
  "colors": ["#ff4444", "#ff8844"],
  "pattern": "gradient",
  "style": "stylized",
  "effects": ["glow"],
  "theme": "DragonMagic",
  "size": 512,
  "details": [],
  "tileable": true
}
```

---

#### generate_gradient_pattern()

**Purpose:** Generate a gradient pattern image.

**Location:** `generate_asset_image.py`

**Signature:**
```python
def generate_gradient_pattern(size, colors, direction="vertical"):
```

**Parameters:**
- `size` - Image size (width and height)
- `colors` - List of hex color strings
- `direction` - "vertical" or "horizontal"

**Returns:** PIL Image object (RGBA mode)

**Behavior:**
- Creates RGBA image of specified size
- Interpolates between colors based on direction
- Defaults to blue gradient if colors insufficient

---

#### generate_noise_pattern()

**Purpose:** Generate a noise-based pattern image.

**Location:** `generate_asset_image.py`

**Signature:**
```python
def generate_noise_pattern(size, colors, intensity=0.3):
```

**Parameters:**
- `size` - Image size
- `colors` - List of hex color strings (uses first)
- `intensity` - Noise intensity (0.0 to 1.0)

**Returns:** PIL Image object (RGBA mode)

**Behavior:**
- Generates random noise around base color
- Intensity controls variation amount
- Creates organic, textured appearance

---

#### generate_spritesheet.py

**Main Function:** `main()`

**Purpose:** Command-line entry point for spritesheet generation.

**Arguments:**
- `--images` - Comma-separated list of image paths (required)
- `--output` - Output spritesheet path (required)
- `--columns` - Number of columns (0 = auto)
- `--rows` - Number of rows (0 = auto)
- `--frame-width` - Frame width in pixels (0 = auto)
- `--frame-height` - Frame height in pixels (0 = auto)
- `--spacing` - Pixels between frames (default: 2)
- `--variable-size` - Use bin-packing for variable frame sizes

**Behavior:**
- Reads all input images
- Calculates optimal grid layout
- Packs images into spritesheet
- Generates metadata JSON
- Saves spritesheet and metadata

**Grid Calculation:**
- Considers aspect ratio of images
- Prefers power-of-2 dimensions
- Minimizes wasted space
- Respects maximum sheet size (8192px default)

---

#### calculate_optimal_grid()

**Purpose:** Calculate optimal grid dimensions for spritesheet.

**Location:** `generate_spritesheet.py`

**Signature:**
```python
def calculate_optimal_grid(num_images, avg_width, avg_height, max_sheet_size=8192):
```

**Parameters:**
- `num_images` - Number of images to pack
- `avg_width` - Average image width
- `avg_height` - Average image height
- `max_sheet_size` - Maximum sheet dimension

**Returns:** Tuple `(columns, rows)`

**Behavior:**
- Starts with square-ish grid (sqrt-based)
- Adjusts for aspect ratio (wide vs tall images)
- Tests power-of-2 sizes for efficiency
- Minimizes wasted space (empty cells)
- Ensures sheet size within limits

**Algorithm:**
1. Calculate base grid from square root
2. Adjust for aspect ratio if images are wide/tall
3. Test nearby power-of-2 sizes
4. Select grid with least waste

---

#### generate_previews.py

**Main Function:** `main()`

**Purpose:** Generate preview thumbnails and asset catalog.

**Arguments:**
- `--input-dir` - Directory containing assets (required)
- `--output-dir` - Output directory for previews (required)
- `--thumbnail-size` - Thumbnail size (default: 128)
- `--preview-size` - Preview image size (default: 512)
- `--format` - Output format: html, json, both (default: both)

**Behavior:**
- Scans input directory for image files
- Generates thumbnails (128x128) and previews (512x512)
- Creates HTML catalog with interactive previews
- Creates JSON catalog with metadata
- Includes statistics and asset information

**Output Files:**
- `thumbnails/` - Directory of thumbnail images
- `previews/` - Directory of preview images
- `catalog.html` - Interactive HTML catalog
- `catalog.json` - JSON metadata catalog

---

## Extension Guide

### Adding a New Asset Type

#### 1. Update Asset Configuration

In `OllamaAssetGenerator.ps1`, add to `$script:AssetConfigs`:

```powershell
$script:AssetConfigs = @{
    # ... existing types ...
    "new_type" = @{
        DefaultSize = 64
        Folder = "NewType"
        Description = "Description of new asset type"
    }
}
```

#### 2. Update Asset Type Validation

Add to `ValidateSet` in parameter definitions:

```powershell
[ValidateSet("icons", "sprites", "textures", "spell_assets", "new_type")]
[string]$AssetTypes = "all"
```

#### 3. Add Generation Logic

In `Generate-Asset` function, add type-specific handling if needed:

```powershell
if ($AssetType -eq "new_type") {
    # Special handling for new type
    $outputPath = Join-Path $script:OutputDir "NewType"
    $outputPath = Join-Path $outputPath $SystemName
}
```

#### 4. Update Python Script (if needed)

In `generate_asset_image.py`, add pattern or style support:

```python
def generate_new_type_pattern(size, colors, spec):
    """Generate pattern specific to new asset type."""
    # Implementation
    pass
```

---

### Adding a New Magic System

#### 1. Add to System List

In `OllamaAssetGenerator.ps1`, add to `$script:AllSystems`:

```powershell
$script:AllSystems = @(
    # ... existing systems ...
    "NewMagicSystem"
)
```

#### 2. Add System-Specific Colors (Optional)

In `Get-DefaultAssetSpec`, add color palette:

```powershell
$systemColors = @{
    # ... existing systems ...
    "NewMagicSystem" = @("#color1", "#color2", "#color3", "#color4")
}
```

#### 3. Update AI Prompts (Optional)

The AI prompt in `Get-AIAssetSpecification` automatically includes the system name, but you can add system-specific prompt enhancements:

```powershell
if ($SystemName -eq "NewMagicSystem") {
    $prompt += "`nSpecial requirements for NewMagicSystem: ..."
}
```

---

### Adding a New Pattern Type

#### 1. Implement Pattern Function

In `generate_asset_image.py`, add new pattern function:

```python
def generate_custom_pattern(size, colors, spec):
    """
    Generate a custom pattern.
    
    Args:
        size: Image size (width, height)
        colors: List of hex color strings
        spec: Full specification object
    
    Returns:
        PIL Image object (RGBA mode)
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # Your pattern generation logic here
    # Use colors, spec.effects, spec.details, etc.
    
    return img
```

#### 2. Register Pattern

In the pattern selection logic, add your pattern:

```python
pattern_generators = {
    "gradient": generate_gradient_pattern,
    "noise": generate_noise_pattern,
    "organic": generate_organic_pattern,
    "geometric": generate_geometric_pattern,
    "custom": generate_custom_pattern  # Add here
}
```

#### 3. Update AI Prompt (Optional)

The AI will automatically discover new patterns if you update the prompt in `Get-AIAssetSpecification`:

```powershell
$prompt = @"
...
- pattern: Pattern type (gradient, noise, organic, geometric, custom, etc.)
...
"@
```

---

### Adding a New Quality Preset

#### 1. Update Configuration File

In `AssetGeneration.config.json`, add to `qualityPresets`:

```json
{
  "name": "Custom",
  "description": "Custom quality preset",
  "qualityTier": "High",
  "textureSize": 768,
  "textureFormat": "BC7",
  "generateMipmaps": true,
  "compressTextures": true,
  "maxVertices": 20000,
  "maxTriangles": 10000,
  "optimizeMeshes": true,
  "usePBR": true,
  "generateNormalMaps": true,
  "generateEmissionMaps": false,
  "maxParticles": 750,
  "useGPUInstancing": true,
  "maxTextureFileSize": 8388608,
  "maxMeshFileSize": 3145728
}
```

#### 2. Update PowerShell Quality Settings

In `OllamaAssetGenerator.ps1`, add to `$script:QualitySettings`:

```powershell
$script:QualitySettings = @{
    # ... existing presets ...
    "custom" = @{ Size = 768; Detail = "custom"; Colors = 7 }
}
```

#### 3. Update Validation

Add to `ValidateSet` for Quality parameter:

```powershell
[ValidateSet("low", "medium", "high", "ultra", "custom")]
[string]$Quality = "high"
```

---

### Creating a New Generator Script

#### 1. Create PowerShell Script

Create new `.ps1` file following the pattern:

```powershell
<#
.SYNOPSIS
    Your Generator Description
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    # Add your parameters
)

$ErrorActionPreference = "Stop"

# Set PSScriptRoot
if (-not $PSScriptRoot) {
    $PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

# Import shared modules
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools
$tools = Initialize-ToolsetTools -RequiredTools @() -OptionalTools @("Python", "Ollama")

# Your generation logic here
```

#### 2. Create Python Script (if needed)

Create new `.py` file with proper structure:

```python
#!/usr/bin/env python3
"""
Your Generator Description
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Check dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("ERROR: Pillow (PIL) is required.", file=sys.stderr)
    sys.exit(1)

# Add Shared directory
script_dir = Path(__file__).parent
shared_dir = script_dir.parent / "Shared"
sys.path.insert(0, str(shared_dir))

def main():
    parser = argparse.ArgumentParser(description="Your generator")
    parser.add_argument("--input", required=True, help="Input path")
    parser.add_argument("--output", required=True, help="Output path")
    
    args = parser.parse_args()
    
    # Your generation logic here
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

#### 3. Create Batch File (Optional)

Create `.bat` file for easy execution:

```batch
@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "YourGenerator.ps1" %*
```

---

### Integrating with Unity

#### 1. Unity Asset Structure

Assets should be placed in:
```
$ModPath/
  Assets/
    Textures/
      $SystemName/
        texture_name.png
        texture_name.png.meta
```

#### 2. Generate Unity Meta Files

Use the Unity integration functions (if available):

```powershell
# After generating texture
$texturePath = Join-Path $modPath "Assets\Textures\$systemName\$textureName.png"
New-UnityTextureMeta -TexturePath $texturePath -Format "DXT5" -GenerateMipmaps
```

#### 3. Material Generation

Create material presets:

```powershell
$materialPath = Join-Path $modPath "Assets\Materials\$systemName\$materialName.mat"
New-UnityMaterial -MaterialPath $materialPath -TexturePath $texturePath
```

---

### Extending Ollama Integration

#### 1. Custom Task Types

In Shared `OllamaIntegration.psm1`, you can add custom task types:

```powershell
# The module automatically routes:
# - "visual" tasks to visual tier
# - Dark tone detection routes to dark_tone tier
# - Escalation on refusal to escalation tier

# Use existing task types:
Invoke-OllamaRequest -Prompt $prompt -TaskType "visual" -AutoEscalate
```

#### 2. Custom Prompts

Enhance prompts in `Get-AIAssetSpecification`:

```powershell
$prompt = @"
Your enhanced prompt with:
- Specific requirements
- Style guidelines
- Technical constraints
- Examples or references
"@

$systemPrompt = "Your custom system prompt for the AI"
```

#### 3. Response Parsing

Customize JSON extraction in `Get-AIAssetSpecification`:

```powershell
# Current: Extracts JSON from response
if ($response -match '\{.*\}') {
    $jsonMatch = $Matches[0]
    $spec = $jsonMatch | ConvertFrom-Json
}

# Enhanced: Handle markdown code blocks
if ($response -match '```json\s*(\{.*?\})\s*```') {
    $spec = $Matches[1] | ConvertFrom-Json
} elseif ($response -match '\{.*\}') {
    $spec = $Matches[0] | ConvertFrom-Json
}
```

---

### Testing Extensions

#### 1. Unit Testing Functions

Test PowerShell functions:

```powershell
# Test path normalization
$testPath = "C:\Test Folder\file.png"
$normalized = Normalize-PathForCommand -Path $testPath
if ($normalized -ne $testPath) {
    Write-Error "Path normalization failed"
}

# Test default specs
$spec = Get-DefaultAssetSpec -SystemName "DragonMagic" -AssetType "icons"
if (-not $spec.colors) {
    Write-Error "Default spec missing colors"
}
```

#### 2. Integration Testing

Test full workflow:

```powershell
# Test asset generation
$spec = Get-AIAssetSpecification -SystemName "DragonMagic" -AssetType "icons"
$success = Generate-Asset -SystemName "DragonMagic" -AssetType "icons" -AssetName "test" -Specification $spec
if (-not $success) {
    Write-Error "Asset generation failed"
}
```

#### 3. Python Script Testing

Test Python scripts directly:

```bash
python generate_asset_image.py --spec test_spec.json --output test.png --type icons --size 64
```

---

### Best Practices

#### 1. Error Handling

Always use try-catch blocks:

```powershell
try {
    $result = Generate-Asset -SystemName $sys -AssetType $type -AssetName $name -Specification $spec
} catch {
    Write-ErrorWithContext `
        -Message "Generation failed" `
        -Context "System: $sys, Type: $type" `
        -Suggestions @("Check logs", "Verify inputs")
}
```

#### 2. Path Handling

Always normalize paths:

```powershell
$normalizedPath = Normalize-PathForCommand -Path $userPath
$outputPath = Join-Path $baseDir $normalizedPath
```

#### 3. Configuration

Use configuration files instead of hardcoding:

```powershell
$config = Get-Content "config.json" | ConvertFrom-Json
$quality = $config.qualityPresets | Where-Object { $_.name -eq $Quality }
```

#### 4. User Feedback

Provide clear, actionable feedback:

```powershell
Write-Host "✓ Success message" -ForegroundColor Green
Write-Host "⚠ Warning message" -ForegroundColor Yellow
Write-Host "✗ Error message" -ForegroundColor Red
```

#### 5. Documentation

Document all functions with `.SYNOPSIS`:

```powershell
function My-Function {
    <#
    .SYNOPSIS
    Brief description of what the function does.
    
    .DESCRIPTION
    Detailed description with examples.
    
    .PARAMETER ParamName
    Parameter description.
    
    .EXAMPLE
    My-Function -ParamName "value"
    #>
    param(...)
}
```

---

## Additional Resources

- **User Documentation:** See `OLLAMA_ASSET_GENERATOR_GUIDE.md`
- **Configuration Guide:** See `CONFIG_README.md`
- **Troubleshooting:** See `TROUBLESHOOTING.md`
- **Unity Integration:** See `UNITY_INTEGRATION_GUIDE.md`
- **Texture Formats:** See `TEXTURE_FORMAT_GUIDE.md`

---

## Version History

- **v1.0** - Initial developer documentation
  - Architecture overview
  - Function documentation
  - Extension guide

---

*Last Updated: 2024*
