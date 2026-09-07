# Hybrid C++23/26 + Lua In-Game Multi-Form Mech Generator

## Overview

This enhanced mech generator system integrates the original FormShiftMechGen pipeline with hybrid C++23/26 + Lua features, providing **endless mech variety** through procedural generation, multi-form support, and comprehensive Lua scripting capabilities.

## Key Features

### 🚀 **Hybrid Architecture**
- **C++23/26 Core**: High-performance procedural generation and asset management
- **Lua Scripting**: Rapid iteration and runtime mech customization
- **Seamless Integration**: Preserves all existing FormShiftMechGen features

### 🎨 **Procedural Generation**
- **No Pre-made Art Required**: Generate fully rigged, textured, and animated mechs from parameters
- **Infinite Variety**: Procedural mesh, texture, and skeleton generation
- **Real-time Creation**: Spawn mech variants on-the-fly during gameplay

### 🔄 **Multi-Form Support**
- **Dynamic Form Shifting**: Transform between different mech configurations
- **Smooth Morphing**: GPU-accelerated blend shape and skeleton transitions
- **Runtime Form Switching**: Change forms without pre-loading assets

### ⚡ **Performance Optimized**
- **Concurrent Generation**: Thread-pool based async asset creation
- **LRU Caching**: Intelligent cache management with hash-based keys
- **GPU Acceleration**: Hardware-accelerated morphing and physics simulation

## Architecture

### Core Components

```
mech_generator/
├── MechTypes.hpp              # Enhanced type definitions
├── MechFactory.hpp            # Hybrid factory interface
├── MechFactory.cpp            # Factory implementation
├── MechGenerators.hpp         # Procedural generators
├── MechGenerators.cpp         # Generator implementations
├── MechLuaBindings.hpp        # Enhanced Lua bindings
├── MechLuaBindings.cpp        # Lua binding implementations
├── hybrid_example.cpp         # Comprehensive demo
└── HYBRID_INTEGRATION_README.md
```

### Integration with Existing Pipeline

The hybrid system seamlessly integrates with the existing FormShiftMechGen pipeline:

- **Preserves All Features**: All original functionality maintained
- **Enhances Capabilities**: Adds procedural generation and Lua scripting
- **Shared Infrastructure**: Uses existing MultithreadBus and GPU interfaces
- **Consistent Patterns**: Follows established asset generator patterns

## MechParams Schema

### Enhanced Parameter Structure

```lua
MechParams {
  -- Core parameters
  id            = "recon_biped",
  style         = "scout",              -- heavy, scout, support
  forms         = {"mobile", "siege"},  -- multi-form names
  colorPrimary  = {0.2, 0.8, 0.3},     -- RGB [0–1]
  colorAccent   = {1.0, 0.6, 0.1},
  limbCount     = 2,
  torsoSize     = {1.0, 1.2, 0.6},     -- width, height, depth
  limbLength    = 0.8,
  armorPlates   = true,
  weaponMounts  = {"shoulder", "arm"},
  pattern       = "hexCamouflage",      -- procedural skin pattern
  detailLevel   = 2,                    -- 0=low,1=medium,2=high
  pulseEmission = true,                 -- glowing vents, power cores
  
  -- Enhanced hybrid features
  variant       = "recon",              -- mech variant type
  armorTypes    = {"light", "reactive"}, -- armor plate types
  weaponTypes   = {"pulse_rifle", "missile_pod"}, -- weapon systems
  scale         = {1.0, 1.0, 1.0},     -- overall scale
  mass          = 800.0,                -- total mass
  enableGlow    = true,                 -- emissive effects
  enableShield  = false,                -- shield generator
  aiBehavior    = "stealth",            -- AI behavior type
  crewCapacity  = 1,                    -- crew members
  maxSpeed      = 15.0,                 -- max movement speed
  jumpHeight    = 3.0,                  -- jump capability
  canFly        = false,                -- flight capability
  canSwim       = true,                 -- aquatic capability
  faction       = "alliance",           -- faction alignment
  abilities     = {"cloak", "emp_blast", "rapid_fire"}, -- special abilities
  stats         = {                     -- custom stats
    armor = 0.7,
    speed = 0.9,
    firepower = 0.6,
    stealth = 0.8
  },
  
  -- Procedural generation parameters
  noiseScale        = 2.0,              -- texture noise scale
  patternIntensity  = 0.7,              -- pattern strength
  textureResolution = 1024,             -- texture size
  generateNormalMap = true,             -- normal map generation
  generateRoughnessMap = true,          -- roughness map
  generateMetallicMap = true,           -- metallic map
  
  -- Animation parameters
  morphDuration = 1.2,                  -- form change duration
  morphCurve    = "easeInOut",          -- morph interpolation
  enableIK      = true,                 -- inverse kinematics
  enablePhysics = true,                 -- physics simulation
  
  -- LOD parameters
  lodDistances = {10.0, 50.0, 100.0, 200.0},
  lodTriangleCounts = {5000, 2000, 500, 100}
}
```

## C++ API Usage

### Basic Hybrid Generation

```cpp
#include "MechFactory.hpp"

// Initialize enhanced factory
MechFactory factory;
factory.initialize(100, 4); // 100 cache entries, 4 threads
factory.setGPUAcceleration(true);

// Create mech parameters
MechParams params;
params.id = "recon_biped";
params.style = "scout";
params.forms = {"mobile", "siege", "stealth"};
params.colorPrimary = glm::vec3(0.2f, 0.8f, 0.3f);
params.colorAccent = glm::vec3(1.0f, 0.6f, 0.1f);
params.limbCount = 2;
params.torsoSize = glm::vec3(1.0f, 1.2f, 0.6f);
params.armorPlates = true;
params.pattern = "hexCamouflage";
params.detailLevel = 2;

// Generate asynchronously
auto future = factory.generateAsync(params);
MechBundle bundle = future.get();

// Create instance
MechInstanceState instance = factory.createInstance(params);
instance.bundle = bundle;

// Start morphing
factory.startMorph(instance, "mobile");
```

### Batch Generation

```cpp
// Generate multiple mechs simultaneously
std::vector<MechParams> mechParams;
// ... populate params ...

std::vector<std::future<MechBundle>> futures;
for (const auto& params : mechParams) {
    futures.push_back(factory.generateAsync(params));
}

// Wait for all to complete
std::vector<MechBundle> bundles;
for (auto& future : futures) {
    bundles.push_back(future.get());
}
```

### Procedural Generation

```cpp
// Set procedural parameters
ProceduralParams procParams;
procParams.frequency = 2.0f;
procParams.amplitude = 1.5f;
procParams.octaves = 6;
procParams.patternType = "hexagonal";
procParams.roughness = 0.3f;
procParams.metallic = 0.8f;

factory.setProceduralParams(procParams);

// Generate with procedural features
MechParams params = createScoutTemplate();
params.pattern = "hexCamouflage";
MechBundle bundle = factory.generateSync(params);
```

## Lua Integration

### Enhanced Lua Bindings

```lua
-- Load mech with hybrid features
local mechParams = {
    id = "recon_biped",
    style = "scout",
    forms = {"mobile", "siege", "stealth"},
    colorPrimary = {0.2, 0.8, 0.3},
    colorAccent = {1.0, 0.6, 0.1},
    limbCount = 2,
    torsoSize = {1.0, 1.2, 0.6},
    limbLength = 0.8,
    armorPlates = true,
    weaponMounts = {"shoulder", "arm"},
    pattern = "hexCamouflage",
    detailLevel = 2,
    pulseEmission = true,
    
    -- Enhanced features
    variant = "recon",
    armorTypes = {"light", "reactive"},
    weaponTypes = {"pulse_rifle", "missile_pod"},
    scale = {1.0, 1.0, 1.0},
    mass = 800.0,
    enableGlow = true,
    enableShield = false,
    aiBehavior = "stealth",
    crewCapacity = 1,
    maxSpeed = 15.0,
    jumpHeight = 3.0,
    canFly = false,
    canSwim = true,
    faction = "alliance",
    abilities = {"cloak", "emp_blast", "rapid_fire"},
    stats = {
        armor = 0.7,
        speed = 0.9,
        firepower = 0.6,
        stealth = 0.8
    }
}

-- Generate mech
local future = mt_mech.generateAsync(mechParams)
local bundle = future:get()

-- Create instance
local instance = mt_mech.createInstance(mechParams)

-- Start morphing
mt_mech.startMorph(instance, "mobile")

-- Update instance
mt_mech.updateInstance(instance, deltaTime)
```

### Template System

```lua
-- Create from template
local params = mt_mech.createFromTemplate("scout")
params.id = "custom_scout_01"
params.colorPrimary = {0.8, 0.2, 0.8} -- Purple

-- Register custom template
local customTemplate = {
    -- ... template parameters ...
}
mt_mech.registerTemplate("custom_template", customTemplate)

-- Get available templates
local templates = mt_mech.getAvailableTemplates()
for i, template in ipairs(templates) do
    print("Template: " .. template)
end
```

### Performance Monitoring

```lua
-- Get performance metrics
local metrics = mt_mech.getPerformanceMetrics()
print("Cache hit rate: " .. (metrics.cacheHitRate * 100) .. "%")
print("Average generation time: " .. metrics.avgGenerationTime .. " ms")
print("Active instances: " .. metrics.activeInstances)

-- Reset metrics
mt_mech.resetPerformanceMetrics()
```

## Procedural Generation Features

### Mesh Generation

```cpp
// Procedural mesh generation
MeshHandle mesh = MeshGenerator::buildProceduralMesh(params, procParams);

// Modular assembly
MeshHandle modularMesh = MeshGenerator::buildModularMesh(params);

// LOD generation
MeshHandle lodMesh = MeshGenerator::buildLODMesh(params, lodLevel);

// Primitive generation
MeshHandle box = MeshGenerator::createBox(glm::vec3(1.0f, 1.0f, 1.0f));
MeshHandle cylinder = MeshGenerator::createCylinder(0.5f, 2.0f, 16);
MeshHandle sphere = MeshGenerator::createSphere(1.0f, 16);
MeshHandle capsule = MeshGenerator::createCapsule(0.5f, 2.0f, 16);
```

### Texture Generation

```cpp
// Procedural skin generation
TextureHandle skin = TextureGenerator::buildProceduralSkin(params, procParams);

// Pattern generation
TextureHandle pattern = TextureGenerator::buildPatternTexture("hexagonal", params);

// Material maps
TextureHandle normalMap = TextureGenerator::buildNormalMap(params);
TextureHandle roughnessMap = TextureGenerator::buildRoughnessMap(params);
TextureHandle metallicMap = TextureGenerator::buildMetallicMap(params);
TextureHandle emissiveMap = TextureGenerator::buildEmissiveMap(params);
```

### Skeleton Generation

```cpp
// Multi-form rigging
SkeletonHandle rig = SkeletonGenerator::buildMultiFormRig(params);

// IK rigging
SkeletonHandle ikRig = SkeletonGenerator::buildIKRig(params);

// Physics rigging
SkeletonHandle physicsRig = SkeletonGenerator::buildPhysicsRig(params);

// Animation generation
AnimationHandle idleAnim = SkeletonGenerator::createIdleAnimation(params);
AnimationHandle walkAnim = SkeletonGenerator::createWalkAnimation(params);
AnimationHandle morphAnim = SkeletonGenerator::createMorphAnimation(params, "mobile", "siege");
```

## Multi-Form Support

### Form Types

- **WALKER**: Standard bipedal configuration
- **FLYER**: Aerial configuration with thrusters
- **TANK**: Heavy armored configuration
- **SWIMMER**: Aquatic configuration
- **CLIMBER**: Vertical mobility
- **STEALTH**: Low-profile configuration
- **COMBAT**: Battle-optimized
- **UTILITY**: Specialized tasks

### Morphing System

```cpp
// Start morphing
factory.startMorph(instance, "mobile");

// Control morph progress
factory.setMorphProgress(instance, 0.5f);

// Pause/resume morphing
factory.pauseMorph(instance);
factory.resumeMorph(instance);

// Update instance
factory.updateInstance(instance, deltaTime);
```

## Performance Features

### Caching Strategy

- **LRU Cache**: Least recently used asset eviction
- **Hash-based Keys**: Efficient cache key generation using xxHash
- **Thread Safety**: Concurrent access with proper synchronization
- **Memory Management**: Automatic cleanup and garbage collection

### GPU Acceleration

- **Compute Shaders**: Offload morph calculations to GPU
- **Texture-based Morphs**: Store morph data in textures
- **Instanced Rendering**: Efficient multi-instance rendering
- **Memory Optimization**: Minimize GPU memory usage

### Hot Reload

- **File Watching**: Efficient file change detection
- **Incremental Updates**: Only rebuild changed components
- **Background Processing**: Non-blocking asset updates
- **Memory Coalescing**: Minimize memory fragmentation

## Integration Benefits

### Rapid Iteration
- **Lua Scripting**: Tweak parameters and see results immediately
- **Hot Reload**: Live editing without restarting
- **Template System**: Reuse and modify mech configurations
- **Batch Generation**: Create multiple variants simultaneously

### No Asset Dependencies
- **Procedural Generation**: Create mechs from parameters only
- **Runtime Creation**: Generate assets on-demand
- **Infinite Variety**: Endless mech combinations
- **Memory Efficient**: Generate only what's needed

### Multi-Form Support
- **Dynamic Forms**: Switch between configurations at runtime
- **Smooth Morphing**: GPU-accelerated transitions
- **Form-specific Features**: Different capabilities per form
- **Seamless Integration**: Works with existing game systems

### Performance Optimized
- **Concurrent Generation**: Multi-threaded asset creation
- **Intelligent Caching**: LRU cache with hash-based keys
- **GPU Acceleration**: Hardware-accelerated features
- **Memory Management**: Efficient resource allocation

## Future Enhancements

### Planned Features

1. **AI-Driven Generation**: Machine learning for mech design
2. **Procedural Animations**: Auto-generated animation sequences
3. **Network Synchronization**: Multiplayer morph synchronization
4. **VR Editor Support**: 3D manipulation in virtual reality
5. **Advanced Physics**: Soft body and fluid simulation

### Performance Optimizations

1. **Nanite Integration**: Cluster-based mesh streaming
2. **Ray Tracing**: Hardware-accelerated rendering
3. **Machine Learning**: AI-optimized generation
4. **Compression**: Advanced asset compression

## Conclusion

The hybrid C++23/26 + Lua mech generator provides a comprehensive solution for creating dynamic, form-shifting mechs with endless variety. The system's procedural approach, multi-form support, and comprehensive Lua integration make it ideal for rapid development and runtime customization.

By integrating seamlessly with the existing FormShiftMechGen pipeline while adding powerful new capabilities, this hybrid system enables the creation of complex, dynamic mech systems that can transform between different configurations in real-time, all without requiring pre-made art assets. 