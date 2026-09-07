# Transcendence Mod Tools - Installation Guide

## Quick Start

1. **Download** the `Tools` folder to your Transcendence Extensions directory
2. **Double-click** `TranscendenceModTools.bat` to launch
3. **Drag and drop** your mod folder onto the tool window

That's it! The tool is ready to use.

---

## System Requirements

### Required
- **Windows 10/11** (or Windows 7/8.1)
- **PowerShell 5.1 or later** (included with Windows 10/11)
- **.NET Framework 4.7.2 or later** (usually pre-installed)

### Recommended
- **PowerShell 7+** (pwsh) for better performance
- **VS Code** (optional) for opening files at error lines

---

## Installation Steps

### Step 1: Locate Your Transcendence Extensions Folder

The Extensions folder is typically located at:
```
D:\games\Steam\steamapps\common\Transcendence\Extensions
```

Or if you installed Transcendence elsewhere:
```
C:\Program Files\Transcendence\Extensions
```

### Step 2: Copy the Tools Folder

1. Copy the entire `Tools` folder into your Extensions directory
2. Your structure should look like:
   ```
   Extensions/
   ├── Tools/
   │   ├── TranscendenceModTools.bat
   │   ├── TranscendenceModTools.ps1
   │   ├── TranscendenceModTools_*.ps1 (modules)
   │   └── ... (other files)
   ├── YourMod1/
   ├── YourMod2/
   └── ...
   ```

### Step 3: Verify Installation

1. Navigate to `Extensions\Tools`
2. Double-click `TranscendenceModTools.bat`
3. The tool window should open

If you see an error, see **Troubleshooting** below.

---

## Launching the Tool

### Method 1: Double-Click (Recommended)
- Double-click `TranscendenceModTools.bat`
- The GUI will open automatically

### Method 2: With a Mod Path (Command Line)
You can pass a mod path as an argument to automatically fill it in the tool:

**From Command Prompt:**
```cmd
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
TranscendenceModTools.bat "..\ZZZ_CrossModCompatibility"
```

**From PowerShell:**
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
.\TranscendenceModTools.ps1 -Path "..\ZZZ_CrossModCompatibility"
```

**Using absolute paths:**
```cmd
TranscendenceModTools.bat "D:\games\Steam\steamapps\common\Transcendence\Extensions\MyMod"
```

The path will be automatically filled in all relevant tabs (XML Checker, Project Health, etc.).

### Method 3: PowerShell Command (No Arguments)
Open PowerShell and run:
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
.\TranscendenceModTools.ps1
```

### Method 4: From Command Prompt (No Arguments)
```cmd
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
TranscendenceModTools.bat
```

---

## First-Time Setup

### Check PowerShell Execution Policy

If you get an execution policy error, run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Verify PowerShell Version

Check your PowerShell version:
```powershell
$PSVersionTable.PSVersion
```

**Minimum**: 5.1  
**Recommended**: 7.0+

### Install PowerShell 7 (Optional)

If you want PowerShell 7 for better performance:
1. Download from: https://aka.ms/powershell-release?tag=stable
2. Install normally
3. The tool will automatically use it if available

---

## Testing the Installation

### Quick Test

1. Launch the tool
2. Drag and drop a mod folder onto the window
3. You should see the Smart Detection dialog

### Test on Sample Mod

Test on the CrossModCompatibility mod:
1. Navigate to: `Extensions\ZZZ_CrossModCompatibility`
2. Drag the folder onto the tool window
3. Check the analysis results

**Expected Results**:
- Type: TranscendenceExtension
- XML Files: 24
- API Version: 57 (Current)
- Issues: Various (will be detected by tool)

### Automated Test

Run the automated test script:
```powershell
cd Extensions\Tools
.\TestInstall.ps1
```

This will verify:
- ✓ All required files are present
- ✓ Smart detection works
- ✓ Modules load correctly

---

## File Structure

### Core Files
- `TranscendenceModTools.ps1` - Main tool script
- `TranscendenceModTools.bat` - Launcher batch file

### Module Files
- `TranscendenceModTools_Advanced.ps1` - Advanced checks
- `TranscendenceModTools_DependencyGraph.ps1` - Dependency analysis
- `TranscendenceModTools_DiffMode.ps1` - Diff comparison
- `TranscendenceModTools_Formatting.ps1` - XML formatting
- `TranscendenceModTools_LivePreview.ps1` - Live type preview
- `TranscendenceModTools_ResourceIntegrity.ps1` - Resource checking
- `TranscendenceModTools_Semantic.ps1` - Semantic validation
- `TranscendenceModTools_SmartDetect.ps1` - Smart detection
- `TranscendenceModTools_TMLStaticAnalysis.ps1` - TML analysis
- `TranscendenceModTools_UNIDIntelligence.ps1` - UNID intelligence

### Documentation
- `INSTALL_GUIDE.md` - This file
- `QUICK_REFERENCE.md` - Quick usage guide
- `FEATURES.md` - Complete feature list
- `CHANGELOG.md` - Version history
- Various feature-specific guides

---

## Troubleshooting

### Error: "Execution policy prevents running scripts"

**Solution**: Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "Cannot find path"

**Solution**: 
- Make sure all `.ps1` files are in the `Tools` folder
- Check that the batch file is in the same folder as the PowerShell script

### Error: "PowerShell not found"

**Solution**:
- Windows 10/11 includes PowerShell 5.1
- If missing, install PowerShell 7 from Microsoft

### Tool Opens But Shows Errors

**Solution**:
- Check that all module files (`.ps1`) are present
- Make sure you have .NET Framework 4.7.2+
- Try running from PowerShell directly to see detailed errors

### Drag-and-Drop Not Working

**Solution**:
- Make sure you're dragging onto the main window (not a tab)
- Try clicking "Browse..." button instead
- Check Windows permissions

### VS Code Integration Not Working

**Solution**:
- Install VS Code
- Add VS Code to your PATH
- Or manually set the path in the tool code

---

## Updating the Tool

### Method 1: Replace Files
1. Backup your settings (if any)
2. Replace all `.ps1` and `.bat` files
3. Keep your documentation if customized

### Method 2: Git (If Using)
```bash
cd Extensions/Tools
git pull
```

---

## Uninstallation

Simply delete the `Tools` folder:
```
Extensions\Tools\  ← Delete this folder
```

No registry entries or system files are modified.

---

## Advanced Configuration

### Custom Paths

Edit `TranscendenceModTools.bat` to change paths:
```batch
set SCRIPT_DIR=%~dp0
set TOOL_SCRIPT=%SCRIPT_DIR%TranscendenceModTools.ps1
```

### PowerShell Version

Force PowerShell 7:
```batch
pwsh -NoProfile -ExecutionPolicy Bypass -File "%TOOL_SCRIPT%"
```

Force PowerShell 5.1:
```batch
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOL_SCRIPT%"
```

---

## Getting Help

### Documentation
- `QUICK_REFERENCE.md` - Quick start guide
- `FEATURES.md` - Complete feature list
- Feature-specific guides (e.g., `DRAG_DROP_GUIDE.md`)

### Common Issues
- Check `Troubleshooting` section above
- Review error messages in the tool
- Check PowerShell execution policy

---

## System Compatibility

### Tested On
- ✅ Windows 10 (21H2, 22H2)
- ✅ Windows 11 (22H2, 23H2)
- ✅ PowerShell 5.1
- ✅ PowerShell 7.0+
- ✅ .NET Framework 4.7.2+

### Not Tested
- ❌ Windows 7/8.1 (should work but untested)
- ❌ Linux/Mac (PowerShell Core may work)
- ❌ Windows Server (should work)

---

## Next Steps

After installation:

1. **Read** `QUICK_REFERENCE.md` for basic usage
2. **Try** dragging a mod folder onto the tool
3. **Explore** the different tabs and features
4. **Read** feature-specific guides for advanced usage

---

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the documentation
3. Check the CHANGELOG for known issues
4. Review error messages carefully

---

**Version**: 4.9  
**Last Updated**: 2024  
**Compatible With**: Transcendence 2.0+ (API 57)

