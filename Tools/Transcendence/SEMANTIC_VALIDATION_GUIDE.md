# Semantic Validation - User Guide

## Overview

Semantic Validation goes **beyond syntax checking** to understand Transcendence's engine structure. It validates that type references are correct, inheritance chains are valid, and relationships make sense.

## What Makes It Different

Unlike syntax checkers that only verify XML is well-formed, Semantic Validation understands:
- **Type relationships**: Which types reference which other types
- **Inheritance chains**: How types inherit from each other
- **Event handlers**: Which events are implemented by which types
- **Cross-file dependencies**: References across multiple files

## Features

### 1. Type Reference Validation

**Checks**:
- ShipClass → ArmorClass references
- StationType → ArmorClass references
- Device → ItemType references
- Weapon → Weapon type references
- Inherit → Parent type references

**Example Error**:
```
ShipClass 'scMyShip' references nonexistent ArmorClass 'itMissingArmor'
```

### 2. Inheritance Tree

**Shows**:
- All types with inheritance
- Parent-child relationships
- Inheritance chains
- Override hierarchies

**Example**:
```
MyShip (ShipClass)
  UNID: 0xE1271001
  Inherits: &scBaseShip;
  Children: 2
```

### 3. Event Flow Analysis

**Tracks**:
- Which types implement which events
- Event handler locations
- Event usage patterns

## How to Use

### Basic Validation

1. Go to **Semantic Validation** tab
2. Enter mod folder path
3. Click **Validate**
4. Review issues in the grid
5. Double-click issues to jump to file/line

### Inheritance Tree

1. Enter mod folder path
2. Click **Inheritance Tree**
3. Review inheritance relationships
4. See parent-child hierarchies

## Understanding Results

### Error Severity

- **Error**: Critical issues that will cause runtime failures
  - Missing ArmorClass references
  - Missing Device references
  - Missing Weapon type references

- **Warning**: Potential issues that may cause problems
  - Missing inherit references (may be base game types)
  - Unresolved references

### Issue Codes

- `SEMANTIC_MISSING_ARMOR`: ArmorClass reference not found
- `SEMANTIC_MISSING_DEVICE`: Device/ItemType reference not found
- `SEMANTIC_MISSING_WEAPON`: Weapon type reference not found
- `SEMANTIC_MISSING_INHERIT`: Inherit parent not found

## Use Cases

### Debugging Complex Mods
- Find broken type references
- Verify inheritance chains
- Check cross-file dependencies

### Mod Architecture
- Understand type relationships
- Map inheritance hierarchies
- Track event implementations

### Compatibility Checking
- Verify all references are valid
- Check for missing dependencies
- Validate mod structure

## Tips

- **Large mods**: Validation may take a moment for large projects
- **Base game types**: Some warnings about missing inherit may be base game types (safe to ignore)
- **Cross-mod**: Currently validates within single mod - future versions may check across mods

## Technical Details

### Two-Pass Analysis

1. **Registry Building**: Scans all files to build type registry
2. **Validation**: Checks all references against registry

### Type Registry

The registry includes:
- ItemTypes
- ShipClasses
- StationTypes
- ArmorClasses (ItemTypes with Armor element)

### Reference Resolution

- Resolves entity references (`&entityName;`)
- Resolves UNID values (`0x12345678`)
- Tracks cross-file references

---

Semantic Validation helps you catch issues that syntax checkers miss!

