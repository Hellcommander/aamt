# Tech Module System Asset Generation Guide

Generate assets for the Tech Module System including module icons, drone sprites, sensor effects, overclock effects, field effects, and energy core icons.

## Quick Start

```powershell
# Generate all tech assets
.\GenerateTechAssets.ps1

# Use C++ backend for better quality
.\GenerateTechAssets.ps1 -UseCppBackend

# Or generate everything including tech assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Tech Module Icons (6 icons)

1. **tech_module_icon** - Generic tech module icon
2. **tech_module_drone** - Drone module icon
3. **tech_module_sensor** - Sensor module icon
4. **tech_module_field** - Field module icon
5. **tech_module_overclock** - Overclock module icon
6. **tech_module_energy** - Energy module icon

### Drone Sprites (6 sprites)

1. **drone_basic** - Basic drone
2. **drone_combat** - Combat drone
3. **drone_repair** - Repair drone
4. **drone_scout** - Scout drone
5. **drone_cargo** - Cargo drone
6. **drone_mining** - Mining drone

### Sensor Visual Effects (3 effects)

1. **sensor_scan** - Sensor scan particle effect
2. **sensor_detection** - Sensor detection particle effect
3. **sensor_range** - Sensor range indicator texture

### Overclock Visual Effects (4 effects)

1. **overclock_active** - Overclock active particle effect
2. **overclock_heat** - Overclock heat particle effect
3. **overclock_overheat** - Overclock overheat particle effect
4. **overclock_heat_indicator** - Overclock heat indicator icon

### Field Module Effects (5 effects)

1. **field_effect_shield** - Shield field particle effect
2. **field_effect_heal** - Heal field particle effect
3. **field_effect_damage** - Damage field particle effect
4. **field_effect_slow** - Slow field particle effect
5. **field_range_indicator** - Field range indicator texture

### Energy Core Icons (4 icons)

1. **energy_core_icon** - Energy core icon
2. **energy_core_full** - Energy core full indicator
3. **energy_core_empty** - Energy core empty indicator
4. **energy_core_charging** - Energy core charging indicator

## Total: ~28 Assets

## Output Structure

```
assets/
└── tech/
    ├── tech_module_icon.png
    ├── tech_module_drone.png
    ├── ... (all module icons)
    ├── drone_basic.png
    ├── drone_combat.png
    ├── ... (all drone sprites)
    ├── sensor_scan.particle
    ├── sensor_detection.particle
    ├── sensor_range.png
    ├── overclock_active.particle
    ├── overclock_heat.particle
    ├── overclock_overheat.particle
    ├── overclock_heat_indicator.png
    ├── field_effect_shield.particle
    ├── field_effect_heal.particle
    ├── field_effect_damage.particle
    ├── field_effect_slow.particle
    ├── field_range_indicator.png
    ├── energy_core_icon.png
    ├── energy_core_full.png
    ├── energy_core_empty.png
    └── energy_core_charging.png
```

## Integration

### Tech Module Icons

```lua
-- Use module icons in UI
local moduleIcon = "/tech/tech_module_drone.png"
-- Display in module selection UI
```

### Drone Sprites

```lua
-- Spawn drone with sprite
DroneModuleManager:spawnDrone(ownerID, "drone_basic", position)
-- Drone sprite: /tech/drone_basic.png
```

### Sensor Effects

```lua
-- Display sensor scan effect
SensorModuleManager:scan(ownerID, position)
-- Show sensor_scan.particle effect at position
```

### Overclock Effects

```lua
-- Show overclock active effect
OverclockManager:setActive(itemID, true)
-- Display overclock_active.particle effect

-- Show heat indicator
local heat = OverclockManager:getHeat(itemID)
-- Display heat indicator based on heat level
```

### Field Module Effects

```lua
-- Emit field with effect
FieldModuleManager:emitField(position, radius, duration, "shield")
-- Display field_effect_shield.particle effect
```

### Energy Core Icons

```lua
-- Display energy core status
local energy = EnergyCoreManager:getCurrent(itemID)
local maxEnergy = EnergyCoreManager:getCapacity(itemID)
-- Display appropriate energy core icon based on level
```

## Tech Module Types

### Drone Modules
- **Basic**: General purpose drone
- **Combat**: Armed combat drone
- **Repair**: Repair and maintenance drone
- **Scout**: Scouting and reconnaissance drone
- **Cargo**: Cargo transport drone
- **Mining**: Mining and resource gathering drone

### Sensor Modules
- **Scan**: Active scanning for enemies/resources
- **Detection**: Detection pulse effects
- **Range**: Visual range indicator

### Overclock Modules
- **Active**: Speed/power boost effects
- **Heat**: Heat buildup effects
- **Overheat**: Critical heat warning effects

### Field Modules
- **Shield**: Protective barrier field
- **Heal**: Healing field effect
- **Damage**: Damage field effect
- **Slow**: Slowing field effect

### Energy Cores
- **Full**: Maximum energy indicator
- **Empty**: No energy indicator
- **Charging**: Recharging indicator

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateTechAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure Modules

Configure tech modules with asset references.

### Step 3: Integrate Effects

Integrate particle effects and visual indicators.

### Step 4: Test in Game

Load the mod and test tech modules in-game.

## Advanced Options

### Custom Drone Types

Edit `GenerateTechAssets.ps1` to add custom drone types:

```powershell
@{
    Id = "drone_custom"
    Name = "Custom Drone"
    Description = "Custom drone description"
}
```

### Custom Field Effects

Add custom field effects to the `$fieldEffects` array.

### Custom Module Icons

Add custom module icons to the `$techModuleIcons` array.

## Tips

1. **Icon size**: Use 32x32 for UI icons
2. **Drone size**: Use 32x32 for drone sprites
3. **Effect particles**: Create distinct effects for each module type
4. **Indicators**: Use clear visual indicators for status
5. **Range indicators**: Use circular textures for range visualization

## Troubleshooting

### Icons Not Appearing

- Check icon paths in module definitions
- Verify icons are in `assets/tech/`
- Ensure UI system is loading icons

### Drones Not Spawning

- Check drone sprite paths
- Verify drone definitions reference correct sprites
- Ensure drone system is initialized

### Effects Not Playing

- Verify particle files are in correct location
- Check effect paths in module definitions
- Ensure particle system is initialized

---

*Part of the Starbound Ollama Asset Generator suite*
