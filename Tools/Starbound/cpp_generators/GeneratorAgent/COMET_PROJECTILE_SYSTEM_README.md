# Comet/Meteor Projectile Asset Generation Pipeline

A complete C++ pipeline for generating blazing comets and meteors with rocky cores, glowing reentry fire, particle-driven dust trails, and optional fragmentation—all from pure data into mesh, shader, texture, and particle generators.

## Overview

This system provides a comprehensive asset generation pipeline for creating dynamic comet and meteor projectiles in OpenStarbound. The pipeline generates:

- **Mesh Assets**: Irregular spherical cores with noise-based vertex displacement
- **Shader Assets**: Emissive materials with heat distortion and trail effects
- **Texture Assets**: Procedural rock textures with color gradients
- **Particle Assets**: Dust trails, sparks, and fragmentation effects

## Architecture

### Core Components

1. **CometProjectileParams**: Complete parameter schema for all comet properties
2. **CometProjectileFactory**: Asynchronous asset generation with caching
3. **MeshGen**: Procedural mesh generation with noise-based deformation
4. **ShaderGen**: Dynamic shader compilation with parameter-driven effects
5. **TextureGen**: Procedural texture generation with noise and gradients
6. **ParticleGen**: Particle system generation for trails and effects

### Namespace Structure

```cpp
namespace MagiTech::CometProjectiles {
    // Parameter types and enums
    struct CometProjectileParams;
    enum class CometType, CometShape, TrailType, etc.
    
    // Factory and generation
    class CometProjectileFactory;
    namespace MeshGen, ShaderGen, TextureGen, ParticleGen;
    
    // Utilities
    namespace ParamUtils;
}
```

## Parameter Schema

### Basic Properties

```lua
CometProjectileParams {
  id                    = "skyfall_meteor",      -- unique identifier
  cometType            = CometType.METEOR,       -- meteor, comet, asteroid, etc.
  cometShape           = CometShape.IRREGULAR,   -- sphere, irregular, fragmented, etc.
  trailType            = TrailType.DUST,         -- none, dust, fire, smoke, sparks
  fragmentationType    = FragmentationType.EXPLOSIVE, -- none, explosive, shatter, etc.
  noiseType            = NoiseType.PERLIN,       -- perlin, simplex, curl, fractal
  blendMode            = BlendMode.ADDITIVE,     -- additive, multiply, screen, etc.
}
```

### Physical Properties

```lua
-- Core properties
coreRadius            = 0.5,                   -- world units
irregularity          = 0.8,                   -- 0–1 noise displacement
speed                 = 30.0,                  -- units/sec
gravityInfluence      = 1.0,                   -- fall acceleration multiplier
mass                  = 1.2,                   -- physics mass
drag                  = 0.15,                  -- air resistance
lift                  = 0.05,                  -- aerodynamic lift
```

### Visual Properties

```lua
-- Colors
heatColor             = {1.0, 0.5, 0.1},       -- emissive tint at core
burnColor             = {1.0, 0.8, 0.3},       -- outer flame tint
coreColor             = {0.8, 0.6, 0.4},       -- base rock color
glowColor             = {1.0, 0.4, 0.0},       -- glow emission color
dustColor             = {0.5, 0.5, 0.5, 0.6},  -- trail particle color
sparkColor            = {1.0, 0.4, 0.1, 1.0}, -- spark particle color

-- Visual effects
glowIntensity         = 2.0,                   -- emissive power
emissivePower         = 1.5,                   -- core emission strength
coreOpacity           = 1.0,                   -- core transparency
trailOpacity          = 0.8,                   -- trail transparency
enableCoreGlow        = true,                  -- enable core emission
enableTrailGlow       = true,                  -- enable trail emission
```

### Trail Properties

```lua
-- Trail configuration
trailLength           = 2.0,                   -- seconds of ribbon length
trailWidth            = 0.15,                  -- trail width in units
trailNoiseScale       = 1.5,                   -- distortion tiling
trailNoiseSpeed       = 3.0,                   -- animation speed
trailFadeSpeed        = 1.2,                   -- fade-out speed
enableTrailFade       = true,                  -- enable trail fading
enableTrailDistortion = true,                  -- enable trail distortion
trailDistortionStrength = 0.2,                -- distortion intensity
```

### Particle Properties

```lua
-- Dust trail particles
dustParticleCount     = 100,                   -- particles per second
dustLifetime          = 1.5,                   -- seconds
dustSize              = 0.05,                  -- particle size
dustSpeed             = 1.0,                   -- velocity magnitude
enableDustFade        = true,                  -- enable particle fade
dustFadeSpeed         = 1.5,                   -- fade speed

-- Spark particles
sparkParticleCount    = 30,                    -- particles per second
sparkLifetime         = 0.6,                   -- seconds
sparkSize             = 0.03,                  -- particle size
sparkSpeed            = 1.5,                   -- velocity magnitude
enableSparkFade       = true,                  -- enable particle fade
sparkFadeSpeed        = 1.0,                   -- fade speed
```

### Fragmentation Properties

```lua
-- Fragmentation effects
fragmentationCount    = 8,                     -- number of shards on impact
fragmentSizeFactor    = 0.3,                   -- size relative to core
fragmentSpread        = 1.5,                   -- spread radius
fragmentVelocity      = 2.5,                   -- ejection velocity
enableFragmentPhysics = true,                  -- enable physics simulation
fragmentLifetime      = 2.0,                   -- shard lifetime
```

### Shader Properties

```lua
-- Shader configuration
shaderType            = "meteor",              -- shader variant
shaderIntensity       = 1.2,                   -- overall intensity
enableDistortion      = true,                  -- enable vertex distortion
distortionStrength    = 0.15,                  -- distortion intensity
enableBlur            = false,                 -- enable motion blur
blurStrength          = 0.1,                   -- blur intensity
enableHeatDistortion  = true,                  -- enable heat distortion
heatDistortionStrength = 0.1,                 -- heat distortion intensity
```

### Physics Properties

```lua
-- Physics simulation
enablePhysics         = true,                  -- enable physics simulation
enableCollision       = true,                  -- enable collision detection
collisionRadius       = 0.5,                   -- collision sphere radius
enableGravity         = true,                  -- enable gravity effects
enableAirResistance   = true,                  -- enable air resistance
airResistanceFactor   = 0.1,                   -- air resistance coefficient
```

### Performance Properties

```lua
-- Performance settings
enableCaching         = true,                  -- enable asset caching
enableHotReload       = true,                  -- enable hot reloading
enableParallelProcessing = true,               -- enable multi-threading
lodLevel              = 0,                     -- level of detail
```

## Usage Examples

### Basic Comet Generation

```lua
-- Create a basic meteor
local meteor = spawn_comet_projectile(CometProjectileParams{
    id = "basic_meteor",
    cometType = CometType.METEOR,
    cometShape = CometShape.IRREGULAR,
    coreRadius = 0.5,
    speed = 30.0,
    heatColor = {1.0, 0.5, 0.1},
    burnColor = {1.0, 0.8, 0.3},
    glowIntensity = 2.0,
    trailLength = 2.0,
    dustParticleCount = 100,
    sparkParticleCount = 30
});

print("Meteor mesh handle:", meteor.mesh);
print("Meteor shader handle:", meteor.shader);
print("Meteor texture handle:", meteor.texture);
```

### Advanced Falling Star

```lua
-- Create a spectacular falling star
local fallingStar = spawn_comet_projectile(CometProjectileParams{
    id = "falling_star",
    cometType = CometType.FALLING_STAR,
    cometShape = CometShape.CRYSTALLINE,
    coreRadius = 0.4,
    irregularity = 0.9,
    speed = 40.0,
    heatColor = {1.0, 0.7, 0.2},
    burnColor = {1.0, 0.9, 0.5},
    glowIntensity = 3.0,
    trailLength = 1.8,
    trailNoiseScale = 2.0,
    trailNoiseSpeed = 4.0,
    dustParticleCount = 120,
    dustLifetime = 1.2,
    sparkParticleCount = 25,
    sparkLifetime = 0.5,
    fragmentationCount = 5,
    fragmentSizeFactor = 0.2,
    enableHeatDistortion = true,
    heatDistortionStrength = 0.15
});
```

### Explosive Meteor

```lua
-- Create an explosive meteor with fragmentation
local explosiveMeteor = spawn_comet_projectile(CometProjectileParams{
    id = "explosive_meteor",
    cometType = CometType.METEOR,
    cometShape = CometShape.FRAGMENTED,
    fragmentationType = FragmentationType.EXPLOSIVE,
    coreRadius = 0.6,
    irregularity = 0.8,
    speed = 35.0,
    mass = 1.5,
    heatColor = {1.0, 0.4, 0.0},
    burnColor = {1.0, 0.6, 0.2},
    glowIntensity = 2.5,
    trailLength = 2.5,
    dustParticleCount = 150,
    sparkParticleCount = 50,
    fragmentationCount = 12,
    fragmentSizeFactor = 0.25,
    fragmentSpread = 2.0,
    fragmentVelocity = 3.0,
    enableFragmentPhysics = true,
    fragmentLifetime = 3.0
});
```

### JSON Configuration

```json
{
  "id": "skyfall_meteor",
  "cometType": "meteor",
  "cometShape": "irregular",
  "trailType": "dust",
  "fragmentationType": "explosive",
  "noiseType": "perlin",
  "blendMode": "additive",
  
  "coreRadius": 0.5,
  "irregularity": 0.8,
  "speed": 30.0,
  "gravityInfluence": 1.0,
  "mass": 1.2,
  "drag": 0.15,
  "lift": 0.05,
  
  "heatColor": [1.0, 0.5, 0.1],
  "burnColor": [1.0, 0.8, 0.3],
  "coreColor": [0.8, 0.6, 0.4],
  "glowColor": [1.0, 0.4, 0.0],
  "dustColor": [0.5, 0.5, 0.5, 0.6],
  "sparkColor": [1.0, 0.4, 0.1, 1.0],
  
  "glowIntensity": 2.0,
  "emissivePower": 1.5,
  "coreOpacity": 1.0,
  "trailOpacity": 0.8,
  "enableCoreGlow": true,
  "enableTrailGlow": true,
  
  "trailLength": 2.0,
  "trailWidth": 0.15,
  "trailNoiseScale": 1.5,
  "trailNoiseSpeed": 3.0,
  "trailFadeSpeed": 1.2,
  "enableTrailFade": true,
  "enableTrailDistortion": true,
  "trailDistortionStrength": 0.2,
  
  "dustParticleCount": 100,
  "dustLifetime": 1.5,
  "dustSize": 0.05,
  "dustSpeed": 1.0,
  "enableDustFade": true,
  "dustFadeSpeed": 1.5,
  
  "sparkParticleCount": 30,
  "sparkLifetime": 0.6,
  "sparkSize": 0.03,
  "sparkSpeed": 1.5,
  "enableSparkFade": true,
  "sparkFadeSpeed": 1.0,
  
  "fragmentationCount": 8,
  "fragmentSizeFactor": 0.3,
  "fragmentSpread": 1.5,
  "fragmentVelocity": 2.5,
  "enableFragmentPhysics": true,
  "fragmentLifetime": 2.0,
  
  "shaderType": "meteor",
  "shaderIntensity": 1.2,
  "enableDistortion": true,
  "distortionStrength": 0.15,
  "enableBlur": false,
  "blurStrength": 0.1,
  "enableHeatDistortion": true,
  "heatDistortionStrength": 0.1,
  
  "enablePhysics": true,
  "enableCollision": true,
  "collisionRadius": 0.5,
  "enableGravity": true,
  "enableAirResistance": true,
  "airResistanceFactor": 0.1,
  
  "enableCaching": true,
  "enableHotReload": true,
  "enableParallelProcessing": true,
  "lodLevel": 0,
  
  "description": "A powerful skyfall meteor with explosive fragmentation",
  "tags": ["meteor", "skyfall", "projectile", "high_damage", "explosive"],
  "metadata": {
    "author": "Magi-Tech Comet Projectile System",
    "version": "1.0.0",
    "damage": "very_high",
    "range": "long",
    "difficulty": "expert"
  }
}
```

## Factory API

### Synchronous Generation

```cpp
CometProjectileFactory factory;
factory.initialize(1000, 4); // 1000 cache entries, 4 threads

CometProjectileParams params;
// ... set parameters ...

CometAssetBundle bundle = factory.generateSync(params);
```

### Asynchronous Generation

```cpp
auto future = factory.generateAsync(params);
// ... do other work ...
CometAssetBundle bundle = future.get();
```

### Batch Generation

```cpp
std::vector<CometProjectileParams> paramsList;
// ... populate parameters ...

auto futures = factory.generateBatchAsync(paramsList);
for (auto& future : futures) {
    CometAssetBundle bundle = future.get();
    // Process bundle
}
```

### JSON Loading

```cpp
auto future = factory.generateFromJson("meteor_config.json");
CometAssetBundle bundle = future.get();
```

## Validation

### Parameter Validation

```cpp
if (!factory.validateParams(params)) {
    auto errors = factory.getValidationErrors(params);
    for (const auto& error : errors) {
        std::cout << "Validation error: " << error << std::endl;
    }
}
```

### Common Validation Rules

- `id` cannot be empty
- `coreRadius` must be greater than 0
- `irregularity` must be between 0 and 1
- `speed` must be greater than 0
- `mass` must be greater than 0
- All particle counts must be non-negative
- All lifetimes must be greater than 0
- All opacity values must be between 0 and 1

## Performance Features

### Caching

The factory uses an LRU cache to avoid regenerating identical assets:

```cpp
// Cache management
factory.clearCache();
size_t cacheSize = factory.getCacheSize();
double hitRate = factory.getCacheHitRate();
factory.setCacheCapacity(2000);
```

### Performance Metrics

```cpp
auto metrics = factory.getPerformanceMetrics();
std::cout << "Total generations: " << metrics.totalGenerations << std::endl;
std::cout << "Cache hit rate: " << metrics.getHitRate() << std::endl;
std::cout << "Average generation time: " << metrics.averageGenerationTime << "ms" << std::endl;
```

### Multi-threading

The factory supports parallel processing:

```cpp
factory.initialize(1000, 8); // 8 worker threads
```

## Asset Types

### Mesh Assets

- **Core Mesh**: Irregular spherical geometry with noise-based vertex displacement
- **Trail Mesh**: Ribbon geometry that follows the projectile path
- **Fragment Meshes**: Multiple smaller meshes for fragmentation effects

### Shader Assets

- **Core Shader**: Emissive materials with heat distortion
- **Trail Shader**: Additive blending with fade effects
- **Heat Distortion Shader**: Post-process distortion for fast projectiles

### Texture Assets

- **Rock Texture**: 3D noise-based rock surface
- **Color Map**: Radial gradient from heat to burn colors
- **Effect Textures**: Procedural effects based on comet type

### Particle Assets

- **Dust Trail**: Billboard particles with fade effects
- **Sparks**: Point particles with velocity variation
- **Fragments**: Mesh particles with physics simulation

## Integration with OpenStarbound

### Lua Bindings

The system provides comprehensive Lua bindings for easy integration:

```lua
-- Initialize the factory
CometFactory.initialize(1000, 4)

-- Generate a comet
local comet = spawn_comet_projectile(params)

-- Access generated assets
local meshHandle = comet.mesh
local shaderHandle = comet.shader
local textureHandle = comet.texture
local dustTrailHandle = comet.dustTrail
local sparksHandle = comet.sparks
local fragmentsHandle = comet.fragments
local heatDistortionHandle = comet.heatDistortion
```

### Asset Handles

All generated assets return OpenStarbound-compatible handles:

- `MeshHandle`: Compatible with OpenStarbound mesh system
- `ShaderHandle`: Compatible with OpenStarbound shader system
- `TextureHandle`: Compatible with OpenStarbound texture system
- `ParticleHandle`: Compatible with OpenStarbound particle system

## Extensions and Customization

### Custom Comet Types

Add new comet types by extending the `CometType` enum and implementing type-specific generation logic.

### Custom Shaders

Implement custom shader variants by extending the `ShaderGen` namespace and adding new shader compilation paths.

### Custom Particle Effects

Add new particle effects by extending the `ParticleGen` namespace and implementing new particle emitter types.

### Custom Noise Functions

Extend the noise system by implementing new noise functions in the `NoiseGenerator` utility.

## Performance Considerations

### Memory Usage

- Large particle counts can consume significant memory
- High-detail meshes increase vertex count
- Texture resolution affects memory usage

### GPU Performance

- Complex shaders may impact rendering performance
- Particle counts affect GPU fill rate
- Heat distortion effects require additional render passes

### CPU Performance

- Mesh generation is CPU-intensive
- Noise calculations can be expensive
- Parameter validation adds overhead

## Best Practices

### Parameter Tuning

1. Start with conservative particle counts
2. Use appropriate detail levels for target hardware
3. Balance visual quality with performance
4. Test on target hardware configurations

### Caching Strategy

1. Cache frequently used parameter combinations
2. Monitor cache hit rates
3. Adjust cache size based on memory constraints
4. Clear cache periodically to prevent memory leaks

### Error Handling

1. Always validate parameters before generation
2. Handle generation failures gracefully
3. Provide meaningful error messages
4. Implement fallback configurations

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Reduce particle counts or mesh detail
2. **Poor Performance**: Enable caching and parallel processing
3. **Visual Artifacts**: Adjust noise parameters and shader settings
4. **Generation Failures**: Check parameter validation errors

### Debug Features

- Enable detailed logging for generation steps
- Monitor performance metrics
- Validate all parameters before generation
- Test with minimal configurations first

## Future Enhancements

### Planned Features

1. **GPU-Accelerated Generation**: Move mesh/texture generation to GPU
2. **Real-time Fracturing**: Dynamic mesh fracturing on impact
3. **Style Transfer**: AI-powered texture generation
4. **Network Replication**: Efficient parameter synchronization
5. **Advanced Physics**: More sophisticated physics simulation

### Extension Points

1. **Custom Noise Functions**: Plugin system for custom noise
2. **Shader Variants**: Dynamic shader compilation
3. **Particle Systems**: Extensible particle effect framework
4. **Asset Formats**: Support for additional asset formats

This comprehensive pipeline provides a complete solution for generating dynamic, high-performance comet and meteor projectiles in OpenStarbound, with full integration into the existing asset system and extensive customization options. 