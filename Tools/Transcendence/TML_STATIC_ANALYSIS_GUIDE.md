# TML Static Analysis - User Guide

## Overview

TML Static Analysis performs deep analysis of TLisp code to find issues that syntax checkers miss. It helps you write better, more efficient code.

## Features

### 1. Unused Variable Detection 🔍

**Detects**:
- Variables defined in `(block (var1 var2) ...)` but never used
- Variables set with `(setq var value)` but never referenced
- Dead code from unused variables

**Example**:
```
⚠ MyMod.xml:45
   Variable 'myVar' is defined but never used in <OnCreate>
```

**Fix**: Remove unused variable or use it

### 2. Unreachable Code Detection 🚫

**Detects**:
- `(if Nil ...)` - condition always false
- `(if false ...)` - condition always false
- Dead code paths

**Example**:
```
⚠ MyMod.xml:67
   Unreachable code in <OnUpdate>: if condition is always false (Nil/false)
```

**Fix**: Remove unreachable code or fix condition

### 3. Expensive Operations Warning ⚡

**Detects**:
- Expensive operations in frequently-called events
- Performance issues in hot paths

**Frequently-Called Events**:
- `OnUpdate` - Called every frame
- `OnDamage` - Called on every damage
- `OnFireWeapon` - Called on every weapon fire
- `OnGlobalObjAttacked` - Called on every attack

**Expensive Operations**:
- `sysFindObject` - Searches all objects
- `sysCreateShip` - Creates new object
- `sysCreateStation` - Creates new object
- `enum` - Can be slow with large lists
- `typGetData` / `typSetData` - Type data access

**Example**:
```
⚠ MyMod.xml:89
   Expensive operation 'sysFindObject' in frequently-called event <OnUpdate>:
   Expensive - searches all objects in system
```

**Fix**: Cache results, use less expensive alternatives, or move to less frequent event

### 4. Deprecated Function Detection ⚠️

**Detects**:
- Functions deprecated in API 57
- Functions with breaking changes
- Suggests replacements

**Deprecated Functions**:
- `objGetItems` → `objGetProperty ... 'items'`
- `objGetArmorType` → `objGetProperty ... 'armorClass'`
- `shpGetDirection` → `objGetProperty ... 'rotation'`
- `sysGetNodes` → `unvGetTopologyNodes`
- `objDestroy` → `objDestroy obj objSource` (API 57 requires source)
- `Register` → `Register obj Registrar` (API 57 requires Registrar)

**Example**:
```
❌ MyMod.xml:120
   Deprecated function 'objDestroy' in <OnCreate>:
   API 57 requires source parameter. Consider: objDestroy obj objSource
```

**Fix**: Update to new API or suggested replacement

## How to Use

### Run TML Static Analysis

1. Go to **Semantic Validation** tab
2. Enter mod folder path
3. Click **TML Analysis** button
4. Review issues in grid
5. Filter by issue type
6. Double-click to jump to code

### Using Filters

**Filter Options**:
- **All**: Show all issues
- **Unused Variables**: Only unused variable warnings
- **Unreachable Code**: Only unreachable code warnings
- **Expensive Operations**: Only performance warnings
- **Deprecated Functions**: Only deprecated function warnings

## Understanding Results

### Severity Levels

- **❌ Error**: Breaking changes (e.g., objDestroy without source)
- **⚠ Warning**: Performance or code quality issues
- **ℹ Info**: Informational (e.g., expensive operations)

### Issue Codes

- `UNUSED_VARIABLE`: Variable defined but never used
- `UNREACHABLE_CODE`: Code that can never execute
- `EXPENSIVE_OPERATION`: Expensive operation in hot path
- `DEPRECATED_FUNCTION`: Deprecated or changed function

## Use Cases

### Code Quality
- Find and remove unused variables
- Remove dead code
- Improve code cleanliness

### Performance Optimization
- Identify expensive operations in hot paths
- Optimize frequently-called events
- Cache expensive lookups

### API Compliance
- Update to API 57
- Replace deprecated functions
- Fix breaking changes

## Tips

- **Unused Variables**: Review before removing - may be for future use
- **Expensive Operations**: Consider caching or moving to less frequent events
- **Deprecated Functions**: Update to new API for future compatibility
- **Unreachable Code**: Remove to reduce confusion

## Example Scenarios

### Scenario 1: Performance Issue

**Problem**: `sysFindObject` in `OnUpdate` causes lag

**Solution**: Cache result or move to less frequent event

### Scenario 2: Dead Code

**Problem**: Unused variable cluttering code

**Solution**: Remove unused variable

### Scenario 3: API Update

**Problem**: Using deprecated `objGetItems`

**Solution**: Update to `objGetProperty ... 'items'`

---

TML Static Analysis helps you write better, more efficient code!

