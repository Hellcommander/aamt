# Caves of Qud Mod Fixer

Automatically fixes Caves of Qud mods to work with newer API versions and corrects Harmony patch asset references using CodeLlama AI.

## Features

- **API Compatibility Fixes**: Compares mod code against decompiled source to identify and fix API changes
- **Asset Reference Fixes**: Validates and corrects asset paths in Harmony patches (sounds, textures, etc.)
- **Harmony Patch Analysis**: Detects and fixes issues in Harmony patches
- **AI-Powered Fixes**: Uses CodeLlama language model for intelligent code fixes
- **CPU Management**: Uses all but 1 core, maintaining minimum 6% CPU usage per core to prevent burn-in test behavior
- **Automatic Backups**: Creates backups before making changes

## Requirements

- Python 3.7 or higher
- Ollama installed and running (https://ollama.com)
- CodeLlama model installed: `ollama pull codellama`
- Required Python packages: `psutil`, `requests`

## Installation

1. Ensure Python is installed and in your PATH
2. Install Ollama from https://ollama.com
3. Pull the CodeLlama model:
   ```bash
   ollama pull codellama
   ```
4. Install Python dependencies (automatically checked on first run):
   ```bash
   pip install psutil requests
   ```

## Configuration

The tool uses these default paths (can be overridden with parameters):

- **Source Code**: `G:\CavesofQud-decompiledsource`
- **StreamingAssets**: `E:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets`
- **Mods Directory**: `C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods`

## Usage

### Basic Usage

Fix a specific mod:
```powershell
.\QudModFixer.ps1 -ModName "Broodmother Mutation"
```

Fix all mods:
```powershell
.\QudModFixer.ps1 -ModName "all"
```

Interactive mode (shows list of mods):
```powershell
.\QudModFixer.ps1
```

### Analyze Only (No Fixes)

Analyze mods without applying fixes:
```powershell
.\QudModFixer.ps1 -ModName "Broodmother Mutation" -AnalyzeOnly
```

### Custom Paths

Specify custom paths:
```powershell
.\QudModFixer.ps1 -ModName "MyMod" `
    -SourcePath "D:\MySource" `
    -AssetsPath "D:\MyAssets" `
    -ModsPath "D:\MyMods"
```

### No Backups

Skip backup creation (not recommended):
```powershell
.\QudModFixer.ps1 -ModName "MyMod" -NoBackup
```

### Batch File

You can also use the batch file directly:
```cmd
QudModFixer.bat "Broodmother Mutation"
```

## How It Works

1. **Indexing**: 
   - Indexes decompiled source code to build API reference
   - Indexes StreamingAssets to build asset reference

2. **Analysis**:
   - Scans all C# files in the mod
   - Identifies Harmony patches
   - Detects API calls and checks against source index
   - Validates asset references against StreamingAssets

3. **Fixing**:
   - Groups issues by file
   - Uses CodeLlama AI to generate fixes
   - Applies fixes with automatic backups
   - Reports results

## CPU Management

The tool is configured to:
- Use all available CPU cores except 1 (leaves 1 core free for system)
- Maintain minimum 6% CPU usage per core to prevent burn-in test behavior
- Monitor CPU usage during AI operations

## Output

The tool provides detailed output including:
- Number of API issues found
- Number of asset issues found
- Number of Harmony patches detected
- Files fixed and changes applied
- Any errors encountered

## Backup Files

Backups are created in the mods directory with the format:
```
{ModName}_backup_{YYYYMMDD_HHMMSS}
```

## Troubleshooting

### Ollama Not Found
- Ensure Ollama is installed and running
- Check that `ollama serve` is running or start it manually
- Verify CodeLlama is installed: `ollama list`

### Python Not Found
- Ensure Python 3.7+ is installed
- Add Python to your PATH
- Or specify Python path in the PowerShell script

### Missing Dependencies
- The script will attempt to auto-install missing packages
- Or manually install: `pip install psutil requests`

### Source/Assets Path Not Found
- Verify paths exist
- Use `-SourcePath` and `-AssetsPath` parameters to specify correct paths

### Low CPU Usage Warning
- This indicates the AI model may not be using all available cores
- Check Ollama configuration
- Ensure CodeLlama model is properly loaded

## Examples

### Fix Single Mod
```powershell
.\QudModFixer.ps1 -ModName "Broodmother Mutation"
```

### Analyze All Mods
```powershell
.\QudModFixer.ps1 -ModName "all" -AnalyzeOnly
```

### Fix with Custom Paths
```powershell
.\QudModFixer.ps1 -ModName "MyMod" `
    -SourcePath "G:\MySource" `
    -AssetsPath "E:\MyAssets" `
    -ModsPath "C:\MyMods"
```

## Technical Details

### API Comparison
- Parses C# source files to extract class and method definitions
- Builds index of available API calls
- Compares mod code against index to find missing/outdated calls

### Asset Validation
- Scans StreamingAssets for available files
- Normalizes asset paths for comparison
- Suggests similar assets if exact match not found

### Harmony Patch Detection
- Identifies files using HarmonyLib
- Extracts asset references from patches
- Validates asset paths

### AI Fix Generation
- Uses CodeLlama for code generation
- Provides context about issues and source code
- Generates complete fixed code files

## License

This tool is part of the Transcendence Tools collection.

