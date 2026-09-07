# "What Changed?" Diff Mode - User Guide

## Overview

The Diff Mode compares two versions of a mod or game XML to show what changed. Perfect for updating mods between game versions or tracking changes in your mod.

## Features

### 1. Added Types ✅
Shows all new types added in the new version:
- ItemTypes
- ShipClasses
- StationTypes
- Sovereigns
- Missions

**Example**:
```
✅ MyNewShip [ShipClass]
   UNID: 0x12345678
   File: MyMod.xml
```

### 2. Removed Types ❌
Shows all types removed in the new version:
- Types that existed in old version but not in new

**Example**:
```
❌ OldShip [ShipClass]
   UNID: 0x87654321
   File: MyMod.xml
```

### 3. Changed Types 🔄
Shows types with modified attributes:
- Added attributes
- Removed attributes
- Modified attribute values

**Example**:
```
🔄 MyShip [ShipClass]
   UNID: 0x12345678
   Attribute Changes:
     ✅ newAttribute = value
     ❌ oldAttribute = value (removed)
     🔄 level: '5' → '7'
```

### 4. Added Events ✅
Shows new event handlers added to types:
- Event name
- Type that has the event

**Example**:
```
✅ MyShip → OnCreate
```

### 5. Removed Events ❌
Shows event handlers removed from types:
- Event name
- Type that lost the event

**Example**:
```
❌ MyShip → OnDestroy
```

### 6. Deprecated Fields ⚠️
Shows attributes marked as deprecated:
- UNID
- Attribute name
- Attribute value

**Example**:
```
⚠ UNID: 0x12345678
   Attribute: obsoleteVersion = 1.0
```

## How to Use

### Step 1: Select Old Version
1. Click "Browse..." next to "Old Version"
2. Select the folder containing the old version XML files

### Step 2: Select New Version
1. Click "Browse..." next to "New Version"
2. Select the folder containing the new version XML files

### Step 3: Compare
1. Click "Compare Versions"
2. Wait for analysis to complete
3. Review the diff report

## Use Cases

### Updating Mods Between Game Versions
Compare your mod against the new game version to see:
- What types were added/removed
- What attributes changed
- What events were added/removed

### Tracking Mod Changes
Compare two versions of your mod to:
- Document changes
- Find breaking changes
- Track attribute modifications

### Debugging Issues
Compare working vs broken versions to:
- Identify what changed
- Find the cause of issues
- Revert problematic changes

### Generating Change Logs
Use the diff report to:
- Document updates
- Create release notes
- Track version history

## Report Format

The diff report includes:
- **Summary**: Counts of all changes
- **Added Types**: List of new types
- **Removed Types**: List of removed types
- **Changed Types**: Types with attribute changes
- **Added Events**: New event handlers
- **Removed Events**: Removed event handlers
- **Deprecated Fields**: Deprecated attributes

## Tips

- **Large Comparisons**: May take time for large mods
- **File Structure**: Ensure both versions have similar file structures
- **UNID Matching**: Types are matched by UNID
- **Attribute Changes**: Only shows attributes in type opening tags
- **Event Detection**: Finds events in `<Events>` blocks

## Limitations

- **Nested Attributes**: Only compares top-level attributes
- **Event Content**: Doesn't compare event handler code
- **File Paths**: Doesn't track file moves/renames
- **Comments**: Doesn't track comment changes

---

The Diff Mode helps you understand what changed between versions!

