# Starbound Behavior Generator Guide

A PowerShell tool for generating Starbound/OpenStarbound behavior tree files (`.behavior`) for monster and NPC AI.

## Overview

Starbound uses behavior trees for AI logic. These are JSON files that define decision-making patterns through a hierarchy of nodes:

- **Composite Nodes**: Control flow (sequence, selector, parallel, dynamic)
- **Action Nodes**: Leaf nodes that do things (move, attack, timer, etc.)
- **Decorator Nodes**: Modifiers (repeater, inverter, cooldown, etc.)
- **Module Nodes**: References to other behavior files for reusability

## Quick Start

```powershell
# Generate a basic monster behavior
.\StarboundBehaviorGenerator.ps1 -BehaviorName "mymonster" -Preset Default

# Generate a boss with health stages
.\StarboundBehaviorGenerator.ps1 -BehaviorName "myboss" -Preset Boss -HealthStages 3

# Generate a ranged attacker
.\StarboundBehaviorGenerator.ps1 -BehaviorName "archer" -Preset Ranged -ProjectileType "flarrow"
```

## Available Presets

| Preset | Description |
|--------|-------------|
| `Default` | Basic monster with targeting, chase, and melee attack |
| `Patrol` | Walks between patrol points near home position |
| `Attack` | Single attack action (standalone, for modules) |
| `Flee` | Runs away from target |
| `Chase` | Follows target until in range |
| `Guard` | Guards a position, engages intruders, returns to post |
| `Boss` | Multi-stage boss with health thresholds and damage bar |
| `Ranged` | Maintains distance, fires projectiles |
| `Melee` | Close-range combat |
| `Idle` | Stands in place with idle animation |
| `Wander` | Random movement pattern |
| `Targeting` | Just the monster-targeting module |
| `Custom` | Use with `-CustomRoot` for fully custom behaviors |

## Parameters

### Basic Parameters

```powershell
-BehaviorName     # Required. Internal name and filename
-Preset           # Behavior preset (see above)
-OutputDir        # Output directory (default: "StarboundBehaviors")
-Description      # Optional description
```

### Combat Parameters

```powershell
-AggroRange       # Detection range (default: 30)
-DeaggroRange     # Range to lose target (default: 50)
-AttackRange      # Melee attack range (default: 5)
-MoveSpeed        # Movement speed (default: 8)
-AttackCooldown   # Time between attacks (default: 1.0)
-ProjectileType   # Projectile to fire (enables ranged attacks)
-ProjectileOffset # Spawn offset for projectiles [x, y]
```

### Animation Parameters

```powershell
-AttackAnimation  # Animation state for attacking (default: "attack")
-IdleAnimation    # Animation state for idle (default: "idle")
-WalkAnimation    # Animation state for walking (default: "walk")
```

### Boss Parameters

```powershell
-HealthStages      # Number of health stages
-HealthThresholds  # Array of health percentages (default: @(0.66, 0.33))
-HasDamageBar      # Show boss health bar
```

### Patrol Parameters

```powershell
-PatrolRadius     # Patrol area size (default: 20)
-PatrolIdleTime   # Time to wait at each point (default: 2)
```

### Advanced Parameters

```powershell
-TargetTypes        # Entity types to target (default: @("player"))
-AdditionalScripts  # Extra Lua scripts to include
-Modules           # Module references to include
-CustomRoot        # Custom root node hashtable (for Custom preset)
```

## Examples

### Basic Monster

```powershell
.\StarboundBehaviorGenerator.ps1 `
    -BehaviorName "basicmonster" `
    -Preset Default `
    -AggroRange 25 `
    -AttackRange 3 `
    -MoveSpeed 10
```

### Guard Monster

```powershell
.\StarboundBehaviorGenerator.ps1 `
    -BehaviorName "guardian" `
    -Preset Guard `
    -PatrolRadius 10 `
    -AggroRange 20 `
    -AttackRange 4
```

### Ranged Attacker

```powershell
.\StarboundBehaviorGenerator.ps1 `
    -BehaviorName "archer-behavior" `
    -Preset Ranged `
    -ProjectileType "flarrow" `
    -ProjectileOffset @(1.5, 0.5) `
    -AttackCooldown 1.5 `
    -AggroRange 40
```

### Multi-Stage Boss

```powershell
.\StarboundBehaviorGenerator.ps1 `
    -BehaviorName "myboss" `
    -Preset Boss `
    -HealthStages 3 `
    -HealthThresholds @(0.75, 0.50, 0.25) `
    -HasDamageBar `
    -ProjectileType "fireball" `
    -ProjectileOffset @(2, 0) `
    -AggroRange 60
```

### Patrol Monster

```powershell
.\StarboundBehaviorGenerator.ps1 `
    -BehaviorName "patroller" `
    -Preset Patrol `
    -PatrolRadius 30 `
    -PatrolIdleTime 3 `
    -MoveSpeed 5
```

## Behavior Tree Structure

### Generated File Format

```json
{
  "name": "mybehavior",
  "description": "",
  "scripts": [
    "/scripts/actions/movement.lua",
    "/scripts/actions/time.lua",
    "/scripts/actions/entity.lua"
  ],
  "parameters": {},
  "root": {
    "title": "MainBehavior",
    "type": "composite",
    "name": "sequence",
    "parameters": {},
    "children": [...]
  }
}
```

### Node Types

#### Composite Nodes

| Type | Description |
|------|-------------|
| `sequence` | Runs children in order, fails on first failure |
| `selector` | Runs children until one succeeds |
| `parallel` | Runs children simultaneously |
| `dynamic` | Re-evaluates priorities each tick |

#### Common Action Nodes

| Action | Description |
|--------|-------------|
| `timer` | Waits for specified time |
| `faceEntity` | Turns to face target |
| `moveToEntity` | Moves toward target |
| `spawnProjectile` | Creates a projectile |
| `setAnimationState` | Changes animation |
| `playSound` | Plays a sound effect |
| `entityExists` | Checks if entity is valid |
| `entityInRange` | Checks distance to entity |
| `wasDamaged` | Reacts to taking damage |

#### Decorator Nodes

| Decorator | Description |
|-----------|-------------|
| `repeater` | Repeats child node |
| `inverter` | Inverts child result |
| `succeeder` | Always returns success |
| `cooldown` | Limits execution frequency |

## Integration with MultiAssetGenerator

The behavior generator is integrated with `MultiAssetGenerator.ps1`:

```powershell
.\MultiAssetGenerator.ps1 `
    -GameType Starbound `
    -AssetType Behavior `
    -AssetName "mymonster" `
    -Description "aggressive fire monster"
```

## Script Dependencies

The generator automatically includes required Lua scripts based on the preset:

| Script | Purpose |
|--------|---------|
| `/scripts/actions/movement.lua` | Movement actions |
| `/scripts/actions/entity.lua` | Entity queries |
| `/scripts/actions/time.lua` | Timers and delays |
| `/scripts/actions/animator.lua` | Animation control |
| `/scripts/actions/projectiles.lua` | Projectile spawning |
| `/scripts/actions/status.lua` | Health/status checks |
| `/scripts/actions/monster.lua` | Monster-specific actions |
| `/scripts/behavior/bdata.lua` | Behavior data utilities |

## Tips

1. **Start Simple**: Use presets first, then customize
2. **Test Incrementally**: Test each behavior change in-game
3. **Use Modules**: Break complex behaviors into reusable modules
4. **Check Logs**: Starbound's `starbound.log` shows behavior errors
5. **Watch Health Thresholds**: Boss stages trigger at exact percentages

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Monster doesn't move | Check movement scripts are included |
| No attacks | Verify attack animation state exists |
| Projectile not spawning | Check projectile type name is correct |
| Boss doesn't die | Ensure death sequence is reached |
| Infinite loop | Add `runner` nodes at end of dynamic children |

## See Also

- `StarboundParticleGenerator.ps1` - For particle effects
- `StarboundAnimationGenerator.ps1` - For animation files
- `MultiAssetGenerator.ps1` - For batch asset generation

