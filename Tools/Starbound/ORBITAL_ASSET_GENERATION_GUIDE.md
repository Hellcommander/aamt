# OrbitalWorldManager System Asset Generation Guide

Generate visual assets for the OrbitalWorldManager System including planet icons, atmospheric layer visuals, entry trajectory visuals, burnout effects, plasma effects, entry trail effects, atmospheric scattering effects, orbital UI elements, entry status indicators, layer transition effects, and metric indicators.

## Quick Start

```powershell
# Generate all Orbital assets
.\GenerateOrbitalAssets.ps1

# Use C++ backend for better quality
.\GenerateOrbitalAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Planet Icons (6 icons)

1. **planet_terrestrial** - Terrestrial planet
2. **planet_gas_giant** - Gas giant planet
3. **planet_ice** - Ice planet
4. **planet_lava** - Lava planet
5. **planet_ocean** - Ocean planet
6. **planet_barren** - Barren planet

### Atmospheric Layer Visuals (6 visuals)

1. **layer_space** - Space layer texture
2. **layer_exosphere** - Exosphere layer texture
3. **layer_thermosphere** - Thermosphere layer texture
4. **layer_mesosphere** - Mesosphere layer texture
5. **layer_stratosphere** - Stratosphere layer texture
6. **layer_troposphere** - Troposphere layer texture

### Entry Trajectory Visuals (5 visuals)

1. **trajectory_line** - Entry trajectory line texture
2. **trajectory_waypoint** - Trajectory waypoint icon
3. **trajectory_safe** - Safe trajectory indicator
4. **trajectory_unsafe** - Unsafe trajectory indicator
5. **trajectory_optimal** - Optimal trajectory indicator

### Burnout Effects (4 effects)

1. **burnout_start** - Burnout start particle effect
2. **burnout_active** - Burnout active particle effect
3. **burnout_end** - Burnout end particle effect
4. **burnout_critical** - Critical burnout particle effect

### Plasma Effects (4 effects)

1. **plasma_ionization** - Plasma ionization particle effect
2. **plasma_glow** - Plasma glow particle effect
3. **plasma_trail** - Plasma trail particle effect
4. **plasma_intense** - Intense plasma particle effect

### Entry Trail Effects (4 effects)

1. **trail_entry** - Entry trail particle effect
2. **trail_atmospheric** - Atmospheric trail particle effect
3. **trail_heat** - Heat trail particle effect
4. **trail_smoke** - Smoke trail particle effect

### Atmospheric Scattering Effects (3 effects)

1. **scattering_light** - Light scattering particle effect
2. **scattering_rayleigh** - Rayleigh scattering particle effect
3. **scattering_mie** - Mie scattering particle effect

### Orbital UI Elements (5 elements)

1. **ui_panel_orbital** - Orbital panel background
2. **ui_panel_trajectory** - Trajectory panel background
3. **ui_button_start_entry** - Start entry button icon
4. **ui_button_cancel_entry** - Cancel entry button icon
5. **ui_button_calculate_trajectory** - Calculate trajectory button icon

### Entry Status Indicators (4 indicators)

1. **status_entry_ready** - Entry ready indicator
2. **status_entry_active** - Entry active indicator
3. **status_entry_complete** - Entry complete indicator
4. **status_entry_cancelled** - Entry cancelled indicator

### Layer Transition Effects (3 effects)

1. **transition_layer** - Layer transition particle effect
2. **transition_enter** - Enter layer particle effect
3. **transition_exit** - Exit layer particle effect

### Metric Indicators (9 indicators)

1. **metric_heat** - Heat indicator icon
2. **metric_speed** - Speed indicator icon
3. **metric_altitude** - Altitude indicator icon
4. **metric_gforce** - G-force indicator icon
5. **metric_drag** - Drag indicator icon
6. **metric_ionization** - Ionization indicator icon
7. **metric_bar_heat** - Heat bar background texture
8. **metric_bar_speed** - Speed bar background texture
9. **metric_bar_altitude** - Altitude bar background texture

## Total: ~57 Assets

## Output Structure

```
assets/
└── orbital/
    ├── planets/
    │   ├── planet_terrestrial.png
    │   ├── planet_gas_giant.png
    │   └── ... (all planet icons)
    ├── atmosphere/
    │   └── layers/
    │       ├── layer_space.png
    │       ├── layer_exosphere.png
    │       └── ... (all atmospheric layer textures)
    ├── trajectory/
    │   ├── trajectory_line.png
    │   ├── trajectory_waypoint.png
    │   └── ... (all trajectory visuals)
    ├── burnout/
    │   ├── burnout_start.particle
    │   ├── burnout_active.particle
    │   └── ... (all burnout effects)
    ├── plasma/
    │   ├── plasma_ionization.particle
    │   ├── plasma_glow.particle
    │   └── ... (all plasma effects)
    ├── trails/
    │   ├── trail_entry.particle
    │   ├── trail_atmospheric.particle
    │   └── ... (all trail effects)
    ├── scattering/
    │   ├── scattering_light.particle
    │   ├── scattering_rayleigh.particle
    │   └── ... (all scattering effects)
    ├── ui/
    │   ├── ui_panel_orbital.png
    │   ├── ui_button_start_entry.png
    │   └── ... (all orbital UI elements)
    ├── status/
    │   ├── status_entry_ready.png
    │   ├── status_entry_active.png
    │   └── ... (all status indicators)
    ├── transitions/
    │   ├── transition_layer.particle
    │   ├── transition_enter.particle
    │   └── ... (all transition effects)
    └── metrics/
        ├── metric_heat.png
        ├── metric_speed.png
        └── ... (all metric indicators)
```

## Integration

### OrbitalWorldManager

```cpp
// Register planet
OrbitalWorldManager::instance().registerPlanet(planetId, planet);
// Uses: /assets/orbital/planets/planet_*.png

// Start entry
OrbitalWorldManager::instance().startEntry(shipId, planetId, startPos, startVel);
// Uses: /assets/orbital/status/status_entry_active.png
// Uses: /assets/orbital/trails/trail_entry.particle
// Uses: /assets/orbital/plasma/plasma_ionization.particle

// Calculate trajectory
EntryTrajectory trajectory = OrbitalWorldManager::instance().calculateEntryTrajectory(planetId, startPos, startVel);
// Uses: /assets/orbital/trajectory/trajectory_line.png
// Uses: /assets/orbital/trajectory/trajectory_waypoint.png
// Uses: /assets/orbital/trajectory/trajectory_safe.png
```

### AtmosphericLayer

```cpp
// Atmospheric layer
AtmosphericLayer layer;
layer.particleEffect = "plasma_ionization";
layer.skyColor = glm::vec3(0.5f, 0.7f, 1.0f);
// Uses: /assets/orbital/plasma/plasma_ionization.particle
// Uses: /assets/orbital/atmosphere/layers/layer_*.png
```

### EntryState

```cpp
// Entry state
EntryState state = OrbitalWorldManager::instance().getEntryState(shipId);
// Uses: /assets/orbital/metrics/metric_heat.png
// Uses: /assets/orbital/metrics/metric_speed.png
// Uses: /assets/orbital/metrics/metric_altitude.png
// Uses: /assets/orbital/metrics/metric_gforce.png

// Check burnout
if (state.isBurningOut) {
    // Uses: /assets/orbital/burnout/burnout_active.particle
}
```

### EntryTrajectory

```cpp
// Entry trajectory
EntryTrajectory trajectory = OrbitalWorldManager::instance().calculateEntryTrajectory(planetId, startPos, startVel);
// Uses: /assets/orbital/trajectory/trajectory_line.png
// Uses: /assets/orbital/trajectory/trajectory_waypoint.png

if (trajectory.isSafe) {
    // Uses: /assets/orbital/trajectory/trajectory_safe.png
} else {
    // Uses: /assets/orbital/trajectory/trajectory_unsafe.png
}
```

## Atmospheric Layers

### Layer Types
- **Space**: Space layer (no atmosphere)
- **Exosphere**: Exosphere layer (outermost)
- **Thermosphere**: Thermosphere layer
- **Mesosphere**: Mesosphere layer
- **Stratosphere**: Stratosphere layer
- **Troposphere**: Troposphere layer (lowest)

## Entry States

### Entry Status
- **Ready**: Ready for entry
- **Active**: Entry in progress
- **Complete**: Entry finished
- **Cancelled**: Entry cancelled

## Burnout States

### Burnout Types
- **Start**: Burnout initiation
- **Active**: Active burnout
- **End**: Burnout completion
- **Critical**: Critical burnout (exceeded max time)

## Plasma Effects

### Plasma Types
- **Ionization**: Plasma ionization effect
- **Glow**: Plasma glow effect
- **Trail**: Plasma trail effect
- **Intense**: Intense plasma effect

## Trail Effects

### Trail Types
- **Entry**: Entry trail
- **Atmospheric**: Atmospheric trail
- **Heat**: Heat trail
- **Smoke**: Smoke trail

## Scattering Effects

### Scattering Types
- **Light**: Light scattering
- **Rayleigh**: Rayleigh scattering (blue sky)
- **Mie**: Mie scattering (haze)

## Metrics

### Metric Types
- **Heat**: Temperature/heat level
- **Speed**: Velocity/speed
- **Altitude**: Height above surface
- **G-Force**: Acceleration force
- **Drag**: Drag force
- **Ionization**: Plasma ionization level

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateOrbitalAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure OrbitalWorldManager

Set up OrbitalWorldManager with asset paths.

### Step 3: Register Planets

```cpp
OrbitalWorldManager::instance().registerPlanet(planetId, planet);
```

### Step 4: Add Atmospheric Layers

```cpp
AtmosphericLayer layer;
layer.name = "troposphere";
layer.altitudeMin = 0.0f;
layer.altitudeMax = 10000.0f;
OrbitalWorldManager::instance().addAtmosphericLayer(planetId, layer);
```

### Step 5: Start Entry

```cpp
OrbitalWorldManager::instance().startEntry(shipId, planetId, startPos, startVel);
```

### Step 6: Update System

```cpp
OrbitalWorldManager::instance().update(deltaTime);
```

### Step 7: Test in Game

Load the mod and test orbital entry system in-game.

## Advanced Options

### Custom Atmospheric Layers

Edit `GenerateOrbitalAssets.ps1` to add custom atmospheric layer textures.

### Custom Planet Types

Add custom planet icons for new planet types.

### Custom Effects

Add custom particle effects for new visual effects.

## Tips

1. **Planet icons**: Use 64x64 for planet icons
2. **Atmospheric layers**: Use 128x128 for layer textures
3. **Trajectory lines**: Use 256x8 for trajectory lines
4. **Trail effects**: Use 128x32 for trail effects
5. **Plasma effects**: Keep effects visually distinct and informative
6. **UI panels**: Use 256x256 for main panels, 128x128 for smaller panels
7. **Status indicators**: Use 32x32 for status indicators
8. **Metric bars**: Use 128x16 for metric bar textures
9. **Particle effects**: Keep effects subtle and informative
10. **Layer transitions**: Make transitions smooth and visually clear

## Troubleshooting

### Entry Not Displaying

- Check entry status indicator paths
- Verify indicators are in `assets/orbital/status/`
- Ensure OrbitalWorldManager is initialized

### Effects Not Showing

- Check effect paths
- Verify effects are in `assets/orbital/`
- Ensure effect system is enabled

### Trajectory Not Displaying

- Check trajectory visual paths
- Verify visuals are in `assets/orbital/trajectory/`
- Ensure trajectory calculation is enabled

### Metrics Not Displaying

- Check metric indicator paths
- Verify indicators are in `assets/orbital/metrics/`
- Ensure metric system is enabled

---

*Part of the Starbound Ollama Asset Generator suite*
