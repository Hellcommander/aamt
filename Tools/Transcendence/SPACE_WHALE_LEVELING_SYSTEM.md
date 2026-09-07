# Space Whale Leveling System

## Overview

The Space Whale uses the **same leveling system as Evolved Ships** - it scales with the player's level from `objGetLevel`, which ranges from **level 1 to level 50**.

## Level Source

```lisp
(setq level (objGetLevel gSource))  ; Get player level (1-50)
```

This is the same mechanism used by all evolved ships in the mod system.

## Size Scaling

### Base Size (Level 1 - Tier 1 Balanced)
- **Length**: 4.0 units
- **Width**: 1.75 units  
- **Height**: 1.0 units
- **Description**: Balanced for tier 1 content, starts small like a regular ship

### Maximum Size (Level 50 - Tier 5 Capital Ship)
- **Length**: 8.0 units
- **Width**: 3.5 units
- **Height**: 2.0 units
- **Description**: Full capital ship scale, massive presence

### Scaling Formula

**Linear Scaling:**
```
length = 4.0 + (level - 1) * 0.082
width = 1.75 + (level - 1) * 0.036
height = 1.0 + (level - 1) * 0.020
```

**Growth Per Level:**
- Length: +0.082 per level
- Width: +0.036 per level
- Height: +0.020 per level

## Stat Scaling

All stats scale linearly from level 1 to level 50:

### Hull HP
- **Base (L1)**: 500
- **Max (L50)**: 2000
- **Per Level**: +30.61

### Armor
- **Base (L1)**: 50
- **Max (L50)**: 150
- **Per Level**: +2.04

### Mass
- **Base (L1)**: 2000
- **Max (L50)**: 5000
- **Per Level**: +61.22
- **Scales with size**: Yes

### Bio-Core Max Energy
- **Base (L1)**: 400
- **Max (L50)**: 1000
- **Per Level**: +12.24

### Orbit Field Radius
- **Base (L1)**: 1.5
- **Max (L50)**: 2.5
- **Per Level**: +0.020
- **Scales with size**: Yes

### Drone Bay Max Drones
- **Base (L1)**: 6
- **Max (L50)**: 12
- **Per Level**: +0.122 (rounded down)

## Tier Mapping

| Tier | Level Range | Size Range | Description |
|------|-------------|------------|-------------|
| Tier 1 | 1-10 | 4.0-4.74 length | Starting size, balanced for early game |
| Tier 2 | 11-20 | 4.82-5.64 length | Growing, mid-game size |
| Tier 3 | 21-30 | 5.64-6.46 length | Large, late-game size |
| Tier 4 | 31-40 | 6.54-7.36 length | Very large, end-game size |
| Tier 5 | 41-50 | 7.36-8.0 length | Maximum capital ship scale |

## Implementation in XML

The Space Whale already uses the evolved ship leveling system:

```xml
<OnCreate>
    ; Initialize as Evolved Ship (for mod system integration)
    (objSetData gSource 'evolvedShip true)
    
    ; Get player level (same as evolved ships)
    (setq level (objGetLevel gSource))
    
    ; Calculate size from level
    (setq sizeScale (swCalculateSizeFromLevel level))
    
    ; Apply size scaling to ship
    (objSetScale gSource sizeScale)
</OnCreate>
```

## Visual Scaling

All visual modules scale proportionally:
- **Head Module**: Scales with ship size
- **Mid Section**: Scales with ship size
- **Belly Bay**: Scales with ship size
- **Tail**: Scales with ship size
- **Dorsal Crest**: Scales with ship size

## Balance Notes

- **Level 1**: Starts small (4.0×1.75×1.0) - balanced for tier 1 content
- **Level 10**: End of tier 1 (4.74×2.11×1.18) - still manageable
- **Level 25**: Mid-game (5.97×2.61×1.48) - noticeable growth
- **Level 50**: Maximum (8.0×3.5×2.0) - full capital ship scale

The ship grows gradually, ensuring it's always balanced for the player's current level and tier content.

