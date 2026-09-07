# Remaining System Asset Generation Guide

Generate assets for UI, Weapons, Wildfire, Status Effects, Traps, and Tiles systems.

## Quick Start

```powershell
# Generate all remaining system assets
.\GenerateRemainingSystemAssets.ps1

# Use C++ backend for better quality
.\GenerateRemainingSystemAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### UI Elements (9 elements)

1. **ui_spell_mod_icon_template** - Spell mod icon template
2. **ui_button_default** - Default button
3. **ui_button_hover** - Button hover state
4. **ui_button_pressed** - Button pressed state
5. **ui_panel_background** - Panel background
6. **ui_panel_border** - Panel border
7. **ui_scrollbar** - Scrollbar element
8. **ui_slot_template** - Slot template
9. **ui_overflow_indicator** - Overflow indicator

### Weapon Sprites and Sub-Ability Icons (7 assets)

1. **weapon_sword_basic** - Basic sword
2. **weapon_bow_basic** - Basic bow
3. **weapon_staff_basic** - Basic staff
4. **weapon_pistol_basic** - Basic pistol
5. **subability_icon_template** - Sub-ability icon template
6. **subability_cooldown** - Sub-ability cooldown indicator
7. **subability_ready** - Sub-ability ready indicator

### Cluster Bomb Sprites (11 sprites)

1. **cluster_bomb_explosive** - Explosive cluster bomb
2. **cluster_bomb_incendiary** - Incendiary cluster bomb
3. **cluster_bomb_shrapnel** - Shrapnel cluster bomb
4. **cluster_bomb_plasma** - Plasma cluster bomb
5. **cluster_bomb_cryo** - Cryo cluster bomb
6. **cluster_bomb_poison_gas** - Poison gas cluster bomb
7. **cluster_bomb_emp** - EMP cluster bomb
8. **cluster_bomb_gravity** - Gravity cluster bomb
9. **cluster_bomb_temporal** - Temporal cluster bomb
10. **cluster_bomb_arcane** - Arcane cluster bomb
11. **cluster_bomb_void** - Void cluster bomb

### Wildfire Effects (6 effects)

1. **wildfire_fire_particle** - Wildfire fire particle
2. **wildfire_smoke** - Wildfire smoke
3. **wildfire_ember** - Wildfire ember
4. **wildfire_ignition** - Wildfire ignition
5. **wildfire_extinguish** - Wildfire extinguish
6. **wildfire_texture** - Wildfire texture

### Status Effect Icons and Particles (11 assets)

1. **status_burn** - Burn status icon
2. **status_freeze** - Freeze status icon
3. **status_poison** - Poison status icon
4. **status_stun** - Stun status icon
5. **status_slow** - Slow status icon
6. **status_regeneration** - Regeneration status icon
7. **status_strength** - Strength status icon
8. **status_weakness** - Weakness status icon
9. **status_burn_particle** - Burn particle effect
10. **status_freeze_particle** - Freeze particle effect
11. **status_poison_particle** - Poison particle effect

### Trap Sprites and Effects (7 assets)

1. **trap_spike** - Spike trap
2. **trap_pressure_plate** - Pressure plate trap
3. **trap_arrow** - Arrow trap
4. **trap_fire** - Fire trap
5. **trap_poison** - Poison trap
6. **trap_activation** - Trap activation effect
7. **trap_disarmed** - Trap disarmed effect

### Tile Textures (8 textures)

1. **tile_stone** - Stone tile
2. **tile_dirt** - Dirt tile
3. **tile_grass** - Grass tile
4. **tile_sand** - Sand tile
5. **tile_wood** - Wood tile
6. **tile_metal** - Metal tile
7. **tile_brick** - Brick tile
8. **tile_cobblestone** - Cobblestone tile

## Total: ~59 Assets

## Output Structure

```
assets/
├── ui/
│   └── elements/
│       ├── ui_spell_mod_icon_template.png
│       ├── ui_button_default.png
│       ├── ui_button_hover.png
│       └── ... (all UI elements)
├── weapons/
│   ├── sprites/
│   │   ├── weapon_sword_basic.png
│   │   ├── weapon_bow_basic.png
│   │   └── ... (all weapon sprites)
│   └── cluster_bombs/
│       ├── cluster_bomb_explosive.png
│       ├── cluster_bomb_incendiary.png
│       └── ... (all cluster bomb sprites)
├── wildfire/
│   ├── wildfire_fire_particle.particle
│   ├── wildfire_smoke.particle
│   └── ... (all wildfire effects)
├── status_effects/
│   ├── status_burn.png
│   ├── status_freeze.png
│   └── ... (all status effects)
├── traps/
│   ├── trap_spike.png
│   ├── trap_pressure_plate.png
│   └── ... (all trap assets)
└── tiles/
    ├── tile_stone.png
    ├── tile_dirt.png
    └── ... (all tile textures)
```

## Integration

### UI Module

```cpp
// Display spell mods
EnhancedSpellModDisplay::showGrid(mods);
// Uses: /ui/elements/ui_spell_mod_icon_template.png for mod icons
// Uses: /ui/elements/ui_panel_background.png for panel
// Uses: /ui/elements/ui_button_*.png for buttons
// Uses: /ui/elements/ui_scrollbar.png for scrolling
```

### Weapons Module

```cpp
// Generate weapon
WeaponGenerationSystem::generateWeapon(definition);
// Uses: /weapons/sprites/weapon_*.png based on weapon type

// Sub-ability system
SubAbilityManager::equip(weaponId, abilityId, slot);
// Uses: /weapons/sprites/subability_icon_template.png for icons
// Uses: /weapons/sprites/subability_cooldown.png for cooldown
// Uses: /weapons/sprites/subability_ready.png for ready state
```

### Cluster Bomb System

```cpp
// Spawn cluster bomb
ClusterBombSystem::spawnClusterBomb(definition);
// Uses: /weapons/cluster_bombs/cluster_bomb_*.png based on type
```

### Wildfire System

```cpp
// Ignite fire
FireSimulationManager::ignite(x, y);
// Uses: /wildfire/wildfire_fire_particle.particle
// Uses: /wildfire/wildfire_texture.png for fire cells
// Uses: /wildfire/wildfire_smoke.particle for smoke
// Uses: /wildfire/wildfire_ember.particle for embers

// Extinguish fire
FireSimulationManager::extinguish(x, y, radius);
// Uses: /wildfire/wildfire_extinguish.particle
```

### Status Effect System

```cpp
// Apply status effect
applyStatusEffect(entityId, "burn");
// Uses: /status_effects/status_burn.png for icon
// Uses: /status_effects/status_burn_particle.particle for effect
```

### Trap System

```cpp
// Place trap
placeTrap(position, "spike");
// Uses: /traps/trap_spike.png for sprite

// Activate trap
activateTrap(trapId);
// Uses: /traps/trap_activation.particle for activation effect
```

### Tile Library

```cpp
// Build tile library
TileLibraryBuilder::addTile("stone", texture);
// Uses: /tiles/tile_stone.png for stone tiles
```

## System Details

### UI Elements

- **Spell Mod Icons**: 32x32 icons for spell modifiers
- **Buttons**: 64x32 sprites with hover/pressed states
- **Panels**: 128x128 backgrounds and borders
- **Scrollbars**: 16x64 scrollbar elements
- **Slots**: 32x32 item slot templates

### Weapon Categories

- **Melee**: Swords, axes, hammers, spears, daggers
- **Ranged**: Bows, crossbows, slings
- **Firearms**: Pistols, rifles, shotguns
- **Energy**: Laser rifles, plasma guns
- **Magic**: Wands, staves, orbs
- **Thrown**: Daggers, spears, grenades
- **Heavy**: Cannons, launchers
- **Shield**: Defensive weapons
- **Hybrid**: Multi-mode weapons

### Cluster Bomb Types

- **Explosive**: Standard explosive
- **Incendiary**: Fire/napalm
- **Shrapnel**: Metal fragments
- **Plasma**: Energy/plasma
- **Cryo**: Freezing/ice
- **Poison Gas**: Chemical weapon
- **EMP**: Electronic disruption
- **Gravity**: Gravitational anomalies
- **Temporal**: Time distortion
- **Arcane**: Magic clusters
- **Void**: Void/antimatter

### Status Effects

- **Burn**: Fire damage over time
- **Freeze**: Ice damage, movement reduction
- **Poison**: Toxic damage over time
- **Stun**: Unable to act
- **Slow**: Movement speed reduction
- **Regeneration**: Health regeneration
- **Strength**: Damage boost
- **Weakness**: Damage reduction

### Trap Types

- **Spike**: Physical damage trap
- **Pressure Plate**: Trigger-based trap
- **Arrow**: Projectile trap
- **Fire**: Fire damage trap
- **Poison**: Toxic damage trap

### Tile Types

- **Stone**: Stone tiles
- **Dirt**: Dirt tiles
- **Grass**: Grass tiles
- **Sand**: Sand tiles
- **Wood**: Wood tiles
- **Metal**: Metal tiles
- **Brick**: Brick tiles
- **Cobblestone**: Cobblestone tiles

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateRemainingSystemAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Systems

Set up system configurations with asset paths.

### Step 3: Test in Game

Load the mod and test all systems in-game.

## Advanced Options

### Custom UI Elements

Edit `GenerateRemainingSystemAssets.ps1` to add custom UI elements.

### Custom Weapon Types

Add custom weapon sprites to the `$weaponSprites` array.

### Custom Cluster Bomb Types

Add custom cluster bomb sprites to the `$clusterBombTypes` array.

### Custom Status Effects

Add custom status effect icons/particles to the `$statusEffects` array.

### Custom Traps

Add custom trap sprites/effects to the `$traps` array.

### Custom Tiles

Add custom tile textures to the `$tiles` array.

## Tips

1. **UI elements**: Use appropriate sizes (32x32 for icons, 64x32 for buttons)
2. **Weapon sprites**: Use 64x64 for most weapons
3. **Cluster bombs**: Use 32x32 for cluster bomb sprites
4. **Status effects**: Use 32x32 for status icons
5. **Tiles**: Use 16x16 for seamless tiles
6. **Particle effects**: Match particle colors to effect type

## Troubleshooting

### UI Not Displaying

- Check UI element paths
- Verify elements are in `assets/ui/elements/`
- Ensure UI system is initialized

### Weapons Not Showing

- Check weapon sprite paths
- Verify sprites are in `assets/weapons/sprites/`
- Ensure weapon system is initialized

### Wildfire Not Working

- Check wildfire effect paths
- Verify effects are in `assets/wildfire/`
- Ensure wildfire system is initialized

### Status Effects Not Appearing

- Check status effect paths
- Verify effects are in `assets/status_effects/`
- Ensure status effect system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
