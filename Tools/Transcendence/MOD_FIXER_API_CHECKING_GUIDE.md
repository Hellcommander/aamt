# Mod Fixer API Checking Guide

## Overview

The mod fixer now includes **AI-powered API compatibility checking** that validates mods against the current Transcendence API source. This ensures mods are compatible with the latest API version and helps identify deprecated functions, tags, and attributes.

## Features

- **Automatic API Detection**: Auto-detects API version from `api_rules.json` files
- **Deprecated Function Detection**: Identifies deprecated functions and suggests replacements
- **Deprecated Tag Detection**: Finds deprecated XML tags
- **Deprecated Attribute Detection**: Identifies deprecated attributes per tag
- **Unknown Element Detection**: Warns about tags/functions not in current API
- **API Version Checking**: Validates mod's declared API version
- **AI-Powered Fixes**: Uses Ollama to generate fixes based on API compatibility issues

## Quick Start

### Check API Compatibility

```bash
# Run API check before fixing
python mod_fixer.py "path/to/mod" \
  --profile transcendence \
  --check-api \
  --issue "API compatibility issues" \
  --template fix_api_compatibility
```

### Standalone API Checker

```bash
# Check mod against API (standalone tool)
python mod_fixer_api_checker.py "path/to/mod"

# Output JSON report
python mod_fixer_api_checker.py "path/to/mod" --output api_report.json --format json
```

## API Rules Files

The system uses `api_rules.json` files that are generated from the Transcendence source:

- `api_rules_59.json` - API 59 (latest)
- `api_rules_58.json` - API 58
- `api_rules_57.json` - API 57
- `api_rules_56.json` - API 56
- `api_rules.json` - Default (usually latest)

The checker auto-detects the highest available version.

## What Gets Checked

### 1. API Version

Checks if mod declares correct API version:

```xml
<!-- Good -->
<TranscendenceExtension apiVersion="59">

<!-- Warning: Outdated -->
<TranscendenceExtension apiVersion="53">

<!-- Info: Missing -->
<TranscendenceExtension>
```

### 2. Deprecated Functions

Detects deprecated function calls:

```xml
<!-- Deprecated -->
(objGetArmor gSource)

<!-- Should use -->
(objGetArmorLevel gSource)
```

### 3. Deprecated Tags

Finds deprecated XML tags:

```xml
<!-- Deprecated -->
<obsoleteVersion>...</obsoleteVersion>
```

### 4. Deprecated Attributes

Identifies deprecated attributes:

```xml
<!-- Deprecated attribute -->
<ItemType massBonusPerCharge="10">

<!-- Should remove or replace -->
<ItemType>
```

### 5. Unknown Elements

Warns about tags/functions not in current API:

```xml
<!-- Unknown tag -->
<CustomTag>...</CustomTag>

<!-- Unknown function -->
(customFunction arg1 arg2)
```

## Integration with Mod Fixer

The API checker is automatically integrated into the mod fixer for Transcendence mods:

1. **Automatic Context**: API issues are included in fix generation context
2. **Template Support**: `fix_api_compatibility` template for comprehensive fixes
3. **Pre-fix Validation**: Use `--check-api` to validate before fixing

### Example Workflow

```bash
# 1. Check API compatibility
python mod_fixer.py "path/to/mod" --profile transcendence --check-api

# 2. Fix API issues
python mod_fixer.py "path/to/mod" \
  --profile transcendence \
  --issue "API compatibility issues" \
  --template fix_api_compatibility \
  --check-api

# 3. Review and apply
python mod_fixer.py "path/to/mod" \
  --profile transcendence \
  --issue "API compatibility issues" \
  --template fix_api_compatibility \
  --apply
```

## Common API Migration Patterns

### Register Function (API 53 → 57+)

**Old:**
```xml
(register gSource)
```

**New:**
```xml
(register gSource Registrar)
```

### objDestroy Function (API 53 → 57+)

**Old:**
```xml
(objDestroy targetObj)
```

**New:**
```xml
(objDestroy targetObj objSource)
```

### FinalRender Function (API 53 → 57+)

**Old:**
```xml
(FinalRender event true)
```

**New:**
```xml
(FinalRender event)
```

### API Version Update

**Old:**
```xml
<TranscendenceExtension apiVersion="53">
```

**New:**
```xml
<TranscendenceExtension apiVersion="59">
```

## API Checker Output

### Text Format

```
API COMPATIBILITY REPORT
============================================================
API Version: 59
Total Issues: 15
  Errors: 3
  Warnings: 8
  Info: 4

MyMod.xml:
  ✗ [DEPRECATED_FUNCTION] (line 45): Deprecated function 'objGetArmor' used
    → Replace 'objGetArmor' with recommended alternative (check API migration guide)
  ! [OUTDATED_API_VERSION] (line 1): Mod uses API 53, but current API is 59
    → Update apiVersion="59"
```

### JSON Format

```json
{
  "api_version": 59,
  "total_issues": 15,
  "errors": 3,
  "warnings": 8,
  "infos": 4,
  "issues_by_file": {
    "MyMod.xml": [
      {
        "severity": "error",
        "line": 45,
        "code": "DEPRECATED_FUNCTION",
        "message": "Deprecated function 'objGetArmor' used",
        "suggestion": "Replace 'objGetArmor' with recommended alternative",
        "deprecated_item": "objGetArmor"
      }
    ]
  }
}
```

## Custom API Rules

You can specify a custom API rules file:

```bash
python mod_fixer.py "path/to/mod" \
  --profile transcendence \
  --api-rules "path/to/custom_api_rules.json" \
  --check-api
```

## Best Practices

1. **Check Before Fixing**: Always run `--check-api` first to see what needs fixing
2. **Review Deprecated Items**: Check migration guides for deprecated functions
3. **Update API Version**: Keep mod's API version current
4. **Test After Fixes**: Verify fixes work in-game
5. **Use Templates**: Leverage `fix_api_compatibility` template for comprehensive fixes

## Troubleshooting

### "API rules file not found"

- Ensure `api_rules.json` or `api_rules_*.json` exists in Tools directory
- Generate rules: `pwsh -File TranscendenceModTools_ApiRules.ps1`

### "API checker not available"

- Check `mod_fixer_api_checker.py` exists
- Verify Python dependencies are installed

### "No issues found but mod doesn't work"

- API checker only validates syntax/compatibility
- Some issues require runtime testing
- Check game logs for actual errors

## See Also

- [MOD_FIXER_TRANSCENDENCE_GUIDE.md](MOD_FIXER_TRANSCENDENCE_GUIDE.md) - Transcendence mod fixing guide
- [API_RULES_GUIDE.md](API_RULES_GUIDE.md) - API rules system documentation
- [TranscendenceModTools_ApiRules.ps1](TranscendenceModTools_ApiRules.ps1) - API rules generator

