# Auto-Update Module for API Changes

## Overview

The Auto-Update module automatically updates mods to new API versions by:
- **Detecting deprecated functions/tags/attributes**
- **Auto-fixing with known replacements**
- **Updating apiVersion attributes**
- **Generating reports for manual fixes**

## Quick Start

### Update a Single Mod

```powershell
.\UpdateModToApi.ps1 -ModPath "..\1237_UpgradedWingmen"
```

### Dry Run (Preview Changes)

```powershell
.\UpdateModToApi.ps1 -ModPath "..\YourMod" -DryRun
```

### Update All Mods

```powershell
.\UpdateModToApi.ps1 -AllMods -Backup
```

## What Gets Auto-Fixed

### ✅ Auto-Fixable

- **apiVersion updates** - Updates `apiVersion="57"` to target version
- **Missing apiVersion** - Adds `apiVersion` attribute if missing
- **Deprecated functions** - Replaces with known replacements:
  - `shpGetArmor` → `objGetArmorType`
  - `objGetArmor` → `objGetArmorType`
  - `objArmorGetHitPoints` → `objGetArmorDamage`
  - `itmGetDamageType` → `itmGetTypeData`
  - `typGet` → `typGetData`

### ⚠️ Manual Fix Required

- **Deprecated tags** - Need manual replacement
- **Deprecated attributes** - Need manual removal/replacement
- **Unknown deprecated functions** - No replacement available

## Examples

### Example 1: Update Single Mod

```powershell
PS> .\UpdateModToApi.ps1 -ModPath "..\MyMod" -Backup

Using auto-detected API version: 57

Auto-Updating Mod to API 57
Mod: D:\...\MyMod

Scanning for API issues...
Found 3 issue(s)

DeprecatedFunction (2):
  Auto-fixable: 2
OutdatedApiVersion (1):
  Auto-fixable: 1

Backup created: Backups\MyMod_20251224_174350

Updated: MyMod.xml

═══════════════════════════════════════════════════════════
  UPDATE SUMMARY
═══════════════════════════════════════════════════════════

Files Updated: 1
Total Issues:  3
Auto-Fixed:    3
Manual Fix:    0
```

### Example 2: Preview Changes

```powershell
PS> .\UpdateModToApi.ps1 -ModPath "..\MyMod" -DryRun

Would fix:
  MyMod.xml:1 - Deprecated function: (shpGetArmor)
  MyMod.xml:5 - apiVersion is 54, should be 57
```

## Integration with Main Tool

The auto-update module integrates with the main tool:

1. **API rules auto-update** when source changes
2. **Deprecation detection** during scans
3. **Migration suggestions** in scan results

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│              API RULES (api_rules.json)                 │
│  - Deprecated functions/tags/attributes                 │
│  - Function replacements                                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           SCAN MOD FOR API ISSUES                        │
│  - Find deprecated functions                              │
│  - Check apiVersion                                       │
│  - Detect deprecated tags/attributes                      │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           AUTO-FIX APPLICABLE ISSUES                     │
│  - Replace deprecated functions                          │
│  - Update apiVersion                                     │
│  - Create backup                                          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│           GENERATE REPORT                                │
│  - Show what was fixed                                   │
│  - List manual fixes needed                              │
└─────────────────────────────────────────────────────────┘
```

## Backup Safety

Always use `-Backup` flag to create backups:

```powershell
.\UpdateModToApi.ps1 -ModPath "..\MyMod" -Backup
```

Backups are saved to: `Tools\Backups\ModName_YYYYMMDD_HHMMSS\`

## Adding New Replacements

Edit `TranscendenceModTools_AutoUpdate.ps1` and add to the `$replacements` hashtable:

```powershell
$replacements = @{
    'oldFunction' = 'newFunction'
    'anotherOld' = 'anotherNew'
}
```

## Future Enhancements

- [ ] Auto-detect replacements from API rules
- [ ] Context-aware replacements (handle argument changes)
- [ ] Batch update with progress tracking
- [ ] Rollback functionality
- [ ] Integration with migration safety tools

