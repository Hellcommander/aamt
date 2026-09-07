# Transcendence 2.0.7 Update Toolkit

Complete toolkit for updating Transcendence mods to version 2.0.7.

## 📦 What's Included

### Scripts
1. **`UpdateModsTo207.ps1`** - Main update script
2. **`FixUpdate207Errors.ps1`** - Auto-fix invalid comments
3. **`AnalyzeEntityErrors.ps1`** - Analyze entity errors

### Documentation
1. **`QUICK_START.md`** - Quick start guide
2. **`FIXING_GUIDE.md`** - Detailed fixing instructions
3. **`UPDATE_207_ERRORS_SUMMARY.md`** - Error overview
4. **`UPDATE_207_COMPLETE.md`** - Status tracking

### Generated Files
- `update_207_errors_*.txt` - Error log
- `entity_analysis_*.txt` - Entity analysis report

## 🚀 Quick Start

```powershell
# 1. Update all mods
.\UpdateModsTo207.ps1

# 2. Fix auto-fixable errors
.\FixUpdate207Errors.ps1 -ErrorLogFile (Get-ChildItem update_207_errors_*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name

# 3. Analyze entity errors
.\AnalyzeEntityErrors.ps1 -ErrorLogFile (Get-ChildItem update_207_errors_*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name
```

## 📊 Current Status

### ✅ Completed
- **150 mods** processed
- **61 mods** fully updated automatically
- **504 API versions** updated to 57
- **504 files** formatted to 2.0.7 style
- **32 files** with invalid comments fixed

### ⚠️ Remaining
- **~578 files** need manual fixes
- **534 entity errors** (most common)
- **437 unique entities** missing

### 📈 Entity Analysis Results
The entity analyzer found that **many entities are actually defined in other files**:
- `unidCoreTypesLibrary` - Found in 2 files
- `rsItems1` - Found in 10 files
- `unidRPGLibrary` - Found in 13 files
- `svCommonwealth` - Found in 3 files
- And many more...

**This means:** Many errors can be fixed by ensuring the right files are included or by copying DOCTYPE declarations.

## 🔧 Tools Overview

### UpdateModsTo207.ps1
Main update script that:
- Scans all mods
- Updates API versions
- Formats XML files
- Creates backups
- Generates error log

**Usage:**
```powershell
.\UpdateModsTo207.ps1                    # All mods
.\UpdateModsTo207.ps1 -ModFilter "1237_*"  # Specific mod
.\UpdateModsTo207.ps1 -DryRun            # Preview
```

### FixUpdate207Errors.ps1
Auto-fixes invalid XML comments:
- Fixes comments containing `--`
- Creates additional backups

**Usage:**
```powershell
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```

### AnalyzeEntityErrors.ps1
Analyzes entity errors and:
- Identifies missing entities
- Searches for entity definitions
- Suggests fixes
- Creates detailed report

**Usage:**
```powershell
.\AnalyzeEntityErrors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```

## 📝 Error Types

### 1. Undeclared Entity References (534 errors)
**Most common issue**

**Examples:**
- `svCommonwealth` - Found in 3 files
- `rsItems1` - Found in 10 files
- `unidRPGLibrary` - Found in 13 files

**Fix:**
- Check `entity_analysis_*.txt` for found definitions
- Copy DOCTYPE from files that define the entity
- Or ensure the defining file is included

### 2. Invalid XML Comments (32 fixed)
**Auto-fixable**

Fixed automatically by `FixUpdate207Errors.ps1`.

### 3. Missing DTD Markup (~50 files)
**Files using entities without DOCTYPE**

**Fix:** Add DOCTYPE declaration (see FIXING_GUIDE.md)

### 4. Other Errors (~20 files)
- Invalid characters
- Data at root level
- Module files without apiVersion

## 🎯 Recommended Workflow

### Step 1: Run Update Script
```powershell
.\UpdateModsTo207.ps1
```
Review the summary and error count.

### Step 2: Fix Auto-fixable Errors
```powershell
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```
This fixes invalid comments automatically.

### Step 3: Analyze Entity Errors
```powershell
.\AnalyzeEntityErrors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```
Review `entity_analysis_*.txt` to see which entities are found.

### Step 4: Fix Entity Errors
For each mod you use:
1. Check `entity_analysis_*.txt` for your mod
2. If entity definitions are found, copy DOCTYPE from those files
3. If not found, check game files or library dependencies
4. Add DOCTYPE declaration (see FIXING_GUIDE.md)

### Step 5: Test
Load mods in-game and verify they work.

## 📚 Documentation

- **QUICK_START.md** - Get started quickly
- **FIXING_GUIDE.md** - Detailed fixing instructions
- **UPDATE_207_ERRORS_SUMMARY.md** - Error overview
- **UPDATE_207_COMPLETE.md** - Status tracking

## 💡 Tips

1. **Focus on mods you use** - Don't fix everything at once
2. **Check entity analysis first** - Many entities are already defined elsewhere
3. **Test in-game** - Some "errors" may not prevent mods from working
4. **Use backups** - All files are backed up (`.backup`, `.backup2`)
5. **Re-run scripts** - Safe to run multiple times (skips updated files)

## 🔍 Finding Entity Definitions

The entity analyzer searches all XML files and reports where entities are defined. Check `entity_analysis_*.txt` for:
- Which files define each entity
- The UNID values
- How many files use each entity

**Example:**
```
Entity: svCommonwealth
  Found in: 1237_UpgradedWingmen\Upgraded_Wingmen.xml = 0x00001000
  Found in: d912_FighterBay\FighterBay.xml = 0x00001000
```

You can copy the DOCTYPE from these files.

## 🛡️ Backups

All scripts create backups:
- `.backup` - From UpdateModsTo207.ps1
- `.backup2` - From FixUpdate207Errors.ps1

**Restore:**
```powershell
Copy-Item "file.xml.backup" "file.xml" -Force
```

## ❓ Getting Help

1. Check `FIXING_GUIDE.md` for detailed instructions
2. Review `entity_analysis_*.txt` for entity definitions
3. Use `TranscendenceModTools.ps1` to scan individual files
4. Check error log for specific line numbers

## 📊 Statistics

- **Total Mods:** 150
- **Successfully Updated:** 61 (41%)
- **Needs Manual Fix:** 89 (59%)
- **Total Errors:** ~578
- **Entity Errors:** 534 (92%)
- **Auto-fixed:** 32 (6%)
- **Unique Entities:** 437

## ✅ Success Criteria

A mod is successfully updated when:
- ✅ API version is 57
- ✅ File is formatted to 2.0.7 style
- ✅ No XML parsing errors
- ✅ All entities are defined
- ✅ Mod loads in-game without errors

## 🎉 Next Steps

1. Review error log for your active mods
2. Check entity analysis for found definitions
3. Fix high-priority errors first
4. Test mods after fixing
5. Re-run scripts if needed

For detailed instructions, see **FIXING_GUIDE.md**.

