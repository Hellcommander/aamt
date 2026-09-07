# Crossbow Bolts, Arrows & Crossbow Generation Pipeline

This document describes the complete asset generation pipeline for crossbow weapons and their projectiles (bolts and arrows). The system provides both synchronous and asynchronous generation with comprehensive parameter validation, caching, and performance optimization.

## Overview

The crossbow generation pipeline consists of three main components:
1. **Crossbows** - The main weapon with draw mechanics, reload animations, and material systems
2. **Bolts** - Short, high-velocity projectiles with optional fletching
3. **Arrows** - Long-range projectiles with fletch stabilization and spine rating

## Architecture

### Core Components

#### 1. Parameter Schemas
- `CrossbowParams` - Weapon configuration (draw length, weight, materials)
- `BoltParams` - Short projectile configuration (length, radius, tip mass)
- `ArrowParams` - Long projectile configuration (shaft length, spine rating, fletch style)

#### 2. Asset Bundles
- `CrossbowBundle` - Complete weapon assets (mesh, string, animation, materials)
- `ProjectileBundle` - Complete projectile assets (mesh, material, VFX, simulation, collision)

#### 3. Factory System
- `CrossbowAssetFactory` - Main factory with thread pool and caching
- Async generation with futures for background processing
- Synchronous generation for immediate access
- Intelligent caching with hash-based lookups

### Generator Modules

#### BowGen
- **Purpose**: Generate crossbow mesh geometry
- **Features**: 
  - Stock with ergonomic curves
  - Curved limbs using spline-based segments
  - Trigger mechanism
  - Sight rail system
- **Parameters**: Draw length, draw weight influence geometry

#### StringGen
- **Purpose**: Generate bowstring mesh
- **Features**:
  - Main string cylinder
  - End loops for attachment
  - Material-based tension simulation
- **Parameters**: Draw length, string material

#### AnimGen
- **Purpose**: Generate reload animations
- **Features**:
  - Auto-reload sequences
  - Manual reload with longer draw phases
  - Keyframe-based timing
- **Parameters**: Auto-reload flag, reload time

#### MaterialGen
- **Purpose**: Assign and load materials
- **Features**:
  - Stock material assignment
  - Limb material assignment
  - Trigger material (metal)
  - Shaft material based on projectile ID
- **Parameters**: Material names, projectile IDs

#### BoltGen
- **Purpose**: Generate bolt mesh geometry
- **Features**:
  - Main shaft cylinder
  - Cone tip with optional barbs
  - Optional fletching (3 vanes)
  - Barbed tip variations
- **Parameters**: Length, radius, tip mass, barbed flag

#### ArrowGen
- **Purpose**: Generate arrow mesh geometry
- **Features**:
  - Longer, thinner shaft
  - Narrower, longer tip
  - Nock for string attachment
  - Elaborate fletching (3-4 vanes)
  - Multiple fletch styles
- **Parameters**: Shaft length, diameter, spine rating, fletch style

#### VFXGen
- **Purpose**: Generate visual effects trails
- **Features**:
  - Spark trails for bolts (particle system)
  - Feather trails for arrows (ribbon system)
  - Intensity-based scaling
- **Parameters**: Style ("spark"/"feather"), intensity

#### ProjectileSim
- **Purpose**: Setup flight simulation
- **Features**:
  - Linear simulation for bolts
  - Fletched simulation for arrows
  - Drag coefficients and gravity influence
  - Maximum distance limits
- **Parameters**: Length, mass, spine rating, fletch style

#### CollisionGen
- **Purpose**: Generate collision geometry
- **Features**:
  - Cylinder/capsule colliders
  - Continuous collision detection (CCD)
  - Projectile material assignment
- **Parameters**: Radius, height

## Usage Patterns

### Synchronous Generation (Immediate Access)

```lua
-- Create parameters
local crossbow = create_light_crossbow()
crossbow.id = "my_crossbow"
crossbow.drawLength = 0.5
crossbow.drawWeight = 300

-- Generate immediately
local bundle = generate_crossbow(crossbow)
if bundle.mesh ~= 0 then
    print("Crossbow generated successfully")
end
```

### Asynchronous Generation (Background Processing)

```lua
-- Start async generation
local success = spawn_crossbow(crossbow)
if success then
    print("Generation started")
end

-- Set up completion callbacks
function on_crossbow_ready(id, bundle)
    print("Crossbow ready: " .. id)
end

function on_crossbow_error(id, error)
    print("Generation failed: " .. error)
end

-- Poll for completion (call periodically)
poll_assets(lua)
```

### Parameter Validation

```lua
local params = CrossbowParams()
params.id = "test"
params.drawLength = 0.5
params.drawWeight = 300

if params:validate() then
    local bundle = generate_crossbow(params)
else
    print("Invalid parameters")
end
```

## Performance Features

### Caching System
- Hash-based caching using XXH64
- Automatic cache invalidation
- Memory-efficient storage
- Cache size monitoring

### Thread Pool
- Configurable thread count (default: 4)
- Non-blocking async operations
- Efficient resource utilization
- Background processing

### Optimization
- Mesh optimization and LOD
- Material sharing
- Collision geometry reuse
- VFX trail optimization

## Advanced Features

### Custom Configurations

#### Light Crossbow
- Draw length: 0.4m
- Draw weight: 200N
- Auto-reload: true
- Reload time: 0.8s
- Materials: WoodOak stock, Fiberglass limbs

#### Heavy Crossbow
- Draw length: 0.7m
- Draw weight: 500N
- Auto-reload: false
- Reload time: 2.5s
- Materials: MetalSteel stock, CarbonFiber limbs

#### Steel Bolt
- Length: 0.35m
- Shaft radius: 0.004m
- No fletching
- Barbed tip
- High tip mass for penetration

#### Wood Arrow
- Shaft length: 1.0m
- Shaft diameter: 0.008m
- Spine rating: 500
- Parabolic fletching
- Balanced tip mass

### Fletch Styles
- **Parabolic**: 4 vanes, high stability
- **Shield**: 3 vanes, larger surface area
- **Flu-Flu**: 6 vanes, short range stability

### Material Systems
- **Stock Materials**: WoodOak, MetalSteel, CarbonFiber
- **Limb Materials**: Fiberglass, CarbonFiber, Steel
- **String Materials**: Hemp, Synthetic, Kevlar
- **Shaft Materials**: Auto-detected from projectile ID

## Integration Points

### Lua Bindings
- Parameter type bindings with validation
- Bundle type bindings for asset access
- Async/sync generation functions
- Progress monitoring functions
- Cache management functions

### Error Handling
- Parameter validation with detailed error messages
- Generation failure detection
- Exception handling and logging
- Graceful degradation

### Monitoring
- Real-time progress tracking
- Performance benchmarking
- Cache hit/miss statistics
- Memory usage monitoring

## File Structure

```
cpp_backend/agents/GeneratorAgent/
├── CrossbowAssetFactory.hpp      # Factory interface
├── CrossbowAssetFactory.cpp      # Factory implementation
├── CrossbowTypes.hpp            # Parameter schemas
├── CrossbowGenerators.cpp       # Generator modules
├── CrossbowLuaBindings.hpp      # Lua binding interface
├── CrossbowLuaBindings.cpp      # Lua binding implementation
└── example_crossbow_generation.lua  # Usage examples
```

## Future Extensions

### Planned Features
1. **Elemental Projectiles**: Fire, ice, electric damage VFX
2. **Procedural Bow Styles**: GAN-based limb curve generation
3. **Dynamic String Tension**: Variable draw force simulation
4. **Multiplayer Sync**: Cross-client state replication
5. **Enchantment System**: Rune-based projectile modification

### Performance Optimizations
1. **GPU Acceleration**: Compute shader mesh generation
2. **LOD System**: Distance-based detail reduction
3. **Instancing**: Batch rendering for projectiles
4. **Memory Pooling**: Reusable asset buffers

## Conclusion

The crossbow generation pipeline provides a comprehensive, high-performance system for creating realistic crossbow weapons and projectiles. With both synchronous and asynchronous generation, intelligent caching, and extensive customization options, it serves as a foundation for advanced weapon systems in the Magi-Tech mod.

The modular design allows for easy extension and modification, while the performance optimizations ensure smooth gameplay even with complex weapon configurations. 