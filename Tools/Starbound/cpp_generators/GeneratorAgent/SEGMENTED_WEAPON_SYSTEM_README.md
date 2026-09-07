# ⚔️ Segmented Weapon Asset Generation System

## 🎯 **Overview**

The Segmented Weapon Asset Generation System is a comprehensive C++23-based pipeline for procedurally generating segmented weapons—from whips and chains to flails and nunchaku—using pure data and C++ generators. The system drives mesh, texture, skeleton, and physics from Lua/JSON into a unified pipeline.

## 🏗️ **Architecture**

### **✅ Core Components**

```
┌─────────────────────────────────────────────────────────────────┐
│         SEGMENTED WEAPON GENERATION PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│  🦴 MeshGen    │  🎨 TextureGen  │  🦴 RigGen      │  ⚡ PhysGen    │
│  ┌─────────────┐ │  ┌─────────────┐  │  ┌─────────────┐   │  ┌─────────────┐ │
│  │ SegmentGen  │ │  │ BaseTexture │  │  │ BoneChain   │   │  │ RigidBody   │ │
│  │ SplineGen   │ │  │ PatternGen  │  │  │ JointLimits │   │  │ Collision   │ │
│  │ HeadTailGen │ │  │ MaterialGen │  │  │ Articulation│   │  │ Joints      │ │
│  │ ArmorGen    │ │  │ PBRMaps     │  │  │ Constraints │   │  │ Solver      │ │
│  └─────────────┘ │  └─────────────┘  │  └─────────────┘   │  └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 **Parameter Schema**

### **SegmentedWeaponParams**

```cpp
struct SegmentedWeaponParams {
    std::string id;                    // Unique identifier
    WeaponType weaponType;             // Weapon type (whip, chain, flail, etc.)
    int segmentCount;                  // Number of segments
    float segmentLength;               // Length per segment
    float segmentRadius;               // Radius of segments
    SegmentShape segmentShape;         // Shape of segments
    TaperProfile taperProfile;         // Tapering profile
    float jointFlexibility;            // Joint flexibility (0-1)
    ArticulationLimits articulationLimits; // Joint limits
    MaterialType materialType;         // Material type
    glm::vec3 colorPrimary;            // Primary color
    glm::vec3 colorSecondary;          // Secondary color
    float noiseDetail;                 // Surface noise
    float textureScale;                // Texture scaling
    bool ornamentation;                // Enable ornamentation
    EndAttachment endAttachment;       // End attachment type
};
```

### **PhysicsParams**

```cpp
struct PhysicsParams {
    float massPerSegment;              // Mass per segment
    float damping;                     // Joint damping
    float restitution;                 // Bounciness
    float collisionRadius;             // Collision radius
    int solverIterations;              // Physics solver iterations
    float gravityInfluence;            // Gravity influence
    float friction;                    // Friction coefficient
    float rollingFriction;             // Rolling friction
    float spinningFriction;            // Spinning friction
    bool enableGravity;                // Enable gravity
    bool enableCollisionDetection;     // Enable collision detection
    float maxLinearVelocity;           // Max linear velocity
    float maxAngularVelocity;          // Max angular velocity
    float jointDamping;                // Joint damping
    float jointFriction;               // Joint friction
    bool enableJointLimits;            // Enable joint limits
    float jointLimitSoftness;          // Joint limit softness
    float jointLimitBias;              // Joint limit bias
    float jointLimitRelaxation;        // Joint limit relaxation
};
```

## 🎨 **Enum Types**

### **WeaponType**
- `WHIP` - Flexible whip weapon
- `CHAIN` - Chain weapon
- `FLAIL` - Flail weapon
- `NUNCHAKU` - Nunchaku weapon
- `ROPE` - Rope weapon

### **SegmentShape**
- `CYLINDER` - Cylindrical segments
- `BOX` - Box-shaped segments
- `SPHERE` - Spherical segments
- `CUSTOM_MESH` - Custom mesh segments

### **TaperProfile**
- `NONE` - No tapering
- `LINEAR` - Linear tapering
- `EXPONENTIAL` - Exponential tapering
- `CUSTOM_CURVE` - Custom curve tapering

### **MaterialType**
- `LEATHER` - Leather material
- `STEEL` - Steel material
- `ROPE` - Rope material
- `CHAIN_METAL` - Chain metal material

### **EndAttachment**
- `NONE` - No end attachment
- `WEIGHT` - Weight attachment
- `SPIKE` - Spike attachment
- `HOOK` - Hook attachment
- `BLADE` - Blade attachment

## 🚀 **Usage Examples**

### **Lua Usage**

```lua
-- Create a segmented weapon
local weaponParams = SegmentedWeaponParams{
    id = "venom_whip",
    weaponType = WeaponType.WHIP,
    segmentCount = 16,
    segmentLength = 0.3,
    segmentRadius = 0.02,
    segmentShape = SegmentShape.CYLINDER,
    taperProfile = TaperProfile.LINEAR,
    jointFlexibility = 0.9,
    articulationLimits = ArticulationLimits{
        twist = 45.0,
        swing = 60.0
    },
    materialType = MaterialType.LEATHER,
    colorPrimary = {0.15, 0.05, 0.02},
    colorSecondary = {0.9, 0.7, 0.5},
    noiseDetail = 0.3,
    textureScale = 2.0,
    ornamentation = true,
    endAttachment = EndAttachment.BLADE
}

local physicsParams = PhysicsParams{
    massPerSegment = 0.1,
    damping = 0.2,
    restitution = 0.1,
    collisionRadius = 0.025,
    solverIterations = 8,
    gravityInfluence = 1.0,
    friction = 0.5,
    rollingFriction = 0.1,
    spinningFriction = 0.1,
    enableGravity = true,
    enableCollisionDetection = true,
    maxLinearVelocity = 100.0,
    maxAngularVelocity = 10.0,
    jointDamping = 0.2,
    jointFriction = 0.1,
    enableJointLimits = true,
    jointLimitSoftness = 0.5,
    jointLimitBias = 0.3,
    jointLimitRelaxation = 1.0
}

-- Spawn the weapon
local bundle = spawn_segmented_weapon(weaponParams, physicsParams)
```

### **JSON Usage**

```json
{
  "id": "venom_whip",
  "weaponType": "whip",
  "segmentCount": 16,
  "segmentLength": 0.3,
  "segmentRadius": 0.02,
  "segmentShape": "cylinder",
  "taperProfile": "linear",
  "jointFlexibility": 0.9,
  "articulationLimits": {
    "twist": 45.0,
    "swing": 60.0
  },
  "materialType": "leather",
  "colorPrimary": [0.15, 0.05, 0.02],
  "colorSecondary": [0.9, 0.7, 0.5],
  "noiseDetail": 0.3,
  "textureScale": 2.0,
  "ornamentation": true,
  "endAttachment": "blade"
}
```

## 🔧 **C++ API**

### **Factory Classes**

```cpp
// Segmented weapon factory
SegmentedWeaponFactory weaponFactory;
weaponFactory.initialize(1000, 4); // Cache size, thread count

// Generate assets
auto weaponFuture = weaponFactory.generateAsync(weaponParams, physicsParams);

// Wait for completion
auto weaponBundle = weaponFuture.get();
```

### **Batch Generation**

```cpp
// Generate multiple weapons
std::vector<std::pair<SegmentedWeaponParams, PhysicsParams>> weaponParams;
// ... populate params ...

auto weaponFutures = weaponFactory.generateBatch(weaponParams);
std::vector<AssetBundle> weaponBundles;

for (auto& future : weaponFutures) {
    weaponBundles.push_back(future.get());
}
```

### **JSON Loading**

```cpp
// Load from JSON file
auto weaponFuture = weaponFactory.generateFromJson("venom_whip.json", "whip_physics.json");

auto weaponBundle = weaponFuture.get();
```

## 🎯 **Key Features**

### **✅ Mesh Generation**
- **Segment Types**: Cylinder, Box, Sphere, Custom Mesh
- **Tapering Profiles**: None, Linear, Exponential, Custom Curve
- **End Attachments**: Blade, Weight, Spike, Hook, None
- **Ornamentation**: Procedural rings, spikes, leather wraps
- **Noise Displacement**: Procedural surface detail
- **Spline Assembly**: Smooth segment connection along curves

### **✅ Texture Generation**
- **PBR Materials**: Roughness and metallic maps
- **Material Types**: Leather, Steel, Rope, Chain Metal
- **Color Systems**: Primary and secondary color support
- **Pattern Generation**: Procedural wear and surface patterns
- **Material Properties**: Full PBR material pipeline

### **✅ Skeleton & Rigging**
- **Bone Chain**: Automatic bone chain generation
- **Joint Limits**: Configurable articulation limits
- **Joint Flexibility**: Adjustable joint stiffness
- **Constraints**: Advanced joint constraint system

### **✅ Physics Setup**
- **Rigid Bodies**: Per-segment rigid body generation
- **Collision Detection**: Capsule or sphere colliders
- **Joint Physics**: Hinge and cone twist joints
- **Solver Configuration**: Adjustable solver iterations
- **Velocity Limits**: Linear and angular velocity limits
- **Friction Systems**: Multiple friction types

### **✅ Performance Features**
- **Caching**: LRU cache for generated assets
- **Parallel Processing**: Multi-threaded generation
- **Hot Reload**: Runtime parameter updates
- **Batch Processing**: Efficient bulk generation
- **GPU Acceleration**: Compute shader integration

## 🔍 **Validation & Error Handling**

### **Parameter Validation**

```cpp
// Validate weapon parameters
if (!weaponFactory.validateWeaponParams(weaponParams)) {
    std::string errors = weaponFactory.getWeaponValidationErrors(weaponParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}

// Validate physics parameters
if (!weaponFactory.validatePhysicsParams(physicsParams)) {
    std::string errors = weaponFactory.getPhysicsValidationErrors(physicsParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}
```

### **Error Handling**

```cpp
try {
    auto bundle = weaponFactory.generateSync(weaponParams, physicsParams);
    // Use bundle...
} catch (const std::exception& e) {
    std::cerr << "Generation failed: " << e.what() << std::endl;
}
```

## 📁 **File Structure**

```
segmented_weapon_generator/
├── SegmentedWeaponTypes.hpp           # Parameter structures
├── SegmentedWeaponParams.cpp          # Parameter implementation
├── SegmentedWeaponFactory.hpp         # Factory classes
├── SegmentedWeaponGenerators.cpp      # Generator implementation
├── SegmentedWeaponLuaBindings.hpp     # Lua binding interface
├── SegmentedWeaponLuaBindings.cpp     # Lua binding implementation
├── example_venom_whip.json            # Example weapon definition
├── example_whip_physics.json          # Example physics definition
└── SEGMENTED_WEAPON_SYSTEM_README.md  # This documentation
```

## 🚀 **Next Steps**

### **Planned Features**
1. **GPU-Driven Physics**: Offload chain simulation to compute shaders
2. **Dynamic Wear System**: Segments degrade or break based on usage
3. **Style Transfer Texturing**: Mimic real-world leather or metal patina
4. **Network Replication**: Sync only parameter blobs and key joint states
5. **Attachment Modularity**: Allow swapping blades, hooks, charms at runtime

### **Advanced Features**
- **Real-time Spline Deformation**: Dynamic rope weapon deformation
- **Procedural Sparks**: Metal impact effects driven by physics velocity
- **Sound FX Integration**: Weapon sounds based on physics interactions
- **Neural Network Integration**: AI-driven weapon evolution
- **Procedural Combat Systems**: Complete weapon combat ecosystems

## 📚 **Examples**

See the included example files:
- `example_venom_whip.json` - Complete weapon definition
- `example_whip_physics.json` - Complete physics definition

These examples demonstrate all the features and capabilities of the segmented weapon system.

---

**🎯 The Segmented Weapon Asset Generation System provides a complete, production-ready solution for procedurally generating complex segmented weapons with advanced physics behaviors, all driven by declarative JSON/Lua configuration files.** 