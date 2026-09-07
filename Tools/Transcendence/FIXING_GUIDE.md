# Fixing 2.0.7 Update Errors - Complete Guide

## Overview

After running `UpdateModsTo207.ps1`, you may have errors that need manual fixing. This guide explains how to fix each type of error.

## Automatic Fixes Available

### 1. Invalid XML Comments (Auto-fixable)

**Script:** `FixUpdate207Errors.ps1`

**What it fixes:**
- Comments containing `--` (e.g., `<!-- Comment -- text -->`)
- Comments ending with `--` (e.g., `<!--	--`)
- Comments ending with `-` before `-->`

**Usage:**
```powershell
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_YYYYMMDD_HHMMSS.txt"
```

**Dry run first:**
```powershell
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_YYYYMMDD_HHMMSS.txt" -DryRun
```

## Manual Fixes Required

### 1. Undeclared Entity References (Most Common - 500+ files)

**Error:** `Reference to undeclared entity 'entityName'`

**Cause:** The file uses an entity (like `&svCommonwealth;`) but doesn't have a DOCTYPE declaration defining it.

**Fix Options:**

#### Option A: Add DOCTYPE Declaration
If the entity should be defined in this file:

1. Open the XML file
2. Find the line with the error (e.g., Line 47, position 20)
3. Add a DOCTYPE declaration after `<?xml version="1.0" ?>`:

```xml
<?xml version="1.0" ?>
<!DOCTYPE TranscendenceExtension [
    <!ENTITY svCommonwealth "0x00008001">
    <!ENTITY rsItems1 "0x00004001">
    <!-- Add other entities here -->
]>
<TranscendenceExtension ...>
```

#### Option B: Check Library Dependencies
If the entity is defined in a library file:

1. Check if the mod includes a library (e.g., `TranscendenceLibrary`)
2. Ensure the library is loaded before this file
3. The entity should be defined in the library's DOCTYPE

#### Option C: Replace with Direct Value
If you know the UNID value:

Replace:
```xml
<StationType UNID="&svCommonwealth;">
```

With:
```xml
<StationType UNID="0x00008001">
```

**Common Entities:**
- `svCommonwealth` = `0x00008001` (Commonwealth sovereign)
- `rsItems1` = Various resource IDs (check game files)
- `dsCargohold` = Dockscreen ID (check mod files)
- `tbSystemMorphologies` = Table ID (check library files)

### 2. Missing DTD Markup

**Error:** `Expected DTD markup was not found`

**Cause:** File uses entity references but has no DOCTYPE declaration.

**Fix:** Add DOCTYPE declaration as shown in "Undeclared Entity References" above.

### 3. Invalid Characters

**Error:** `Name cannot begin with the '#' character`

**Example:** `1365_VCantHeliotropeGunship\VcantHeliotrope.xml` (Line 32)

**Fix:**
1. Open the file at the specified line
2. Find the `#` character
3. Remove it or replace with valid XML (e.g., `&num;` if needed as text)

### 4. Data at Root Level

**Error:** `Data at the root level is invalid`

**Example:** `1606_IdentifyBeforeBuyingandSellingV2\IdentifyBeforeBuyingOrSelling.xml` (Line 9)

**Fix:**
1. Open the file
2. Check line 9 - there's likely text or XML outside the root element
3. Move the content inside the root `<TranscendenceExtension>` or `<TranscendenceModule>` tag
4. Or remove invalid content

### 5. Module Files Without apiVersion

**Error:** `Module File - No apiVersion`

**Files:**
- `StarGenesis_Source\StarGenesis.xml`
- `StarNetwork_Source\StarNetwork.xml`

**Fix:**
1. Check if these files are included by a main extension
2. If standalone, add `apiVersion="57"` to the root element:
   ```xml
   <TranscendenceModule apiVersion="57">
   ```

## Step-by-Step Fixing Process

### Step 1: Fix Auto-fixable Issues
```powershell
cd "D:\games\Steam\steamapps\common\Transcendence\Extensions\Tools"
.\FixUpdate207Errors.ps1 -ErrorLogFile "update_207_errors_YYYYMMDD_HHMMSS.txt"
```

### Step 2: Prioritize Your Mods
1. Open the error log: `update_207_errors_YYYYMMDD_HHMMSS.txt`
2. Find mods you actually use
3. Focus on those first

### Step 3: Fix Undeclared Entities
For each mod:
1. Open the main XML file
2. Check what entities it uses
3. Add DOCTYPE with entity definitions OR
4. Check if entities are in a library file

### Step 4: Test After Fixing
1. Load the mod in-game
2. Check for errors in the game log
3. Verify functionality works

### Step 5: Re-run Update Script
After fixing errors, you can re-run:
```powershell
.\UpdateModsTo207.ps1
```
It will skip already-updated files and catch any remaining issues.

## Tools to Help

### XML Checker
```powershell
.\TranscendenceModTools.ps1
```
- Use "XML Checker" tab
- Browse to your mod folder
- Click "Scan"
- Double-click errors to open in editor

### Error Helper
```powershell
.\TranscendenceModTools.ps1
```
- Use "Error Helper" tab
- Paste error messages from game
- Get diagnosis and solutions

## Common Entity Definitions

If you need to add entities, here are some common ones:

```xml
<!DOCTYPE TranscendenceExtension [
    <!-- Sovereigns -->
    <!ENTITY svCommonwealth "0x00008001">
    <!ENTITY svFriendly "0x00008002">
    <!ENTITY svEnemy "0x00008003">
    
    <!-- Resources (check game files for actual IDs) -->
    <!ENTITY rsItems1 "0x00004001">
    
    <!-- Dockscreens (check mod files) -->
    <!ENTITY dsCargohold "0x...">
    
    <!-- Tables (check library files) -->
    <!ENTITY tbSystemMorphologies "0x...">
]>
```

## Tips

1. **Backup First:** All files are backed up with `.backup` extension
2. **Fix One Mod at a Time:** Easier to track what you've done
3. **Test Incrementally:** Test after fixing each mod
4. **Check Dependencies:** Many entities come from library files
5. **Use Search:** Search for entity definitions in other mod files

## When to Give Up

Some mods may be:
- Too old to update easily
- Have too many dependencies
- Require complete rewrite

In these cases:
- Check if there's an updated version available
- Consider if the mod is essential
- May need to contact mod author

## Getting Help

1. Check the error log for specific line numbers
2. Use TranscendenceModTools to scan individual files
3. Check mod documentation/readme
4. Look for similar mods to see how they handle entities
5. Check game XML files for entity definitions

