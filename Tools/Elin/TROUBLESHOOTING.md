# Troubleshooting Guide

Common issues and solutions for the Asset Generator.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Python and Dependencies](#python-and-dependencies)
3. [Ollama Issues](#ollama-issues)
4. [Generation Problems](#generation-problems)
5. [Unity Integration](#unity-integration)
6. [Path and File Issues](#path-and-file-issues)
7. [Performance Issues](#performance-issues)
8. [Error Messages](#error-messages)
9. [Steam Deck / Linux — Mods Not Loading](#steam-deck--linux--mods-not-loading)

## Installation Issues

### Python Not Found

**Error**: `Python is not installed or not in PATH`

**Solutions**:
1. Install Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart your terminal/PowerShell after installation
4. Verify: Run `python --version` in PowerShell
5. If using `python3`, ensure it's in PATH

### Pillow Not Installed

**Error**: `Pillow (PIL) is required but not installed`

**Solutions**:
1. Install Pillow: `pip install Pillow`
2. Or: `python -m pip install Pillow`
3. If using Python 3: `python3 -m pip install Pillow`
4. Verify: `python -c "import PIL; print('OK')"`

### Script Not Found

**Error**: `Python generator not found` or `Preview generator not found`

**Solutions**:
1. Ensure all Python scripts are in the same directory as `OllamaAssetGenerator.ps1`
2. Required files:
   - `generate_asset_image.py`
   - `generate_previews.py`
   - `generate_spritesheet.py`
3. Check file paths don't contain special characters
4. Verify you're running from the correct directory

## Python and Dependencies

### Import Errors

**Error**: `ModuleNotFoundError` or `ImportError`

**Solutions**:
1. Verify Python version: `python --version` (3.7+ required)
2. Install missing package: `pip install [package-name]`
3. Check virtual environment: Ensure you're in the correct environment
4. Reinstall Pillow: `pip uninstall Pillow && pip install Pillow`

### Permission Errors

**Error**: `Permission denied` when installing packages

**Solutions**:
1. Use `--user` flag: `pip install --user Pillow`
2. Run PowerShell as Administrator
3. Check Python installation permissions
4. Use virtual environment: `python -m venv venv`

### Python Version Issues

**Error**: Script fails with version-related errors

**Solutions**:
1. Check Python version: `python --version`
2. Required: Python 3.7 or higher
3. Update Python if needed
4. Use `python3` if both Python 2 and 3 are installed

## Ollama Issues

### Ollama Not Running

**Error**: `Ollama not available` or connection errors

**Solutions**:
1. Start Ollama: `ollama serve`
2. Verify it's running: Open http://localhost:11434 in browser
3. Check firewall settings
4. Verify Ollama is installed: `ollama --version`

### No Models Available

**Error**: `No models found` or model errors

**Solutions**:
1. List models: `ollama list`
2. Pull a model: `ollama pull llama3.1:8b`
3. Recommended models:
   - `llama3.1:8b` - General purpose
   - `llama3.1:70b` - Higher quality (requires more RAM)
4. Check available disk space

### Slow Generation

**Problem**: Ollama responses are very slow

**Solutions**:
1. Use smaller model: `llama3.1:8b` instead of `70b`
2. Check system RAM (8GB+ recommended)
3. Close other applications
4. Use GPU acceleration if available
5. Consider disabling Ollama and using default specs

## Generation Problems

### No Assets Generated

**Problem**: Script runs but no files are created

**Solutions**:
1. Check output directory permissions
2. Verify output path exists and is writable
3. Check Python script executed successfully
4. Review error messages in console
5. Verify asset type is valid: `icons`, `sprites`, `textures`, `spell_assets`

### Assets Generated but Empty/Corrupt

**Problem**: Files created but can't be opened

**Solutions**:
1. Verify Pillow is working: `python -c "from PIL import Image; print('OK')"`
2. Check disk space
3. Verify file permissions
4. Regenerate with lower quality to test
5. Check Python error output

### Wrong Asset Sizes

**Problem**: Assets are wrong dimensions

**Solutions**:
1. Check quality setting (affects size)
2. Verify specification file is valid JSON
3. Check `--size` parameter if used
4. Review `AssetGeneration.config.json` settings

### Missing Unity Meta Files

**Problem**: `.meta` files not generated

**Solutions**:
1. Verify script completed successfully
2. Check for errors in generation output
3. `.meta` files are only created for textures
4. Manually create if needed (copy from existing texture)

## Unity Integration

### Textures Not Appearing in Unity

**Problem**: Assets don't show up in Unity Project window

**Solutions**:
1. Verify files are in `Assets/` folder (not outside)
2. Refresh Unity: `Assets > Refresh` (Ctrl+R)
3. Check Unity Console for import errors
4. Verify `.meta` files exist alongside textures
5. Check file permissions

### Import Errors in Unity

**Problem**: Unity shows import errors

**Solutions**:
1. Check Unity Console for specific error
2. Verify texture dimensions are power-of-2
3. Ensure PNG files are valid (open in image viewer)
4. Check file isn't corrupted
5. Verify `.meta` file format is correct

### Materials Not Working

**Problem**: Materials don't display correctly

**Solutions**:
1. Verify texture is assigned to material
2. Check shader compatibility
3. Ensure textures finished importing
4. Check material rendering mode
5. Verify texture import settings

### Performance Issues in Unity

**Problem**: Unity is slow with generated assets

**Solutions**:
1. Use lower quality settings
2. Enable texture compression
3. Reduce texture max size in import settings
4. Use texture atlases instead of individual textures
5. Check total asset count and file sizes

## Path and File Issues

### Paths with Spaces

**Problem**: Script fails with paths containing spaces

**Solutions**:
1. Use quotes around paths: `"C:\My Mod\Path"`
2. Path normalization is automatic in recent versions
3. Avoid special characters in paths if possible
4. Use relative paths when possible

### Invalid Characters in Paths

**Problem**: Errors about invalid path characters

**Solutions**:
1. Avoid these characters: `< > : " | ? *`
2. Use underscores instead of spaces: `My_Mod`
3. Keep paths reasonably short
4. Use alphanumeric characters and underscores

### File Permission Errors

**Problem**: `Access denied` or permission errors

**Solutions**:
1. Run PowerShell as Administrator
2. Check folder permissions
3. Ensure output directory is writable
4. Close files that might be locked (Unity, image viewers)
5. Check antivirus isn't blocking file creation

### Relative vs Absolute Paths

**Problem**: Script can't find files with relative paths

**Solutions**:
1. Use absolute paths when possible
2. Verify current directory: `Get-Location` in PowerShell
3. Use `-ModPath` with full path
4. Check path resolution in error messages

## Performance Issues

### Slow Generation

**Problem**: Asset generation takes too long

**Solutions**:
1. Use lower quality setting
2. Generate fewer assets at once
3. Disable Ollama if not needed
4. Close other applications
5. Check system resources (CPU, RAM, disk)

### High Memory Usage

**Problem**: Script uses too much RAM

**Solutions**:
1. Generate assets in smaller batches
2. Use lower quality settings
3. Close other applications
4. Increase system RAM if possible
5. Process one asset type at a time

### Disk Space Issues

**Problem**: Out of disk space errors

**Solutions**:
1. Check available disk space
2. Use lower quality settings (smaller files)
3. Clean up old generated assets
4. Use texture compression
5. Generate to different drive if needed

## Error Messages

### Common Error Codes

#### Python Exit Code 1
- **Cause**: Missing dependencies (Pillow)
- **Solution**: Install Pillow: `pip install Pillow`

#### Python Exit Code 2
- **Cause**: Invalid arguments or file paths
- **Solution**: Check command-line arguments and file paths

#### Python Exit Code 3
- **Cause**: Image generation failed
- **Solution**: Check Python error output, verify specifications

#### Python Exit Code 4
- **Cause**: File I/O error
- **Solution**: Check file permissions, disk space, path validity

### PowerShell Errors

#### "Unexpected token"
- **Cause**: Syntax error in PowerShell script
- **Solution**: Check script for syntax issues, ensure proper encoding (UTF-8)

#### "The Try statement is missing its Catch or Finally block"
- **Cause**: Malformed try-catch block
- **Solution**: Verify script structure, check for missing braces

#### "Cannot bind parameter"
- **Cause**: Invalid parameter or argument
- **Solution**: Check parameter names and values

### Getting Help

1. **Check Error Messages**: Read full error output for details
2. **Review Logs**: Check console output for warnings/errors
3. **Verify Dependencies**: Ensure Python, Pillow, and Ollama are installed
4. **Test Components**: Test Python scripts individually
5. **Check Documentation**: Review relevant guides

## Diagnostic Commands

### Test Python Installation
```powershell
python --version
python -c "import sys; print(sys.version)"
```

### Test Pillow
```powershell
python -c "from PIL import Image; print('Pillow OK')"
```

### Test Ollama
```powershell
ollama --version
ollama list
curl http://localhost:11434/api/tags
```

### Test Script Location
```powershell
Get-Location
Test-Path "generate_asset_image.py"
Test-Path "generate_previews.py"
```

### Check File Permissions
```powershell
Test-Path "C:\Your\Output\Path"
Get-Acl "C:\Your\Output\Path" | Format-List
```

## Still Having Issues?

1. **Check All Dependencies**: Python, Pillow, Ollama (if used)
2. **Verify Paths**: All paths should be valid and accessible
3. **Review Error Messages**: Full error text often contains the solution
4. **Test Minimal Case**: Try generating one asset with minimal settings
5. **Check System Requirements**: Ensure sufficient RAM, disk space, permissions

## Steam Deck / Linux — Mods Not Loading

**Symptom**: Code-based mods (CustomRaceClassCreator, other BepInEx plugins) are installed but do nothing on Steam Deck / Linux.

**Cause**: Elin ships BepInEx natively. Under Proton, `winhttp` must be overridden or injectors never hook.

**Fix**: Set Elin's Steam Launch Options to this exact line:

```bash
WINEDLLOVERRIDES="winhttp=n,b" %command%
```

Full write-up and Workshop blurb: [`STEAM_DECK_LINUX.md`](./STEAM_DECK_LINUX.md).

## See Also

- `QUICK_START.md` - Basic usage guide
- `STEAM_DECK_LINUX.md` - Proton / Steam Deck launch options for code mods
- `UNITY_INTEGRATION_GUIDE.md` - Unity-specific help
- `TEXTURE_FORMAT_GUIDE.md` - Format and quality information
- `OLLAMA_ASSET_GENERATOR_GUIDE.md` - Detailed generator documentation
