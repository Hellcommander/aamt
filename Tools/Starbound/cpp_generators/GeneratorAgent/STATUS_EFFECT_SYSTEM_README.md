# ✨ Status Effect Asset Generation System

## 🎯 **Overview**

The Status Effect Asset Generation System is a comprehensive C++23-based pipeline for procedurally generating visual and UI assets for buffs, debuffs, and environmental effects—from glowing auras to icy shatters. The system drives shaders, textures, meshes, particles, and icons from Lua/JSON into a unified pipeline.

## 🏗️ **Architecture**

### **✅ Core Components**

```
┌─────────────────────────────────────────────────────────────────┐
│         STATUS EFFECT GENERATION PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│  🎨 ShaderGen  │  🖼️ TextureGen  │  🦴 MeshGen    │  ✨ ParticleGen │  🎯 IconGen    │
│  ┌─────────────┐ │  ┌─────────────┐  │  ┌─────────────┐   │  ┌─────────────┐ │  ┌─────────────┐ │
│  │ EffectShader│ │  │ NoiseTexture │  │  │ RingMesh    │   │  │ Sparkle     │ │  │ IconTexture │ │
│  │ Animation   │ │  │ Gradient     │  │  │ AuraQuad    │   │  │ Smoke       │ │  │ Background  │ │
│  │ Distortion  │ │  │ Material     │  │  │ BeamMesh    │   │  │ Fire        │ │  │ Border      │ │
│  │ Blur        │ │  │ Atlas        │  │  │ SplashMesh  │   │  │ Ice         │ │  │ Glow        │ │
│  └─────────────┘ │  └─────────────┘  │  └─────────────┘   │  └─────────────┘ │  └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 **Parameter Schema**

### **StatusEffectParams**

```cpp
struct StatusEffectParams {
    std::string id;                    // Unique identifier
    EffectType effectType;             // Effect type (buff, debuff, etc.)
    ShapeType shapeType;               // Shape type (circle, square, etc.)
    ParticleType particleType;         // Particle type (sparkle, smoke, etc.)
    IconStyle iconStyle;               // Icon style (simple, detailed, etc.)
    EffectCategory category;           // Effect category (combat, magic, etc.)
    
    // Timing parameters
    float duration;                    // Effect duration in seconds
    float intensity;                   // Effect intensity (0-1)
    float fadeInTime;                  // Fade in duration
    float fadeOutTime;                 // Fade out duration
    bool isPermanent;                  // Is effect permanent
    bool canStack;                     // Can effect stack
    int maxStacks;                     // Maximum stack count
    
    // Visual parameters
    float noiseScale;                  // Noise texture scale
    float noiseSpeed;                  // Noise animation speed
    float oscillationFreq;             // Oscillation frequency
    int coverage;                      // Coverage in degrees
    int particleCount;                 // Particle count
    bool dissolve;                     // Enable dissolve effect
    float opacity;                     // Effect opacity
    float scale;                       // Effect scale
    
    // Color parameters
    glm::vec3 colorPrimary;            // Primary color
    glm::vec3 colorSecondary;          // Secondary color
    glm::vec3 iconColor;               // Icon color
    glm::vec3 glowColor;               // Glow color
    
    // Animation parameters
    bool enablePulsing;                // Enable pulsing
    float pulseSpeed;                  // Pulse speed
    float pulseIntensity;              // Pulse intensity
    bool enableRotation;               // Enable rotation
    float rotationSpeed;               // Rotation speed
    bool enableScaling;                // Enable scaling
    float scaleSpeed;                  // Scale speed
    float scaleRange;                  // Scale range
    
    // Shader parameters
    std::string shaderType;            // Shader type
    float shaderIntensity;             // Shader intensity
    bool enableDistortion;             // Enable distortion
    float distortionStrength;          // Distortion strength
    bool enableBlur;                   // Enable blur
    float blurStrength;                // Blur strength
};
```

### **UIParams**

```cpp
struct UIParams {
    int iconSize;                      // Icon size in pixels
    glm::vec4 borderColor;             // Border color (RGBA)
    std::string backgroundShape;       // Background shape
    bool flashOnApply;                 // Flash on apply
    
    // Additional UI parameters
    bool enableGlow;                   // Enable glow effect
    float glowIntensity;               // Glow intensity
    bool enablePulse;                  // Enable pulse effect
    float pulseSpeed;                  // Pulse speed
    bool enableRotation;               // Enable rotation effect
    float rotationSpeed;               // Rotation speed
    
    // Border parameters
    float borderWidth;                 // Border width
    bool enableBorderGlow;             // Enable border glow
    float borderGlowIntensity;         // Border glow intensity
    
    // Background parameters
    bool enableBackground;             // Enable background
    float backgroundOpacity;           // Background opacity
    bool enableBackgroundBlur;         // Enable background blur
    float backgroundBlurStrength;      // Background blur strength
    
    // Animation parameters
    bool enableFadeIn;                 // Enable fade in
    float fadeInDuration;              // Fade in duration
    bool enableFadeOut;                // Enable fade out
    float fadeOutDuration;             // Fade out duration
    bool enableScaleIn;                // Enable scale in
    float scaleInDuration;             // Scale in duration
    bool enableScaleOut;               // Enable scale out
    float scaleOutDuration;            // Scale out duration
    
    // Stacking parameters
    bool showStackCount;               // Show stack count
    std::string stackCountStyle;       // Stack count style
    glm::vec3 stackCountColor;         // Stack count color
    float stackCountScale;             // Stack count scale
};
```

## 🎨 **Enum Types**

### **EffectType**
- `BUFF` - Positive effect
- `DEBUFF` - Negative effect
- `DOT` - Damage over time
- `HOT` - Healing over time
- `SHIELD` - Protective effect
- `STUN` - Stun effect
- `SLOW` - Slow effect
- `HASTE` - Speed effect
- `INVISIBILITY` - Invisibility effect
- `POISON` - Poison effect
- `BURN` - Fire effect
- `FREEZE` - Ice effect
- `SHOCK` - Lightning effect
- `CURSE` - Curse effect
- `BLESSING` - Blessing effect
- `CUSTOM` - Custom effect

### **ShapeType**
- `CIRCLE` - Circular shape
- `SQUARE` - Square shape
- `HEXAGON` - Hexagonal shape
- `STAR` - Star shape
- `CROSS` - Cross shape
- `DIAMOND` - Diamond shape
- `CUSTOM_SHAPE` - Custom shape

### **ParticleType**
- `NONE` - No particles
- `SPARKLE` - Sparkle particles
- `SMOKE` - Smoke particles
- `FIRE` - Fire particles
- `ICE` - Ice particles
- `LIGHTNING` - Lightning particles
- `POISON` - Poison particles
- `HEALING` - Healing particles
- `SHIELD` - Shield particles
- `CUSTOM_PARTICLE` - Custom particles

### **IconStyle**
- `SIMPLE` - Simple icon
- `DETAILED` - Detailed icon
- `ANIMATED` - Animated icon
- `GLOWING` - Glowing icon
- `PULSING` - Pulsing icon
- `CUSTOM_ICON` - Custom icon

### **EffectCategory**
- `COMBAT` - Combat effect
- `MAGIC` - Magic effect
- `ENVIRONMENTAL` - Environmental effect
- `TEMPORARY` - Temporary effect
- `PERMANENT` - Permanent effect
- `STACKING` - Stacking effect
- `NON_STACKING` - Non-stacking effect

## 🚀 **Usage Examples**

### **Lua Usage**

```lua
-- Create a status effect
local effectParams = StatusEffectParams{
    id = "frost_nova",
    effectType = EffectType.DEBUFF,
    shapeType = ShapeType.CIRCLE,
    particleType = ParticleType.ICE,
    iconStyle = IconStyle.DETAILED,
    category = EffectCategory.COMBAT,
    
    duration = 5.0,
    intensity = 0.8,
    fadeInTime = 0.3,
    fadeOutTime = 0.5,
    isPermanent = false,
    canStack = false,
    maxStacks = 1,
    
    noiseScale = 2.0,
    noiseSpeed = 1.5,
    oscillationFreq = 0.8,
    coverage = 360,
    particleCount = 80,
    dissolve = true,
    opacity = 0.9,
    scale = 1.2,
    
    colorPrimary = {0.4, 0.8, 1.0},
    colorSecondary = {0.0, 0.2, 0.5},
    iconColor = {1.0, 1.0, 1.0},
    glowColor = {0.2, 0.4, 0.8},
    
    enablePulsing = true,
    pulseSpeed = 1.2,
    pulseIntensity = 0.3,
    enableRotation = false,
    rotationSpeed = 1.0,
    enableScaling = true,
    scaleSpeed = 0.8,
    scaleRange = 0.1,
    
    shaderType = "frost",
    shaderIntensity = 1.0,
    enableDistortion = true,
    distortionStrength = 0.15,
    enableBlur = false,
    blurStrength = 0.1
}

local uiParams = UIParams{
    iconSize = 48,
    borderColor = {0.4, 0.8, 1.0, 0.9},
    backgroundShape = "circle",
    flashOnApply = true,
    
    enableGlow = true,
    glowIntensity = 1.2,
    enablePulse = true,
    pulseSpeed = 1.5,
    enableRotation = false,
    rotationSpeed = 1.0,
    
    borderWidth = 3.0,
    enableBorderGlow = true,
    borderGlowIntensity = 1.5,
    
    enableBackground = true,
    backgroundOpacity = 0.85,
    enableBackgroundBlur = false,
    backgroundBlurStrength = 0.1,
    
    enableFadeIn = true,
    fadeInDuration = 0.4,
    enableFadeOut = true,
    fadeOutDuration = 0.6,
    enableScaleIn = true,
    scaleInDuration = 0.3,
    enableScaleOut = true,
    scaleOutDuration = 0.4,
    
    showStackCount = false,
    stackCountStyle = "number",
    stackCountColor = {1.0, 1.0, 1.0},
    stackCountScale = 0.8
}

-- Spawn the status effect
local bundle = spawn_status_effect(effectParams, uiParams)
```

### **JSON Usage**

```json
{
  "id": "frost_nova",
  "effectType": "debuff",
  "shapeType": "ring",
  "particleType": "ice",
  "iconStyle": "detailed",
  "category": "combat",
  
  "duration": 5.0,
  "intensity": 0.8,
  "fadeInTime": 0.3,
  "fadeOutTime": 0.5,
  "isPermanent": false,
  "canStack": false,
  "maxStacks": 1,
  
  "noiseScale": 2.0,
  "noiseSpeed": 1.5,
  "oscillationFreq": 0.8,
  "coverage": 360,
  "particleCount": 80,
  "dissolve": true,
  "opacity": 0.9,
  "scale": 1.2,
  
  "colorPrimary": [0.4, 0.8, 1.0],
  "colorSecondary": [0.0, 0.2, 0.5],
  "iconColor": [1.0, 1.0, 1.0],
  "glowColor": [0.2, 0.4, 0.8],
  
  "enablePulsing": true,
  "pulseSpeed": 1.2,
  "pulseIntensity": 0.3,
  "enableRotation": false,
  "rotationSpeed": 1.0,
  "enableScaling": true,
  "scaleSpeed": 0.8,
  "scaleRange": 0.1,
  
  "shaderType": "frost",
  "shaderIntensity": 1.0,
  "enableDistortion": true,
  "distortionStrength": 0.15,
  "enableBlur": false,
  "blurStrength": 0.1
}
```

## 🔧 **C++ API**

### **Factory Classes**

```cpp
// Status effect factory
StatusEffectFactory effectFactory;
effectFactory.initialize(1000, 4); // Cache size, thread count

// Generate assets
auto effectFuture = effectFactory.generateAsync(effectParams, uiParams);

// Wait for completion
auto effectBundle = effectFuture.get();
```

### **Batch Generation**

```cpp
// Generate multiple effects
std::vector<std::pair<StatusEffectParams, UIParams>> effectParams;
// ... populate params ...

auto effectFutures = effectFactory.generateBatch(effectParams);
std::vector<EffectBundle> effectBundles;

for (auto& future : effectFutures) {
    effectBundles.push_back(future.get());
}
```

### **JSON Loading**

```cpp
// Load from JSON file
auto effectFuture = effectFactory.generateFromJson("frost_nova.json", "frost_nova_ui.json");

auto effectBundle = effectFuture.get();
```

## 🎯 **Key Features**

### **✅ Shader Generation**
- **Effect Shaders**: Custom shaders for different effect types
- **Animation Support**: Pulsing, rotation, and scaling animations
- **Distortion Effects**: Procedural distortion and blur effects
- **Material Properties**: Full PBR material pipeline

### **✅ Texture Generation**
- **Noise Textures**: Procedural noise generation
- **Gradient Textures**: Radial and linear gradients
- **Material Maps**: Roughness and metallic maps
- **Texture Atlases**: Efficient texture packing

### **✅ Mesh Generation**
- **Shape Types**: Circle, square, hexagon, star, cross, diamond
- **Ring Meshes**: Customizable ring geometry
- **Aura Quads**: Billboard quad meshes
- **Beam Meshes**: Directional beam geometry
- **Splash Meshes**: Radial splash geometry

### **✅ Particle Generation**
- **Particle Types**: Sparkle, smoke, fire, ice, lightning, poison, healing, shield
- **Emission Control**: Configurable emission rates
- **Color Systems**: Primary and secondary color support
- **Lifetime Management**: Automatic particle lifecycle

### **✅ Icon Generation**
- **Icon Styles**: Simple, detailed, animated, glowing, pulsing
- **Background Shapes**: Circle, square, custom shapes
- **Border Effects**: Glowing borders and custom styling
- **Animation Support**: Fade, scale, and rotation animations
- **Stack Count Display**: Configurable stack count visualization

### **✅ Performance Features**
- **Caching**: LRU cache for generated assets
- **Parallel Processing**: Multi-threaded generation
- **Hot Reload**: Runtime parameter updates
- **Batch Processing**: Efficient bulk generation
- **GPU Acceleration**: Compute shader integration

## 🔍 **Validation & Error Handling**

### **Parameter Validation**

```cpp
// Validate effect parameters
if (!effectFactory.validateEffectParams(effectParams)) {
    std::string errors = effectFactory.getEffectValidationErrors(effectParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}

// Validate UI parameters
if (!effectFactory.validateUIParams(uiParams)) {
    std::string errors = effectFactory.getUIValidationErrors(uiParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}
```

### **Error Handling**

```cpp
try {
    auto bundle = effectFactory.generateSync(effectParams, uiParams);
    // Use bundle...
} catch (const std::exception& e) {
    std::cerr << "Generation failed: " << e.what() << std::endl;
}
```

## 📁 **File Structure**

```
status_effect_generator/
├── StatusEffectTypes.hpp              # Parameter structures
├── StatusEffectParams.cpp             # Parameter implementation
├── StatusEffectFactory.hpp            # Factory classes
├── StatusEffectGenerators.cpp         # Generator implementation
├── StatusEffectLuaBindings.hpp        # Lua binding interface
├── StatusEffectLuaBindings.cpp        # Lua binding implementation
├── example_frost_nova.json            # Example effect definition
├── example_frost_nova_ui.json         # Example UI definition
└── STATUS_EFFECT_SYSTEM_README.md     # This documentation
```

## 🚀 **Next Steps**

### **Planned Features**
1. **GPU-Driven Particle Simulation**: Offload particle simulation to compute shaders
2. **Layered Effects**: Blend multiple effects simultaneously
3. **Audio Asset Generation**: Procedural sound effects for status effects
4. **Cross-Platform Atlas Baking**: Mobile optimization tools
5. **Real-time Collaborative Editor**: Designer-friendly effect editor

### **Advanced Features**
- **Neural Network Integration**: AI-driven effect evolution
- **Procedural Combat Systems**: Complete effect combat ecosystems
- **Dynamic Effect Blending**: Real-time effect combination
- **Network Replication**: Efficient effect synchronization
- **Procedural Audio**: Sound effects based on visual parameters

## 📚 **Examples**

See the included example files:
- `example_frost_nova.json` - Complete frost nova effect definition
- `example_frost_nova_ui.json` - Complete UI definition

These examples demonstrate all the features and capabilities of the status effect system.

---

**✨ The Status Effect Asset Generation System provides a complete, production-ready solution for procedurally generating complex visual and UI assets for buffs, debuffs, and environmental effects, all driven by declarative JSON/Lua configuration files.** 