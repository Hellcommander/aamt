# Test Batch Files Guide

## Quick Reference

All test batch files are located in the `Tools` directory. Double-click any `.bat` file to run it.

## Available Test Files

### 1. `TestDualModelSystem.bat`
**Purpose**: Tests the dual-model routing system

**What it tests**:
- Model detection (CodeLlama-34B, WizardLM-uncensored)
- Task-based routing (code vs visual tasks)
- Dual model configuration

**Usage**: Double-click or run from command line
```batch
TestDualModelSystem.bat
```

**Expected output**: Confirms both models are detected and assigned correctly

---

### 2. `TestMinimalSpaceWhale.bat`
**Purpose**: Quick test of core functionality (under 1 minute)

**What it tests**:
- FX Assets multithreading (2 variations)
- GUI window display (WPF with visual elements)

**Usage**: Double-click or run from command line
```batch
TestMinimalSpaceWhale.bat
```

**Expected time**: ~15 seconds

---

### 3. `TestGUI.bat`
**Purpose**: Launches the Control Room Monitor GUI to verify it displays images and XML

**What it tests**:
- GUI window creation
- Image preview display
- XML content display
- Real-time updates

**Usage**: Double-click or run from command line
```batch
TestGUI.bat
```

**What to check**:
- Left panel should show image grid (when files exist)
- Right top should show XML file list
- Right bottom should show progress bars
- Bottom should show log output

**Note**: GUI will stay open until you close it manually

---

### 4. `RunAllTests.bat`
**Purpose**: Runs all tests in sequence

**What it runs**:
1. Dual Model System test
2. Minimal Space Whale test

**Usage**: Double-click or run from command line
```batch
RunAllTests.bat
```

**Expected time**: ~20 seconds total

---

### 5. `TestMinimal.bat` (Existing)
**Purpose**: Original minimal test (same as TestMinimalSpaceWhale.bat)

---

### 6. `TestSpaceWhaleGeneration.bat` (Existing)
**Purpose**: Creates a simple tiny space whale with minimal variations

**What it does**:
- Generates 5 variations per asset type (instead of 150)
- Tests all core systems
- Quick verification (~1-2 minutes)

---

## Running Tests

### From Windows Explorer
1. Navigate to `Transcendence\Tools`
2. Double-click any `.bat` file

### From Command Line
```batch
cd D:\games\Steam\steamapps\common\Transcendence\Tools
TestDualModelSystem.bat
```

### From PowerShell
```powershell
cd D:\games\Steam\steamapps\common\Transcendence\Tools
cmd /c TestDualModelSystem.bat
```

## Test Results

### Success Indicators
- ✅ `[OK]` messages in output
- ✅ "Test Passed!" message
- ✅ Exit code 0

### Failure Indicators
- ❌ `[FAIL]` or `[ERROR]` messages
- ❌ "Test Failed" message
- ❌ Exit code non-zero

## Troubleshooting

### "Python is not installed"
- Install Python 3.8+ from python.org
- Add Python to system PATH

### "Ollama models not detected"
- Ensure Ollama is running: `ollama list`
- Pull required models:
  ```bash
  ollama pull codellama:34b
  ollama pull wizardlm-uncensored:latest
  ```

### "GUI not showing images"
- Check that files exist in the output directory
- Verify GUI is watching the correct directory
- Check log output for image loading errors

## Next Steps

After all tests pass:
1. Run full asset generation: `StartSpaceWhaleAssetGeneration.bat`
2. Monitor progress: `TestGUI.bat` (in separate window)
3. Review generated assets in `Output\SpaceWhaleAssets`

