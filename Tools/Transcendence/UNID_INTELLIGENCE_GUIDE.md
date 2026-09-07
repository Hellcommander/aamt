# UNID Intelligence - User Guide

## Overview

UNID Intelligence provides advanced UNID analysis beyond simple scanning. It tracks references, detects conflicts, and suggests unused ranges - essential for large modpacks.

## Features

### 1. Reference Tracking 🧭

**Shows**:
- Where each UNID is referenced
- Reference count for each UNID
- Line numbers and context
- File locations

**Use Cases**:
- Find all uses of a UNID
- Verify UNID is actually used
- Track UNID dependencies

### 2. Dangling UNID Detection ⚠️

**Detects**:
- UNIDs defined but never referenced
- Potential dead code
- Unused entity definitions

**Use Cases**:
- Clean up unused UNIDs
- Identify dead code
- Optimize mod size

### 3. Override Conflict Detection 🔥

**Detects**:
- UNIDs defined in multiple mods
- Modpack compatibility issues
- Override conflicts

**Use Cases**:
- Check modpack compatibility
- Find conflicting mods
- Resolve UNID conflicts

### 4. Unused Range Suggestions 💡

**Suggests**:
- Available UNID ranges
- Safe ranges for new mods
- Gaps in user UNID space

**Use Cases**:
- Find UNID range for new mod
- Avoid conflicts
- Plan UNID allocation

## How to Use

### Basic Scan

1. Go to **UNID Manager** tab
2. Enter mod folder path
3. Click **Scan UNIDs**
4. View UNIDs with reference counts

### Intelligence Report

1. Enter mod folder path
2. Click **Intelligence** button
3. Review four tabs:
   - **All UNIDs**: Complete list
   - **Dangling UNIDs**: Unused UNIDs
   - **Override Conflicts**: Multi-mod conflicts
   - **Unused Ranges**: Available ranges

### View References

1. In Intelligence report
2. Double-click any UNID
3. View all reference locations
4. See line numbers and context

## Understanding Results

### Reference Counts

- **0**: Dangling UNID (not used)
- **1+**: Number of references
- **Color**: Yellow for dangling, red for duplicates

### Dangling UNIDs

UNIDs that are:
- Defined in DOCTYPE
- Never referenced in code
- Potential dead code

### Override Conflicts

UNIDs that are:
- Defined in multiple mods
- Will conflict in modpacks
- Need resolution

### Unused Ranges

Ranges that are:
- Available for new mods
- Within user UNID space (0xD000-0xEFFF)
- Respect reserved ranges

## UNID Ranges

### Reserved Ranges

- **0x0000-0x9FFF**: Kronosaur Productions
- **0xA000-0xCFFF**: Registered Extensions
- **0xD000-0xEFFF**: User UNIDs (available)
- **0xF000-0xFFFF**: Dynamic UNIDs

### Special Reserved

- **0xD000**: Ministry/wiki
- **0x0070-0x007F**: Compatibility libraries
- **0xEFFC**: Stable patches
- **0xEFFD**: Alpha/beta patches
- **0xEFFE**: Expansion Library Template
- **0xEFFF**: Transcendence Next++

## Tips

- **Dangling UNIDs**: Review before removing - may be used by other mods
- **Override Conflicts**: Critical for modpack compatibility
- **Unused Ranges**: Use for new mods to avoid conflicts
- **Reference Tracking**: Double-click to see all uses

## Example Scenarios

### Scenario 1: Finding Dead Code

**Problem**: Mod has unused UNIDs

**Solution**: Check Dangling UNIDs tab - remove if not needed

### Scenario 2: Modpack Conflicts

**Problem**: Mods conflict in modpack

**Solution**: Check Override Conflicts tab - resolve conflicts

### Scenario 3: New Mod UNID Range

**Problem**: Need UNID range for new mod

**Solution**: Check Unused Ranges tab - use suggested range

---

UNID Intelligence helps you manage UNIDs effectively, especially in large modpacks!

