# Migration Safety & Verification Guide

## Overview

This guide covers the migration safety tools for verifying, merging, and testing AI-updated mods during 2.0.7 migration.

## Quick Safety Checklist

Before starting any migration work:

1. **Backup** the original mod folder and the AI-updated folder
2. **Create a diff** between manual updates and AI updates
3. **Lock a test environment** (copy of game or sandbox) for playtests

## Features

### 1. Migration Diff Viewer

**Three-way diff**: Compare original → manual update → AI update

- Shows what changed in each version
- Highlights conflicts where manual and AI edits differ
- Risk scores files by change type (event handlers = high risk)

**Usage:**
```powershell
$diff = Get-MigrationDiff -OriginalPath "OriginalMod" -ManualPath "ManualUpdate" -AiPath "AIUpdate" -OutputPath "diff_report.txt"
```

### 2. Automated Verification Pipeline

**Schema & Syntax Pass:**
- XML well-formedness
- BOM detection
- Tag matching

**Semantic Checks:**
- UNID reference validation
- Duplicate UNID detection
- Resource existence (images, sounds)

**API Deprecation Scan:**
- Detects old API versions
- Flags deprecated functions/attributes

**Usage:**
```powershell
$results = Invoke-MigrationVerification -ModPath "ModFolder" -All
```

### 3. Risk Scoring

Files are scored by risk level:
- **High Risk (50+)**: Event handlers, TLisp code blocks, UNID changes
- **Medium Risk (20-49)**: Attribute changes, resource references
- **Low Risk (<20)**: Comments, whitespace, formatting

**Usage:**
```powershell
$riskReport = Get-MigrationRiskReport -Diff $diff
```

### 4. Behavioral Smoke Tests

**Core Test Scenarios:**
1. Ship spawns correctly
2. Weapons fire without errors
3. Encounters spawn correctly
4. Missions start and progress
5. Docking works at stations
6. AI behaves correctly
7. Loot drops as expected
8. UI strings display correctly
9. Resources load (images/sounds)
10. Save/load works correctly

**Usage:**
```powershell
$testResults = Invoke-BehavioralSmokeTests -ModPath "ModFolder" -GamePath "GamePath" -LogPath "LogPath"
```

### 5. Merge Conflict Resolution

**Three-way merge strategy:**
- Compare original → manual → AI
- Identify semantic changes (event bodies, UNID changes)
- Prefer intent-preserving edits
- Record decisions with comments

**Conflict Types:**
- Line conflicts (same line changed differently)
- UNID conflicts (different UNIDs assigned)
- Event handler conflicts (different implementations)

### 6. Test Runner

**Playtest Checklist:**
- Automated test execution
- Log monitoring for errors/warnings
- Regression detection (compare baseline vs test logs)

**Usage:**
```powershell
$regression = Invoke-RegressionHarness -ModPath "ModFolder" -BaselineLogPath "baseline.log" -TestLogPath "test.log"
```

## GUI Features

### Migration Safety Tab

The GUI includes a dedicated "Migration Safety" tab with:

1. **Diff Viewer Panel**
   - Three-way diff display
   - Conflict highlighting
   - Risk score visualization

2. **Verification Panel**
   - Run schema/semantic/API checks
   - View results in real-time
   - Export verification reports

3. **Risk Assessment Panel**
   - High/medium/low risk file lists
   - Prioritized review queue
   - Change summaries

4. **Test Runner Panel**
   - Playtest checklist
   - Test execution
   - Log monitoring

5. **Merge Tools Panel**
   - Accept/reject per-change UI
   - Decision recording
   - Automated rollback

## Best Practices

1. **Always backup** before merging
2. **Review high-risk files** manually first
3. **Test incrementally** - don't merge everything at once
4. **Document decisions** - why you kept or reverted changes
5. **Use test environment** - never test on main install
6. **Monitor logs** - watch for new errors after migration

## Workflow

1. **Prepare**
   - Backup original and AI-updated mods
   - Create test environment

2. **Diff**
   - Run three-way diff
   - Review risk scores
   - Identify conflicts

3. **Verify**
   - Run verification pipeline
   - Fix schema/syntax issues
   - Address semantic problems

4. **Merge**
   - Resolve conflicts
   - Accept/reject changes
   - Document decisions

5. **Test**
   - Run smoke tests
   - Playtest core scenarios
   - Monitor logs

6. **Deploy**
   - Final verification
   - Deploy to main install
   - Monitor for issues

## Future Enhancements

- **Rule Learning**: Track which AI suggestions you accept/reject
- **Migration Preview**: Show resolved types after changes
- **Automated Test Runner**: Launch sandbox and run tests
- **Change Tracking**: Version control integration

