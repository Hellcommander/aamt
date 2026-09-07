# Transcendence 2.0.7 Update - Error Summary

**Generated:** 2025-12-24  
**Total Errors:** 611 files require manual attention

## Error Categories

### 1. Module Files - No apiVersion (2 files)
These files appear to be modules but don't have an `apiVersion` attribute:

- `StarGenesis_Source\StarGenesis.xml`
- `StarNetwork_Source\StarNetwork.xml`

**Fix:** Check if these files are included by a main extension with `apiVersion="57"`. If they're standalone, add `apiVersion="57"` to the root element.

### 2. XML Parsing Errors (609 files)

These files have XML syntax errors that prevent automatic processing. Common issues:

#### A. Undeclared Entity References (Most Common)
**Error Pattern:** `Reference to undeclared entity 'entityName'`

**Examples:**
- `svCommonwealth` - Commonwealth Police mod
- `rsItems1` - Shield generator mod
- `dsCargohold` - Cargo hold mod
- `tbSystemMorphologies` - System Density mods
- Many others...

**Fix:** 
1. Check if the entity is defined in a DOCTYPE declaration at the top of the file
2. If missing, add the entity definition:
   ```xml
   <!DOCTYPE TranscendenceExtension [
       <!ENTITY entityName "0x...">
   ]>
   ```
3. Or check if the entity is defined in a library file that should be included

#### B. Invalid XML Comments
**Error Pattern:** `An XML comment cannot contain '--', and '-' cannot be the last character`

**Examples:**
- `[0000 - 000F] Arch Globals\Arch Globals Library.xml` (Line 27)
- `[1630]_PlayershipDrones\PSDm_BaseClass.xml` (Line 12)
- `1550_ComGroups\Com Groups.xml` (Line 92)
- `1614_autominerscanner\autoMinerDevices.xml` (Line 13)

**Fix:** 
- Remove `--` from inside XML comments
- Replace with single `-` or use a different comment style
- Example: `<!-- Comment with -- inside -->` → `<!-- Comment with - inside -->`

#### C. Missing DTD Markup
**Error Pattern:** `Expected DTD markup was not found`

**Examples:**
- `[1630]_PlayershipDrones\PlayerShipDrones_Selector.xml` (Line 27)
- `[1630]_PlayershipDrones\PlayerShipDrones.xml` (Line 6)
- `1637_Network19b3\Networkdev108\Network.xml` (Line 5)

**Fix:**
- Add DOCTYPE declaration if the file uses entity references
- Or remove entity references if DOCTYPE is not needed

#### D. Invalid Characters
**Error Pattern:** `Name cannot begin with the '#' character`

**Example:**
- `1365_VCantHeliotropeGunship\VcantHeliotrope.xml` (Line 32)

**Fix:** Remove or escape the `#` character if it's not part of a valid XML construct

#### E. Data at Root Level
**Error Pattern:** `Data at the root level is invalid`

**Example:**
- `1606_IdentifyBeforeBuyingandSellingV2\IdentifyBeforeBuyingOrSelling.xml` (Line 9)

**Fix:** Ensure all content is within proper XML root element tags

## Priority Fixes

### High Priority (Common Patterns)
1. **Undeclared entities** - These will cause mods to fail loading
2. **Invalid comments** - Can cause parsing failures
3. **Missing DTD** - Required for files using entity references

### Medium Priority
- Module files without apiVersion (if standalone)
- Invalid characters

### Low Priority
- Files that may work despite warnings (verify in-game)

## How to Fix

1. **Open the error log:** `update_207_errors_20251224_165448.txt`
2. **Find your mod** in the "SUMMARY BY FILE" section
3. **Check the error type** and line number
4. **Open the file** in a text editor
5. **Apply the fix** based on the error category above
6. **Test the mod** in-game to verify it works

## Tools to Help

- Use `TranscendenceModTools.ps1` to scan individual files
- The XML Checker tab can help identify specific issues
- Error Helper tab can diagnose error messages

## Notes

- All files have been backed up with `.backup` extension
- API versions have been updated to 57 where possible
- Files have been formatted to 2.0.7 style where possible
- These errors prevent automatic processing but may not all prevent the mod from working

## Next Steps

1. Review the error log for your mods
2. Fix high-priority errors first (undeclared entities, invalid comments)
3. Test mods after fixing
4. Re-run the update script if needed (it will skip already-updated files)

