# Enhanced Cross-File Dependency Graph - User Guide

## Overview

The Enhanced Cross-File Dependency Graph visualizes all relationships between mod elements. It's incredibly useful for debugging complex mods and balancing spawn tables.

## Node Types

### 1. ItemTypes
- All `<ItemType>` definitions
- Weapons, armor, devices, etc.

### 2. ShipClasses
- All `<ShipClass>` definitions
- Player ships, NPC ships, etc.

### 3. StationTypes
- All `<StationType>` definitions
- Stations, planets, asteroids, etc.

### 4. Sovereigns
- All `<Sovereign>` definitions
- Factions, relationships

### 5. Missions
- All `<MissionType>` definitions
- Mission objectives, rewards

### 6. Tables
- All `<EncounterTable>` and `<ShipTable>` definitions
- Spawn tables, encounter tables

## Relationship Types

### 1. Uses 🔗
**Meaning**: Type uses another type

**Examples**:
- ShipClass uses ItemType (devices, armor)
- StationType uses Sovereign
- ItemType uses ItemType (weapons)

**Visualization**:
```
MyShip [ShipClass]
  → itLaserCannon [ItemType]
```

### 2. Spawns 🎲
**Meaning**: Type spawns another type

**Examples**:
- StationType spawns ShipClass
- StationType spawns Encounter
- Table spawns ShipClass

**Visualization**:
```
MyStation [StationType]
  → MyShip [ShipClass]
```

### 3. Overrides 🔄
**Meaning**: Type overrides another type

**Examples**:
- StationTypeOverride overrides StationType
- TypeOverride overrides base type

**Visualization**:
```
MyOverride [StationType]
  → BaseStation [StationType]
```

### 4. Inherits 🧬
**Meaning**: Type inherits from parent type

**Examples**:
- ShipClass inherits from base ship
- StationType inherits from base station

**Visualization**:
```
MyShip [ShipClass]
  → BaseShip [ShipClass]
```

### 5. Calls Event On 📞
**Meaning**: Type calls event on another type

**Examples**:
- objFireEvent calls event on object
- typFireEvent calls event on type

**Visualization**:
```
MyItem [ItemType]
  → TargetItem [ItemType] (event: OnCreate)
```

## Graph Summary

The graph shows:
- **Total Nodes**: All types found
- **Total Relationships**: All connections
- **Relationship Types**: Breakdown by type
- **Node Types**: Count by category

## Use Cases

### Debugging Complex Mods
- See all relationships at a glance
- Find circular dependencies
- Track type usage

### Balancing Spawn Tables
- Visualize what spawns what
- See spawn chains
- Balance encounter rates

### Understanding Mod Structure
- Map type dependencies
- See inheritance chains
- Track overrides

### Finding Issues
- Missing references
- Circular dependencies
- Override conflicts

## Example Graph

```
═══════════════════════════════════════════════════════════
                    GRAPH SUMMARY
═══════════════════════════════════════════════════════════

Total Nodes: 45
Total Relationships: 127

Relationship Types:
  calls_event_on: 12
  inherits: 8
  overrides: 3
  spawns: 45
  uses: 59

═══════════════════════════════════════════════════════════
USES
═══════════════════════════════════════════════════════════

  MyShip [ShipClass]
    → itLaserCannon [ItemType]
  MyStation [StationType]
    → svPlayer [Sovereign]

═══════════════════════════════════════════════════════════
SPAWNS
═══════════════════════════════════════════════════════════

  MyStation [StationType]
    → MyShip [ShipClass]
  MyStation [StationType]
    → Encounter [Encounter]
```

## Tips

- **Large Graphs**: Use Export to review offline
- **Spawn Tables**: Focus on "spawns" relationships
- **Dependencies**: Focus on "uses" relationships
- **Overrides**: Check "overrides" for conflicts
- **Inheritance**: Use "inherits" to see type hierarchy

---

The Enhanced Dependency Graph helps you understand your mod's complete structure!

