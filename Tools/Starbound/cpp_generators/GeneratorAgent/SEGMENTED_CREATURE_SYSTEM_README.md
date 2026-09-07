# 🐛 Segmented Creature Asset Generation System

## 🎯 **Overview**

The Segmented Creature Asset Generation System is a comprehensive C++23-based pipeline for procedurally generating segmented creatures—from slithering worms to armored centipedes—using pure data and C++ generators. The system drives mesh, texture, skeleton, animation, and AI from Lua/JSON into a unified pipeline.

## 🏗️ **Architecture**

### **✅ Core Components**

```
┌─────────────────────────────────────────────────────────────────┐
│         SEGMENTED CREATURE GENERATION PIPELINE                │
├─────────────────────────────────────────────────────────────────┤
│  🦴 MeshGen    │  🎨 TextureGen  │  🦴 RigGen      │  🎭 AnimGen    │
│  ┌─────────────┐ │  ┌─────────────┐  │  ┌─────────────┐   │  ┌─────────────┐ │
│  │ SegmentGen  │ │  │ BaseTexture │  │  │ BoneChain   │   │  │ WaveAnim    │ │
│  │ SplineGen   │ │  │ PatternGen  │  │  │ JointLimits │   │  │ CrawlAnim   │ │
│  │ HeadTailGen │ │  │ MaterialGen │  │  │ Articulation│   │  │ CoilAnim    │ │
│  │ ArmorGen    │ │  │ PBRMaps     │  │  │ Constraints │   │  │ BurrowAnim  │ │
│  └─────────────┘ │  └─────────────┘  │  └─────────────┘   │  └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### **✅ Behavior & AI Systems**

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEHAVIOR & AI SYSTEMS                      │
├─────────────────────────────────────────────────────────────────┤
│  🧠 AIGen      │  🎯 BehaviorGen  │  🧮 StateMachine │  🎮 CombatGen   │
│  ┌─────────────┐ │  ┌─────────────┐  │  ┌─────────────┐   │  ┌─────────────┐ │
│  │ BehaviorTree│ │  │ Personality │  │  │ StateTrans  │   │  │ CombatStyle │ │
│  │ DecisionTree│ │  │ Movement    │  │  │ Memory      │   │  │ Tactics     │ │
│  │ Pathfinding │ │  │ Social      │  │  │ Learning    │   │  │ Coordination│ │
│  │ Navigation  │ │  │ Territory   │  │  │ Adaptation  │   │  │ Strategy    │ │
│  └─────────────┘ │  └─────────────┘  │  └─────────────┘   │  └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 **Parameter Schema**

### **SegmentedCreatureParams**

```cpp
struct SegmentedCreatureParams {
    std::string id;                    // Unique identifier
    int segmentCount = 20;             // Total number of segments
    float segmentLength = 0.5f;        // Length per segment
    TaperProfile taperProfile;         // Tapering profile
    float segmentRadius = 0.2f;        // Base radius
    SegmentType segmentType;           // Segment shape type
    HeadType headType;                 // Head configuration
    TailType tailType;                 // Tail configuration
    float articulationStiffness;       // Joint flexibility (0-1)
    float noiseDetail;                 // Surface noise intensity
    bool armorPlates;                  // Enable armor overlay
    int plateDetailLevel;              // Armor detail level
    std::array<float, 3> colorPrimary; // Primary color RGB
    std::array<float, 3> colorSecondary; // Secondary color RGB
    float materialRoughness;           // PBR roughness
    float materialMetallic;            // PBR metallic
    AnimationProfile animationProfile; // Animation type
    AIProfile aiProfile;               // AI behavior type
};
```

### **BehaviorParams**

```cpp
struct BehaviorParams {
    float speed;                       // Movement speed multiplier
    float detectionRange;              // Detection range in meters
    float attackRange;                 // Attack range in meters
    float aggression;                  // Aggression level (0-1)
    int packSize;                      // Group size
    float burrowDepth;                 // Burrowing depth
    bool climbAbility;                 // Can climb walls/ceilings
    float patrolRadius;                // Patrol area radius
    float idleTime;                    // Time spent idle
    float chaseSpeed;                  // Speed when chasing
    float retreatHealth;               // Health threshold for retreat
    bool canSwim;                      // Swimming ability
    bool canFly;                       // Flying ability
    bool nocturnal;                    // Nocturnal behavior
    bool territorial;                  // Territorial behavior
    float territorySize;               // Territory size
    float attackDamage;                // Attack damage
    float attackCooldown;              // Attack cooldown
    bool canRangedAttack;              // Ranged attack ability
    float rangedAttackRange;           // Ranged attack range
    bool canUseAbilities;              // Special abilities
    std::vector<std::string> abilities; // List of abilities
    bool packHunting;                  // Pack hunting behavior
    float packCohesion;                // Pack cohesion level
    bool hierarchical;                 // Hierarchical structure
    int dominanceRank;                 // Dominance rank
    bool burrower;                     // Burrowing behavior
    bool climber;                      // Climbing behavior
    bool swimmer;                      // Swimming behavior
    bool flyer;                        // Flying behavior
    float preferredTemperature;        // Preferred temperature
    float temperatureTolerance;        // Temperature tolerance
};
```

## 🎨 **Enum Types**

### **TaperProfile**
- `NONE` - No tapering
- `LINEAR` - Linear tapering
- `EXPONENTIAL` - Exponential tapering
- `CUSTOM_CURVE` - Custom curve tapering

### **SegmentType**
- `CYLINDER` - Cylindrical segments
- `BOX` - Box-shaped segments
- `HEXAGON` - Hexagonal segments
- `CUSTOM_MESH` - Custom mesh segments

### **HeadType**
- `SIMPLE` - Simple head
- `MANDIBLE` - Mandible-equipped head
- `MULTI_EYE` - Multi-eyed head
- `HORNED` - Horned head

### **TailType**
- `NONE` - No tail
- `SPIKE` - Spiked tail
- `FLARED` - Flared tail

### **AnimationProfile**
- `SLITHER` - Slithering motion
- `CRAWL` - Crawling motion
- `COIL` - Coiling motion
- `CUSTOM` - Custom animation

### **AIProfile**
- `PASSIVE` - Passive behavior
- `NEUTRAL` - Neutral behavior
- `PREDATOR` - Predator behavior
- `SWARM` - Swarm behavior

## 🚀 **Usage Examples**

### **Lua Usage**

```lua
-- Create a segmented creature
local creatureParams = SegmentedCreatureParams{
    id = "iron_centipede",
    segmentCount = 20,
    segmentLength = 0.5,
    taperProfile = TaperProfile.LINEAR,
    segmentRadius = 0.2,
    segmentType = SegmentType.CYLINDER,
    headType = HeadType.MANDIBLE,
    tailType = TailType.SPIKE,
    articulationStiffness = 0.7,
    noiseDetail = 0.4,
    armorPlates = true,
    plateDetailLevel = 2,
    colorPrimary = {0.3, 0.3, 0.35},
    colorSecondary = {0.1, 0.1, 0.1},
    materialRoughness = 0.6,
    materialMetallic = 0.8,
    animationProfile = AnimationProfile.SLITHER,
    aiProfile = AIProfile.PREDATOR
}

local behaviorParams = BehaviorParams{
    speed = 1.5,
    detectionRange = 15.0,
    attackRange = 1.5,
    aggression = 0.8,
    packSize = 1,
    burrowDepth = 2.0,
    climbAbility = true,
    patrolRadius = 20.0,
    idleTime = 1.5,
    chaseSpeed = 2.0,
    retreatHealth = 0.2,
    canSwim = false,
    canFly = false,
    nocturnal = true,
    territorial = true,
    territorySize = 30.0,
    attackDamage = 15.0,
    attackCooldown = 0.8,
    canRangedAttack = false,
    rangedAttackRange = 0.0,
    canUseAbilities = true,
    abilities = {"venom_bite", "armor_penetration", "stealth_hunt"},
    packHunting = false,
    packCohesion = 0.0,
    hierarchical = false,
    dominanceRank = 0,
    burrower = true,
    climber = true,
    swimmer = false,
    flyer = false,
    preferredTemperature = 15.0,
    temperatureTolerance = 8.0
}

-- Spawn the creature
local success, creatureBundle, behaviorBundle = spawn_segmented_creature(creatureParams, behaviorParams)
```

### **JSON Usage**

```json
{
  "id": "iron_centipede",
  "segmentCount": 20,
  "segmentLength": 0.5,
  "taperProfile": "linear",
  "segmentRadius": 0.2,
  "segmentType": "cylinder",
  "headType": "mandible",
  "tailType": "spike",
  "articulationStiffness": 0.7,
  "noiseDetail": 0.4,
  "armorPlates": true,
  "plateDetailLevel": 2,
  "colorPrimary": [0.3, 0.3, 0.35],
  "colorSecondary": [0.1, 0.1, 0.1],
  "materialRoughness": 0.6,
  "materialMetallic": 0.8,
  "animationProfile": "slither",
  "aiProfile": "predator"
}
```

## 🔧 **C++ API**

### **Factory Classes**

```cpp
// Segmented creature factory
SegmentedCreatureFactory creatureFactory;
creatureFactory.initialize(1000, 4); // Cache size, thread count

// Behavior factory
BehaviorFactory behaviorFactory;
behaviorFactory.initialize(1000, 4);

// Generate assets
auto creatureFuture = creatureFactory.generateAsync(creatureParams);
auto behaviorFuture = behaviorFactory.generateAsync(behaviorParams);

// Wait for completion
auto creatureBundle = creatureFuture.get();
auto behaviorBundle = behaviorFuture.get();
```

### **Batch Generation**

```cpp
// Generate multiple creatures
std::vector<SegmentedCreatureParams> creatureParams;
// ... populate params ...

auto creatureFutures = creatureFactory.generateBatch(creatureParams);
std::vector<AssetBundle> creatureBundles;

for (auto& future : creatureFutures) {
    creatureBundles.push_back(future.get());
}
```

### **JSON Loading**

```cpp
// Load from JSON file
auto creatureFuture = creatureFactory.generateFromJson("iron_centipede.json");
auto behaviorFuture = behaviorFactory.generateFromJson("predator_behavior.json");

auto creatureBundle = creatureFuture.get();
auto behaviorBundle = behaviorFuture.get();
```

## 🎯 **Key Features**

### **✅ Mesh Generation**
- **Segment Types**: Cylinder, Box, Hexagon, Custom Mesh
- **Tapering Profiles**: None, Linear, Exponential, Custom Curve
- **Head/Tail Types**: Simple, Mandible, Multi-Eye, Horned, Spike, Flared
- **Armor Plates**: Configurable armor overlay system
- **Noise Displacement**: Procedural surface detail
- **Spline Assembly**: Smooth segment connection along curves

### **✅ Texture Generation**
- **PBR Materials**: Roughness and metallic maps
- **Color Systems**: Primary and secondary color support
- **Pattern Generation**: Procedural armor and surface patterns
- **Material Properties**: Full PBR material pipeline

### **✅ Skeleton & Rigging**
- **Bone Chain**: Automatic bone chain generation
- **Joint Limits**: Configurable articulation stiffness
- **Head/Tail Bones**: Specialized bone structures
- **Constraints**: Advanced joint constraint system

### **✅ Animation Generation**
- **Wave Slither**: Sine wave propagation along segments
- **Crawl**: Alternating lift/lower motion
- **Coil**: Procedural bezier bend animations
- **Custom**: User-defined animation profiles

### **✅ AI & Behavior**
- **Behavior Trees**: Advanced AI decision making
- **State Machines**: Complex behavior state management
- **Combat Systems**: Attack patterns and tactics
- **Social Behavior**: Pack hunting and hierarchy
- **Environmental**: Burrowing, climbing, swimming, flying

### **✅ Performance Features**
- **Caching**: LRU cache for generated assets
- **Parallel Processing**: Multi-threaded generation
- **Hot Reload**: Runtime parameter updates
- **Batch Processing**: Efficient bulk generation
- **GPU Acceleration**: Compute shader integration

## 🔍 **Validation & Error Handling**

### **Parameter Validation**

```cpp
// Validate creature parameters
if (!creatureFactory.validateParams(creatureParams)) {
    std::string errors = creatureFactory.getValidationErrors(creatureParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}

// Validate behavior parameters
if (!behaviorFactory.validateParams(behaviorParams)) {
    std::string errors = behaviorFactory.getValidationErrors(behaviorParams);
    std::cerr << "Validation errors: " << errors << std::endl;
}
```

### **Error Handling**

```cpp
try {
    auto bundle = creatureFactory.generateSync(creatureParams);
    // Use bundle...
} catch (const std::exception& e) {
    std::cerr << "Generation failed: " << e.what() << std::endl;
}
```

## 📁 **File Structure**

```
segmented_creature_generator/
├── SegmentedCreatureParams.hpp          # Parameter structures
├── SegmentedCreatureParams.cpp          # Parameter implementation
├── ProceduralFactory.hpp                # Factory classes
├── ProceduralFactory.cpp                # Factory implementation
├── SegmentedCreatureAssetBundle.hpp     # Asset bundle structure
├── SegmentedCreatureLuaBindings.hpp     # Lua binding interface
├── SegmentedCreatureLuaBindings.cpp     # Lua binding implementation
├── example_iron_centipede.json          # Example creature definition
├── example_predator_behavior.json       # Example behavior definition
└── SEGMENTED_CREATURE_SYSTEM_README.md  # This documentation
```

## 🚀 **Next Steps**

### **Planned Features**
1. **GPU-Driven Spline Tessellation**: Real-time generation of millions of segments
2. **Dynamic Damage System**: Segment-level damage and dissolution effects
3. **Neural Style Transfer**: AI-powered pattern generation
4. **Procedural Voice Synthesis**: Creature sound generation
5. **Network Replication**: Lightweight multiplayer parameter sharing

### **Advanced Features**
- **Dynamic Segment Deformation**: Real-time physics-based deformation
- **Shader-Based Iridescence**: Advanced material effects
- **Modular Attachment System**: Equipment and parasite systems
- **Neural Network Integration**: AI-driven creature evolution
- **Procedural Ecosystem Generation**: Complete creature ecosystems

## 📚 **Examples**

See the included example files:
- `example_iron_centipede.json` - Complete creature definition
- `example_predator_behavior.json` - Complete behavior definition

These examples demonstrate all the features and capabilities of the segmented creature system.

---

**🎯 The Segmented Creature Asset Generation System provides a complete, production-ready solution for procedurally generating complex segmented creatures with advanced AI behaviors, all driven by declarative JSON/Lua configuration files.** 