# Ship Steering System Asset Generation Guide

Generate assets for the Ship Steering System including thrusters, weapons, shields, landing effects, hazards, combat impacts, and steering indicators.

## Quick Start

```powershell
# Generate all ship steering assets
.\GenerateShipSteeringAssets.ps1

# Use C++ backend for better quality
.\GenerateShipSteeringAssets.ps1 -UseCppBackend

# Or generate everything including ship steering assets
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Thruster/Engine Effects (7 effects)

1. **thruster_exhaust_chemical** - Chemical thruster exhaust
2. **thruster_exhaust_nuclear** - Nuclear thruster exhaust
3. **thruster_exhaust_ion** - Ion thruster exhaust
4. **thruster_exhaust_plasma** - Plasma thruster exhaust
5. **thruster_exhaust_fusion** - Fusion thruster exhaust
6. **thruster_trail** - Thruster trail
7. **engine_afterburner** - Afterburner effect

### Weapon Projectiles (8 projectiles)

1. **projectile_laser** - Laser projectile
2. **projectile_plasma** - Plasma projectile
3. **projectile_missile** - Missile projectile
4. **projectile_kinetic** - Kinetic projectile
5. **projectile_ion** - Ion projectile
6. **projectile_emp** - EMP projectile
7. **projectile_torpedo** - Torpedo projectile
8. **projectile_beam** - Beam projectile

### Shield Visual Effects (4 effects)

1. **shield_active** - Active shield
2. **shield_hit** - Shield hit
3. **shield_regen** - Shield regeneration
4. **shield_depleted** - Shield depleted

### Landing/Takeoff Effects (3 effects)

1. **landing_effect** - Landing particle effect
2. **takeoff_effect** - Takeoff particle effect
3. **landing_zone_marker** - Landing zone marker icon

### Hazard Warning Indicators (5 indicators)

1. **hazard_warning_low** - Low hazard warning icon
2. **hazard_warning_medium** - Medium hazard warning icon
3. **hazard_warning_high** - High hazard warning icon
4. **hazard_warning_critical** - Critical hazard warning icon
5. **hazard_effect** - Hazard particle effect

### Combat Impact Effects (8 effects)

1. **impact_laser** - Laser impact
2. **impact_plasma** - Plasma impact
3. **impact_missile** - Missile impact
4. **impact_kinetic** - Kinetic impact
5. **impact_ion** - Ion impact
6. **impact_emp** - EMP impact
7. **impact_torpedo** - Torpedo impact
8. **impact_beam** - Beam impact

### Steering Indicators (4 indicators)

1. **steering_waypoint** - Waypoint indicator
2. **steering_path** - Path indicator
3. **steering_autopilot** - Autopilot indicator
4. **steering_velocity** - Velocity indicator

## Total: ~39 Assets

## Output Structure

```
assets/
├── ships/
│   ├── thrusters/
│   │   ├── thruster_exhaust_chemical.particle
│   │   ├── thruster_exhaust_nuclear.particle
│   │   └── ... (all thruster effects)
│   ├── weapons/
│   │   ├── projectile_laser.png
│   │   ├── projectile_plasma.png
│   │   └── ... (all weapon projectiles)
│   ├── shields/
│   │   ├── shield_active.particle
│   │   ├── shield_hit.particle
│   │   └── ... (all shield effects)
│   ├── landing/
│   │   ├── landing_effect.particle
│   │   ├── takeoff_effect.particle
│   │   └── landing_zone_marker.png
│   ├── hazards/
│   │   ├── hazard_warning_low.png
│   │   ├── hazard_warning_medium.png
│   │   └── ... (all hazard indicators)
│   ├── combat/
│   │   ├── impact_laser.particle
│   │   ├── impact_plasma.particle
│   │   └── ... (all impact effects)
│   └── steering/
│       ├── steering_waypoint.png
│       ├── steering_path.png
│       └── ... (all steering indicators)
```

## Integration

### Ship Steering

```cpp
// Register ship for steering
ShipSteeringModule::instance().registerShip(shipId, "default");
// Uses: /ships/steering/steering_*.png for indicators
```

### Thruster Effects

```cpp
// Apply thruster effects based on fuel type
FlightControlModule::setFuelType(aircraftId, FuelType::Ion);
// Uses: /ships/thrusters/thruster_exhaust_ion.particle
```

### Weapon Systems

```cpp
// Fire weapon
FlightControlModule::fireWeapon(aircraftId, weaponMountId);
// Uses: /ships/weapons/projectile_*.png for projectiles
// Uses: /ships/combat/impact_*.particle for impacts
```

### Shield Systems

```cpp
// Activate shields
CombatState.shields.isActive = true;
// Uses: /ships/shields/shield_active.particle
// Uses: /ships/shields/shield_hit.particle on impact
```

### Landing/Takeoff

```cpp
// Apply landing effects
FlightControlModule::applyLandingEffects(aircraftId);
// Uses: /ships/landing/landing_effect.particle
// Uses: /ships/landing/landing_zone_marker.png
```

### Hazard Avoidance

```cpp
// Check hazards
HazardManager::instance().avoidanceInfo(position);
// Uses: /ships/hazards/hazard_warning_*.png for warnings
// Uses: /ships/hazards/hazard_effect.particle for visual
```

## Weapon Types

### Projectile Types
- **Laser**: Red energy beam
- **Plasma**: Purple/pink plasma
- **Missile**: Rocket with trail
- **Kinetic**: Bullet/shell
- **Ion**: Blue/purple ion
- **EMP**: Electrical energy
- **Torpedo**: Large explosive
- **Beam**: Continuous energy beam

## Fuel Types

### Thruster Types
- **Chemical**: Orange/yellow flame (LOX/LH2, RP-1)
- **Nuclear**: Blue/white energy
- **Ion**: Blue/purple ion stream
- **Plasma**: Purple/pink plasma
- **Fusion**: White/blue fusion energy

## Shield States

### Shield Effects
- **Active**: Energy barrier visible
- **Hit**: Impact on shield surface
- **Regen**: Energy rebuilding
- **Depleted**: Shield failure

## Hazard Levels

### Warning Levels
- **Low**: Yellow warning
- **Medium**: Orange warning
- **High**: Red warning
- **Critical**: Red flashing warning

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateShipSteeringAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Register Ships

Register ships with the steering system.

### Step 3: Configure Systems

Configure thrusters, weapons, and shields.

### Step 4: Test in Game

Load the mod and test ship steering in-game.

## Advanced Options

### Custom Thruster Types

Edit `GenerateShipSteeringAssets.ps1` to add custom thruster types:

```powershell
@{
    Id = "thruster_exhaust_custom"
    Name = "Custom Thruster Exhaust"
    Desc = "Custom thruster description"
}
```

### Custom Weapon Types

Add custom weapon projectiles to the `$weaponProjectiles` array.

### Custom Shield Effects

Add custom shield effects to the `$shieldEffects` array.

## Tips

1. **Thruster effects**: Match exhaust to fuel type
2. **Weapon projectiles**: Use 32x32 for most, 64x64 for torpedoes
3. **Shield effects**: Create distinct effects for each state
4. **Hazard warnings**: Use color coding for severity
5. **Impact effects**: Match impact type to weapon type

## Troubleshooting

### Thrusters Not Showing

- Check thruster effect paths in fuel system
- Verify effects are in `assets/ships/thrusters/`
- Ensure particle system is initialized

### Weapons Not Firing

- Check projectile sprite paths in weapon mounts
- Verify projectiles are in `assets/ships/weapons/`
- Ensure weapon system is initialized

### Shields Not Appearing

- Verify shield effect paths in shield system
- Check effects are in `assets/ships/shields/`
- Ensure shield system is active

---

*Part of the Starbound Ollama Asset Generator suite*
