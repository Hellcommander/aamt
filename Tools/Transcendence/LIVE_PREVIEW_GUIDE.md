# Live Preview of Resolved Types - User Guide

## Overview

The Live Preview feature shows everything about a type in one place. This is information the game engine itself doesn't expose - it's the "killer feature" for understanding your mod's structure.

## Features

### 1. Fully Resolved Attributes ✅
Shows all attributes after inheritance resolution:
- Attributes from the type itself
- Attributes inherited from parent types
- Source indication (Self/Parent)
- Override conflicts

**Example**:
```
level = 5
  Source: Parent: BaseShip
name = My Custom Ship
  Source: Self: MyShip
```

### 2. All Events 📝
Shows all events the type implements:
- Events defined in the type
- Events inherited from parent types
- Event source indication

**Example**:
```
OnCreate
  Source: Self: MyShip
OnUpdate
  Source: Parent: BaseShip
```

### 3. All Resources 🖼️
Shows all resources used by the type:
- Image references
- Sound references
- Icon references

**Example**:
```
Images:
  - rsShipImage
Sounds:
  - rsShipSound
Icons:
  - rsShipIcon
```

### 4. All References 🔗
Shows all types this type references:
- **Inherits**: Parent types
- **Uses**: Items, weapons, armor, sovereigns
- **Spawns**: Ships, encounters

**Example**:
```
Inherits:
  - BaseShip (0x87654321)
Uses:
  - itLaserCannon (0x11111111)
  - svPlayer (0x00000001)
Spawns:
  - MyFighter (0x22222222)
```

### 5. Referenced By 🔄
Shows all types that reference this type:
- Types that use this type
- Types that inherit from this type
- Types that spawn this type

**Example**:
```
Used by:
  - MyStation [StationType] (0x33333333)
Inherited by:
  - MyAdvancedShip [ShipClass] (0x44444444)
Spawned by:
  - MyEncounter [EncounterTable] (0x55555555)
```

### 6. Override Conflicts ⚠️
Shows attribute conflicts with parent types:
- Attribute name
- Parent value
- Child value
- Source

**Example**:
```
⚠ level
  Parent: 3
  Child:  5
  Source: Parent: BaseShip
```

## How to Use

### Step 1: Select Mod Path
1. Click "Browse..." next to "Mod Path"
2. Select the folder containing your mod XML files

### Step 2: Load Types
1. Click "Load Types"
2. Wait for types to load
3. You'll see "Loaded X types. Select a type and click Preview."

### Step 3: Select Type
1. Open the "Select Type" dropdown
2. Choose the type you want to preview
3. Types are shown as "Name [Type]"

### Step 4: Preview
1. Click "Preview"
2. Wait for preview to generate
3. Review the comprehensive preview

## Use Cases

### Understand Type Structure
See all attributes and their sources:
- What comes from the type itself
- What comes from parent types
- Any conflicts

### Debug Inheritance
See inheritance chain:
- Parent types
- Inherited attributes
- Inherited events

### Track Dependencies
See what types use this type:
- Direct references
- Inheritance relationships
- Spawn relationships

### Find References
See where this type is used:
- Which types use it
- Which types inherit from it
- Which types spawn it

### Resource Management
See all resources:
- Images used
- Sounds used
- Icons used

### Event Analysis
See all events:
- Events implemented by type
- Events inherited from parents
- Event sources

## Preview Sections

### Type Information
- Type name
- UNID
- File location

### Resolved Attributes
- All attributes after inheritance
- Source for each attribute
- Override conflicts

### Events
- All events (implemented and inherited)
- Source for each event

### Resources
- Images
- Sounds
- Icons

### References
- Inherits
- Uses
- Spawns

### Referenced By
- Used by
- Inherited by
- Spawned by

## Tips

- **Large Mods**: Loading may take time for large mods
- **Type Selection**: Use the dropdown to quickly find types
- **Preview Updates**: Click Preview again to refresh
- **Inheritance**: Preview shows full inheritance resolution
- **References**: Both forward and reverse references shown

## Limitations

- **Event Content**: Doesn't show event handler code
- **Nested Attributes**: Only shows top-level attributes
- **Resource Validation**: Doesn't validate resource existence
- **Performance**: May be slow for very large mods

---

The Live Preview is the ultimate tool for understanding your mod's structure!

