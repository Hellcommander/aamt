# Quick Start Guide - 2.0.7 Update Tools

## Overview

This toolkit helps you update Transcendence mods to version 2.0.7. It includes automatic updates and tools to help fix remaining errors.

## Quick Start (3 Steps)

### Step 1: Run the Update Script
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
.\UpdateModsTo207.ps1
```

This will:
- Update API versions to 57
- Format XML files to 2.0.7 style
- Create backups (`.backup` files)
- Generate error log

### Step 2: Fix Auto-fixable Errors
```powershell
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_YYYYMMDD_HHMMSS.txt"
```

This fixes invalid XML comments automatically.

### Step 3: Analyze Remaining Errors
```powershell
.\AnalyzeEntityErrors.ps1 -ErrorLogFile "update_207_errors_YYYYMMDD_HHMMSS.txt"
```

This creates a detailed analysis of entity errors with suggestions.

## What Each Script Does

### UpdateModsTo207.ps1
**Main update script**
- Scans all mods in Extensions folder
- Updates `apiVersion` to 57
- Formats XML to 2.0.7 style
- Creates backups
- Generates error log

**Options:**
- `-ModFilter "pattern"` - Only process matching mods
- `-DryRun` - Preview changes without applying
- `-SkipBackup` - Don't create backups (not recommended)

**Example:**
```powershell
# Update all mods
.\UpdateModsTo207.ps1

# Preview changes for one mod
.\UpdateModsTo207.ps1 -ModFilter "1237_*" -DryRun

# Update specific mod
.\UpdateModsTo207.ps1 -ModFilter "1237_*"
```

### FixUpdate207Errors.ps1
**Auto-fix helper**
- Fixes invalid XML comments (containing `--`)
- Creates additional backups (`.backup2`)

**Usage:**
```powershell
# Dry run first
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_*.txt" -DryRun

# Apply fixes
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```

### AnalyzeEntityErrors.ps1
**Entity error analyzer**
- Analyzes undeclared entity errors
- Identifies entity types
- Searches for entity definitions
- Creates detailed report

**Usage:**
```powershell
.\AnalyzeEntityErrors.ps1 -ErrorLogFile "update_207_errors_*.txt"
```

Output: `entity_analysis_YYYYMMDD_HHMMSS.txt`

## Files Created

After running the scripts, you'll have:

1. **Error Log:** `update_207_errors_YYYYMMDD_HHMMSS.txt`
   - Lists all files with errors
   - Includes line numbers and error messages

2. **Entity Analysis:** `entity_analysis_YYYYMMDD_HHMMSS.txt`
   - Detailed analysis of entity errors
   - Suggestions for fixes

3. **Backups:**
   - `.backup` - From UpdateModsTo207.ps1
   - `.backup2` - From FixUpdate207Errors.ps1

## Common Workflow

### For All Mods
```powershell
# 1. Update all mods
.\UpdateModsTo207.ps1

# 2. Fix comments
.\FixUpdate207Errors.ps1 -ErrorLogFile (Get-ChildItem update_207_errors_*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name

# 3. Analyze entities
.\AnalyzeEntityErrors.ps1 -ErrorLogFile (Get-ChildItem update_207_errors_*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name

# 4. Review reports and fix manually
```

### For One Mod
```powershell
# 1. Update specific mod
.\UpdateModsTo207.ps1 -ModFilter "YourModName*"

# 2. Check errors
notepad (Get-ChildItem update_207_errors_*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name

# 3. Fix manually using FIXING_GUIDE.md
```

## Understanding the Results

### Success Indicators
- ✅ "Mods Updated: X" - Mods successfully updated
- ✅ "API Versions Updated: X" - API versions updated
- ✅ "Files Formatted: X" - Files formatted

### Error Indicators
- ⚠️ "Errors: X" - Files with errors (need manual fix)
- ⚠️ "Errors Requiring Manual Fixing" - List of errors

### Error Types

1. **XML Parsing Error** - XML syntax issues
   - Most common: Undeclared entities
   - Fix: Add DOCTYPE or entity definitions

2. **Invalid Comment** - Comments with `--`
   - Auto-fixable with FixUpdate207Errors.ps1

3. **Missing DTD** - Files using entities without DOCTYPE
   - Fix: Add DOCTYPE declaration

## Next Steps After Running Scripts

1. **Review Error Log**
   - Open `update_207_errors_*.txt`
   - Find mods you use
   - Note error types

2. **Review Entity Analysis**
   - Open `entity_analysis_*.txt`
   - See which entities are missing
   - Check if definitions found

3. **Fix Errors**
   - Follow `FIXING_GUIDE.md`
   - Start with high-priority errors
   - Test after each fix

4. **Re-run if Needed**
   - Scripts skip already-updated files
   - Safe to run multiple times

## Getting Help

### Documentation
- `FIXING_GUIDE.md` - Detailed fixing instructions
- `UPDATE_207_ERRORS_SUMMARY.md` - Error overview
- `UPDATE_207_COMPLETE.md` - Status tracking

### Tools
- `TranscendenceModTools.ps1` - GUI tool for scanning
- `ScanMod.ps1` - Command-line scanner

### Tips
- Always backup before manual fixes
- Test mods in-game after fixing
- Focus on mods you actually use
- Many "errors" may not prevent mods from working

## Restoring Backups

If something goes wrong:

```powershell
# Restore from UpdateModsTo207.ps1 backup
Copy-Item "file.xml.backup" "file.xml" -Force

# Restore from FixUpdate207Errors.ps1 backup
Copy-Item "file.xml.backup2" "file.xml" -Force
```

## Troubleshooting

### Script Won't Run
- Check PowerShell version: `$PSVersionTable.PSVersion` (need 7+)
- Run: `pwsh -NoProfile -ExecutionPolicy Bypass -File "script.ps1"`

### Too Many Errors
- Focus on mods you actually use
- Many errors may not prevent mods from working
- Test mods in-game first

### Can't Find Entity Definitions
- Check game XML files
- Check library files mod depends on
- May need to define in DOCTYPE

## Summary

✅ **Automatic:** API updates, formatting, comment fixes  
⚠️ **Manual:** Entity definitions, DTD declarations  
📊 **Analysis:** Entity analyzer helps identify issues  
🔧 **Tools:** Multiple scripts for different tasks  

For detailed instructions, see `FIXING_GUIDE.md`.

