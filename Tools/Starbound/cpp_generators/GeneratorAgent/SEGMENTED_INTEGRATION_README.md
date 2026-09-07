# Segmented Mech Asset Generation Pipeline

## Overview

This enhanced mech generator system integrates **segmented mech capabilities** (snake and worm mechs) with the existing hybrid C++23/26 + Lua FormShiftMechGen pipeline, providing **modular, worm-like mechs** with articulated cockpits and armored segments—all generated from pure data into C++ mesh, texture, skeleton, animation, and cockpit-integration generators.

## Key Features

### 🐍 **Segmented Mech Types**
- **Snake Mechs**: Agile, fast-moving segmented mechs with internal cockpits
- **Worm Mechs**: Heavy, armored segmented mechs with external cockpits  
- **Serpent Mechs**: Hybrid segmented mechs with modular cockpits

### 🔧 **Dynamic Segment Management**
- **Runtime Segment Addition/Removal**: Add or remove segments during gameplay
- **Dynamic Property Updates**: Modify segment properties in real-time
- **Live Skeleton Updates**: Automatic skeleton rebuilding for segment changes

### 🎮 **Cockpit Integration**
- **Internal Cockpits**: Recessed spherical cockpits within segments
- **External Cockpits**: Bulged cockpit modules on segment surfaces
- **Modular Cockpits**: Swappable cockpit configurations
- **Interactive Controls**: Joysticks, displays, gauges, and HUD elements

### ⚡ **Performance Optimized**
- **Concurrent Generation**: Thread-pool based async asset creation
- **LRU Caching**: Intelligent cache management for segmented assets
- **GPU Acceleration**: Hardware-accelerated segment morphing and physics
- **LOD Support**: Dynamic level-of-detail for segment complexity

## Architecture

### Core Components

```
mech_generator/
├── MechTypes.hpp                    # Enhanced with segmented types
├── MechFactory.hpp                  # Enhanced with segmented factory
├── MechGenerators.hpp               # Enhanced with segmented generators
├── MechLuaBindings.hpp              # Enhanced with segmented bindings
├── hybrid_example.cpp               # Hybrid C++23/26 + Lua demo
├── segmented_example.cpp            # Segmented mech demo
├── HYBRID_INTEGRATION_README.md     # Hybrid pipeline documentation
└── SEGMENTED_INTEGRATION_README.md  # This file
```

### Integration with Existing Pipeline

The segmented system seamlessly integrates with the existing FormShiftMechGen pipeline:

- **Preserves All Features**: All original functionality maintained
- **Enhances Capabilities**: Adds segmented mech generation and cockpit integration
- **Shared Infrastructure**: Uses existing MultithreadBus and GPU interfaces
- **Consistent Patterns**: Follows established asset generator patterns

## Parameter Schemas

### SegmentedMechParams

```lua
SegmentedMechParams {
  id                   = "sand_serpent_mkI",
  mechType             = "snake",              -- "snake", "worm", "serpent"
  segmentCount         = 25,                   -- total repeating modules
  segmentLength        = 1.2,                  -- units per segment
  segmentRadius        = 0.5,                  -- base radius of spine
  connectorGap         = 0.1,                  -- spacing between segments
  maxBendAngleDeg      = 45.0,                 -- per-joint max articulation
  bendStiffness        = 100.0,                -- spring strength for auto-align
  jointFlexibility     = 0.7,                  -- 0–1 stiffness of pitch/yaw joints
  
  -- Armor & Details
  enablePlating        = true,                 -- enable external plate overlays
  platesPerSegment     = 6,                    -- number of plates per link
  plateThickness       = 0.05,                 -- thickness of armor plates
  platingColor         = {0.3,0.3,0.35,1.0},  -- armor plate color
  platingDetailLevel   = 2,                    -- 0=none,1=low,2=med,3=high
  
  -- Emissive Strips
  stripeCount          = 2,                    -- number of glowing strips
  stripeWidth          = 0.02,                 -- width of emissive strips
  stripeColor          = {1.0,0.2,0.2,1.0},   -- emissive strip color
  stripeGlowIntensity  = 3.0,                  -- glow intensity multiplier
  
  -- VFX
  enableJointSparks    = true,                 -- enable joint spark effects
  sparkRate            = 20.0,                 -- sparks per second per joint
  sparkLifetime        = 0.4,                  -- spark particle lifetime
  sparkColor           = {1.0,0.8,0.5,1.0},   -- spark particle color
  
  -- Physics
  segmentMass          = 10.0,                 -- mass per segment
  jointDamping         = 0.7,                  -- joint damping coefficient
  
  -- Animation
  waveAmplitude        = 1.5,                  -- max offset for procedural wave
  waveFrequency        = 1.0,                  -- speed of traveling wave
  animationProfile     = "mech_slither",       -- slither | coil | undulate
  
  -- Cockpit Integration
  cockpitType          = "internal",           -- internal | external | module
  cockpitSegmentIndex  = 5,                    -- segment index where cockpit attaches
  cockpitRadius        = 0.8,                  -- radius of cockpit sphere
  cockpitOrientation   = {0, 1, 0},            -- local up-vector for cockpit mount
  
  -- Tapering & Shape
  taperProfile         = "linear",             -- none | linear | exponential | customCurve
  segmentShape         = "cylinder",           -- cylinder | hexagon | customMesh
  noiseDetail          = 0.3,                  -- surface vertex noise
  textureScale         = 1.5,                  -- UV tiling factor
  
  -- Colors
  colorPrimary         = {0.2,0.3,0.35},      -- base metal tint
  colorSecondary       = {0.8,0.6,0.4},       -- accent or hazard stripes
  
  -- AI & Behavior
  aiProfile            = "patrol",             -- passive | neutral | aggressive
  
  -- LOD & Performance
  rebuildOnLOD         = false,                -- toggle dynamic LOD rebuild
  lodCount             = 3                     -- number of LOD levels
}
```

### CockpitParams

```lua
CockpitParams {
  -- Seat & Interior
  seatWidth            = 0.8,                  -- lateral clearance
  seatDepth            = 1.2,                  -- cushion length
  seatHeight           = 0.5,                  -- vertical offset
  seatFabricColor      = {0.2,0.2,0.25,1.0},  -- seat fabric color
  headrestEnabled      = true,                 -- enable headrest
  
  -- Canopy & Glass
  canopyRadius         = 1.0,                  -- dome curvature radius
  canopyHeight         = 0.8,                  -- peak above seat
  glassThickness       = 0.02,                 -- glass panel thickness
  glassTint            = {0.1,0.1,0.15,0.3},  -- glass tint color
  reflectivity         = 0.8,                  -- glass reflectivity
  
  -- Console & Controls
  displayCount         = 3,                    -- number of screens
  displayResolution    = {512.0, 384.0},       -- per-screen resolution
  stickOffsetX         = 0.3,                  -- joystick X position
  stickOffsetY         = 0.2,                  -- joystick Y position
  throttleLever        = true,                 -- enable throttle lever
  pedalControls        = true,                 -- enable foot pedals
  
  -- Instrumentation
  gaugeCount           = 6,                    -- analog dial count
  gaugeRadius          = 0.1,                  -- gauge dial radius
  gaugeNeedleColor     = {1.0,0.2,0.2,1.0},   -- gauge needle color
  holographicHUD       = true,                 -- enable holographic HUD
  
  -- Ambient FX
  cockpitLight         = true,                 -- enable cockpit lighting
  lightColor           = {0.8,0.8,1.0,1.0},   -- light color
  lightIntensity       = 1.0,                  -- light intensity
  
  -- Interaction
  canopyAnimEnabled    = true,                 -- enable canopy animation
  canopyOpenAngleDeg   = 90.0,                 -- canopy open angle
  canopyOpenDuration   = 2.0,                  -- canopy animation duration
  
  -- Integration
  mountOffset          = {0.0, 0.5, 0.0},     -- relative to mech head
  mountRotation        = {1.0, 0.0, 0.0, 0.0} -- mount orientation quaternion
}
```

### UIParams

```lua
UIParams {
  iconSize             = 64,                   -- pixels
  borderColor          = {1.0,1.0,1.0,0.9},   -- RGBA
  backgroundShape      = "hexagon",            -- circle | square | hexagon | none
  flashOnSelect        = true                  -- pulse when active
}
```

## C++ API Usage

### Basic Segmented Mech Generation

```cpp
#include "MechFactory.hpp"

// Initialize enhanced factory
MechFactory factory;
factory.initialize(100, 4); // 100 cache entries, 4 threads
factory.setGPUAcceleration(true);

// Create segmented mech parameters
SegmentedMechParams params;
params.id = "viper_mk1";
params.mechType = "snake";
params.segmentCount = 15;
params.segmentLength = 1.0f;
params.segmentRadius = 0.4f;
params.animationProfile = "mech_slither";
params.cockpitType = "internal";
params.cockpitSegmentIndex = 5;

// Create cockpit parameters
CockpitParams cockpit;
cockpit.seatWidth = 0.8f;
cockpit.seatDepth = 1.2f;
cockpit.canopyRadius = 1.0f;
cockpit.displayCount = 3;

// Create UI parameters
UIParams ui;
ui.iconSize = 64;
ui.backgroundShape = "hexagon";

// Generate asynchronously
auto future = factory.generateSegmentedAsync(params, cockpit, ui);
SegmentedMechBundle bundle = future.get();

// Create instance
SegmentedMechInstanceState instance = factory.createSegmentedInstance(params, cockpit);
instance.bundle = bundle;
```

### Dynamic Segment Management

```cpp
// Add segments at runtime
factory.addSegment(instance, instance.currentSegmentCount);

// Remove segments at runtime
factory.removeSegment(instance, instance.currentSegmentCount - 1);

// Update segment properties
std::unordered_map<std::string, float> properties;
properties["segmentRadius"] = 0.6f;
properties["segmentLength"] = 1.3f;
properties["maxBendAngleDeg"] = 60.0f;
factory.updateSegmentProperties(instance, 3, properties);

// Set segment count
factory.setSegmentCount(instance, 25);
```

### Cockpit Integration

```cpp
// Attach cockpit
CockpitParams newCockpit;
newCockpit.seatWidth = 1.2f;
newCockpit.canopyRadius = 1.5f;
newCockpit.displayCount = 6;
factory.attachCockpit(instance, newCockpit);

// Update cockpit parameters
newCockpit.lightIntensity = 2.0f;
factory.updateCockpitParams(instance, newCockpit);

// Detach cockpit
factory.detachCockpit(instance);
```

### Segmented Animation Control

```cpp
// Start segmented animation
factory.startSegmentedAnimation(instance, "mech_slither");

// Control animation progress
factory.setSegmentedAnimationProgress(instance, 0.5f);

// Pause/resume animation
factory.pauseSegmentedAnimation(instance);
factory.resumeSegmentedAnimation(instance);

// Update instance
factory.updateSegmentedInstance(instance, deltaTime);
```

## Lua Integration

### Enhanced Lua Bindings

```lua
-- Create segmented mech parameters in Lua
local snakeParams = {
    id = "lua_viper",
    mechType = "snake",
    segmentCount = 20,
    segmentLength = 1.1,
    segmentRadius = 0.45,
    connectorGap = 0.12,
    maxBendAngleDeg = 50.0,
    bendStiffness = 120.0,
    enablePlating = true,
    platesPerSegment = 8,
    plateThickness = 0.06,
    platingColor = {0.3, 0.3, 0.35, 1.0},
    stripeCount = 3,
    stripeWidth = 0.025,
    stripeColor = {1.0, 0.3, 0.3, 1.0},
    stripeGlowIntensity = 4.0,
    enableJointSparks = true,
    sparkRate = 25.0,
    sparkLifetime = 0.5,
    sparkColor = {1.0, 0.9, 0.6, 1.0},
    segmentMass = 12.0,
    jointDamping = 0.8,
    waveAmplitude = 1.8,
    waveFrequency = 1.2,
    animationProfile = "mech_slither",
    cockpitType = "internal",
    cockpitSegmentIndex = 6,
    cockpitRadius = 0.9,
    colorPrimary = {0.25, 0.35, 0.4},
    colorSecondary = {0.9, 0.7, 0.5}
}

-- Create cockpit parameters
local cockpitParams = {
    seatWidth = 0.9,
    seatDepth = 1.3,
    seatHeight = 0.55,
    canopyRadius = 1.1,
    canopyHeight = 0.9,
    displayCount = 4,
    gaugeCount = 7,
    cockpitLight = true,
    lightColor = {0.85, 0.85, 1.0, 1.0},
    lightIntensity = 1.1,
    holographicHUD = true,
    canopyAnimEnabled = true,
    canopyOpenAngleDeg = 95.0,
    canopyOpenDuration = 1.8
}

-- Create UI parameters
local uiParams = {
    iconSize = 96,
    borderColor = {1.0, 0.9, 0.3, 0.9},
    backgroundShape = "hexagon",
    flashOnSelect = true
}

-- Generate segmented mech
local future = mt_mech.generateSegmentedAsync(snakeParams, cockpitParams, uiParams)
local bundle = future:get()

-- Create instance
local instance = mt_mech.createSegmentedInstance(snakeParams, cockpitParams)

-- Start animation
mt_mech.startSegmentedAnimation(instance, "mech_slither")

-- Update instance
mt_mech.updateSegmentedInstance(instance, 0.016)

-- Dynamic segment management
mt_mech.addSegment(instance, 20)
mt_mech.removeSegment(instance, 19)
mt_mech.setSegmentCount(instance, 25)

-- Cockpit integration
mt_mech.attachCockpit(instance, cockpitParams)
mt_mech.updateCockpitParams(instance, cockpitParams)
mt_mech.detachCockpit(instance)
```

## Segmented Generation Features

### Mesh Generation

```cpp
// Segmented mesh generation
MeshHandle mesh = SegmentedMeshGenerator::buildSegmentedMech(params);

// Segment generation
MeshHandle segment = SegmentedMeshGenerator::createSegment(params, segmentIndex);
MeshHandle connector = SegmentedMeshGenerator::createSegmentConnector(params, segmentIndex);
MeshHandle armor = SegmentedMeshGenerator::createArmorPlates(params, segmentIndex);
MeshHandle strips = SegmentedMeshGenerator::createEmissiveStrips(params, segmentIndex);

// Assembly
MeshHandle assembled = SegmentedMeshGenerator::assembleSegments(segments, params);
MeshHandle tapered = SegmentedMeshGenerator::applyTapering(mesh, params);
MeshHandle detailed = SegmentedMeshGenerator::addNoiseDetail(mesh, params);

// Primitive generation
MeshHandle cylinder = SegmentedMeshGenerator::createCylinderSegment(radius, length, segments);
MeshHandle hexagon = SegmentedMeshGenerator::createHexagonSegment(radius, length);
MeshHandle custom = SegmentedMeshGenerator::createCustomSegment(shape, radius, length);
```

### Texture Generation

```cpp
// Segmented texture generation
TextureHandle skin = SegmentedTextureGenerator::buildSegmentedSkin(params);

// Pattern generation
TextureHandle pattern = SegmentedTextureGenerator::buildSegmentPattern(params);
TextureHandle armor = SegmentedTextureGenerator::buildArmorTexture(params);
TextureHandle emissive = SegmentedTextureGenerator::buildEmissiveTexture(params);
TextureHandle normal = SegmentedTextureGenerator::buildNormalMap(params);
TextureHandle roughness = SegmentedTextureGenerator::buildRoughnessMap(params);
TextureHandle metallic = SegmentedTextureGenerator::buildMetallicMap(params);

// Procedural patterns
SegmentedTextureGenerator::generateHexPattern(pixels, width, height, params);
SegmentedTextureGenerator::generateTechPattern(pixels, width, height, params);
SegmentedTextureGenerator::generateDamagedPattern(pixels, width, height, params);
SegmentedTextureGenerator::generateEmissiveStrips(pixels, width, height, params);
```

### Skeleton Generation

```cpp
// Segmented skeleton generation
SkeletonHandle rig = SegmentedSkeletonGenerator::buildSegmentedRig(params);

// Bone chain generation
SegmentedSkeletonGenerator::createSegmentBones(skeleton, params);
SegmentedSkeletonGenerator::createJointConstraints(skeleton, params);
SegmentedSkeletonGenerator::createCockpitBone(skeleton, params);

// Animation generation
AnimationHandle slither = SegmentedSkeletonGenerator::createSlitherAnimation(params);
AnimationHandle coil = SegmentedSkeletonGenerator::createCoilAnimation(params);
AnimationHandle undulate = SegmentedSkeletonGenerator::createUndulateAnimation(params);
AnimationHandle custom = SegmentedSkeletonGenerator::createCustomAnimation(params, profile);

// Procedural animation
AnimationHandle wave = SegmentedSkeletonGenerator::createWaveAnimation(params, amplitude, frequency);
AnimationHandle ik = SegmentedSkeletonGenerator::createIKAnimation(params, target);
```

### Physics Generation

```cpp
// Segmented physics generation
PhysicsHandle physics = SegmentedPhysicsGenerator::buildSegmentedPhysics(params);

// Segment physics
PhysicsHandle segmentPhysics = SegmentedPhysicsGenerator::createSegmentPhysics(params, segmentIndex);
SegmentedPhysicsGenerator::createJointPhysics(params, segmentIndex);
SegmentedPhysicsGenerator::createCockpitPhysics(params);

// Collision generation
SegmentedPhysicsGenerator::generateSegmentCollision(params, segmentIndex, vertices, indices);
SegmentedPhysicsGenerator::generateConnectorCollision(params, segmentIndex, vertices, indices);
```

### Particle Generation

```cpp
// Particle generation for segmented mechs
ParticleHandle sparks = SegmentedParticleGenerator::buildJointSparks(params);
ParticleHandle exhaust = SegmentedParticleGenerator::buildExhaustEffects(params);
ParticleHandle emissive = SegmentedParticleGenerator::buildEmissiveParticles(params);

// Particle systems
ParticleHandle sparkEmitter = SegmentedParticleGenerator::createSparkEmitter(params, jointIndex);
ParticleHandle exhaustEmitter = SegmentedParticleGenerator::createExhaustEmitter(params, segmentIndex);
ParticleHandle emissiveEmitter = SegmentedParticleGenerator::createEmissiveEmitter(params, segmentIndex);
```

### Cockpit Generation

```cpp
// Cockpit generation
MeshHandle cockpit = CockpitGenerator::buildCockpit(cockpitParams);
TextureHandle cockpitTex = CockpitGenerator::buildCockpitTexture(cockpitParams);
MaterialHandle cockpitMat = CockpitGenerator::buildCockpitMaterial(cockpitParams);

// Cockpit components
MeshHandle seat = CockpitGenerator::createSeat(cockpitParams);
MeshHandle canopy = CockpitGenerator::createCanopy(cockpitParams);
MeshHandle console = CockpitGenerator::createConsole(cockpitParams);
MeshHandle controls = CockpitGenerator::createControls(cockpitParams);
MeshHandle instruments = CockpitGenerator::createInstruments(cockpitParams);

// Glass and materials
MaterialHandle glass = CockpitGenerator::createGlassMaterial(cockpitParams);
MaterialHandle seatMat = CockpitGenerator::createSeatMaterial(cockpitParams);
MaterialHandle consoleMat = CockpitGenerator::createConsoleMaterial(cockpitParams);
```

### UI Icon Generation

```cpp
// UI icon generation
TextureHandle icon = UIIconGenerator::buildMechIcon(params, ui);

// Icon components
UIIconGenerator::drawMechSilhouette(pixels, width, height, params);
UIIconGenerator::drawBackground(pixels, width, height, ui);
UIIconGenerator::drawBorder(pixels, width, height, ui);
UIIconGenerator::addFlashEffect(pixels, width, height, ui);
```

## Animation Profiles

### Available Animation Types

- **mech_slither**: Sine wave lateral undulation along spine
- **coil**: Wrap segments into spiral patterns  
- **undulate**: Smooth wave motion through segments
- **custom**: Load keyframe or procedural curves

### Procedural Animation Features

- **Traveling Wave**: Automatic wave propagation through segments
- **Target-Following IK**: Head segment aims at target points
- **Blend Modes**: Mix procedural and IK animations
- **Real-time Control**: Modify animation parameters during runtime

## Cockpit Integration Features

### Cockpit Types

- **Internal**: Recessed spherical cockpits within segments
- **External**: Bulged cockpit modules on segment surfaces
- **Modular**: Swappable cockpit configurations

### Cockpit Components

- **Seat**: Sculpted cushion with headrest options
- **Canopy**: Glass dome with refraction and Fresnel effects
- **Console**: Multiple displays and control panels
- **Controls**: Joysticks, levers, and foot pedals
- **Instruments**: Analog gauges and digital displays
- **HUD**: Holographic heads-up display elements

### Interactive Features

- **Canopy Animation**: Automatic opening/closing sequences
- **Seat Dynamics**: Settling effects and vibration response
- **Console Vibrations**: Engine vibration feedback
- **Ambient Lighting**: Dynamic cockpit illumination
- **Particle Effects**: Sparks and alert particles

## Performance Features

### Caching Strategy

- **LRU Cache**: Least recently used asset eviction
- **Hash-based Keys**: Efficient cache key generation using xxHash
- **Thread Safety**: Concurrent access with proper synchronization
- **Memory Management**: Automatic cleanup and garbage collection

### GPU Acceleration

- **Compute Shaders**: Offload segment calculations to GPU
- **Texture-based Morphs**: Store morph data in textures
- **Instanced Rendering**: Efficient multi-segment rendering
- **Memory Optimization**: Minimize GPU memory usage

### Dynamic LOD

- **Distance-based LOD**: Reduce segment detail at distance
- **Performance-based LOD**: Adjust based on frame rate
- **Impostor Generation**: Replace segments with billboards
- **Memory Coalescing**: Minimize memory fragmentation

## Integration Benefits

### Rapid Iteration
- **Lua Scripting**: Tweak parameters and see results immediately
- **Dynamic Segments**: Add/remove segments without rebuilding
- **Live Cockpit**: Modify cockpit configurations in real-time
- **Batch Generation**: Create multiple variants simultaneously

### No Asset Dependencies
- **Procedural Generation**: Create segmented mechs from parameters only
- **Runtime Creation**: Generate assets on-demand
- **Infinite Variety**: Endless segment combinations
- **Memory Efficient**: Generate only what's needed

### Dynamic Behavior
- **Runtime Morphing**: Change segment count during gameplay
- **Live Animation**: Switch animation profiles on-the-fly
- **Interactive Cockpits**: Real-time cockpit modifications
- **Seamless Integration**: Works with existing game systems

### Performance Optimized
- **Concurrent Generation**: Multi-threaded asset creation
- **Intelligent Caching**: LRU cache with hash-based keys
- **GPU Acceleration**: Hardware-accelerated features
- **Memory Management**: Efficient resource allocation

## Future Enhancements

### Planned Features

1. **GPU-driven Spline Tessellation**: Ultra-smooth segment generation
2. **Modular Weapon Hardpoints**: Procedural weapon attachments per segment
3. **Real-time Cockpit UI**: Integrated HUD in generated cockpit meshes
4. **Particle Effects**: Segment joint stress and damage effects
5. **Network Synchronization**: Multiplayer segment state synchronization

### Performance Optimizations

1. **Nanite Integration**: Cluster-based mesh streaming for segments
2. **Ray Tracing**: Hardware-accelerated rendering for glass cockpits
3. **Machine Learning**: AI-optimized segment generation
4. **Compression**: Advanced asset compression for segmented data

## Conclusion

The segmented mech asset generation pipeline provides a comprehensive solution for creating dynamic, modular mechs with endless variety. The system's procedural approach, dynamic segment management, and comprehensive cockpit integration make it ideal for rapid development and runtime customization.

By integrating seamlessly with the existing FormShiftMechGen pipeline while adding powerful new segmented capabilities, this system enables the creation of complex, dynamic mech systems that can transform between different configurations in real-time, all without requiring pre-made art assets.

The combination of snake, worm, and serpent mech types with fully featured cockpit integration creates a versatile platform for creating diverse mech experiences in your Magi-Tech Arcane Alchemy and Sorcery universe. 