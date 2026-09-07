# Dependency Graph - User Guide

## Overview

The Dependency Graph visualizes relationships between mod elements, helping you understand how your mod's components interact.

## What It Shows

### Relationship Types

1. **Items → Weapons** (`uses_weapon`)
   - Which items use which weapons
   - Found in `<Weapon type="...">` elements

2. **Ships → Items** (`uses_item`, `carries_item`)
   - Which ships have which devices installed
   - Which ships carry which items in cargo
   - Found in `<Device>` and `<Items>` elements

3. **Stations → Encounters** (`spawns_encounter`)
   - Which stations spawn encounters
   - Found in `<Encounter>` elements

4. **Stations → Ships** (`spawns_ships`)
   - Which stations spawn which ships
   - Found in `<Ships>` and `<Reinforcements>` elements

5. **Items → Events** (`has_event`)
   - Which items have event handlers
   - Found in `<Events>` and `<On*>` elements

## How to Use

1. Go to **Dependency Graph** tab
2. Enter your mod folder path
3. Click **Generate Graph**
4. Review the relationships
5. Click **Export** to save the graph

## Graph Format

```
═══════════════════════════════════════════════════════════
                    DEPENDENCY GRAPH
═══════════════════════════════════════════════════════════

Items: 15
Ships: 8
Stations: 5
Relationships: 42

═══════════════════════════════════════════════════════════
CARRIES_ITEM
═══════════════════════════════════════════════════════════

  MyShip (Ship)
    → itLaserCannon (Item)

═══════════════════════════════════════════════════════════
USES_WEAPON
═══════════════════════════════════════════════════════════

  MyWeapon (Item)
    → vtLaserBeam (Weapon)
```

## Use Cases

### Debugging Complex Mods
- See which items depend on which weapons
- Find orphaned items (no relationships)
- Understand item dependencies

### Mod Architecture
- Visualize mod structure
- Plan refactoring
- Document mod relationships

### Compatibility Checking
- See which mods share dependencies
- Identify potential conflicts
- Plan mod load order

## Tips

- **Large mods**: The graph can be extensive - use Export to review offline
- **Filtering**: Currently shows all relationships - future versions may add filtering
- **Visualization**: Text-based for now - future versions may add visual graphs

---

The Dependency Graph helps you understand your mod's structure and relationships!

