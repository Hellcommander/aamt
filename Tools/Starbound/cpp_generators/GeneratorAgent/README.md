# QuadMechGen Pipeline

An end-to-end system for authoring four-legged Magitech mechs with functional cockpits—covering module definitions, procedural materials, skeleton assembly, animations, LODs, physics rigs, packaging, runtime loading, caching, and live editor tooling.

## Overview

The QuadMechGen Pipeline provides a comprehensive solution for generating complex quadraped mech assets with the following capabilities:

- **Declarative module definitions** with YAML configuration
- **Magitech styling** with procedural rune glows, energy arcs, and emissive materials
- **Functional cockpit interiors** with displays and control systems
- **Quadraped skeleton assembly** with joint limits and drive targets
- **Auto-generated animations** for walk/trot/gallop cycles and cockpit interactions
- **Multiple LOD levels** for meshes, morph targets, and material detail
- **Physics rig generation** with per-module colliders and joint constraints
- **Package management** with `.mechpack` format for optimized runtime loading
- **Thread-safe caching** and hot-reload capabilities
- **Editor integration** with drag-drop modules and live preview

## Architecture

### 1. Source Definitions
QuadMech definitions are written in YAML format (`.quadmechdef`) and specify:
- Module configurations (chassis, legs, head, cockpit, weapons, energy core)
- Magitech material parameters (energy runes, core effects, canopy properties)
- Animation definitions (walk/trot/gallop, cockpit interactions)
- Physics configuration (mass distribution, joint limits)
- LOD rules (mesh decimation, material simplification)

### 2. Offline Generator Workflow
1. **Parse & Validate** - Ensure module meshes exist and parameters are valid
2. **Mesh Import & Skin Bake** - Convert FBX/glTF → engine mesh format
3. **Material Graph Compilation** - Build procedural shaders for Magitech effects
4. **Skeleton Assembly** - Merge bone hierarchies into quadraped rig
5. **Animation Retargeting** - Retarget animations to assembled skeleton
6. **Physics Rig Construction** - Create colliders and joint constraints
7. **LOD Generation** - Decimate meshes and simplify materials per LOD
8. **Package Serialization** - Write `.mechpack` with all assets

### 3. Runtime Loader & Cache
- **Concurrent LRU Cache** - Thread-safe asset caching with performance metrics
- **Async Loading** - Non-blocking asset loading with futures
- **Hot-Reload** - File watching for live updates during development
- **Instance Management** - Runtime mech instances with physics and state

### 4. Editor Integration
- **Module Picker** - Drag-drop chassis, leg, head, and cockpit prefabs
- **Material Tuner** - Sliders for rune emissive colors, glow intensity, animation rates
- **Animation Scrubber** - Timeline to preview walk/trot/gallop and cockpit animations
- **LOD Slider** - Switch between high/medium/low detail live
- **Physics Inspector** - Joint limits, mass distribution, collision shapes

## Usage Examples

### Basic QuadMech Definition

```yaml
# assets/mechs/phoenix_quad.quadmechdef
name: phoenix_quad
version: "1.0.0"
author: "MagiTech Engineering"
description: "High-performance quadraped mech with advanced Magitech systems"

modules:
  chassis:
    mesh: "modules/phoenix_body.fbx"
    attachBone: "root"
    mass: 800.0
  
  leg_front_left:
    mesh: "modules/phoenix_leg_fl.fbx"
    attachBone: "hip_FL"
    offset: [-0.8, 0, 1.2]
    mass: 150.0
  
  # ... additional modules

magitechMaterials:
  energyRunes:
    emissiveColor: [0.1, 0.6, 1.0]
    glowIntensity: { min: 0.5, max: 2.0 }
    animationRate: 1.0
  
  energyCore:
    coreColor: [0.8, 0.2, 0.1]
    energyLevel: 1.0
    pulseRate: 3.0

animations:
  - id: "walk"
    type: "walk"
    path: "animations/walk.fbx"
    speed: 1.0
    loop: true

physics:
  totalMass: 1500.0
  moduleMass:
    chassis: 800.0
    legs: 600.0
    cockpit: 100.0

lods:
  - quality: "high"
    meshDecimate: 0.0
    materialDetail: 1.0
  - quality: "medium"
    meshDecimate: 0.4
    materialDetail: 0.6
  - quality: "low"
    meshDecimate: 0.8
    materialDetail: 0.3
```

### Lua API Usage

```lua
-- Initialize the system
local factory = QuadMechFactory.new()
factory:initialize(100, 4) -- cache_size, num_threads

-- Load a mech synchronously
local mech = factory:loadSync("phoenix_quad", LODQuality.HIGH)

-- Load a mech asynchronously
local future = factory:loadAsync("phoenix_quad", LODQuality.HIGH)
local mech = future:get()

-- Create runtime instance
local instance = QuadMechLoader.createInstance("phoenix_quad", LODQuality.HIGH)

-- Set Magitech effects
instance:setEnergyLevel(0.8)
instance:setRuneGlowIntensity(1.5)
instance:setCockpitState(true, false) -- open, no pilot

-- Set animation
instance:setAnimation("gallop")

-- Apply physics forces
instance:applyForce(Vec3(0, 1000, 0), Vec3(0, 2, 0))

-- Editor operations
local editor = QuadMechEditor.new()
editor:loadMechForEditing("phoenix_quad")

-- Update materials
local runes = EnergyRunes.new()
runes.emissiveColor = Vec3(1.0, 0.2, 0.8)
runes.glowIntensity = Vec2(0.8, 3.0)
editor:updateEnergyRunes(runes)

-- Save changes
editor:saveCurrentMech("assets/mechs/phoenix_quad_updated.mechpack")
```

### C++ API Usage

```cpp
// Initialize factory
auto factory = std::make_unique<QuadMech::QuadMechFactory>();
factory->initialize(100, 4);

// Load mech
auto mech = factory->loadSync("phoenix_quad", QuadMech::LODQuality::HIGH);

// Create loader for runtime instances
auto loader = std::make_unique<QuadMech::QuadMechLoader>();
auto instance = loader->createInstance("phoenix_quad", QuadMech::LODQuality::HIGH);

// Set Magitech runtime state
loader->setEnergyLevel(instance.hashKey(), 0.8f);
loader->setRuneGlowIntensity(instance.hashKey(), 1.5f);
loader->setCockpitState(instance.hashKey(), true, false);

// Apply physics
loader->applyForce(instance.hashKey(), glm::vec3(0, 1000, 0), glm::vec3(0, 2, 0));

// Editor operations
auto editor = std::make_unique<QuadMech::QuadMechEditor>();
editor->loadMechForEditing("phoenix_quad");

// Update materials
QuadMech::EnergyRunes runes;
runes.emissiveColor = glm::vec3(1.0f, 0.2f, 0.8f);
runes.glowIntensity = glm::vec2(0.8f, 3.0f);
editor->updateEnergyRunes(runes);

// Save changes
editor->saveCurrentMech("assets/mechs/phoenix_quad_updated.mechpack");
```

## Package Structure

The `.mechpack` format organizes assets efficiently:

```
phoenix_quad.mechpack/
├── metadata.json              # Package metadata and hash
├── definition.yaml            # Original definition file
├── skeleton/
│   └── skeleton.bin          # Bone hierarchy and transforms
├── physics/
│   └── rig.bin              # Collision shapes and joint constraints
├── meshes/
│   ├── high/
│   │   ├── chassis.bin
│   │   ├── leg_front_left.bin
│   │   └── ...
│   ├── medium/
│   ├── low/
│   └── ultra_low/
├── materials/
│   ├── high/
│   │   ├── energy_runes.mat
│   │   ├── energy_core.mat
│   │   └── canopy.mat
│   ├── medium/
│   ├── low/
│   └── ultra_low/
└── animations/
    ├── walk.anim
    ├── trot.anim
    ├── gallop.anim
    └── ...
```

## Performance Features

### Caching System
- **LRU Cache** with configurable capacity
- **Thread-safe** concurrent access
- **Performance metrics** (hit rate, load times)
- **Hash-based** invalidation

### Async Loading
- **Non-blocking** asset loading
- **Thread pool** for parallel processing
- **Future-based** API for async operations
- **Progress tracking** for large assets

### Hot-Reload
- **File watching** for definition changes
- **Incremental updates** for modified modules
- **Cache invalidation** for changed assets
- **Live preview** updates in editor

## Magitech Material System

### Energy Runes
- **Procedural emissive** materials with pulsing intensity
- **Noise-based flicker** effects
- **Animated glow patterns** with configurable rates
- **LOD-aware** simplification for performance

### Energy Core
- **Pulsing core** with dynamic intensity
- **Energy arc effects** with configurable count and intensity
- **Energy level** affects visual intensity
- **Procedural shader** generation

### Canopy Materials
- **Transparency** with tint control
- **Reflectivity** for realistic glass effects
- **Optional scratch** effects for wear
- **Hologram support** for HUD elements

## Animation System

### Quadraped Locomotion
- **Walk cycles** with configurable stride length and leg lift
- **Trot and gallop** with different gait patterns
- **Inverse kinematics** for foot placement
- **Gait phase** control for smooth transitions

### Cockpit Interactions
- **Cockpit open/close** animations
- **Pilot entry/exit** sequences
- **Hologram activation** effects
- **HUD element** animations

### Combat Animations
- **Attack sequences** with weapon integration
- **Defensive postures** and blocking
- **Weapon reload** and maintenance
- **Damage response** animations

## Physics System

### Module-Based Physics
- **Per-module colliders** (capsule, box, convex hull)
- **Mass distribution** based on module definitions
- **Joint constraints** with configurable limits
- **Inertia tensors** for realistic motion

### Joint Configuration
- **Swing limits** for leg movement ranges
- **Twist limits** for rotation constraints
- **Damping** and friction parameters
- **CCD** (Continuous Collision Detection) support

## Editor Features

### Module Management
- **Drag-drop** module placement
- **Real-time** transform editing
- **Mass distribution** visualization
- **Collision shape** preview

### Material Editing
- **Live preview** of Magitech effects
- **Color picker** for emissive materials
- **Intensity sliders** for glow effects
- **Animation rate** controls

### Animation Tools
- **Timeline scrubber** for preview
- **Gait phase** adjustment
- **Speed control** for locomotion
- **Blend time** configuration

### LOD Management
- **Quality slider** for live LOD switching
- **Decimation preview** for mesh simplification
- **Material detail** controls
- **Performance metrics** display

## Development Workflow

### 1. Define Mech Structure
```yaml
# Create YAML definition with modules, materials, animations
# Validate with QuadMechGen validation tools
```

### 2. Generate Package
```bash
# Generate optimized package from definition
quadmechgen generate phoenix_quad.quadmechdef -o phoenix_quad.mechpack
```

### 3. Runtime Integration
```cpp
// Load and instantiate mech in game
auto mech = factory->loadSync("phoenix_quad");
auto instance = loader->createInstance("phoenix_quad");
```

### 4. Editor Iteration
```lua
-- Use editor for live tweaking
editor:loadMechForEditing("phoenix_quad")
editor:updateEnergyRunes(newRunes)
editor:saveCurrentMech("updated_mech.mechpack")
```

## Performance Considerations

### Memory Management
- **LOD streaming** for large mechs
- **Texture compression** for Magitech materials
- **Mesh optimization** with decimation
- **Animation compression** for runtime

### Rendering Optimization
- **Frustum culling** for off-screen mechs
- **LOD selection** based on distance
- **Material batching** for similar effects
- **Shadow optimization** for complex geometry

### Physics Performance
- **Sleeping bodies** for inactive mechs
- **Broad phase** optimization for collision detection
- **Joint limit** caching for repeated calculations
- **Mass distribution** optimization

## Future Enhancements

### Planned Features
1. **GPU-accelerated** procedural glow effects via compute shaders
2. **AI-assisted** module suggestions for thematic coherence
3. **Network-synced** physics for multiplayer mech battles
4. **VR cockpit** walkthrough preview in the editor
5. **Procedural weapon** loadouts that adapt to Magitech energy levels

### Advanced Capabilities
- **Dynamic LOD** based on performance metrics
- **Material instancing** for multiple mechs
- **Animation blending** for smooth transitions
- **Physics cloth** for decorative elements
- **Particle effects** integration with Magitech systems

## Troubleshooting

### Common Issues

**Module Loading Errors**
- Verify mesh file paths in definition
- Check bone name consistency
- Ensure proper file permissions

**Material Compilation Failures**
- Validate shader syntax in material definitions
- Check texture file availability
- Verify LOD material compatibility

**Physics Rig Issues**
- Confirm joint limit validity
- Check mass distribution balance
- Verify collision shape generation

**Performance Problems**
- Reduce LOD complexity for distant mechs
- Simplify Magitech material effects
- Optimize animation bone count
- Adjust cache capacity settings

## API Reference

### Core Classes
- `QuadMechFactory` - Main factory for loading and generating mechs
- `QuadMechLoader` - Runtime instance management
- `QuadMechEditor` - Editor integration and live preview
- `QuadMechCache` - Thread-safe asset caching

### Key Types
- `QuadMechDefinition` - YAML definition structure
- `ModuleDefinition` - Individual module configuration
- `MagitechMaterials` - Procedural material parameters
- `QuadMechInstance` - Runtime mech instance
- `LODQuality` - Detail level enumeration

### Lua Bindings
- Complete Lua API for all functionality
- Type-safe bindings for all C++ types
- Async operation support
- Hot-reload callbacks

This QuadMechGen pipeline empowers your team to craft robust, visually stunning four-legged Magitech mechs with realistic cockpits—streamlining every step from definition to runtime. 