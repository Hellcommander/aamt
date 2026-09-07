# Workflow: Using Transcendence Mod Tools for 2.0.7 Compatibility

## Overview

The Transcendence Mod Tools are designed to **fix errors, warnings, and format XML files**, which in turn helps mods be compatible with Transcendence 2.0.7. This guide shows the proper workflow.

## Understanding the Tools

Based on the CHANGELOG, the tools provide:

### Core Capabilities
- ✅ **Error Detection & Fixing** - XML syntax errors, BOM, invalid symbols
- ✅ **Warning Detection** - Deprecated attributes, missing resources, unused UNIDs
- ✅ **XML Formatting** - Format to 2.0.7 style (Version 3.2+)
- ✅ **Semantic Validation** - Type references, inheritance, event flow
- ✅ **Resource Validation** - Missing images, sounds, invalid formats
- ✅ **UNID Management** - Duplicate detection, conflict checking

### What They Do NOT Do
- ❌ They do NOT automatically update `apiVersion` attributes
- ❌ They do NOT change mod functionality
- ❌ They do NOT add missing DOCTYPE declarations

### What They DO
- ✅ Fix XML syntax errors (BOM, invalid comments, etc.)
- ✅ Format XML to 2.0.7 style (tabs, alignment)
- ✅ Detect deprecated API usage
- ✅ Validate type references
- ✅ Check resource integrity

## Recommended Workflow

### Step 1: Scan Your Mod

**Using GUI:**
1. Run `TranscendenceModTools.bat`
2. Go to **XML Checker** tab
3. Browse to your mod folder
4. Click **Scan**

**Using Command Line:**
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
pwsh -File TranscendenceModTools.ps1 -AutoScan -Path "..\YourModName"
```

### Step 2: Review Issues

The scan will show:
- **Errors** (red) - Must fix
- **Warnings** (yellow) - Should fix
- **Info** (blue) - Nice to fix

**Common Issues:**
- BOM_DETECTED - UTF-8 BOM (auto-fixable)
- INVALID_SYMBOL_SYNTAX - Trailing quote in symbols (auto-fixable)
- RAW_GT_IN_CONTENT - Raw `>` character (may need manual fix)
- XML_WELLFORMED_ERROR - XML parsing errors (manual fix)
- Missing resources - Missing image/sound files
- Deprecated attributes - Old API usage

### Step 3: Auto-Fix Issues

**Using GUI:**
1. After scanning, click **Auto-Fix** button
2. Review what was fixed
3. Check `.bak` backup files created

**Using Script:**
```powershell
.\FixMod.ps1 -ModPath "..\YourModName"
```

This fixes:
- UTF-8 BOM removal
- Invalid symbol syntax
- Some other auto-fixable issues

### Step 4: Format XML Files

**Using GUI:**
1. Go to **XML Checker** tab
2. After scanning, click **Format** button
3. Files will be formatted to 2.0.7 style

**What Formatting Does (Version 3.2+):**
- Normalizes indentation (tabs)
- Aligns attributes
- Breaks long lines
- Matches Transcendence 2.0.7 style

### Step 5: Check Project Health

**Using GUI:**
1. Go to **Project Health** tab
2. Enter mod folder path
3. Click **Generate Report**

This shows:
- Total issues breakdown
- Files with errors/warnings
- Missing resources
- Unused UNIDs
- Deprecated attributes
- Inconsistent indentation

### Step 6: Semantic Validation

**Using GUI:**
1. Go to **Semantic Validation** tab
2. Enter mod folder path
3. Click **Run Validation**

This checks:
- Missing type references
- Invalid inheritance
- Event flow issues
- Type registry completeness

### Step 7: Resource Integrity

**Using GUI:**
1. Go to **Project Health** tab
2. Click **Resource Integrity** button

This validates:
- Image files exist and match dimensions
- Sound files exist and are valid formats
- Resource entries are correct

### Step 8: Manual Fixes

After using the tools, you may still need to:

1. **Update apiVersion manually:**
   ```xml
   <TranscendenceExtension apiVersion="57" ...>
   ```

2. **Add DOCTYPE declarations:**
   ```xml
   <!DOCTYPE TranscendenceExtension [
       <!ENTITY svCommonwealth "0x00001000">
   ]>
   ```

3. **Fix entity references:**
   - Check if entities are defined in library files
   - Add missing entity definitions
   - Or replace with direct UNID values

## Batch Processing Multiple Mods

### Using the Main Tool

For each mod:
```powershell
# Scan mod
pwsh -File TranscendenceModTools.ps1 -AutoScan -Path "..\ModName1"

# Fix issues
.\FixMod.ps1 -ModPath "..\ModName1"

# Repeat for each mod
```

### Using ProcessModsFor207.ps1

The script I created (`ProcessModsFor207.ps1`) automates this:
```powershell
# Process all mods
.\ProcessModsFor207.ps1

# Process specific mod
.\ProcessModsFor207.ps1 -ModFilter "1237_*"

# Dry run first
.\ProcessModsFor207.ps1 -DryRun
```

This script:
1. Scans each mod using `TranscendenceModTools.ps1 -AutoScan`
2. Fixes issues using `FixMod.ps1`
3. Formats files using `Format-XmlFile` from formatting module

## What Gets Fixed Automatically

### By FixMod.ps1:
- ✅ UTF-8 BOM removal
- ✅ Invalid symbol syntax (`'symbol'` → `'symbol`)

### By Formatting:
- ✅ Indentation normalization (tabs)
- ✅ Attribute alignment
- ✅ Line breaking
- ✅ 2.0.7 style formatting

### By Auto-Fix in GUI:
- ✅ BOM removal
- ✅ Invalid symbols
- ✅ Some raw `>` characters (in comments)

## What Needs Manual Fixing

### XML Syntax Errors:
- Unclosed tags
- Tag mismatches
- Entity reference errors
- DOCTYPE declarations

### API Updates:
- `apiVersion` attribute (manual edit)
- Deprecated function usage (manual update)
- Deprecated attribute usage (manual update)

### Resource Issues:
- Missing image files (add files)
- Missing sound files (add files)
- Invalid file formats (convert files)

## Best Practices

1. **Always backup before running tools**
   - Tools create `.bak` files, but manual backup is safer

2. **Test after each step**
   - Scan → Review → Fix → Test
   - Don't fix everything at once

3. **Use GUI for detailed work**
   - Command line is good for batch processing
   - GUI is better for reviewing and understanding issues

4. **Check Project Health regularly**
   - Run health report before and after fixes
   - Track improvement

5. **Fix errors before warnings**
   - Errors prevent mods from loading
   - Warnings may not prevent loading

## Tools Reference

### Main Tool
- **TranscendenceModTools.ps1** - GUI tool with all features
- **TranscendenceModTools.bat** - Launcher

### Helper Scripts
- **FixMod.ps1** - Auto-fix issues
- **ScanMod.ps1** - Quick scan
- **GetXmlIssues.ps1** - Issue detection

### Modules
- **TranscendenceModTools_Formatting.ps1** - XML formatting
- **TranscendenceModTools_Advanced.ps1** - Advanced validation
- **TranscendenceModTools_Semantic.ps1** - Semantic validation
- **TranscendenceModTools_SmartDetect.ps1** - Auto-detection

## Summary

The tools help prepare mods for 2.0.7 by:
1. ✅ Fixing XML syntax errors
2. ✅ Formatting to 2.0.7 style
3. ✅ Detecting deprecated API usage
4. ✅ Validating type references
5. ✅ Checking resource integrity

You still need to manually:
- Update `apiVersion` to 57
- Add DOCTYPE declarations if needed
- Fix entity reference errors
- Update deprecated function calls

But the tools make the process much easier by handling the formatting and common errors automatically.

