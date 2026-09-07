# Lightning-Like Projectile Asset Generation Pipeline

A complete C++ pipeline for generating crackling, branching lightning bolts with pulsing glow, jittery arcs, spark particles, and optional discharge trails—all from pure data into mesh, shader, texture, particle, and audio generators.

## Overview

This system provides a comprehensive asset generation pipeline for creating dynamic lightning and electric projectile effects in OpenStarbound. The pipeline generates:

- **Mesh Assets**: Procedural lightning arcs with noise-based vertex displacement and branching
- **Shader Assets**: Emissive materials with flicker effects, pulse animations, and distortion
- **Texture Assets**: Procedural lightning gradients with noise patterns and glow effects
- **Particle Assets**: Spark emitters with physics simulation and trail effects
- **Audio Assets**: Procedural crackle and electric sound effects

## Core Architecture

### 1. Parameter System

The system uses a comprehensive parameter schema with 50+ configurable properties:

```cpp
struct LightningProjectileParams {
    // Basic properties
    std::string id;
    LightningType lightningType;
    TrailType trailType;
    NoiseType noiseType;
    BlendMode blendMode;
    AudioType audioType;
    
    // Physical properties
    float length;
    float thickness;
    float speed;
    float mass;
    float charge;
    float conductivity;
    
    // Color properties
    glm::vec3 mainColor;
    glm::vec3 glowColor;
    glm::vec3 coreColor;
    glm::vec3 sparkColor;
    glm::vec4 trailColor;
    
    // Visual properties
    float noiseIntensity;
    float noiseScale;
    float flickerSpeed;
    float pulseFrequency;
    float glowIntensity;
    float emissivePower;
    float coreOpacity;
    float trailOpacity;
    bool enableCoreGlow;
    bool enableTrailGlow;
    
    // Branch properties
    int branchCount;
    float branchLengthFactor;
    float branchSpread;
    float branchAngle;
    bool enableBranching;
    bool enableBranchPhysics;
    
    // Jitter properties
    float jitterAmplitude;
    float jitterFrequency;
    float jitterPhase;
    bool enableJitter;
    bool enableRandomJitter;
    
    // Arc properties
    float arcWidthVariation;
    float arcSegments;
    float arcSmoothness;
    bool enableArcPhysics;
    float arcStiffness;
    
    // Trail properties
    float trailLength;
    float trailWidth;
    float trailFadeSpeed;
    bool enableTrailFade;
    bool enableTrailDistortion;
    float trailDistortionStrength;
    
    // Particle properties
    int sparkCount;
    float sparkLifetime;
    float sparkSize;
    float sparkSpeed;
    bool enableSparkFade;
    float sparkFadeSpeed;
    bool enableSparkPhysics;
    float sparkGravity;
    
    // Audio properties
    float soundPitch;
    float soundVolume;
    float soundDuration;
    bool enableAudio;
    bool enableSpatialAudio;
    float audioDistance;
    
    // Shader properties
    std::string shaderType;
    float shaderIntensity;
    bool enableDistortion;
    float distortionStrength;
    bool enableBlur;
    float blurStrength;
    bool enableHeatDistortion;
    float heatDistortionStrength;
    
    // Physics properties
    bool enablePhysics;
    bool enableCollision;
    float collisionRadius;
    bool enableGravity;
    bool enableAirResistance;
    float airResistanceFactor;
    
    // Performance properties
    bool enableCaching;
    bool enableHotReload;
    bool enableParallelProcessing;
    int lodLevel;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;
};
```

### 2. Enum Types

The system supports various lightning types and effects:

```cpp
enum class LightningType {
    BOLT,      // Standard lightning bolt
    ARC,       // Electric arc
    CHAIN,     // Chain lightning
    FORK,      // Forked lightning
    STORM,     // Storm lightning
    PLASMA,    // Plasma bolt
    MAGIC,     // Magical lightning
    CUSTOM     // Custom lightning
};

enum class TrailType {
    NONE,           // No trail
    ELECTRIC_TAIL,  // Electric trail
    PLASMA_STREAK,  // Plasma streak
    MAGIC_TRAIL,    // Magic trail
    CUSTOM          // Custom trail
};

enum class NoiseType {
    PERLIN,     // Perlin noise
    SIMPLEX,    // Simplex noise
    CURL,       // Curl noise
    FRACTAL,    // Fractal noise
    CUSTOM      // Custom noise
};

enum class BlendMode {
    ADDITIVE,   // Additive blending
    MULTIPLY,   // Multiply blending
    SCREEN,     // Screen blending
    OVERLAY,    // Overlay blending
    NORMAL      // Normal blending
};

enum class AudioType {
    CRACKLE,    // Electric crackle
    ZAP,        // Electric zap
    THUNDER,    // Thunder sound
    ELECTRIC,   // Electric sound
    CUSTOM      // Custom audio
};
```

## 3. Factory System

The `LightningProjectileFactory` provides comprehensive generation capabilities:

```cpp
class LightningProjectileFactory {
public:
    // Asynchronous generation
    std::future<LightningBundle> generateAsync(const LightningProjectileParams& p);
    
    // Synchronous generation
    LightningBundle generateSync(const LightningProjectileParams& p);
    
    // JSON-based generation
    std::future<LightningBundle> generateFromJson(const std::string& jsonPath);
    
    // Batch generation
    std::vector<std::future<LightningBundle>> generateBatchAsync(
        const std::vector<LightningProjectileParams>& params);
    
    // Parameter validation
    bool validateParams(const LightningProjectileParams& params);
    std::vector<std::string> getValidationErrors(const LightningProjectileParams& params);
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    size_t getCacheCapacity() const;
    double getCacheHitRate() const;
    void setCacheCapacity(size_t capacity);
    
    // Performance monitoring
    struct PerformanceMetrics {
        size_t totalGenerations = 0;
        size_t cacheHits = 0;
        size_t cacheMisses = 0;
        double totalGenerationTime = 0.0;
        double averageGenerationTime = 0.0;
        double getHitRate() const;
        void reset();
    };
    
    PerformanceMetrics getPerformanceMetrics() const;
    void resetPerformanceMetrics();
};
```

## 4. Generation Components

### Mesh Generation

The mesh generation system creates procedural lightning arcs with branching and trails:

```cpp
namespace MeshGen {
    // Main lightning mesh generation
    MeshHandle buildLightning(const LightningProjectileParams& p);
    
    // Component mesh generation
    MeshHandle buildLightningArc(const LightningProjectileParams& p);
    MeshHandle buildLightningBranches(const LightningProjectileParams& p);
    MeshHandle buildLightningTrail(const LightningProjectileParams& p);
    
    // Utility functions
    std::vector<glm::vec3> generateArcPoints(float length, int segments, 
                                            float noiseScale, float noiseIntensity);
    void applyJitter(std::vector<glm::vec3>& points, float amplitude, float frequency);
    MeshHandle buildPolylineRibbon(const std::vector<glm::vec3>& points, 
                                  float thickness, float widthVariation);
    MeshHandle buildTrailRibbon(const std::vector<glm::vec3>& points, 
                               float trailLength, float thickness);
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes);
}
```

**Mesh Generation Features:**
- **Procedural Arc Generation**: Creates lightning arcs using noise-based vertex displacement
- **Branching System**: Generates multiple branch arcs from main lightning
- **Jitter Effects**: Applies temporal jitter for dynamic movement
- **Trail Generation**: Creates fading trail meshes behind lightning
- **Ribbon Construction**: Builds polyline ribbons with variable thickness
- **Mesh Merging**: Combines multiple mesh components into final lightning

### Shader Generation

The shader generation system creates emissive materials with advanced effects:

```cpp
namespace ShaderGen {
    // Main shader generation
    ShaderHandle buildLightning(const LightningProjectileParams& p);
    
    // Component shader generation
    ShaderHandle buildLightningVertexShader(const LightningProjectileParams& p);
    ShaderHandle buildLightningFragmentShader(const LightningProjectileParams& p);
    
    // Utility functions
    std::string generateLightningShaderCode(const LightningProjectileParams& p);
}
```

**Shader Generation Features:**
- **Emissive Materials**: Creates glowing lightning effects
- **Flicker Effects**: Implements temporal flicker animations
- **Pulse Animations**: Adds brightness pulse effects
- **Distortion Effects**: Applies noise-based distortion
- **Blend Modes**: Supports additive, multiply, screen, overlay blending
- **Core/Trail Glow**: Separate glow effects for core and trail
- **Heat Distortion**: Optional heat distortion effects

### Texture Generation

The texture generation system creates procedural lightning textures:

```cpp
namespace TextureGen {
    // Main texture generation
    TextureHandle buildLightning(const LightningProjectileParams& p);
    
    // Component texture generation
    TextureHandle buildLightningGradient(const glm::vec3& mainColor, const glm::vec3& glowColor);
    TextureHandle buildLightningNoise(float noiseScale, float flickerSpeed);
    
    // Utility functions
    TextureHandle mergeLightningTextures(const TextureHandle& gradient, const TextureHandle& noise);
}
```

**Texture Generation Features:**
- **Gradient Generation**: Creates radial gradients from main to glow color
- **Noise Patterns**: Generates procedural noise for lightning texture
- **Texture Merging**: Combines gradient and noise textures
- **Dynamic Textures**: Supports temporal texture animation
- **High Resolution**: Generates 256x256 textures with 4-channel RGBA

### Particle Generation

The particle generation system creates spark and trail effects:

```cpp
namespace ParticleGen {
    // Main particle generation
    ParticleHandle buildSparks(const LightningProjectileParams& p);
    
    // Component particle generation
    ParticleHandle buildLightningParticles(const LightningProjectileParams& p);
    ParticleHandle buildElectricTrail(const LightningProjectileParams& p);
}
```

**Particle Generation Features:**
- **Spark Emitters**: Creates electric spark particles
- **Trail Effects**: Generates electric trail particles
- **Physics Simulation**: Supports gravity and air resistance
- **Fade Effects**: Implements particle fade-out
- **Size Variation**: Dynamic particle sizing
- **Color Gradients**: Particle color transitions
- **Spatial Audio**: Position-based audio effects

### Audio Generation

The audio generation system creates procedural electric sounds:

```cpp
namespace AudioGen {
    // Main audio generation
    AudioHandle buildCrackle(const LightningProjectileParams& p);
    
    // Component audio generation
    AudioHandle buildLightningAudio(const LightningProjectileParams& p);
    AudioHandle buildElectricSound(const LightningProjectileParams& p);
}
```

**Audio Generation Features:**
- **Procedural Audio**: Generates electric crackle sounds
- **Spatial Audio**: Position-based audio effects
- **Pitch Control**: Adjustable sound pitch
- **Volume Control**: Configurable audio volume
- **Duration Control**: Variable sound duration
- **Intensity Mapping**: Maps lightning properties to audio intensity

## 5. Parameter Utilities

The system includes comprehensive parameter utilities:

```cpp
namespace ParamUtils {
    // String to enum conversions
    LightningType parseLightningType(const std::string& str);
    TrailType parseTrailType(const std::string& str);
    NoiseType parseNoiseType(const std::string& str);
    BlendMode parseBlendMode(const std::string& str);
    AudioType parseAudioType(const std::string& str);
    
    // Enum to string conversions
    std::string lightningTypeToString(LightningType type);
    std::string trailTypeToString(TrailType type);
    std::string noiseTypeToString(NoiseType type);
    std::string blendModeToString(BlendMode mode);
    std::string audioTypeToString(AudioType type);
    
    // JSON serialization/deserialization
    nlohmann::json toJson(const LightningProjectileParams& params);
    LightningProjectileParams fromJson(const nlohmann::json& json);
}
```

## 6. Usage Examples

### Basic Lightning Generation

```cpp
// Create lightning parameters
LightningProjectileParams params;
params.id = "storm_strike";
params.lightningType = LightningType::BOLT;
params.trailType = TrailType::ELECTRIC_TAIL;
params.noiseType = NoiseType::PERLIN;
params.blendMode = BlendMode::ADDITIVE;
params.audioType = AudioType::CRACKLE;

// Physical properties
params.length = 8.0f;
params.thickness = 0.05f;
params.speed = 30.0f;
params.mass = 1.0f;
params.charge = 1.0f;
params.conductivity = 1.0f;

// Color properties
params.mainColor = {0.8f, 1.0f, 1.0f};
params.glowColor = {0.2f, 0.6f, 1.0f};
params.coreColor = {1.0f, 1.0f, 1.0f};
params.sparkColor = {1.0f, 0.8f, 0.5f};
params.trailColor = {0.5f, 0.8f, 1.0f, 0.6f};

// Visual properties
params.noiseIntensity = 0.5f;
params.noiseScale = 4.0f;
params.flickerSpeed = 25.0f;
params.pulseFrequency = 2.0f;
params.glowIntensity = 1.0f;
params.emissivePower = 1.0f;
params.coreOpacity = 1.0f;
params.trailOpacity = 0.8f;
params.enableCoreGlow = true;
params.enableTrailGlow = true;

// Branch properties
params.branchCount = 3;
params.branchLengthFactor = 0.5f;
params.branchSpread = 1.0f;
params.branchAngle = 0.5f;
params.enableBranching = true;
params.enableBranchPhysics = true;

// Jitter properties
params.jitterAmplitude = 0.1f;
params.jitterFrequency = 30.0f;
params.jitterPhase = 0.0f;
params.enableJitter = true;
params.enableRandomJitter = true;

// Arc properties
params.arcWidthVariation = 0.3f;
params.arcSegments = 16.0f;
params.arcSmoothness = 0.5f;
params.enableArcPhysics = true;
params.arcStiffness = 1.0f;

// Trail properties
params.trailLength = 0.5f;
params.trailWidth = 0.1f;
params.trailFadeSpeed = 1.0f;
params.enableTrailFade = true;
params.enableTrailDistortion = true;
params.trailDistortionStrength = 0.1f;

// Particle properties
params.sparkCount = 60;
params.sparkLifetime = 0.3f;
params.sparkSize = 0.02f;
params.sparkSpeed = 1.0f;
params.enableSparkFade = true;
params.sparkFadeSpeed = 1.0f;
params.enableSparkPhysics = true;
params.sparkGravity = 0.5f;

// Audio properties
params.soundPitch = 1.0f;
params.soundVolume = 1.0f;
params.soundDuration = 1.0f;
params.enableAudio = true;
params.enableSpatialAudio = true;
params.audioDistance = 10.0f;

// Shader properties
params.shaderType = "lightning";
params.shaderIntensity = 1.0f;
params.enableDistortion = true;
params.distortionStrength = 0.1f;
params.enableBlur = false;
params.blurStrength = 0.1f;
params.enableHeatDistortion = false;
params.heatDistortionStrength = 0.1f;

// Physics properties
params.enablePhysics = true;
params.enableCollision = true;
params.collisionRadius = 0.1f;
params.enableGravity = false;
params.enableAirResistance = true;
params.airResistanceFactor = 0.1f;

// Performance properties
params.enableCaching = true;
params.enableHotReload = true;
params.enableParallelProcessing = true;
params.lodLevel = 0;

// Metadata
params.description = "Generated lightning projectile";
params.tags = {"lightning", "projectile"};
params.metadata = {{"source", "cpp"}};

// Generate lightning bundle
auto future = g_lightningFactory.generateAsync(params);
LightningBundle bundle = future.get();

// Use the generated assets
MeshHandle mesh = bundle.mesh;
ShaderHandle shader = bundle.shader;
TextureHandle texture = bundle.texture;
ParticleHandle sparks = bundle.sparks;
AudioHandle sfx = bundle.sfx;
```

### JSON-Based Generation

```cpp
// Load parameters from JSON file
auto future = g_lightningFactory.generateFromJson("lightning_config.json");
LightningBundle bundle = future.get();
```

### Batch Generation

```cpp
// Create multiple lightning configurations
std::vector<LightningProjectileParams> paramsList;
// ... populate paramsList ...

// Generate all lightning bundles asynchronously
auto futures = g_lightningFactory.generateBatchAsync(paramsList);

// Wait for all generations to complete
std::vector<LightningBundle> bundles;
for (auto& future : futures) {
    bundles.push_back(future.get());
}
```

### Parameter Validation

```cpp
// Validate parameters before generation
if (!g_lightningFactory.validateParams(params)) {
    auto errors = g_lightningFactory.getValidationErrors(params);
    for (const auto& error : errors) {
        Log::error("Parameter validation error: {}", error);
    }
    return;
}

// Generate lightning with validated parameters
auto bundle = g_lightningFactory.generateSync(params);
```

## 7. Performance Features

### Caching System

The factory includes a comprehensive LRU cache for generated assets:

```cpp
// Cache management
g_lightningFactory.clearCache();
size_t cacheSize = g_lightningFactory.getCacheSize();
size_t cacheCapacity = g_lightningFactory.getCacheCapacity();
double hitRate = g_lightningFactory.getCacheHitRate();
g_lightningFactory.setCacheCapacity(1000);
```

### Performance Monitoring

```cpp
// Get performance metrics
auto metrics = g_lightningFactory.getPerformanceMetrics();
Log::info("Total generations: {}", metrics.totalGenerations);
Log::info("Cache hit rate: {:.2f}%", metrics.getHitRate() * 100.0);
Log::info("Average generation time: {:.3f}ms", metrics.averageGenerationTime);

// Reset metrics
g_lightningFactory.resetPerformanceMetrics();
```

### Parallel Processing

The system supports parallel generation for improved performance:

```cpp
// Enable parallel processing
params.enableParallelProcessing = true;

// Generate multiple lightning bolts in parallel
std::vector<std::future<LightningBundle>> futures;
for (int i = 0; i < 10; ++i) {
    params.id = "lightning_" + std::to_string(i);
    futures.push_back(g_lightningFactory.generateAsync(params));
}

// Wait for all generations
for (auto& future : futures) {
    LightningBundle bundle = future.get();
    // Process bundle...
}
```

## 8. Integration with OpenStarbound

### Asset Bundle Structure

```cpp
struct LightningBundle {
    MeshHandle mesh;           // OpenStarbound mesh handle
    ShaderHandle shader;       // OpenStarbound shader handle
    TextureHandle texture;     // OpenStarbound texture handle
    ParticleHandle sparks;     // OpenStarbound particle handle
    AudioHandle sfx;           // OpenStarbound audio handle
    
    // Performance metrics
    float generationTime;
    size_t vertexCount;
    size_t triangleCount;
    size_t particleCount;
    bool gpuAccelerated;
};
```

### GPU Acceleration

The system supports GPU acceleration for improved performance:

```cpp
// Enable GPU acceleration
params.enableParallelProcessing = true;

// Check if GPU acceleration is available
if (bundle.gpuAccelerated) {
    Log::info("Lightning generated with GPU acceleration");
}
```

### LOD Support

The system includes Level-of-Detail support:

```cpp
// Set LOD level (0 = high, 1 = medium, 2 = low)
params.lodLevel = 0;

// Generate lightning with appropriate LOD
auto bundle = g_lightningFactory.generateSync(params);
```

## 9. Error Handling

### Parameter Validation

The system includes comprehensive parameter validation:

```cpp
// Validate parameters
if (!g_lightningFactory.validateParams(params)) {
    auto errors = g_lightningFactory.getValidationErrors(params);
    for (const auto& error : errors) {
        Log::error("Validation error: {}", error);
    }
    return;
}
```

### JSON Parsing

Robust JSON parsing with error recovery:

```cpp
try {
    auto params = ParamUtils::fromJson(json);
    auto bundle = g_lightningFactory.generateSync(params);
} catch (const std::exception& e) {
    Log::error("JSON parsing error: {}", e.what());
    // Use default parameters
    LightningProjectileParams defaultParams;
    auto bundle = g_lightningFactory.generateSync(defaultParams);
}
```

### Generation Error Handling

```cpp
try {
    auto bundle = g_lightningFactory.generateSync(params);
    // Use bundle...
} catch (const std::exception& e) {
    Log::error("Lightning generation error: {}", e.what());
    // Handle error...
}
```

## 10. Testing and Debugging

### Logging

The system provides comprehensive logging:

```cpp
// Enable detailed logging
Log::setLevel(LogLevel::DEBUG);

// Generate lightning with logging
auto bundle = g_lightningFactory.generateSync(params);
```

### Performance Profiling

```cpp
// Profile generation performance
auto start = std::chrono::high_resolution_clock::now();
auto bundle = g_lightningFactory.generateSync(params);
auto end = std::chrono::high_resolution_clock::now();

auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
Log::info("Lightning generation took {}ms", duration.count());
```

### Asset Inspection

```cpp
// Inspect generated assets
Log::info("Generated lightning bundle:");
Log::info("  - Mesh handle: {}", bundle.mesh);
Log::info("  - Shader handle: {}", bundle.shader);
Log::info("  - Texture handle: {}", bundle.texture);
Log::info("  - Particle handle: {}", bundle.sparks);
Log::info("  - Audio handle: {}", bundle.sfx);
Log::info("  - Generation time: {:.3f}ms", bundle.generationTime);
Log::info("  - Vertex count: {}", bundle.vertexCount);
Log::info("  - Triangle count: {}", bundle.triangleCount);
Log::info("  - Particle count: {}", bundle.particleCount);
Log::info("  - GPU accelerated: {}", bundle.gpuAccelerated);
```

## 11. Future Extensions

### Planned Features

1. **GPU Compute Shaders**: Direct GPU computation for lightning generation
2. **Volumetric Effects**: 3D volumetric lightning with light shafts
3. **Network Replication**: Real-time network synchronization of lightning states
4. **Style Transfer**: AI-powered lightning style transfer
5. **Hybrid Weapons**: Lightning-weapon combinations with transition effects

### Custom Extensions

The system is designed for easy extension:

```cpp
// Custom lightning type
enum class CustomLightningType {
    PLASMA_BOLT,
    MAGIC_CHAIN,
    QUANTUM_ARC
};

// Custom generator
namespace CustomGen {
    MeshHandle buildCustomLightning(const LightningProjectileParams& p) {
        // Custom implementation
        return MeshGen::buildLightning(p);
    }
}
```

## 12. Conclusion

The Lightning Projectile Asset Generation Pipeline provides a complete solution for creating dynamic, procedurally generated lightning effects in OpenStarbound. With comprehensive parameter control, GPU acceleration, caching, and performance monitoring, the system enables the creation of complex lightning effects with minimal performance impact.

The modular design allows for easy extension and customization, while the robust error handling and validation ensure reliable operation in production environments. The system's integration with OpenStarbound's asset management provides seamless deployment of generated lightning effects.

---

**Generated by Magi-Tech Lightning Projectile System v1.0** 