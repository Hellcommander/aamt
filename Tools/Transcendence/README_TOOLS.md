# Transcendence Mod Tools - Overview

## Purpose

The Transcendence Mod Tools are designed to **fix errors, warnings, and format XML files**, which helps mods be compatible with Transcendence 2.0.7.

## What the Tools Do

### ✅ Automatic Fixes
- Remove UTF-8 BOM
- Fix invalid symbol syntax
- Format XML to 2.0.7 style (tabs, alignment)
- Some raw `>` character fixes

### ✅ Detection & Validation
- XML syntax errors
- Missing resources
- Deprecated API usage
- Type reference validation
- UNID conflicts
- Inheritance issues

### ❌ What They Don't Do
- Do NOT automatically update `apiVersion` attributes
- Do NOT add DOCTYPE declarations
- Do NOT fix entity reference errors automatically
- Do NOT change mod functionality

## Main Tool

**TranscendenceModTools.ps1** - GUI tool with all features

**Launch:** Double-click `TranscendenceModTools.bat`

**Features:**
- XML Checker - Scan and fix issues
- Error Helper - Diagnose error messages
- Project Health - Comprehensive mod health report
- UNID Manager - UNID management and conflict detection
- Cross-Mod Compatibility - Check UNID conflicts between mods
- Semantic Validation - Type references, inheritance
- Resource Integrity - Validate images and sounds
- Formatting - Format XML to 2.0.7 style

## Helper Scripts

- **FixMod.ps1** - Auto-fix issues in a mod
- **ScanMod.ps1** - Quick scan of a mod
- **ProcessModsFor207.ps1** - Batch process multiple mods

## Workflow for 2.0.7 Compatibility

See **WORKFLOW_207.md** for detailed workflow.

Quick version:
1. Scan mod for issues
2. Auto-fix what can be fixed
3. Format XML files
4. Manually update `apiVersion` to 57
5. Manually fix remaining errors (entity references, etc.)

## Documentation

- **WORKFLOW_207.md** - Complete workflow guide
- **CHANGELOG.md** - Version history and features
- **FEATURES.md** - Complete feature list
- **QUICK_REFERENCE.md** - Quick start guide

## Key Points

1. Tools fix **errors and formatting** - this helps with 2.0.7 compatibility
2. Tools do **NOT** update API versions automatically
3. Tools format to **2.0.7 style** (Version 3.2+)
4. Manual work still needed for `apiVersion` and entity references

