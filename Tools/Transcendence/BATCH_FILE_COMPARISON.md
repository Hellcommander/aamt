# Batch File Comparison: StartSpaceWhaleAssetGeneration

## Overview

Two batch files launch the Space Whale asset generator with different interfaces and features.

## `StartSpaceWhaleAssetGeneration_WithGUI.bat`

**Purpose:** Launches the **GUI-based generator** with a Windows Forms progress window.

### Features:
- ✅ **Simple GUI Window** - Windows Forms progress bar and status text
- ✅ **Real-time Progress** - Shows progress bar and task status
- ✅ **Task Logs** - Displays output from each generation task
- ✅ **Minimal Setup** - Just launches the GUI script
- ✅ **User-Friendly** - Visual feedback during generation

### What It Does:
1. Sets basic configuration (Ship ID, Output Directory)
2. Launches `SpaceWhaleAssetGeneratorGUI.ps1` (Windows Forms GUI)
3. Shows progress window with:
   - Progress bar (0-100%)
   - Status text (current task)
   - Log output (real-time)
   - Close button (enabled when complete)

### Configuration:
- `SHIP_ID=leviathan_alpha`
- `OUTPUT_DIR=Output\SpaceWhaleAssets`
- `OLLAMA_MODEL=wizardlm-uncensored:latest` (hardcoded in GUI script)
- `VARIATIONS=150` (hardcoded in GUI script)

### Use When:
- You want a **simple progress window**
- You prefer **visual feedback** over command-line
- You don't need the Control Room Monitor
- You want a **single window** for all progress

---

## `StartSpaceWhaleAssetGeneration.bat`

**Purpose:** Launches the **comprehensive command-line generator** with optional Control Room Monitor.

### Features:
- ✅ **Control Room Monitor** - Optional WPF GUI with job cards (separate window)
- ✅ **Comprehensive Generator** - Uses `space_whale_comprehensive_asset_generator.py`
- ✅ **Pre-flight Checks** - Verifies Python and Ollama availability
- ✅ **Configurable** - Model selection, variations, monitor toggle
- ✅ **Fallback Options** - Multiple generator script options
- ✅ **Detailed Output** - Command-line progress and logs

### What It Does:
1. **Checks Prerequisites:**
   - Verifies Python is installed
   - Checks if Ollama is running
   - Creates output directory

2. **Launches Control Room Monitor** (if `USE_MONITOR=1`):
   - Separate WPF window
   - Shows job cards for each task type
   - Real-time file watching
   - Image previews
   - Progress bars per job

3. **Launches Comprehensive Generator:**
   - Runs `space_whale_comprehensive_asset_generator.py`
   - Multithreaded generation (up to 32 cores)
   - Command-line output
   - Fallback to PowerShell script if Python script not found

### Configuration:
- `SHIP_ID=leviathan_alpha`
- `OUTPUT_DIR=Output\SpaceWhaleAssets`
- `OLLAMA_MODEL=` (empty = auto-detect via dual-model router)
- `VARIATIONS=150`
- `USE_MONITOR=1` (enable/disable Control Room Monitor)

### Use When:
- You want the **Control Room Monitor** (separate monitoring window)
- You need **configurable model selection** (auto-detect or manual)
- You want **comprehensive command-line output**
- You need **pre-flight checks** (Python/Ollama verification)
- You prefer **separate windows** for monitoring and generation

---

## Key Differences

| Feature | WithGUI.bat | StartSpaceWhaleAssetGeneration.bat |
|---------|------------|-----------------------------------|
| **Interface** | Windows Forms (single window) | Command-line + Optional WPF Monitor |
| **Progress Display** | Progress bar in main window | Command-line + Job cards in monitor |
| **Model Selection** | Hardcoded (wizardlm-uncensored) | Auto-detect or configurable |
| **Pre-flight Checks** | None | Python + Ollama verification |
| **Monitor Window** | No | Yes (optional, separate WPF window) |
| **Image Previews** | No | Yes (in Control Room Monitor) |
| **File Watching** | No | Yes (in Control Room Monitor) |
| **Generator Script** | `SpaceWhaleAssetGeneratorGUI.ps1` | `space_whale_comprehensive_asset_generator.py` |
| **Complexity** | Simple | More comprehensive |
| **Configuration** | Minimal | Extensive |

---

## Which One Should You Use?

### Use `StartSpaceWhaleAssetGeneration_WithGUI.bat` if:
- ✅ You want a **simple, single-window** progress display
- ✅ You don't need the Control Room Monitor features
- ✅ You prefer **Windows Forms** over command-line
- ✅ You want **quick launch** without configuration

### Use `StartSpaceWhaleAssetGeneration.bat` if:
- ✅ You want the **Control Room Monitor** with job cards
- ✅ You need **image previews** and file watching
- ✅ You want **configurable model selection** (dual-model router)
- ✅ You need **pre-flight checks** (Python/Ollama verification)
- ✅ You prefer **command-line output** with optional GUI monitoring

---

## Visual Comparison

### WithGUI.bat:
```
┌─────────────────────────────────────┐
│ Space Whale Asset Generator        │
│ Progress: 50%                       │
│ [████████████░░░░░░░░]              │
│                                     │
│ [1/6] Starting: Visual Language... │
│   Running: python ...              │
│   ✓ Visual Language complete!      │
│                                     │
│ [2/6] Starting: FX Assets...         │
│   ...                               │
│                                     │
│ [Close]                             │
└─────────────────────────────────────┘
```

### StartSpaceWhaleAssetGeneration.bat:
```
Command Window:
[1/2] Launching Control Room Monitor...
[2/2] Starting Comprehensive Asset Generation...
  Running: python space_whale_comprehensive_asset_generator.py
  ...

+ Separate Control Room Monitor Window:
┌─────────────────────────────────────┐
│ Space Whale Asset Generator         │
│ ┌─────────────────────────────────┐ │
│ │ Visual Language                 │ │
│ │ [████████░░░░] 80%              │ │
│ │ Preview: [image]                │ │
│ │ Logs: ...                       │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ FX Assets                       │ │
│ │ [██████████] 100%               │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## Summary

- **WithGUI.bat** = Simple, single-window GUI with progress bar
- **StartSpaceWhaleAssetGeneration.bat** = Comprehensive setup with optional Control Room Monitor, pre-flight checks, and configurable options

Both generate the same assets, but provide different user experiences and monitoring capabilities.

