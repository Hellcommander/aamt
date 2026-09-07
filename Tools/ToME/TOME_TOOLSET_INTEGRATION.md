# Tales of Maj'Eyal (ToME) Toolset Integration
**AI-Assisted Modding Tools (AAMT)**

This document describes how the ToME toolset integrates with AAMT's unified tool detection and integration system.

## Overview

The ToME toolset primarily uses Python scripts for asset generation and mod checking. To enable these Python scripts to benefit from AAMT's unified tool detection, PowerShell helper scripts are provided.

## Helper Scripts

### ✅ CheckTools.ps1
- **Purpose**: Check tool availability and output status (JSON or human-readable)
- **Usage**: Can be called from Python scripts or batch files
- **Output**: Tool status in JSON format (for Python parsing) or human-readable format
- **Status**: Created and ready for use

### ✅ InitializeToMETools.ps1
- **Purpose**: Initialize and validate tools for ToME scripts
- **Usage**: Called at the start of batch files or PowerShell wrappers
- **Returns**: Tool status hashtable with paths and availability
- **Status**: Created and integrated into batch files

## Integrated Batch Files

### ✅ tome_asset_generator.bat
- **Required Tools**: Python
- **Optional Tools**: Ollama, ImageMagick
- **Integration**: Uses `InitializeToMETools.ps1` to check tools
- **Status**: Fully integrated

### ✅ tome_mod_checker.bat
- **Required Tools**: Python
- **Optional Tools**: Ollama (recommended for AI features)
- **Integration**: Uses `InitializeToMETools.ps1` to check tools
- **Status**: Fully integrated

### ✅ tome_asset_generator_ai.bat
- **Required Tools**: Python, Ollama
- **Optional Tools**: ImageMagick
- **Integration**: Uses `InitializeToMETools.ps1` to check tools
- **Status**: Fully integrated

### ✅ LaunchToMEAssetGeneratorGUI.bat
- **Required Tools**: Python
- **Optional Tools**: Ollama, ImageMagick
- **Integration**: Uses unified tool detection for Python and Ollama
- **Status**: Fully integrated

### ✅ LaunchToMEModChecker.bat
- **Required Tools**: Python
- **Optional Tools**: Ollama (recommended)
- **Integration**: Uses unified tool detection
- **Status**: Fully integrated

## Integration Methods

### Method 1: PowerShell Wrapper Scripts

Create PowerShell wrappers for Python scripts that check tools first:

```powershell
# Example: tome_asset_generator_wrapper.ps1
$tools = .\InitializeToMETools.ps1 -RequiredTools @("Python") -OptionalTools @("Ollama", "ImageMagick")

if ($tools.AllRequiredAvailable) {
    $pythonPath = $tools.PythonPath
    & $pythonPath tome_asset_generator.py @args
} else {
    exit 1
}
```

### Method 2: Python Script Integration

Python scripts can call the PowerShell helper to check tools:

```python
import subprocess
import json

def check_tools():
    """Check tool availability using AAMT tool detection."""
    result = subprocess.run(
        ["powershell", "-File", "CheckTools.ps1", "-Tool", "All", "-Json"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None
```

### Method 3: Batch File Integration

Batch files can call PowerShell helpers:

```batch
@echo off
REM Check tools before running Python script
powershell -File "InitializeToMETools.ps1" -RequiredTools @("Python")
if %ERRORLEVEL% NEQ 0 (
    echo Tools not available
    pause
    exit /b 1
)

REM Run Python script
python tome_asset_generator.py %*
```

## Tool Requirements

### Required for All ToME Scripts
- **Python** - Core runtime for all ToME Python scripts

### Optional Tools (Enhance Functionality)
- **Ollama** - For AI-assisted asset generation and mod fixing
- **ImageMagick** - For image post-processing (if asset generation includes images)

## Python Script Integration Example

Update Python scripts to check for tools:

```python
import subprocess
import json
import os

def check_ollama_available():
    """Check if Ollama is available using AAMT tool detection."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    check_script = os.path.join(script_dir, "CheckTools.ps1")
    
    if os.path.exists(check_script):
        try:
            result = subprocess.run(
                ["powershell", "-File", check_script, "-Tool", "Ollama", "-Json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status = json.loads(result.stdout)
                return status.get("Ollama", {}).get("Available", False)
        except:
            pass
    
    # Fallback to direct check
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

# Use in script
if check_ollama_available():
    # Use Ollama features
    pass
else:
    # Fallback behavior
    pass
```

## Current Python Scripts

### tome_mod_checker.py
- **Uses**: Ollama (for AI-guided mod fixing)
- **Integration**: Can use `CheckTools.ps1` to verify Ollama availability
- **Status**: Ready for integration

### tome_asset_generator.py
- **Uses**: Python (required)
- **Optional**: Ollama (for AI-enhanced generation), ImageMagick (for post-processing)
- **Integration**: Can use `InitializeToMETools.ps1` to check tools

### tome_asset_generator_ai.py
- **Uses**: Python (required), Ollama (for AI features)
- **Integration**: Should use `InitializeToMETools.ps1` to validate Ollama

## Batch File Updates

Update batch files to check tools:

```batch
@echo off
REM ToME Asset Generator with Tool Detection
powershell -ExecutionPolicy Bypass -File "%~dp0InitializeToMETools.ps1" -RequiredTools @("Python") -OptionalTools @("Ollama")
if %ERRORLEVEL% NEQ 0 (
    echo Required tools not available
    pause
    exit /b 1
)

python "%~dp0tome_asset_generator.py" %*
```

## Benefits

1. **Unified Detection**: Python scripts can benefit from unified tool detection
2. **Better Error Messages**: Clear installation hints when tools are missing
3. **Consistent Behavior**: All toolsets handle missing tools the same way
4. **Easy Maintenance**: Tool detection logic is centralized
5. **Graceful Degradation**: Optional tools enhance but don't block execution

## Tool Detection Details

The unified system automatically:
- Detects tools in system PATH
- Checks environment variables
- Searches common installation paths
- Provides installation hints when tools are missing
- Caches detection results for performance

## See Also

- **[Toolset Integration Guide](../TOOLSET_INTEGRATION_GUIDE.md)** - Complete integration documentation
- **[Setup Guide](../SETUP_REQUIRED_TOOLS.md)** - Installation instructions for all tools
- **[Main README](../README_AAMT.md)** - Overview of AAMT
