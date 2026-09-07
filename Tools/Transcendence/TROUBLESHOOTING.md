# Space Whale Asset Generation - Troubleshooting Guide

## GUI Not Showing

### Test GUI First
Run the test script to verify WPF works:
```batch
powershell -STA -File TestMonitorGUI.ps1
```

If this doesn't show a window, WPF may not be working on your system.

### Launch Monitor Separately
If the GUI doesn't appear when running the main batch file, launch it separately:
```batch
StartSpaceWhaleAssetGeneration_MonitorOnly.bat
```

Or manually:
```powershell
powershell -STA -File AssetGeneratorControlRoom_Monitor.ps1 -WatchDirectory "Output\SpaceWhaleAssets"
```

### Check Taskbar
The GUI window might be minimized or behind other windows. Check your taskbar for "Space Whale Monitor".

## Generation Not Using Worker Threads

### Verify Multithreading
Check Task Manager - you should see high CPU usage across multiple cores when generation is running.

### Check Output
The generators should print messages like:
- "Using X worker threads"
- "Progress: X/Y"

### Manual Test
Test individual generators:
```powershell
# Test FX generator
python space_whale_fx_variation_generator.py space_whale_fx_registry.json 10 5

# Test Visual generator
python ollama_visual_variation_generator.py --registry space_whale_visual_language_registry.json --output TestOutput --count 10
```

## Common Errors

### "Python is not installed"
- Install Python 3.8+ from python.org
- Check "Add Python to PATH" during installation
- Restart command prompt

### "Ollama is not running"
- Install Ollama from ollama.ai
- Start: `ollama serve`
- Verify: `curl http://localhost:11434/api/tags`

### "ERROR: Failed to create window"
- Ensure running in STA mode: `powershell -STA -File ...`
- Check WPF assemblies are available
- Try running TestMonitorGUI.ps1 first

### "IndexError: list index out of range"
- Fixed in latest version
- Update to latest code
- Check that registries have valid data

## Performance Issues

### Generation Takes Too Long
- Check CPU usage (should be high with multithreading)
- Verify thread count matches CPU cores
- Close other applications
- Use SSD for output directory

### Low CPU Usage
- Multithreading may not be working
- Check for errors in output
- Verify Python version (3.8+)
- Check system resources

## Getting Help

1. **Check Logs**: Review output in console
2. **Test Components**: Run test scripts individually
3. **Verify Prerequisites**: Python, Ollama, PowerShell
4. **Check File Paths**: Ensure all scripts are in Tools directory

## Quick Fixes

### Reset Everything
1. Close all PowerShell windows
2. Delete `Output\SpaceWhaleAssets` directory
3. Restart from batch file

### Manual Generation
If batch file doesn't work, run manually:
```powershell
cd Tools
python space_whale_comprehensive_asset_generator.py
```

### GUI Only
If you just want to monitor:
```batch
StartSpaceWhaleAssetGeneration_MonitorOnly.bat
```

