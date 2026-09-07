# Smart Drag-and-Drop with Auto-Detection - User Guide

## Overview

Drag and drop files or folders directly onto the tool window for instant smart analysis. The tool automatically detects the content type and suggests the best actions.

## How to Use

### Step 1: Drag
Drag any of these onto the tool window:
- Single XML file
- Mod folder
- Multiple files
- Resource files (images, sounds)

### Step 2: View Analysis
The Smart Detection dialog shows:
- Mod name and type
- API version status
- Health score (0-100)
- Issue summary
- Recommended actions

### Step 3: Choose Action
Click a recommended action button:
- **Quick Validate** - Run XML/TLisp checks
- **Fix Errors** - Auto-fix detected issues
- **Full Health Report** - Comprehensive analysis
- **Dependency Graph** - Visualize relationships
- **Check Deprecated API** - Find outdated functions

Or click "Skip to Normal Menu" to browse manually.

## Smart Detection Features

### 1. File Type Detection
Automatically identifies:
- **TranscendenceExtension** - Main mod file
- **TranscendenceLibrary** - Shared library
- **TranscendenceModule** - Module file
- **ModFolder** - Folder with XML files
- **ImageFile** - PNG, JPG, BMP
- **SoundFile** - WAV, MP3, OGG

### 2. API Version Check
Detects API version and status:

| API | Status | Icon |
|-----|--------|------|
| 57 | Current | ✅ |
| 56 | Outdated | ⚠ |
| 55 | Outdated | ⚠ |
| 50-54 | Legacy | ⚠ |
| 20-25 | Ancient | ❌ |

### 3. Issue Detection
Automatically scans for:
- UTF-8 BOM (parsing issues)
- Raw `>` characters (should be `&gt;`)
- Parentheses mismatch
- Invalid symbol syntax
- Deprecated functions
- xmlCreate with raw tags

### 4. Health Score
Quality score from 0-100:

**Score Calculation**:
- Start at 100
- -15 per error
- -5 per warning
- -1 per info
- -10 for outdated API
- -25 for legacy API
- -50 for ancient API

**Color Coding**:
- 🟢 80-100: Healthy
- 🟡 50-79: Needs attention
- 🔴 0-49: Requires fixes

### 5. Deprecated Function Detection
Detects deprecated API 57 functions:

| Old Function | New Function |
|--------------|--------------|
| objAddItem | objAddItemByValue |
| objRemoveItem | objRemoveItemByValue |
| shpOrder | objSendMessage |
| sysCreateWeaponFire | objFireWeapon |
| itmGetArmorType | itmGetArmorClass |
| rollDice | mathRandom |

## Recommended Actions

### For Single XML Files
1. **Quick Validate** - Run XML/TLisp checks
2. **Fix Errors** - Auto-fix if errors found
3. **Review Warnings** - Check warnings

### For Mod Folders
1. **Quick Validate** - Run all checks
2. **Full Health Report** - Comprehensive analysis
3. **Dependency Graph** - Visualize relationships
4. **Cross-Mod Compatibility** - Check UNID conflicts
5. **Check Deprecated API** - Semantic validation

### For Outdated API Mods
1. **Check Deprecated API** - Find old functions
2. **Semantic Validation** - Full type checking

## Smart Detection Dialog

### Header Section
- **Mod Name** - From `name` attribute
- **Type** - Extension, Library, Module, etc.
- **File Count** - XML and resource files

### API Status
- Shows API version number
- Color-coded status indicator
- Action suggestion if outdated

### Health Score
- Large, color-coded score
- 100 = perfect, 0 = critical issues

### Issue Summary
- Error count (red)
- Warning count (orange)
- Quick overview of problems

### Action Buttons
- One click to run action
- Automatically navigates to correct tab
- Shows action description

### Bottom Buttons
- **Skip to Normal Menu** - Cancel and browse manually
- **Show Full Report** - Detailed analysis text

## Tips

### Best Practices
1. Drop entire mod folder for best analysis
2. Check health score before publishing
3. Fix errors before warnings
4. Update deprecated functions

### Common Issues
- **BOM detected**: Remove UTF-8 BOM from files
- **Raw `>`**: Replace with `&gt;` in content
- **Parentheses mismatch**: Check TLisp code
- **Deprecated functions**: Update to new API

### Workflow
1. Drop mod folder
2. Check health score
3. Click "Quick Validate" if score < 100
4. Fix errors
5. Click "Full Health Report" for details

## Keyboard Shortcuts

- **ESC** - Close dialog
- **Enter** - Select first action

## Supported File Types

### XML Files
- `.xml` - Transcendence XML

### Resource Files
- `.png`, `.jpg`, `.bmp` - Images
- `.wav`, `.mp3`, `.ogg` - Sounds

### Database Files
- `.tdb` - Transcendence database

---

Drag-and-drop makes mod analysis fast and intuitive!

