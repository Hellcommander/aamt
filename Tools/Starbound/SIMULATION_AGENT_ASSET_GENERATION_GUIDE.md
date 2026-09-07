# SimulationAgent System Asset Generation Guide

Generate visual assets for the SimulationAgent System including phase indicators, module icons, simulation state indicators, debug rendering indicators, UI control elements, performance monitoring indicators, and simulation event effects.

## Quick Start

```powershell
# Generate all SimulationAgent assets
.\GenerateSimulationAgentAssets.ps1

# Use C++ backend for better quality
.\GenerateSimulationAgentAssets.ps1 -UseCppBackend

# Or generate everything at once
.\GenerateAllModSprites.ps1 -OllamaModel "codellama:7b-instruct"
```

## What Gets Generated

### Phase Indicators (14 phases)

1. **phase_1** - Phase 1 (Core World & Physics)
2. **phase_2** - Phase 2
3. **phase_3** - Phase 3
4. **phase_4** - Phase 4
5. **phase_5** - Phase 5
6. **phase_6** - Phase 6 (Procedural Generation)
7. **phase_7** - Phase 7
8. **phase_8** - Phase 8
9. **phase_9** - Phase 9
10. **phase_10** - Phase 10
11. **phase_11** - Phase 11
12. **phase_12** - Phase 12
13. **phase_14** - Phase 14 (Flight Control)
14. **phase_15** - Phase 15

### Module Icons (8 modules)

1. **module_orbital** - Orbital simulation module
2. **module_world_state** - World state module
3. **module_physics** - Physics module
4. **module_npc** - NPC module
5. **module_procedural** - Procedural generation module
6. **module_flight_control** - Flight control module
7. **module_star_field** - Star field module
8. **module_noise** - Noise generation module

### Simulation State Indicators (6 states)

1. **state_active** - Active simulation state
2. **state_paused** - Paused simulation state
3. **state_stopped** - Stopped simulation state
4. **state_error** - Error simulation state
5. **state_initializing** - Initializing simulation state
6. **state_shutting_down** - Shutting down simulation state

### Debug Rendering Indicators (5 indicators)

1. **debug_enabled** - Debug rendering enabled
2. **debug_disabled** - Debug rendering disabled
3. **debug_physics** - Debug physics rendering
4. **debug_collision** - Debug collision rendering
5. **debug_pathfinding** - Debug pathfinding rendering

### UI Control Elements (7 controls)

1. **control_play** - Play simulation control
2. **control_pause** - Pause simulation control
3. **control_stop** - Stop simulation control
4. **control_reset** - Reset simulation control
5. **control_step** - Step simulation control
6. **control_speed_up** - Speed up simulation control
7. **control_slow_down** - Slow down simulation control

### Performance Monitoring Indicators (8 indicators)

1. **perf_cpu** - CPU performance indicator
2. **perf_memory** - Memory performance indicator
3. **perf_fps** - FPS performance indicator
4. **perf_entity_count** - Entity count indicator
5. **perf_update_time** - Update time indicator
6. **perf_good** - Good performance indicator
7. **perf_warning** - Warning performance indicator
8. **perf_critical** - Critical performance indicator

### Simulation Event Effects (8 effects)

1. **event_entry_started** - Entry started particle effect
2. **event_entry_completed** - Entry completed particle effect
3. **event_burnout_started** - Burnout started particle effect
4. **event_burnout_ended** - Burnout ended particle effect
5. **event_layer_changed** - Layer changed particle effect
6. **event_npc_spawned** - NPC spawned particle effect
7. **event_npc_despawned** - NPC despawned particle effect
8. **event_entity_collision** - Entity collision particle effect

## Total: ~56 Assets

## Output Structure

```
assets/
└── simulation/
    ├── phases/
    │   ├── phase_1.png
    │   ├── phase_2.png
    │   └── ... (all phase indicators)
    ├── modules/
    │   ├── module_orbital.png
    │   ├── module_world_state.png
    │   └── ... (all module icons)
    ├── states/
    │   ├── state_active.png
    │   ├── state_paused.png
    │   └── ... (all state indicators)
    ├── debug/
    │   ├── debug_enabled.png
    │   ├── debug_disabled.png
    │   └── ... (all debug indicators)
    ├── ui/
    │   ├── control_play.png
    │   ├── control_pause.png
    │   └── ... (all UI controls)
    ├── performance/
    │   ├── perf_cpu.png
    │   ├── perf_memory.png
    │   └── ... (all performance indicators)
    └── events/
        ├── event_entry_started.particle
        ├── event_entry_completed.particle
        └── ... (all event effects)
```

## Integration

### SimulationAgent

```cpp
// Initialize simulation
SimulationAgent agent;
agent.init();
// Uses: /assets/simulation/states/state_initializing.png

// Step simulation
agent.step(universeId, dt);
// Uses: /assets/simulation/states/state_active.png

// Pause simulation
agent.pause();
// Uses: /assets/simulation/states/state_paused.png

// Enable debug rendering
agent.enableDebugRendering(universeId, true);
// Uses: /assets/simulation/debug/debug_enabled.png
// Uses: /assets/simulation/debug/debug_physics.png
// Uses: /assets/simulation/debug/debug_collision.png

// Draw debug info
agent.drawDebugInfo(universeId);
// Uses: /assets/simulation/debug/debug_*.png

// Get performance metrics
agent.getPerformanceMetrics();
// Uses: /assets/simulation/performance/perf_cpu.png
// Uses: /assets/simulation/performance/perf_memory.png
// Uses: /assets/simulation/performance/perf_fps.png
```

### Phase Modules

```cpp
// OrbitalSimulationModule
OrbitalSimulationModule::step(universeId, dt);
// Uses: /assets/simulation/phases/phase_1.png
// Uses: /assets/simulation/modules/module_orbital.png

// ProceduralGenerationModule
ProceduralGenerationModule::step(universeId, dt);
// Uses: /assets/simulation/phases/phase_6.png
// Uses: /assets/simulation/modules/module_procedural.png

// FlightControlSimulationModule
FlightControlSimulationModule::step(universeId, dt);
// Uses: /assets/simulation/phases/phase_14.png
// Uses: /assets/simulation/modules/module_flight_control.png
```

### Event System

```cpp
// Entry started
OrbitalSimulationModule::setEntryStartedCallback(callback);
// Uses: /assets/simulation/events/event_entry_started.particle

// Entry completed
OrbitalSimulationModule::setEntryCompletedCallback(callback);
// Uses: /assets/simulation/events/event_entry_completed.particle

// Burnout started
OrbitalSimulationModule::setBurnoutStartedCallback(callback);
// Uses: /assets/simulation/events/event_burnout_started.particle

// Burnout ended
OrbitalSimulationModule::setBurnoutEndedCallback(callback);
// Uses: /assets/simulation/events/event_burnout_ended.particle

// Layer changed
OrbitalSimulationModule::setLayerChangedCallback(callback);
// Uses: /assets/simulation/events/event_layer_changed.particle
```

## Phase System

### Phase Modules
- **Phase 1**: Core World & Physics Integration
- **Phase 2-5**: Additional simulation phases
- **Phase 6**: Procedural Generation
- **Phase 7-12**: Additional simulation phases
- **Phase 14**: Flight Control
- **Phase 15**: Final simulation phase

### Module Types
- **Orbital**: Orbital mechanics simulation
- **World State**: World state management
- **Physics**: Physics simulation
- **NPC**: NPC behavior simulation
- **Procedural**: Procedural generation
- **Flight Control**: Flight control simulation
- **Star Field**: Star field generation
- **Noise**: Noise generation

## Simulation States

### State Types
- **Active**: Simulation is running
- **Paused**: Simulation is paused
- **Stopped**: Simulation is stopped
- **Error**: Simulation encountered an error
- **Initializing**: Simulation is initializing
- **Shutting Down**: Simulation is shutting down

## Debug Rendering

### Debug Types
- **Enabled**: Debug rendering is enabled
- **Disabled**: Debug rendering is disabled
- **Physics**: Physics debug rendering
- **Collision**: Collision debug rendering
- **Pathfinding**: Pathfinding debug rendering

## UI Controls

### Control Types
- **Play**: Start simulation
- **Pause**: Pause simulation
- **Stop**: Stop simulation
- **Reset**: Reset simulation
- **Step**: Step simulation one frame
- **Speed Up**: Increase simulation speed
- **Slow Down**: Decrease simulation speed

## Performance Monitoring

### Performance Metrics
- **CPU**: CPU usage indicator
- **Memory**: Memory usage indicator
- **FPS**: Frames per second indicator
- **Entity Count**: Entity count indicator
- **Update Time**: Update time indicator

### Performance States
- **Good**: Performance is good
- **Warning**: Performance warning
- **Critical**: Performance is critical

## Event System

### Event Types
- **Entry Started**: Atmospheric entry started
- **Entry Completed**: Atmospheric entry completed
- **Burnout Started**: Atmospheric burnout started
- **Burnout Ended**: Atmospheric burnout ended
- **Layer Changed**: Atmospheric layer changed
- **NPC Spawned**: NPC spawned
- **NPC Despawned**: NPC despawned
- **Entity Collision**: Entity collision occurred

## Workflow

### Step 1: Generate Assets

```powershell
.\GenerateSimulationAgentAssets.ps1 -OllamaModel "codellama:7b-instruct"
```

### Step 2: Configure SimulationAgent

Set up SimulationAgent with asset paths.

### Step 3: Initialize Simulation

```cpp
SimulationAgent agent;
agent.init();
```

### Step 4: Run Simulation

```cpp
agent.step(universeId, dt);
```

### Step 5: Monitor Performance

```cpp
auto metrics = agent.getPerformanceMetrics();
```

### Step 6: Test in Game

Load the mod and test simulation system in-game.

## Advanced Options

### Custom Phase Indicators

Edit `GenerateSimulationAgentAssets.ps1` to add custom phase indicators.

### Custom Module Icons

Add custom module icons as needed.

### Custom Event Effects

Add custom event effects for additional simulation events.

## Tips

1. **Phase indicators**: Use 32x32 for phase icons
2. **Module icons**: Use 32x32 for module icons
3. **State indicators**: Make states clearly visible
4. **Debug indicators**: Keep debug indicators distinct
5. **UI controls**: Use standard control icons
6. **Performance indicators**: Make performance clearly visible
7. **Event effects**: Use 64x64 for particle effects

## Troubleshooting

### Simulation Not Displaying

- Check phase indicator paths
- Verify indicators are in `assets/simulation/phases/`
- Ensure SimulationAgent is initialized

### Modules Not Showing

- Check module icon paths
- Verify icons are in `assets/simulation/modules/`
- Ensure modules are registered

### Debug Not Working

- Check debug indicator paths
- Verify indicators are in `assets/simulation/debug/`
- Ensure debug rendering is enabled

### Events Not Triggering

- Check event effect paths
- Verify effects are in `assets/simulation/events/`
- Ensure event callbacks are registered

---

*Part of the Starbound Ollama Asset Generator suite*
