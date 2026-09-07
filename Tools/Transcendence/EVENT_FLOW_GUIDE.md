# Event Flow Analyzer - User Guide

## Overview

The Event Flow Analyzer maps event usage across your mod, showing which events are implemented, inherited, duplicated, or potentially unused. This helps you avoid dead code and subtle bugs.

## What It Does

### 1. Event Mapping
- Shows all events a type implements
- Shows all events it inherits from parent
- Tracks event sources (self vs. inherited)

### 2. Unused Event Detection
- Identifies events that may not be called by the engine
- Flags custom events that might be dead code
- Warns about potentially unreachable handlers

### 3. Duplicate Detection
- Detects duplicate event handlers (same event defined multiple times)
- Warns that only the last definition will be used

### 4. Engine Event Database
- Knows which events are called by Transcendence engine
- Distinguishes between engine events and custom events
- Provides descriptions for known events

## How to Use

### Run Event Flow Analysis

1. Go to **Semantic Validation** tab
2. Enter mod folder path
3. Click **Event Flow** button
4. Review event flow report

### Using Filters

**Filter by Event Type**:
- **All**: Show all events
- **Implemented**: Events defined in this type
- **Inherited**: Events inherited from parent
- **Duplicate**: Events defined multiple times
- **Unused**: Events that may not be called
- **Summary**: Summary statistics per type

**Filter by Type**:
- Select specific type from dropdown
- Or "All Types" to see everything

## Understanding Results

### Event Status

**✓ Called by engine**:
- Event is known to Transcendence engine
- Will be called during gameplay
- Safe to use

**⚠ May not be called**:
- Custom event or unknown event
- May not be called by engine
- Could be dead code

**⚠ Duplicate handler**:
- Event defined multiple times
- Only last definition will be used
- Earlier definitions are ignored

### Event Types

**Implemented**:
- Events defined directly in the type
- Source: "Self"

**Inherited**:
- Events inherited from parent type
- Source: "Inherited from ParentName"

**Duplicate**:
- Same event handler defined multiple times
- Warning: Only last one used

**Unused**:
- Events that may not be called
- Could be custom events or dead code

## Example Scenarios

### Scenario 1: Dead Code Detection

**Problem**: Custom event that's never called

**Solution**: Event Flow shows "⚠ May not be called" - review if needed

### Scenario 2: Duplicate Handlers

**Problem**: Same event defined twice

**Solution**: Event Flow shows duplicate - remove one definition

### Scenario 3: Missing Events

**Problem**: Type should handle certain events

**Solution**: Check inherited events to see what's available

## Known Events

The analyzer knows about these Transcendence events:

### Object Lifecycle
- `OnCreate` - Called when object is created
- `OnDestroy` - Called when object is destroyed
- `OnUpdate` - Called every frame

### Combat
- `OnFireWeapon` - Called when weapon fires
- `OnDamage` - Called when object takes damage
- `OnDamageArmor` - Called when armor is damaged
- `OnDamageShields` - Called when shields are damaged

### Ship Events
- `OnDocked` - Called when ship docks
- `OnUndocked` - Called when ship undocks
- `OnOrdersChanged` - Called when orders change
- `OnEnteredSystem` - Called when entering system

### Station Events
- `OnPlayerEnteredSystem` - Called when player enters
- `OnPlayerDocked` - Called when player docks
- `OnTrade` - Called during trade

### Global Events
- `OnGlobalObjAttacked` - Called when any object attacked
- `OnGlobalUniverseCreated` - Called when universe created

And many more...

## Tips

- **Custom Events**: If you use custom events, make sure they're actually called
- **Duplicates**: Remove duplicate handlers - only last one is used
- **Inheritance**: Check inherited events to see what's available
- **Unused Events**: Review unused events - they might be dead code

## Technical Details

### Event Detection

Events are detected by:
- Parsing `<On*>` tags
- Parsing `<Events>` blocks
- Tracking inheritance chains
- Comparing against known events database

### Inheritance Tracking

Inherited events are:
- Found by following inheritance chain
- Merged with implemented events
- Tracked with source information

### Duplicate Detection

Duplicates are detected when:
- Same event name appears multiple times
- In same type definition
- Warning: Only last definition is used

---

The Event Flow Analyzer helps you understand your mod's event usage and avoid dead code!

