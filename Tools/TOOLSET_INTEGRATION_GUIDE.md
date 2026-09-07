# Toolset Integration Guide
**AI-Assisted Modding Tools (AAMT)**

This guide shows how game-specific toolsets can easily integrate with AAMT tools.

## Overview

All AAMT toolsets can take advantage of shared tools through the unified detection and integration modules:
- **ToolDetection.psm1** - Detects available tools (Ollama, ImageMagick, Blender, Python, Stable Diffusion)
- **ToolsetIntegration.psm1** - Helper functions for easy tool integration

## Quick Start

### 1. Import the Modules

At the top of your toolset script:

```powershell
# Import tool detection and integration modules
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
```

### 2. Initialize Tools for Your Toolset

```powershell
# Define which tools your toolset needs
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "Blender", "Python")

# Check if required tools are available
if (-not $tools.AllRequiredAvailable) {
    Write-Host "Missing required tools: $($tools.MissingRequired -join ', ')" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "YourToolset" -RequiredTools @("ImageMagick")
    exit 1
}
```

### 3. Use Tools When Available

```powershell
# Use ImageMagick if available
if ($tools.Tools["ImageMagick"].Available) {
    $magickPath = Get-ImageMagickPath
    & $magickPath input.png -resize 512x512 output.png
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    # Now you can use Ollama functions
    $enhanced = Invoke-OllamaRequest -Prompt "Enhance this description..."
}

# Use Blender if available
if ($tools.Tools["Blender"].Available) {
    $blenderPath = Get-BlenderPath
    & $blenderPath --background --python render_script.py
}
```

## Examples by Toolset

### Starbound Toolset

```powershell
# Import modules
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")

# Show status
Show-ToolsetStatus -ToolsetName "Starbound" `
    -RequiredTools @("ImageMagick") `
    -OptionalTools @("Ollama", "StableDiffusion", "Python", "Blender")

# Use Ollama for AI assistance
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    # Use Ollama to enhance asset descriptions
}

# Use ImageMagick for post-processing
if ($tools.Tools["ImageMagick"].Available) {
    $magickPath = Get-ImageMagickPath
    # Process generated images
}
```

### Caves of Qud Toolset

```powershell
# Import modules
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue

# Qud requires Blender for tile baking
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Blender", "ImageMagick") `
    -OptionalTools @()

if (-not $tools.AllRequiredAvailable) {
    Write-Host "ERROR: Missing required tools for Qud tile generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Caves of Qud" `
        -RequiredTools @("Blender", "ImageMagick")
    exit 1
}

# Use Blender for tile baking
$blenderPath = Get-BlenderPath
& $blenderPath --background --python bake_tile.py
```

### Elin Toolset

```powershell
# Import modules
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Elin uses Ollama and ImageMagick
$tools = Initialize-ToolsetTools `
    -RequiredTools @("ImageMagick", "Python") `
    -OptionalTools @("Ollama", "StableDiffusion")

# Use Ollama for asset generation
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    # Generate AI-enhanced asset specifications
}
```

## Available Functions

### Tool Detection Functions

```powershell
# Check if a tool is available
Test-ToolAvailable -ToolName "ImageMagick"  # Returns $true/$false

# Get detailed tool information
$info = Get-ToolInfo -ToolName "Blender"
# Returns: @{Available=$true; Path="..."; Version="..."; InstallationHint="..."}

# Get tool paths
$magickPath = Get-ImageMagickPath
$blenderPath = Get-BlenderPath
$pythonPath = Get-PythonPath

# Get status of all tools
$allStatus = Get-AllToolsStatus
Show-ToolsStatus  # Displays formatted status
```

### Toolset Integration Functions

```powershell
# Initialize tools for your toolset
$tools = Initialize-ToolsetTools -RequiredTools @("ImageMagick") -OptionalTools @("Ollama")

# Show toolset-specific status
Show-ToolsetStatus -ToolsetName "Starbound" -RequiredTools @("ImageMagick")

# Use tools with convenience functions
Use-ImageMagickIfAvailable -Arguments @("input.png", "-resize", "512x512", "output.png")
Use-BlenderIfAvailable -Arguments @("--background", "--python", "script.py")
Use-PythonIfAvailable -ScriptPath "generate.py" -Arguments @("--output", "assets")
Use-OllamaIfAvailable  # Imports Ollama integration module
Use-StableDiffusionIfAvailable  # Imports Stable Diffusion integration module
```

## Best Practices

### 1. Check Required Tools Early

```powershell
# At the start of your script
$tools = Initialize-ToolsetTools -RequiredTools @("ImageMagick")

if (-not $tools.AllRequiredAvailable) {
    Write-Host "ERROR: Required tools missing!" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "YourToolset" -RequiredTools @("ImageMagick")
    exit 1
}
```

### 2. Gracefully Handle Optional Tools

```powershell
# Optional tools enhance functionality but don't block execution
if ($tools.Tools["Ollama"].Available) {
    Write-Host "Using Ollama for AI assistance" -ForegroundColor Green
    Use-OllamaIfAvailable | Out-Null
    # Use Ollama features
} else {
    Write-Host "Ollama not available - using basic generation" -ForegroundColor Yellow
    # Fallback to non-AI generation
}
```

### 3. Provide Helpful Error Messages

```powershell
if (-not (Test-ImageMagickAvailable)) {
    $info = Get-ToolInfo -ToolName "ImageMagick"
    Write-Host "ImageMagick is required but not found." -ForegroundColor Red
    Write-Host "Installation hint: $($info.InstallationHint)" -ForegroundColor Yellow
    exit 1
}
```

### 4. Cache Tool Detection

The ToolDetection module automatically caches results for 5 minutes to avoid repeated checks. You can clear the cache by re-importing the module:

```powershell
Remove-Module ToolDetection -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolDetection.psm1")
```

## Tool-Specific Integration

### ImageMagick

```powershell
if (Test-ImageMagickAvailable) {
    $magickPath = Get-ImageMagickPath
    
    # Resize image
    & $magickPath input.png -resize 512x512 output.png
    
    # Convert format
    & $magickPath input.jpg -format png output.png
    
    # Or use convenience function
    Use-ImageMagickIfAvailable -Arguments @("input.png", "-resize", "512x512", "output.png")
}
```

### Blender

```powershell
if (Test-BlenderAvailable) {
    $blenderPath = Get-BlenderPath
    
    # Run Blender script
    & $blenderPath --background --python render.py
    
    # Or use convenience function
    Use-BlenderIfAvailable -Arguments @("--background", "--python", "render.py")
}
```

### Ollama

```powershell
if (Test-OllamaAvailable) {
    Use-OllamaIfAvailable | Out-Null
    
    # Now Ollama functions are available
    $response = Invoke-OllamaRequest -Prompt "Generate asset description..."
}
```

### Stable Diffusion

```powershell
if (Test-StableDiffusionAvailable) {
    Use-StableDiffusionIfAvailable | Out-Null
    
    # Now Stable Diffusion functions are available
    $image = Invoke-StableDiffusionGeneration -Prompt "A magical portal..."
}
```

### Python

```powershell
if (Test-PythonAvailable) {
    $pythonPath = Get-PythonPath
    
    # Run Python script
    & $pythonPath generate_assets.py --output assets/
    
    # Or use convenience function
    Use-PythonIfAvailable -ScriptPath "generate_assets.py" -Arguments @("--output", "assets/")
}
```

## Troubleshooting

### Module Not Found

If you get "module not found" errors, check the path:

```powershell
# From Tools root
$sharedPath = ".\Shared"

# From game-specific folder (e.g., Starbound/)
$sharedPath = "..\Shared"

# From nested folder (e.g., Qud/)
$sharedPath = "..\..\Shared"
```

### Tools Not Detected

If tools aren't being detected:

1. **Check if tool is in PATH**: `Get-Command toolname`
2. **Check common paths**: See `ToolDetection.psm1` for common paths
3. **Set environment variables**: Some tools use env vars (e.g., `BLENDER_PATH`)
4. **Clear cache**: Re-import the module to clear detection cache

### Integration Not Working

1. **Check module imports**: Ensure both ToolDetection and ToolsetIntegration are imported
2. **Check tool availability**: Use `Show-ToolsStatus` to see what's detected
3. **Check error messages**: Tools provide installation hints when not found

## See Also

- **[Tool Detection Module](../Shared/ToolDetection.psm1)** - Source code for tool detection
- **[Toolset Integration Module](../Shared/ToolsetIntegration.psm1)** - Source code for integration helpers
- **[Setup Guide](SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](README_AAMT.md)** - Overview of AAMT
