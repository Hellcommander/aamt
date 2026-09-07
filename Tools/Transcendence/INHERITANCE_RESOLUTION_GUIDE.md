# Inheritance & Override Resolution - User Guide

## Overview

The Inheritance & Override Resolution feature shows you **fully resolved types** - what a type looks like after all inheritance is applied. This is incredibly powerful for debugging complex mods with inheritance chains.

## What It Does

### 1. Fully Resolved Types

Shows the **final version** of a type after all inheritance:
- All attributes merged from parent chain
- All events merged from parent chain
- Clear indication of what comes from where

### 2. Attribute Source Tracking

For each attribute, shows:
- **Self**: Defined in this type
- **Parent**: Inherited from parent type
- **Chain**: Inherited through multiple levels

### 3. Override Conflict Detection

Detects when:
- Child overrides parent attribute values
- Immutable attributes are overridden (error)
- Parent assumptions might be broken

## How to Use

### View Resolved Type

1. Go to **Semantic Validation** tab
2. Enter mod folder path
3. Click **Inheritance Tree**
4. Select a type from dropdown
5. View fully resolved type with all attributes

### Understanding the Display

**Inheritance Chain**:
```
MyShip → BaseShip → StandardShip
```
Shows the full inheritance hierarchy.

**Attributes**:
```
name = "My Ship"
  Source: Self: MyShip
level = "5"
  Source: Parent: BaseShip
```
Shows each attribute and where it comes from.

**Override Conflicts**:
```
⚠ Attribute: level
  Parent value: 3
  Child value:  5
  Source: Parent: BaseShip
```
Shows when child overrides parent values.

## Use Cases

### Debugging Inheritance Issues
- See what attributes a type actually has
- Understand why a type behaves differently than expected
- Find missing attributes from parent

### Understanding Mod Structure
- Map inheritance hierarchies
- See what each type adds to parent
- Understand type relationships

### Finding Override Problems
- Detect when overrides break parent assumptions
- Find immutable attribute overrides
- Identify potential conflicts

## Example Scenarios

### Scenario 1: Missing Attribute

**Problem**: Type doesn't have expected attribute

**Solution**: Check resolved type to see if it's inherited from parent

### Scenario 2: Override Conflict

**Problem**: Type behaves unexpectedly

**Solution**: Check override conflicts to see if parent assumptions are broken

### Scenario 3: Inheritance Chain

**Problem**: Not sure what a type inherits

**Solution**: View inheritance chain to see full hierarchy

## Technical Details

### Attribute Merging

Attributes are merged bottom-up:
1. Start with root parent attributes
2. Apply each level of inheritance
3. Child attributes override parent

### Conflict Detection

Conflicts are detected when:
- Child defines same attribute as parent with different value
- Immutable attributes are overridden
- Parent assumptions might be broken

### Event Merging

Events are merged from all levels:
- Parent events are inherited
- Child events are added
- No conflicts (events can be added, not overridden)

## Tips

- **Large inheritance chains**: Use the type selector to navigate
- **Override conflicts**: Review carefully - may indicate bugs
- **Immutable overrides**: Always errors - will break parent assumptions
- **Base game types**: Some parent types may be base game (not in mod)

---

Inheritance & Override Resolution helps you understand exactly what your types look like after inheritance!

