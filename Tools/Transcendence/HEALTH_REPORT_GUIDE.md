# Mod Health Report - Detailed Guide

## Overview

The Mod Health Report provides comprehensive statistics about your mod's health, including specific counts for common issues.

## Report Format

The health report displays statistics in this format:

```
═══════════════════════════════════════════════════════════
                  PROJECT HEALTH REPORT
═══════════════════════════════════════════════════════════

Total Files Scanned: 15
Files with Errors: 2
Files with Warnings: 5

═══════════════════════════════════════════════════════════
                    DETAILED STATISTICS
═══════════════════════════════════════════════════════════

✓ XML errors:                    0
⚠ Missing resources:             3
⚠ Unused UNIDs:                   2
⚠ Deprecated attributes:          1
⚠ Files with inconsistent indentation: 4
```

## Statistics Explained

### ✓ XML Errors
**What it counts:**
- XML well-formedness errors
- Tag mismatches
- Unclosed tags
- Unexpected closing tags

**Status indicators:**
- ✓ = No XML errors
- ❌ = XML errors found

### ⚠ Missing Resources
**What it counts:**
- Image files referenced but not found
- Sound files referenced but not found
- Resources with invalid paths

**Status indicators:**
- ✓ = All resources found
- ⚠ = Missing resources detected

### ⚠ Unused UNIDs
**What it counts:**
- UNIDs defined in DOCTYPE but never referenced
- Entity definitions that are never used

**Status indicators:**
- ✓ = All UNIDs are used
- ⚠ = Unused UNIDs found

**Note:** Some UNIDs may be intentionally unused (e.g., for future features).

### ⚠ Deprecated Attributes
**What it counts:**
- Files using API versions 50-56 (should be 57)
- Old API version declarations

**Status indicators:**
- ✓ = Using current API
- ⚠ = Deprecated API versions found

### ⚠ Files with Inconsistent Indentation
**What it counts:**
- Files using both tabs and spaces
- Mixed indentation styles

**Status indicators:**
- ✓ = Consistent indentation
- ⚠ = Inconsistent indentation found

## Additional Metrics

The report also includes:
- **Total Errors**: All error-level issues
- **Total Warnings**: All warning-level issues
- **UNID Duplicates**: UNIDs defined multiple times

## How to Use

1. Go to **Project Health** tab
2. Enter your mod folder path
3. Click **Generate Report**
4. Review the detailed statistics
5. Fix issues starting with errors, then warnings

## Interpreting Results

### Perfect Health
```
✓ XML errors:                    0
✓ Missing resources:             0
✓ Unused UNIDs:                   0
✓ Deprecated attributes:          0
✓ Files with inconsistent indentation: 0
```
All checks passed! Your mod is in excellent shape.

### Issues Found
```
❌ XML errors:                    5
⚠ Missing resources:             3
⚠ Unused UNIDs:                   2
⚠ Deprecated attributes:          1
⚠ Files with inconsistent indentation: 4
```

**Priority order:**
1. Fix XML errors first (❌) - these will prevent the mod from loading
2. Fix missing resources (⚠) - may cause runtime errors
3. Review deprecated attributes (⚠) - update to API 57
4. Clean up unused UNIDs (⚠) - optional but recommended
5. Fix indentation (⚠) - improves code quality

## Tips

- **XML Errors**: Use the XML Checker tab to see details
- **Missing Resources**: Check file paths and ensure files exist
- **Unused UNIDs**: Consider removing if truly unused, or document why they're kept
- **Deprecated Attributes**: Update `apiVersion="57"` in root element
- **Indentation**: Use the Format button to normalize indentation

## Example Workflow

1. Generate health report
2. See "5 XML errors" → Go to XML Checker tab
3. Fix XML errors
4. Regenerate health report
5. See "3 missing resources" → Check resource paths
6. Fix resource paths
7. Regenerate health report
8. Continue until all issues resolved

---

The Mod Health Report gives you a quick overview of your mod's status and helps prioritize fixes!

