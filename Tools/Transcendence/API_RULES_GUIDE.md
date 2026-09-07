# Self-Updating API Rules System

## Overview

The Transcendence Mod Tools now include a **self-updating API rules engine** that:

## Supported API Versions

| Version | Description | Status |
|---------|-------------|--------|
| **API 19** | Transcendence 1.9.4 | **Steam Release** - Stable branch |
| **API 57** | Transcendence 2.0.7 | **Default** - 2.x dev, last with forum function docs |
| **API 59** | 2.x dev | Latest source (2 versions ahead of 57) |

The tool defaults to API 57 since that's the last version with function documentation posted on the forums. Use API 19 if you're targeting the stable Steam release.

### API 59 Additions (vs API 57)

**New Tags:**
- `WMD`
- `InternalDeviceDamageMaxLevels`
- `DamageMethodAdj`
- `ExternalDeviceDamageMaxLevels`

**New Functions:**
- `casualtiesIn`
- `failureIn`
- `bestCurrency`
- `displayCurrency`

---

## How It Works

The Transcendence Mod Tools include a **self-updating API rules engine** that:

1. **Watches the game's source folders** for changes
2. **Automatically extracts** all tags, attributes, events, functions, and entities
3. **Generates a comprehensive ruleset** (`api_rules.json`)
4. **Validates mods** against the current API

This means your tools stay aligned with the latest Transcendence API **without manual updates**.

## Quick Start

### Generate API Rules

```powershell
cd Extensions\Tools
.\GenerateApiRules.ps1
```

This scans the game source and creates `api_rules.json` (~1.5 MB).

### Validate a Mod

```powershell
.\ValidateModAgainstApi.ps1 -ModPath "..\1237_UpgradedWingmen"
```

### Start Live Watcher

```powershell
. .\TranscendenceModTools_SourceWatcher.ps1
Start-SourceWatcher -AutoUpdate
```

The watcher monitors source folders and regenerates rules when files change.

## What Gets Extracted

| Category | Count | Description |
|----------|-------|-------------|
| **Tags** | ~1,000+ | All XML element names used in the game |
| **Attributes** | ~1,300+ | Attribute patterns per tag |
| **Events** | ~225+ | OnCreate, OnDestroy, etc. |
| **Functions** | ~2,300+ | TLisp function calls |
| **Entities** | ~2,900+ | Entity definitions (UNIDs, resources) |
| **Semantic Rules** | ~130+ | What attributes tags typically require |

## Source Paths

The tool looks for source in these locations:

1. `game and dlc source\TranscendenceDev-integration-API57\Transcendence\TransCore`
2. `game and dlc source\Transcendence_Source`

You can customize these in the scripts or pass `-SourcePaths` parameters.

## API Rules File Structure

```json
{
  "Version": "1.0",
  "GeneratedAt": "2025-12-24 17:26:29",
  "ApiVersion": 57,
  
  "Tags": {
    "ShipClass": { "Count": 500, "Attributes": {...} },
    "ItemType": { "Count": 1200, "Attributes": {...} }
  },
  
  "Events": {
    "OnCreate": { "Count": 800, "Files": [...] },
    "OnDestroy": { "Count": 400, "Files": [...] }
  },
  
  "Functions": {
    "objGetData": { "Count": 2000, "Files": [...] },
    "itmGetType": { "Count": 500, "Files": [...] }
  },
  
  "Entities": {
    "unidHumanSpaceLibrary": { "Value": "0x00100000", "DefinedIn": "..." }
  },
  
  "Deprecated": {
    "Tags": ["obsoleteVersion"],
    "Functions": ["objGetArmor", "shpGetArmor"],
    "Attributes": { "ItemType": ["massBonusPerCharge"] }
  },
  
  "SemanticRules": {
    "ShipClass": {
      "RequiredAttributes": ["UNID", "class"],
      "RecommendedAttributes": ["name", "attributes"]
    }
  }
}
```

## Integration with Main Tool

The API rules are automatically loaded by:

- **TranscendenceModTools.ps1** - GUI validation
- **FixMod.ps1** - Auto-fix scripts
- **ProcessModsFor207.ps1** - Batch processing

## Modules

| Module | Purpose |
|--------|---------|
| `TranscendenceModTools_ApiRules.ps1` | Core extraction and rule generation |
| `TranscendenceModTools_SourceWatcher.ps1` | FileSystemWatcher for live updates |
| `GenerateApiRules.ps1` | CLI to regenerate rules |
| `ValidateModAgainstApi.ps1` | CLI to validate a mod |

## Benefits

✅ **Zero manual maintenance** - Rules update when the game updates  
✅ **Future-proof** - New tags/functions are automatically recognized  
✅ **AI-friendly** - Migration assistants always have the latest rules  
✅ **Modder-friendly** - No waiting for tool updates  
✅ **Extensible** - Add custom rule packs for your own mods  

## Detecting API Changes

```powershell
. .\TranscendenceModTools_SourceWatcher.ps1
Get-SourceChanges
```

This compares the current source against stored rules to show:

- New tags added
- Tags removed
- New functions
- Deprecated functions

## Customization

### Add Custom Deprecated Items

Edit `TranscendenceModTools_ApiRules.ps1` and modify:

```powershell
$knownDeprecatedTags = @(
    'obsoleteVersion',
    'myCustomDeprecatedTag'
)

$knownDeprecatedFunctions = @(
    'objGetArmor',
    'myCustomDeprecatedFunc'
)
```

### Add Custom Semantic Rules

```powershell
$rules['MyCustomType'] = @{
    RequiredAttributes = @('UNID', 'myAttr')
    RecommendedAttributes = @('name', 'level')
}
```

## Troubleshooting

**"API rules file not found"**
→ Run `.\GenerateApiRules.ps1` first

**"Source path not found"**
→ Check that the game source is extracted to the expected location

**Rules seem outdated**
→ Run `.\GenerateApiRules.ps1` to regenerate

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE FOLDERS                            │
│  (TransCore/*.xml, Transcendence_Source/*.xml)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              TranscendenceModTools_ApiRules.ps1              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ Tag Extractor│ │Event Extract │ │Func Extractor│         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │Entity Extract│ │Deprec Detect │ │Semantic Gen  │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      api_rules.json                          │
│  (Tags, Events, Functions, Entities, Deprecated, Semantic)  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  VALIDATION & MIGRATION                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │ ValidateMod  │ │ AutoScan     │ │ Migration    │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Future Enhancements

- [ ] Parse FunctionReference.txt for official function docs
- [ ] Extract attribute value constraints (enums, ranges)
- [ ] Generate TypeScript/JSON Schema for IDE support
- [ ] Web dashboard for browsing the API
- [ ] Automatic deprecation detection from changelogs

