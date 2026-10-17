#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <type_traits>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Mechs {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using MaterialHandle = uint32_t;
using ParticleHandle = uint32_t;
using SegmentHandle = uint32_t;
using PhysicsHandle = uint32_t;
using AudioHandle = uint32_t;

// Field-wise hashing. Structs are never hashed as raw memory: that would include
// padding bytes and the heap pointers inside std::string / std::vector.
namespace MechHash {

class Hasher {
public:
    Hasher() { XXH64_reset(&state_, 0); }

    template <typename T>
        requires std::is_arithmetic_v<T> || std::is_enum_v<T>
    Hasher& add(T value) {
        XXH64_update(&state_, &value, sizeof(T));
        return *this;
    }
    Hasher& add(const std::string& s) {
        add(static_cast<uint64_t>(s.size()));
        XXH64_update(&state_, s.data(), s.size());
        return *this;
    }
    Hasher& add(const glm::vec2& v) { return add(v.x).add(v.y); }
    Hasher& add(const glm::vec3& v) { return add(v.x).add(v.y).add(v.z); }
    Hasher& add(const glm::vec4& v) { return add(v.x).add(v.y).add(v.z).add(v.w); }
    Hasher& add(const glm::quat& q) { return add(q.w).add(q.x).add(q.y).add(q.z); }
    template <typename T>
    Hasher& add(const std::vector<T>& values) {
        add(static_cast<uint64_t>(values.size()));
        for (const auto& v : values) add(v);
        return *this;
    }

    uint64_t digest() const { return XXH64_digest(&state_); }

private:
    XXH64_state_t state_;
};

template <typename... Ts>
uint64_t hashFields(const Ts&... fields) {
    Hasher h;
    (h.add(fields), ...);
    return h.digest();
}

} // namespace MechHash

// An atomic counter that can be copied (the copy takes a snapshot of the value),
// so that structs carrying performance counters stay copyable.
template <typename T>
class CopyableAtomic {
public:
    CopyableAtomic() = default;
    CopyableAtomic(T value) : value_(value) {}
    CopyableAtomic(const CopyableAtomic& other) : value_(other.load()) {}
    CopyableAtomic& operator=(const CopyableAtomic& other) {
        store(other.load());
        return *this;
    }
    CopyableAtomic& operator=(T value) {
        store(value);
        return *this;
    }

    T load() const { return value_.load(std::memory_order_relaxed); }
    void store(T value) { value_.store(value, std::memory_order_relaxed); }
    T fetch_add(T delta) { return value_.fetch_add(delta, std::memory_order_relaxed); }
    operator T() const { return load(); }

private:
    std::atomic<T> value_{};
};

// Enhanced MechParams with hybrid C++23/26 + Lua features
struct MechParams {
    std::string   id, style, pattern;
    std::vector<std::string> forms, weaponMounts;
    glm::vec3     colorPrimary = glm::vec3(0.5f);
    glm::vec3     colorAccent = glm::vec3(1.0f, 0.6f, 0.1f);
    int           limbCount = 2;
    int           detailLevel = 1;
    glm::vec3     torsoSize = glm::vec3(1.0f);
    float         limbLength = 1.0f;
    bool          armorPlates = false;
    bool          pulseEmission = false;

    // Enhanced features from hybrid pipeline
    std::string   variant = "standard";           // mech variant type
    std::vector<std::string> armorTypes;          // armor plate types
    std::vector<std::string> weaponTypes;         // weapon system types
    glm::vec3     scale = glm::vec3(1.0f);       // overall scale
    float         mass = 1000.0f;                 // total mass
    bool          enableGlow = false;             // emissive effects
    bool          enableShield = false;           // shield generator
    std::string   aiBehavior = "aggressive";      // AI behavior type
    int           crewCapacity = 1;               // crew members
    float         maxSpeed = 10.0f;               // max movement speed
    float         jumpHeight = 2.0f;              // jump capability
    bool          canFly = false;                 // flight capability
    bool          canSwim = false;                // aquatic capability
    std::string   faction = "neutral";            // faction alignment
    std::vector<std::string> abilities;           // special abilities
    std::unordered_map<std::string, float> stats; // custom stats

    // Procedural generation parameters
    float         noiseScale = 1.0f;              // texture noise scale
    float         patternIntensity = 0.5f;        // pattern strength
    int           textureResolution = 512;         // texture size
    bool          generateNormalMap = true;        // normal map generation
    bool          generateRoughnessMap = true;    // roughness map
    bool          generateMetallicMap = true;     // metallic map

    // Animation parameters
    float         morphDuration = 1.0f;           // form change duration
    std::string   morphCurve = "easeInOut";       // morph interpolation
    bool          enableIK = true;                // inverse kinematics
    bool          enablePhysics = true;           // physics simulation

    // LOD parameters
    std::vector<float> lodDistances = {10.0f, 50.0f, 100.0f, 200.0f};
    std::vector<int> lodTriangleCounts = {5000, 2000, 500, 100};

    // Performance tracking (not part of the identity hash)
    std::chrono::system_clock::time_point creationTime{};
    CopyableAtomic<uint64_t> generationTime{0};
    CopyableAtomic<uint64_t> memoryUsage{0};

    uint64_t hashKey() const noexcept {
        MechHash::Hasher h;
        h.add(id).add(style).add(pattern).add(variant)
         .add(forms).add(weaponMounts).add(armorTypes).add(weaponTypes).add(abilities)
         .add(colorPrimary).add(colorAccent)
         .add(limbCount).add(detailLevel).add(torsoSize).add(limbLength)
         .add(armorPlates).add(pulseEmission).add(scale).add(mass)
         .add(enableGlow).add(enableShield).add(crewCapacity)
         .add(maxSpeed).add(jumpHeight).add(canFly).add(canSwim)
         .add(noiseScale).add(patternIntensity).add(textureResolution)
         .add(generateNormalMap).add(generateRoughnessMap).add(generateMetallicMap)
         .add(morphDuration).add(morphCurve).add(enableIK).add(enablePhysics)
         .add(lodDistances).add(lodTriangleCounts);
        return h.digest();
    }
};

// Segmented Mech Parameters (Snake/Worm)
struct SegmentedMechParams {
    std::string id = "segmented_mech";
    std::string mechType = "snake";  // "snake", "worm", "serpent"

    // Segmentation
    int segmentCount = 15;
    float segmentLength = 1.0f;
    float segmentRadius = 0.4f;
    float connectorGap = 0.1f;

    // Joint Mechanics
    float maxBendAngleDeg = 45.0f;
    float bendStiffness = 100.0f;
    float jointFlexibility = 0.7f;

    // Armor & Details
    bool enablePlating = true;
    int platesPerSegment = 6;
    float plateThickness = 0.05f;
    glm::vec4 platingColor = {0.3f, 0.3f, 0.35f, 1.0f};
    int platingDetailLevel = 2;

    // Emissive Strips
    int stripeCount = 2;
    float stripeWidth = 0.02f;
    glm::vec4 stripeColor = {1.0f, 0.2f, 0.2f, 1.0f};
    float stripeGlowIntensity = 3.0f;

    // VFX
    bool enableJointSparks = true;
    float sparkRate = 20.0f;
    float sparkLifetime = 0.4f;
    glm::vec4 sparkColor = {1.0f, 0.8f, 0.5f, 1.0f};

    // Physics
    float segmentMass = 10.0f;
    float jointDamping = 0.7f;

    // Animation
    float waveAmplitude = 1.5f;
    float waveFrequency = 1.0f;
    std::string animationProfile = "mech_slither";

    // Cockpit Integration
    std::string cockpitType = "internal";
    int cockpitSegmentIndex = 5;
    float cockpitRadius = 0.8f;
    glm::vec3 cockpitOrientation = {0.0f, 1.0f, 0.0f};

    // Tapering & Shape
    std::string taperProfile = "linear";
    std::string segmentShape = "cylinder";
    float noiseDetail = 0.3f;
    float textureScale = 1.5f;

    // Colors
    glm::vec3 colorPrimary = {0.2f, 0.3f, 0.35f};
    glm::vec3 colorSecondary = {0.8f, 0.6f, 0.4f};

    // AI & Behavior
    std::string aiProfile = "patrol";

    // LOD & Performance
    bool rebuildOnLOD = false;
    int lodCount = 3;

    uint64_t hashKey() const noexcept {
        MechHash::Hasher h;
        h.add(id).add(mechType)
         .add(segmentCount).add(segmentLength).add(segmentRadius).add(connectorGap)
         .add(maxBendAngleDeg).add(bendStiffness).add(jointFlexibility)
         .add(enablePlating).add(platesPerSegment).add(plateThickness).add(platingColor).add(platingDetailLevel)
         .add(stripeCount).add(stripeWidth).add(stripeColor).add(stripeGlowIntensity)
         .add(enableJointSparks).add(sparkRate).add(sparkLifetime).add(sparkColor)
         .add(segmentMass).add(jointDamping)
         .add(waveAmplitude).add(waveFrequency).add(animationProfile)
         .add(cockpitType).add(cockpitSegmentIndex).add(cockpitRadius).add(cockpitOrientation)
         .add(taperProfile).add(segmentShape).add(noiseDetail).add(textureScale)
         .add(colorPrimary).add(colorSecondary)
         .add(aiProfile).add(rebuildOnLOD).add(lodCount);
        return h.digest();
    }
};

// Cockpit Parameters
struct CockpitParams {
    // Seat & Interior
    float seatWidth = 0.8f;
    float seatDepth = 1.2f;
    float seatHeight = 0.5f;
    glm::vec4 seatFabricColor = {0.2f, 0.2f, 0.25f, 1.0f};
    bool headrestEnabled = true;

    // Canopy & Glass
    float canopyRadius = 1.0f;
    float canopyHeight = 0.8f;
    float glassThickness = 0.02f;
    glm::vec4 glassTint = {0.1f, 0.1f, 0.15f, 0.3f};
    float reflectivity = 0.8f;

    // Console & Controls
    int displayCount = 3;
    glm::vec2 displayResolution = {512.0f, 384.0f};
    float stickOffsetX = 0.3f, stickOffsetY = 0.2f;
    bool throttleLever = true;
    bool pedalControls = true;

    // Instrumentation
    int gaugeCount = 6;
    float gaugeRadius = 0.1f;
    glm::vec4 gaugeNeedleColor = {1.0f, 0.2f, 0.2f, 1.0f};
    bool holographicHUD = true;

    // Ambient FX
    bool cockpitLight = true;
    glm::vec4 lightColor = {0.8f, 0.8f, 1.0f, 1.0f};
    float lightIntensity = 1.0f;

    // Interaction
    bool canopyAnimEnabled = true;
    float canopyOpenAngleDeg = 90.0f;
    float canopyOpenDuration = 2.0f;

    // Integration
    glm::vec3 mountOffset = {0.0f, 0.5f, 0.0f};
    glm::quat mountRotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);

    uint64_t hashKey() const noexcept {
        MechHash::Hasher h;
        h.add(seatWidth).add(seatDepth).add(seatHeight).add(seatFabricColor).add(headrestEnabled)
         .add(canopyRadius).add(canopyHeight).add(glassThickness).add(glassTint).add(reflectivity)
         .add(displayCount).add(displayResolution).add(stickOffsetX).add(stickOffsetY)
         .add(throttleLever).add(pedalControls)
         .add(gaugeCount).add(gaugeRadius).add(gaugeNeedleColor).add(holographicHUD)
         .add(cockpitLight).add(lightColor).add(lightIntensity)
         .add(canopyAnimEnabled).add(canopyOpenAngleDeg).add(canopyOpenDuration)
         .add(mountOffset).add(mountRotation);
        return h.digest();
    }
};

// UI Parameters
struct UIParams {
    int iconSize = 64;
    glm::vec4 borderColor = {1.0f, 1.0f, 1.0f, 0.9f};
    std::string backgroundShape = "hexagon";
    bool flashOnSelect = true;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(iconSize, borderColor, backgroundShape, flashOnSelect);
    }
};

// Enhanced MechBundle with additional assets
struct MechBundle {
    MeshHandle    mesh = 0;
    TextureHandle tex = 0;
    SkeletonHandle skeleton = 0;
    AnimationHandle animation = 0;
    MaterialHandle material = 0;

    // Additional assets for enhanced pipeline
    TextureHandle normalMap = 0;
    TextureHandle roughnessMap = 0;
    TextureHandle metallicMap = 0;
    TextureHandle emissiveMap = 0;

    // Physics data
    std::vector<glm::vec3> collisionVertices;
    std::vector<uint32_t> collisionIndices;
    glm::vec3 centerOfMass = glm::vec3(0.0f);
    float mass = 0.0f;

    // Animation data
    std::vector<std::string> animationClips;
    std::unordered_map<std::string, float> morphWeights;

    // Performance data
    std::chrono::system_clock::time_point creationTime{};
    uint64_t generationTime = 0;
    uint64_t memoryUsage = 0;
    bool gpuAccelerated = false;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(mesh, tex, skeleton, animation, material,
                                    normalMap, roughnessMap, metallicMap, emissiveMap, mass);
    }
};

// Segmented Mech Asset Bundle
struct SegmentedMechBundle {
    MeshHandle segmentMesh = 0;
    SkeletonHandle skeleton = 0;
    AnimationHandle proceduralAnimation = 0;
    MaterialHandle materialShader = 0;
    ParticleHandle sparkParticles = 0;
    PhysicsHandle physicsAsset = 0;

    // Cockpit integration
    MeshHandle cockpitMesh = 0;
    TextureHandle cockpitTexture = 0;
    MaterialHandle cockpitMaterial = 0;

    // UI elements
    TextureHandle icon = 0;

    // Performance data
    std::chrono::system_clock::time_point creationTime{};
    uint64_t generationTime = 0;
    uint64_t memoryUsage = 0;
    bool gpuAccelerated = false;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(segmentMesh, skeleton, proceduralAnimation, materialShader,
                                    sparkParticles, physicsAsset, cockpitMesh, cockpitTexture,
                                    cockpitMaterial, icon);
    }
};

// Mech instance state for runtime management
struct MechInstanceState {
    std::string id;
    MechParams params;
    MechBundle bundle;

    // Runtime state
    std::string currentForm = "default";
    std::string targetForm = "default";
    float morphProgress = 0.0f;
    bool isMorphing = false;
    bool morphPaused = false;
    bool isActive = true;

    // Transform
    glm::vec3 position = glm::vec3(0.0f);
    glm::quat rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    glm::vec3 scale = glm::vec3(1.0f);

    // Physics
    glm::vec3 velocity = glm::vec3(0.0f);
    glm::vec3 angularVelocity = glm::vec3(0.0f);
    glm::vec3 acceleration = glm::vec3(0.0f);

    // Animation
    float animationTime = 0.0f;
    std::string currentAnimation = "idle";
    bool animationLooping = true;

    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate{};
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(id, params.hashKey(), bundle.hashKey(), position, rotation);
    }
};

// Segmented Mech Instance State
struct SegmentedMechInstanceState {
    std::string id;
    SegmentedMechParams params;
    SegmentedMechBundle bundle;
    CockpitParams cockpitParams;
    bool cockpitAttached = true;

    // Runtime state
    std::vector<SegmentHandle> segments;
    int currentSegmentCount = 0;
    bool isActive = true;

    // Transform
    glm::vec3 position = glm::vec3(0.0f);
    glm::quat rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    glm::vec3 scale = glm::vec3(1.0f);

    // Physics
    glm::vec3 velocity = glm::vec3(0.0f);
    glm::vec3 angularVelocity = glm::vec3(0.0f);
    glm::vec3 acceleration = glm::vec3(0.0f);

    // Animation
    float animationTime = 0.0f;
    std::string currentAnimation = "slither";
    bool animationLooping = true;
    bool animationPaused = false;

    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate{};
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(id, params.hashKey(), bundle.hashKey(), cockpitParams.hashKey(),
                                    position, rotation);
    }
};

// Performance metrics for the mech generation system
struct MechPerformanceMetrics {
    std::atomic<uint64_t> totalGenerations{0};
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> totalGenerationTime{0};
    std::atomic<uint64_t> peakMemoryUsage{0};
    std::atomic<uint64_t> activeInstances{0};
    std::atomic<uint64_t> morphingInstances{0};

    void reset() {
        totalGenerations = 0;
        cacheHits = 0;
        cacheMisses = 0;
        totalGenerationTime = 0;
        peakMemoryUsage = 0;
        activeInstances = 0;
        morphingInstances = 0;
    }

    double getCacheHitRate() const {
        uint64_t total = cacheHits.load() + cacheMisses.load();
        return total > 0 ? static_cast<double>(cacheHits.load()) / total : 0.0;
    }

    double getAverageGenerationTime() const {
        uint64_t generations = totalGenerations.load();
        return generations > 0 ? static_cast<double>(totalGenerationTime.load()) / generations : 0.0;
    }
};

// Procedural generation parameters
struct ProceduralParams {
    // Noise parameters
    float frequency = 1.0f;
    float amplitude = 1.0f;
    int octaves = 4;
    float persistence = 0.5f;
    float lacunarity = 2.0f;

    // Pattern parameters
    std::string patternType = "hexagonal";
    float patternScale = 1.0f;
    float patternRotation = 0.0f;
    glm::vec3 patternColor = glm::vec3(1.0f);

    // Material parameters
    float roughness = 0.5f;
    float metallic = 0.0f;
    float emissive = 0.0f;
    float normalStrength = 1.0f;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(patternType, frequency, amplitude, octaves, persistence, lacunarity,
                                    patternScale, patternRotation, patternColor,
                                    roughness, metallic, emissive, normalStrength);
    }
};

// Centipede Mech Parameters
struct CentipedeMechParams {
    std::string id = "centipede_mech";
    int segmentCount = 8;
    float segmentLength = 1.2f;
    float segmentRadius = 0.3f;
    glm::vec4 baseColor = {0.2f, 0.8f, 0.2f, 1.0f};
    bool seamlessJoints = true;

    // Leg parameters
    int legsPerSegment = 3;
    float upperLegLength = 0.8f;
    float lowerLegLength = 0.6f;
    float jointRadius = 0.1f;
    bool armorPlates = true;
    std::string footType = "Claw";

    // Cockpit parameters
    bool hasCockpit = true;
    glm::vec3 cockpitPosition = {0.0f, 0.0f, 0.0f};
    float cockpitWidth = 1.0f;
    float cockpitHeight = 0.8f;
    float cockpitDepth = 1.2f;
    bool enableDisplays = true;
    int displayCount = 4;
    std::string seatMaterial = "Leather";
    std::string controlStyle = "Holographic";

    // Weapon & sensor parameters
    int missileTubes = 2;
    int autocannonSlots = 1;
    bool enableTurret = true;
    bool enableRadarArray = true;
    float radarRange = 300.0f;

    uint64_t hashKey() const noexcept {
        MechHash::Hasher h;
        h.add(id).add(segmentCount).add(segmentLength).add(segmentRadius).add(baseColor).add(seamlessJoints)
         .add(legsPerSegment).add(upperLegLength).add(lowerLegLength).add(jointRadius).add(armorPlates).add(footType)
         .add(hasCockpit).add(cockpitPosition).add(cockpitWidth).add(cockpitHeight).add(cockpitDepth)
         .add(enableDisplays).add(displayCount).add(seatMaterial).add(controlStyle)
         .add(missileTubes).add(autocannonSlots).add(enableTurret).add(enableRadarArray).add(radarRange);
        return h.digest();
    }
};

// Centipede Mech Asset Bundle
struct CentipedeMechBundle {
    std::vector<MeshHandle> segments;
    std::vector<MeshHandle> joints;
    std::vector<MeshHandle> legs;
    MeshHandle cockpit = 0;
    std::vector<MeshHandle> weapons;
    MeshHandle sensorArray = 0;
    std::vector<MaterialHandle> materials;
    std::vector<ParticleHandle> vfx;
    std::vector<AudioHandle> audio;
    PhysicsHandle collider = 0;

    // Performance data
    std::chrono::system_clock::time_point creationTime{};
    uint64_t generationTime = 0;
    uint64_t memoryUsage = 0;
    bool gpuAccelerated = false;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(segments, joints, legs, cockpit, weapons, sensorArray);
    }
};

// Centipede Mech Instance State
struct CentipedeMechInstanceState {
    std::string id;
    CentipedeMechParams params;
    CentipedeMechBundle bundle;

    // Runtime state
    std::vector<glm::vec3> segmentPositions;
    std::vector<glm::quat> segmentRotations;
    std::vector<glm::vec3> legPositions;
    std::vector<glm::quat> legRotations;
    std::vector<int> segmentLegCounts;   // legs currently mounted on each segment
    bool isActive = true;

    // Transform
    glm::vec3 position = glm::vec3(0.0f);
    glm::quat rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    glm::vec3 scale = glm::vec3(1.0f);

    // Physics
    glm::vec3 velocity = glm::vec3(0.0f);
    glm::vec3 angularVelocity = glm::vec3(0.0f);
    glm::vec3 acceleration = glm::vec3(0.0f);

    // Animation
    float animationTime = 0.0f;
    std::string currentAnimation = "idle";
    bool animationLooping = true;
    bool animationPaused = false;

    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate{};
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;

    uint64_t hashKey() const noexcept {
        return MechHash::hashFields(id, params.hashKey(), bundle.hashKey(), position, rotation);
    }
};

} // namespace Mechs
} // namespace MagiTech
