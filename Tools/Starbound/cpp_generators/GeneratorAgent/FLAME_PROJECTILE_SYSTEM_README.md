# 🔥 Flame-Like Projectile Asset Generation Pipeline

## 🎯 **Overview**

The Flame-Like Projectile Asset Generation Pipeline provides a comprehensive C++23-based system for generating vivid, procedural flame projectiles with volumetric flicker, ember particles, and dynamic trails. The system creates complete flame projectiles from Lua/JSON data into C++ asset generators, producing meshes, shaders, textures, and particle systems.

## 🏗️ **Architecture**

### **✅ Core Components**

```
┌─────────────────────────────────────────────────────────────────┐
│                FLAME PROJECTILE SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│  🎨 MeshGen  │  ✨ ShaderGen  │  🎨 TextureGen  │  🔥 ParticleGen │
│  ┌─────────┐ │  ┌───────────┐ │  ┌────────────┐ │  ┌────────────┐ │
│  │ Cone    │ │  │ Flame     │ │  │ Noise      │ │  │ Embers     │ │
│  │ Ribbon  │ │  │ Heat      │ │  │ Gradient   │ │  │ Trail      │ │
│  │ Sphere  │ │  │ Distortion│ │  │ Merge      │ │  │ Smoke      │ │
│  │ Custom  │ │  │ Blur      │ │  │ Atlas      │ │  │ Particles  │ │
│  └─────────┘ │  └───────────┘ │  └────────────┘ │  └────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 **Parameter Schema**

### **🎨 Basic Properties**

```lua
FlameProjectileParams{
    id = "inferno_bolt",           -- Unique identifier
    flameType = FlameType.INFERNO_BOLT,  -- Type of flame
    flameShape = FlameShape.CONE,  -- Geometric shape
    blendMode = BlendMode.ADDITIVE, -- Rendering blend mode
    noiseType = NoiseType.CURL,    -- Noise algorithm
    trailType = TrailType.RIBBON   -- Trail effect type
}
```

### **⚡ Physical Properties**

```lua
FlameProjectileParams{
    speed = 30.0,                  -- Units per second
    length = 1.5,                  -- Mesh length in world units
    width = 0.3,                   -- Base flame radius
    flameHeight = 1.2,             -- Per-segment height factor
    flameWidthVariation = 0.6      -- Amplitude of width oscillation
}
```

### **🎨 Color Properties**

```lua
FlameProjectileParams{
    coreColor = {1.0, 0.5, 0.2},      -- Inner flame tint (RGB)
    outerColor = {1.0, 0.1, 0.0},     -- Outer flame tint (RGB)
    glowColor = {1.0, 0.4, 0.0},      -- Glow effect color (RGB)
    emberColor = {1.0, 0.4, 0.1, 0.8} -- Ember particle color (RGBA)
}
```

### **✨ Animation Properties**

```lua
FlameProjectileParams{
    flickerIntensity = 0.8,        -- Strength of UV noise distortion (0-1)
    flickerSpeed = 4.0,            -- Animation speed of distortion
    turbulenceStrength = 1.5,      -- Curl-noise displacement strength
    turbulenceScale = 3.0,         -- Frequency of noise
    oscillationFreq = 1.2,         -- Oscillation frequency
    oscillationAmplitude = 0.15    -- Oscillation amplitude
}
```

### **🔥 Trail Properties**

```lua
FlameProjectileParams{
    trailLength = 1.0,             -- Seconds of trailing mesh
    trailWidth = 0.15,             -- Width of trail
    trailOpacity = 0.9,            -- Opacity of trail (0-1)
    enableTrailFade = true,        -- Enable trail fade effect
    trailFadeSpeed = 1.2           -- Speed of trail fade
}
```

### **✨ Particle Properties**

```lua
FlameProjectileParams{
    emberCount = 80,               -- Particles spawned per second
    emberLifetime = 0.4,           -- Seconds
    emberSize = 0.06,              -- Size of ember particles
    emberSpeed = 1.2,              -- Speed of ember particles
    enableEmberFade = true,        -- Enable ember fade effect
    emberFadeSpeed = 1.5           -- Speed of ember fade
}
```

### **🎨 Shader Properties**

```lua
FlameProjectileParams{
    shaderType = "inferno",        -- Shader type identifier
    shaderIntensity = 1.2,         -- Overall shader intensity
    enableDistortion = true,       -- Enable distortion effects
    distortionStrength = 0.2,      -- Strength of distortion
    enableBlur = false,            -- Enable blur effects
    blurStrength = 0.1,            -- Strength of blur
    enableHeatDistortion = true,   -- Enable heat distortion
    heatDistortionStrength = 0.15  -- Strength of heat distortion
}
```

### **⚙️ Physics Properties**

```lua
FlameProjectileParams{
    enablePhysics = true,          -- Enable physics simulation
    physicsMass = 0.15,            -- Mass of projectile
    physicsDrag = 0.1,             -- Air resistance
    physicsLift = 0.05,            -- Lift force
    enableCollision = true,        -- Enable collision detection
    collisionRadius = 0.15         -- Collision radius
}
```

### **🚀 Performance Properties**

```lua
FlameProjectileParams{
    enableCaching = true,          -- Enable asset caching
    enableHotReload = true,        -- Enable hot reloading
    enableParallelProcessing = true, -- Enable parallel processing
    lodLevel = 0                   -- Level of detail (0-3)
}
```

## 🎮 **Enum Types**

### **🔥 FlameType**
- `FIREBALL` - Standard fireball projectile
- `INFERNO_BOLT` - High-intensity inferno bolt
- `HELLFIRE` - Hellfire projectile with dark effects
- `PLASMA_FLAME` - Plasma-based flame
- `MAGIC_FIRE` - Magical fire with special effects
- `CUSTOM` - Custom flame type

### **🎨 FlameShape**
- `CONE` - Cone-shaped flame
- `RIBBON` - Ribbon-like flame
- `SPHERE` - Spherical flame
- `CYLINDER` - Cylindrical flame
- `CUSTOM_SHAPE` - Custom geometric shape

### **✨ BlendMode**
- `ADDITIVE` - Additive blending for bright effects
- `MULTIPLY` - Multiply blending for dark effects
- `SCREEN` - Screen blending for light effects
- `OVERLAY` - Overlay blending for contrast
- `NORMAL` - Normal alpha blending

### **🎨 NoiseType**
- `PERLIN` - Perlin noise for organic effects
- `SIMPLEX` - Simplex noise for smooth effects
- `CURL` - Curl noise for fluid-like effects
- `FRACTAL` - Fractal noise for complex patterns
- `CUSTOM` - Custom noise algorithm

### **🔥 TrailType**
- `NONE` - No trail effect
- `RIBBON` - Ribbon trail
- `PARTICLES` - Particle trail
- `SMOKE` - Smoke trail
- `HEAT_DISTORTION` - Heat distortion trail
- `CUSTOM` - Custom trail effect

## 🚀 **Usage Examples**

### **Lua Usage**

```lua
-- Create a basic fireball
local fireball = FlameProjectileParams{
    id = "basic_fireball",
    flameType = FlameType.FIREBALL,
    flameShape = FlameShape.CONE,
    blendMode = BlendMode.ADDITIVE,
    noiseType = NoiseType.CURL,
    trailType = TrailType.RIBBON,
    
    speed = 25.0,
    length = 1.2,
    width = 0.2,
    flameHeight = 1.0,
    flameWidthVariation = 0.5,
    
    coreColor = {1.0, 0.6, 0.1},
    outerColor = {0.8, 0.1, 0.0},
    glowColor = {1.0, 0.4, 0.0},
    emberColor = {1.0, 0.4, 0.1, 0.8},
    
    flickerIntensity = 0.7,
    flickerSpeed = 3.0,
    turbulenceStrength = 1.0,
    turbulenceScale = 2.5,
    oscillationFreq = 1.0,
    oscillationAmplitude = 0.1,
    
    trailLength = 0.8,
    trailWidth = 0.1,
    trailOpacity = 0.8,
    enableTrailFade = true,
    trailFadeSpeed = 1.0,
    
    emberCount = 60,
    emberLifetime = 0.5,
    emberSize = 0.05,
    emberSpeed = 1.0,
    enableEmberFade = true,
    emberFadeSpeed = 1.0,
    
    shaderType = "flame",
    shaderIntensity = 1.0,
    enableDistortion = true,
    distortionStrength = 0.1,
    enableBlur = false,
    blurStrength = 0.1,
    enableHeatDistortion = false,
    heatDistortionStrength = 0.1,
    
    enablePhysics = true,
    physicsMass = 0.1,
    physicsDrag = 0.1,
    physicsLift = 0.0,
    enableCollision = true,
    collisionRadius = 0.1,
    
    enableCaching = true,
    enableHotReload = true,
    enableParallelProcessing = true,
    lodLevel = 0,
    
    description = "A basic fireball projectile",
    tags = {"fireball", "basic", "projectile"},
    metadata = {
        damage = "medium",
        range = "medium",
        difficulty = "beginner"
    }
}

-- Generate the fireball synchronously
local bundle = spawn_flame_projectile(fireball)
print("Fireball generated! Mesh ID:", bundle.mesh)
print("Shader ID:", bundle.shader)
print("Texture ID:", bundle.texture)
print("Embers ID:", bundle.embers)

-- Generate asynchronously
local future = spawn_flame_projectile_async(fireball)
-- ... later ...
local bundle = future.get()
```

### **JSON Usage**

```json
{
  "id": "inferno_bolt",
  "flameType": "inferno_bolt",
  "flameShape": "cone",
  "blendMode": "additive",
  "noiseType": "curl",
  "trailType": "ribbon",
  
  "speed": 30.0,
  "length": 1.5,
  "width": 0.3,
  "flameHeight": 1.2,
  "flameWidthVariation": 0.6,
  
  "coreColor": [1.0, 0.5, 0.2],
  "outerColor": [1.0, 0.1, 0.0],
  "glowColor": [1.0, 0.4, 0.0],
  "emberColor": [1.0, 0.4, 0.1, 0.8],
  
  "flickerIntensity": 0.8,
  "flickerSpeed": 4.0,
  "turbulenceStrength": 1.5,
  "turbulenceScale": 3.0,
  "oscillationFreq": 1.2,
  "oscillationAmplitude": 0.15,
  
  "trailLength": 1.0,
  "trailWidth": 0.15,
  "trailOpacity": 0.9,
  "enableTrailFade": true,
  "trailFadeSpeed": 1.2,
  
  "emberCount": 80,
  "emberLifetime": 0.4,
  "emberSize": 0.06,
  "emberSpeed": 1.2,
  "enableEmberFade": true,
  "emberFadeSpeed": 1.5,
  
  "shaderType": "inferno",
  "shaderIntensity": 1.2,
  "enableDistortion": true,
  "distortionStrength": 0.2,
  "enableBlur": false,
  "blurStrength": 0.1,
  "enableHeatDistortion": true,
  "heatDistortionStrength": 0.15,
  
  "enablePhysics": true,
  "physicsMass": 0.15,
  "physicsDrag": 0.1,
  "physicsLift": 0.05,
  "enableCollision": true,
  "collisionRadius": 0.15,
  
  "enableCaching": true,
  "enableHotReload": true,
  "enableParallelProcessing": true,
  "lodLevel": 0,
  
  "description": "A powerful inferno bolt with intense visual effects",
  "tags": ["inferno", "bolt", "fire", "projectile", "high_damage"],
  "metadata": {
    "damage": "very_high",
    "range": "medium",
    "difficulty": "expert"
  }
}
```

## 🛠️ **C++ API**

### **Factory Methods**

```cpp
// Synchronous generation
FlameAssetBundle bundle = g_flameFactory.generateSync(params);

// Asynchronous generation
std::future<FlameAssetBundle> future = g_flameFactory.generateAsync(params);

// JSON-based generation
std::future<FlameAssetBundle> future = g_flameFactory.generateFromJson("projectile.json");

// Batch generation
std::vector<std::future<FlameAssetBundle>> futures = g_flameFactory.generateBatchAsync(paramsList);
```

### **Validation Methods**

```cpp
// Validate parameters
bool isValid = g_flameFactory.validateParams(params);

// Get validation errors
std::vector<std::string> errors = g_flameFactory.getValidationErrors(params);
```

### **Cache Management**

```cpp
// Clear cache
g_flameFactory.clearCache();

// Get cache statistics
size_t size = g_flameFactory.getCacheSize();
double hitRate = g_flameFactory.getCacheHitRate();

// Set cache capacity
g_flameFactory.setCacheCapacity(1000);
```

### **Performance Monitoring**

```cpp
// Get performance metrics
auto metrics = g_flameFactory.getPerformanceMetrics();
std::cout << "Total generations: " << metrics.totalGenerations << std::endl;
std::cout << "Cache hit rate: " << metrics.getHitRate() << std::endl;
std::cout << "Average generation time: " << metrics.averageGenerationTime << "s" << std::endl;

// Reset metrics
g_flameFactory.resetPerformanceMetrics();
```

## 🎨 **Generator Namespaces**

### **MeshGen**
- `buildFlame(params)` - Build complete flame mesh
- `buildCone(length, width, height)` - Build cone geometry
- `buildTrailRibbon(length, trailLength, width)` - Build trail ribbon
- `mergeMeshes(meshes)` - Merge multiple meshes

### **ShaderGen**
- `buildFlame(params)` - Build flame shader
- `buildHeatDistortion(params)` - Build heat distortion shader
- `generateFlameShaderCode(params)` - Generate shader code

### **TextureGen**
- `buildFlame(params)` - Build flame texture
- `buildNoiseTexture(scale, type)` - Build noise texture
- `buildGradientTexture(startColor, endColor)` - Build gradient texture
- `mergeTextures(noise, gradient)` - Merge textures

### **ParticleGen**
- `buildEmbers(params)` - Build ember particles
- `buildTrail(params)` - Build trail particles
- `buildSmoke(params)` - Build smoke particles

## 🔍 **Validation & Error Handling**

### **Parameter Validation**

```lua
-- Validate parameters
local isValid = validate_flame_params(params)
if not isValid then
    local errors = get_flame_validation_errors(params)
    for i, error in ipairs(errors) do
        print("Validation error:", error)
    end
end
```

### **Error Handling**

```lua
-- Wrap generation in error handling
local success, bundle = pcall(spawn_flame_projectile, params)
if success then
    print("Flame projectile generated successfully!")
    print("Mesh ID:", bundle.mesh)
    print("Shader ID:", bundle.shader)
    print("Texture ID:", bundle.texture)
    print("Embers ID:", bundle.embers)
    print("Trail ID:", bundle.trail)
    print("Smoke ID:", bundle.smoke)
    print("Heat Distortion ID:", bundle.heatDistortion)
    print("Generation time:", bundle.generationTime, "s")
    print("Vertex count:", bundle.vertexCount)
    print("Triangle count:", bundle.triangleCount)
    print("Particle count:", bundle.particleCount)
    print("GPU accelerated:", bundle.gpuAccelerated)
else
    print("Generation failed:", bundle)
end
```

## 📁 **File Operations**

### **Save/Load Parameters**

```lua
-- Save parameters to file
local success = save_flame_params_to_file(params, "my_projectile.json")
if success then
    print("Parameters saved successfully!")
else
    print("Failed to save parameters")
end

-- Load parameters from file
local loadedParams = load_flame_params_from_file("my_projectile.json")
print("Loaded projectile ID:", loadedParams.id)

-- Generate from loaded parameters
local bundle = spawn_flame_projectile(loadedParams)
```

### **JSON Serialization**

```lua
-- Convert parameters to JSON string
local jsonStr = flame_params_to_json(params)
print("JSON:", jsonStr)

-- Convert JSON string to parameters
local params = flame_params_from_json(jsonStr)
print("Loaded ID:", params.id)
```

## 🚀 **Advanced Features**

### **Batch Generation**

```lua
-- Generate multiple projectiles
local projectileBatch = {
    FlameProjectileParams{id = "fireball_1", ...},
    FlameProjectileParams{id = "fireball_2", ...},
    FlameProjectileParams{id = "fireball_3", ...}
}

local futures = generate_flame_batch(projectileBatch)
for i, future in ipairs(futures) do
    local bundle = future.get()
    print("Projectile", i, "ready!")
end
```

### **Performance Profiling**

```lua
-- Profile generation time
local startTime = os.clock()
local bundle = spawn_flame_projectile(params)
local endTime = os.clock()
print("Generation time:", endTime - startTime, "seconds")

-- Get factory performance metrics
local metrics = get_flame_performance_metrics()
print("Total generations:", metrics.totalGenerations)
print("Cache hit rate:", metrics.getHitRate() * 100, "%")
print("Average generation time:", metrics.averageGenerationTime, "s")
```

### **Cache Management**

```lua
-- Clear cache
clear_flame_cache()

-- Get cache statistics
local cacheSize = get_flame_cache_size()
local cacheCapacity = get_flame_cache_capacity()
local hitRate = get_flame_cache_hit_rate()

print("Cache size:", cacheSize, "/", cacheCapacity)
print("Cache hit rate:", hitRate * 100, "%")

-- Set cache capacity
set_flame_cache_capacity(2000)
```

## 🎯 **Key Features**

### **✅ Complete Integration**
- **Real Lua State**: Full `lua_State` integration with sol3
- **All Asset Systems**: Mesh, shader, texture, particle generation
- **Type Safety**: Proper C++ to Lua type conversion
- **Error Handling**: Comprehensive error reporting and validation

### **✅ Performance Features**
- **Async Generation**: Non-blocking asset generation with futures
- **Caching**: LRU cache for generated assets
- **Parallel Processing**: Multi-threaded generation
- **Performance Monitoring**: Real-time metrics and profiling

### **✅ Developer Experience**
- **Hot Reloading**: Runtime parameter updates
- **JSON Integration**: Load from JSON files
- **Validation**: Parameter validation with detailed error messages
- **Batch Processing**: Efficient bulk generation

### **✅ Production Ready**
- **Error Handling**: Robust error handling and recovery
- **Memory Management**: Proper cleanup and resource management
- **Thread Safety**: Safe multi-threaded operation
- **Scalability**: Handles large numbers of assets efficiently

## 🚀 **Next Steps**

### **Planned Features**
1. **GPU Acceleration**: GPU-driven flame generation
2. **Neural Networks**: AI-driven flame evolution
3. **Real-time Collaboration**: Multi-user flame editing
4. **Plugin System**: Extensible flame generation plugins
5. **Cloud Integration**: Remote flame generation and sharing

### **Advanced Features**
- **Procedural Combat Systems**: Complete flame combat ecosystems
- **Dynamic Flame Blending**: Real-time flame combination
- **Network Replication**: Efficient flame synchronization
- **Procedural Audio**: Sound effects based on flame parameters

---

**🔥 The Flame-Like Projectile Asset Generation Pipeline provides a complete, production-ready solution for generating vivid, procedural flame projectiles with volumetric flicker, ember particles, and dynamic trails, all driven by declarative Lua/JSON configuration files.** 