#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <chrono>
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

// Enhanced MechParams with hybrid C++23/26 + Lua features
struct MechParams {
    std::string   id, style, pattern;
    std::vector<std::string> forms, weaponMounts;
    glm::vec3     colorPrimary, colorAccent;
    int           limbCount, detailLevel;
    glm::vec3     torsoSize;
    float         limbLength;
    bool          armorPlates, pulseEmission;
    
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
    
    // Performance tracking
    std::chrono::system_clock::time_point creationTime;
    std::atomic<uint64_t> generationTime{0};
    std::atomic<uint64_t> memoryUsage{0};

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, style.c_str(), style.length());
        XXH64_update(&hash_state, pattern.c_str(), pattern.length());
        XXH64_update(&hash_state, variant.c_str(), variant.length());
        for(const auto& f : forms) XXH64_update(&hash_state, f.c_str(), f.length());
        for(const auto& wm : weaponMounts) XXH64_update(&hash_state, wm.c_str(), wm.length());
        for(const auto& at : armorTypes) XXH64_update(&hash_state, at.c_str(), at.length());
        for(const auto& wt : weaponTypes) XXH64_update(&hash_state, wt.c_str(), wt.length());
        for(const auto& ab : abilities) XXH64_update(&hash_state, ab.c_str(), ab.length());
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorAccent, sizeof(colorAccent));
        XXH64_update(&hash_state, &limbCount, sizeof(limbCount));
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        XXH64_update(&hash_state, &torsoSize, sizeof(torsoSize));
        XXH64_update(&hash_state, &limbLength, sizeof(limbLength));
        XXH64_update(&hash_state, &armorPlates, sizeof(armorPlates));
        XXH64_update(&hash_state, &pulseEmission, sizeof(pulseEmission));
        XXH64_update(&hash_state, &scale, sizeof(scale));
        XXH64_update(&hash_state, &mass, sizeof(mass));
        XXH64_update(&hash_state, &enableGlow, sizeof(enableGlow));
        XXH64_update(&hash_state, &enableShield, sizeof(enableShield));
        XXH64_update(&hash_state, &crewCapacity, sizeof(crewCapacity));
        XXH64_update(&hash_state, &maxSpeed, sizeof(maxSpeed));
        XXH64_update(&hash_state, &jumpHeight, sizeof(jumpHeight));
        XXH64_update(&hash_state, &canFly, sizeof(canFly));
        XXH64_update(&hash_state, &canSwim, sizeof(canSwim));
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &patternIntensity, sizeof(patternIntensity));
        XXH64_update(&hash_state, &textureResolution, sizeof(textureResolution));
        XXH64_update(&hash_state, &morphDuration, sizeof(morphDuration));
        return XXH64_digest(&hash_state);
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
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, mechType.c_str(), mechType.length());
        XXH64_update(&hash_state, &segmentCount, sizeof(segmentCount));
        XXH64_update(&hash_state, &segmentLength, sizeof(segmentLength));
        XXH64_update(&hash_state, &segmentRadius, sizeof(segmentRadius));
        XXH64_update(&hash_state, &connectorGap, sizeof(connectorGap));
        XXH64_update(&hash_state, &maxBendAngleDeg, sizeof(maxBendAngleDeg));
        XXH64_update(&hash_state, &bendStiffness, sizeof(bendStiffness));
        XXH64_update(&hash_state, &jointFlexibility, sizeof(jointFlexibility));
        XXH64_update(&hash_state, &enablePlating, sizeof(enablePlating));
        XXH64_update(&hash_state, &platesPerSegment, sizeof(platesPerSegment));
        XXH64_update(&hash_state, &plateThickness, sizeof(plateThickness));
        XXH64_update(&hash_state, &platingColor, sizeof(platingColor));
        XXH64_update(&hash_state, &platingDetailLevel, sizeof(platingDetailLevel));
        XXH64_update(&hash_state, &stripeCount, sizeof(stripeCount));
        XXH64_update(&hash_state, &stripeWidth, sizeof(stripeWidth));
        XXH64_update(&hash_state, &stripeColor, sizeof(stripeColor));
        XXH64_update(&hash_state, &stripeGlowIntensity, sizeof(stripeGlowIntensity));
        XXH64_update(&hash_state, &enableJointSparks, sizeof(enableJointSparks));
        XXH64_update(&hash_state, &sparkRate, sizeof(sparkRate));
        XXH64_update(&hash_state, &sparkLifetime, sizeof(sparkLifetime));
        XXH64_update(&hash_state, &sparkColor, sizeof(sparkColor));
        XXH64_update(&hash_state, &segmentMass, sizeof(segmentMass));
        XXH64_update(&hash_state, &jointDamping, sizeof(jointDamping));
        XXH64_update(&hash_state, &waveAmplitude, sizeof(waveAmplitude));
        XXH64_update(&hash_state, &waveFrequency, sizeof(waveFrequency));
        XXH64_update(&hash_state, animationProfile.c_str(), animationProfile.length());
        XXH64_update(&hash_state, cockpitType.c_str(), cockpitType.length());
        XXH64_update(&hash_state, &cockpitSegmentIndex, sizeof(cockpitSegmentIndex));
        XXH64_update(&hash_state, &cockpitRadius, sizeof(cockpitRadius));
        XXH64_update(&hash_state, &cockpitOrientation, sizeof(cockpitOrientation));
        XXH64_update(&hash_state, taperProfile.c_str(), taperProfile.length());
        XXH64_update(&hash_state, segmentShape.c_str(), segmentShape.length());
        XXH64_update(&hash_state, &noiseDetail, sizeof(noiseDetail));
        XXH64_update(&hash_state, &textureScale, sizeof(textureScale));
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorSecondary, sizeof(colorSecondary));
        XXH64_update(&hash_state, aiProfile.c_str(), aiProfile.length());
        XXH64_update(&hash_state, &rebuildOnLOD, sizeof(rebuildOnLOD));
        XXH64_update(&hash_state, &lodCount, sizeof(lodCount));
        return XXH64_digest(&hash_state);
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
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &seatWidth, sizeof(seatWidth));
        XXH64_update(&hash_state, &seatDepth, sizeof(seatDepth));
        XXH64_update(&hash_state, &seatHeight, sizeof(seatHeight));
        XXH64_update(&hash_state, &seatFabricColor, sizeof(seatFabricColor));
        XXH64_update(&hash_state, &headrestEnabled, sizeof(headrestEnabled));
        XXH64_update(&hash_state, &canopyRadius, sizeof(canopyRadius));
        XXH64_update(&hash_state, &canopyHeight, sizeof(canopyHeight));
        XXH64_update(&hash_state, &glassThickness, sizeof(glassThickness));
        XXH64_update(&hash_state, &glassTint, sizeof(glassTint));
        XXH64_update(&hash_state, &reflectivity, sizeof(reflectivity));
        XXH64_update(&hash_state, &displayCount, sizeof(displayCount));
        XXH64_update(&hash_state, &displayResolution, sizeof(displayResolution));
        XXH64_update(&hash_state, &stickOffsetX, sizeof(stickOffsetX));
        XXH64_update(&hash_state, &stickOffsetY, sizeof(stickOffsetY));
        XXH64_update(&hash_state, &throttleLever, sizeof(throttleLever));
        XXH64_update(&hash_state, &pedalControls, sizeof(pedalControls));
        XXH64_update(&hash_state, &gaugeCount, sizeof(gaugeCount));
        XXH64_update(&hash_state, &gaugeRadius, sizeof(gaugeRadius));
        XXH64_update(&hash_state, &gaugeNeedleColor, sizeof(gaugeNeedleColor));
        XXH64_update(&hash_state, &holographicHUD, sizeof(holographicHUD));
        XXH64_update(&hash_state, &cockpitLight, sizeof(cockpitLight));
        XXH64_update(&hash_state, &lightColor, sizeof(lightColor));
        XXH64_update(&hash_state, &lightIntensity, sizeof(lightIntensity));
        XXH64_update(&hash_state, &canopyAnimEnabled, sizeof(canopyAnimEnabled));
        XXH64_update(&hash_state, &canopyOpenAngleDeg, sizeof(canopyOpenAngleDeg));
        XXH64_update(&hash_state, &canopyOpenDuration, sizeof(canopyOpenDuration));
        XXH64_update(&hash_state, &mountOffset, sizeof(mountOffset));
        XXH64_update(&hash_state, &mountRotation, sizeof(mountRotation));
        return XXH64_digest(&hash_state);
    }
};

// UI Parameters
struct UIParams {
    int iconSize = 64;
    glm::vec4 borderColor = {1.0f, 1.0f, 1.0f, 0.9f};
    std::string backgroundShape = "hexagon";
    bool flashOnSelect = true;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &iconSize, sizeof(iconSize));
        XXH64_update(&hash_state, &borderColor, sizeof(borderColor));
        XXH64_update(&hash_state, backgroundShape.c_str(), backgroundShape.length());
        XXH64_update(&hash_state, &flashOnSelect, sizeof(flashOnSelect));
        return XXH64_digest(&hash_state);
    }
};

// Enhanced MechBundle with additional assets
struct MechBundle {
    MeshHandle    mesh;
    TextureHandle tex;
    SkeletonHandle skeleton;
    AnimationHandle animation;
    MaterialHandle material;
    
    // Additional assets for enhanced pipeline
    TextureHandle normalMap;
    TextureHandle roughnessMap;
    TextureHandle metallicMap;
    TextureHandle emissiveMap;
    
    // Physics data
    std::vector<glm::vec3> collisionVertices;
    std::vector<uint32_t> collisionIndices;
    glm::vec3 centerOfMass;
    float mass;
    
    // Animation data
    std::vector<std::string> animationClips;
    std::unordered_map<std::string, float> morphWeights;
    
    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime;
    uint64_t memoryUsage;
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &mesh, sizeof(mesh));
        XXH64_update(&hash_state, &tex, sizeof(tex));
        XXH64_update(&hash_state, &skeleton, sizeof(skeleton));
        XXH64_update(&hash_state, &animation, sizeof(animation));
        XXH64_update(&hash_state, &material, sizeof(material));
        XXH64_update(&hash_state, &normalMap, sizeof(normalMap));
        XXH64_update(&hash_state, &roughnessMap, sizeof(roughnessMap));
        XXH64_update(&hash_state, &metallicMap, sizeof(metallicMap));
        XXH64_update(&hash_state, &emissiveMap, sizeof(emissiveMap));
        XXH64_update(&hash_state, &mass, sizeof(mass));
        return XXH64_digest(&hash_state);
    }
};

// Segmented Mech Asset Bundle
struct SegmentedMechBundle {
    MeshHandle segmentMesh;
    SkeletonHandle skeleton;
    AnimationHandle proceduralAnimation;
    MaterialHandle materialShader;
    ParticleHandle sparkParticles;
    PhysicsHandle physicsAsset;
    
    // Cockpit integration
    MeshHandle cockpitMesh;
    TextureHandle cockpitTexture;
    MaterialHandle cockpitMaterial;
    
    // UI elements
    TextureHandle icon;
    
    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime;
    uint64_t memoryUsage;
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &segmentMesh, sizeof(segmentMesh));
        XXH64_update(&hash_state, &skeleton, sizeof(skeleton));
        XXH64_update(&hash_state, &proceduralAnimation, sizeof(proceduralAnimation));
        XXH64_update(&hash_state, &materialShader, sizeof(materialShader));
        XXH64_update(&hash_state, &sparkParticles, sizeof(sparkParticles));
        XXH64_update(&hash_state, &physicsAsset, sizeof(physicsAsset));
        XXH64_update(&hash_state, &cockpitMesh, sizeof(cockpitMesh));
        XXH64_update(&hash_state, &cockpitTexture, sizeof(cockpitTexture));
        XXH64_update(&hash_state, &cockpitMaterial, sizeof(cockpitMaterial));
        XXH64_update(&hash_state, &icon, sizeof(icon));
        return XXH64_digest(&hash_state);
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
    std::chrono::system_clock::time_point lastUpdate;
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &params.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &bundle.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &position, sizeof(position));
        XXH64_update(&hash_state, &rotation, sizeof(rotation));
        return XXH64_digest(&hash_state);
    }
};

// Segmented Mech Instance State
struct SegmentedMechInstanceState {
    std::string id;
    SegmentedMechParams params;
    SegmentedMechBundle bundle;
    CockpitParams cockpitParams;
    
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
    
    // Performance tracking
    std::chrono::system_clock::time_point lastUpdate;
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &params.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &bundle.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &cockpitParams.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &position, sizeof(position));
        XXH64_update(&hash_state, &rotation, sizeof(rotation));
        return XXH64_digest(&hash_state);
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
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, patternType.c_str(), patternType.length());
        XXH64_update(&hash_state, &frequency, sizeof(frequency));
        XXH64_update(&hash_state, &amplitude, sizeof(amplitude));
        XXH64_update(&hash_state, &octaves, sizeof(octaves));
        XXH64_update(&hash_state, &persistence, sizeof(persistence));
        XXH64_update(&hash_state, &lacunarity, sizeof(lacunarity));
        XXH64_update(&hash_state, &patternScale, sizeof(patternScale));
        XXH64_update(&hash_state, &patternRotation, sizeof(patternRotation));
        XXH64_update(&hash_state, &patternColor, sizeof(patternColor));
        XXH64_update(&hash_state, &roughness, sizeof(roughness));
        XXH64_update(&hash_state, &metallic, sizeof(metallic));
        XXH64_update(&hash_state, &emissive, sizeof(emissive));
        XXH64_update(&hash_state, &normalStrength, sizeof(normalStrength));
        return XXH64_digest(&hash_state);
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
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &segmentCount, sizeof(segmentCount));
        XXH64_update(&hash_state, &segmentLength, sizeof(segmentLength));
        XXH64_update(&hash_state, &segmentRadius, sizeof(segmentRadius));
        XXH64_update(&hash_state, &baseColor, sizeof(baseColor));
        XXH64_update(&hash_state, &seamlessJoints, sizeof(seamlessJoints));
        XXH64_update(&hash_state, &legsPerSegment, sizeof(legsPerSegment));
        XXH64_update(&hash_state, &upperLegLength, sizeof(upperLegLength));
        XXH64_update(&hash_state, &lowerLegLength, sizeof(lowerLegLength));
        XXH64_update(&hash_state, &jointRadius, sizeof(jointRadius));
        XXH64_update(&hash_state, &armorPlates, sizeof(armorPlates));
        XXH64_update(&hash_state, footType.c_str(), footType.length());
        XXH64_update(&hash_state, &hasCockpit, sizeof(hasCockpit));
        XXH64_update(&hash_state, &cockpitPosition, sizeof(cockpitPosition));
        XXH64_update(&hash_state, &cockpitWidth, sizeof(cockpitWidth));
        XXH64_update(&hash_state, &cockpitHeight, sizeof(cockpitHeight));
        XXH64_update(&hash_state, &cockpitDepth, sizeof(cockpitDepth));
        XXH64_update(&hash_state, &enableDisplays, sizeof(enableDisplays));
        XXH64_update(&hash_state, &displayCount, sizeof(displayCount));
        XXH64_update(&hash_state, seatMaterial.c_str(), seatMaterial.length());
        XXH64_update(&hash_state, controlStyle.c_str(), controlStyle.length());
        XXH64_update(&hash_state, &missileTubes, sizeof(missileTubes));
        XXH64_update(&hash_state, &autocannonSlots, sizeof(autocannonSlots));
        XXH64_update(&hash_state, &enableTurret, sizeof(enableTurret));
        XXH64_update(&hash_state, &enableRadarArray, sizeof(enableRadarArray));
        XXH64_update(&hash_state, &radarRange, sizeof(radarRange));
        return XXH64_digest(&hash_state);
    }
};

// Centipede Mech Asset Bundle
struct CentipedeMechBundle {
    std::vector<MeshHandle> segments;
    std::vector<MeshHandle> joints;
    std::vector<MeshHandle> legs;
    MeshHandle cockpit;
    std::vector<MeshHandle> weapons;
    MeshHandle sensorArray;
    std::vector<MaterialHandle> materials;
    std::vector<ParticleHandle> vfx;
    std::vector<AudioHandle> audio;
    PhysicsHandle collider;
    
    // Performance data
    std::chrono::system_clock::time_point creationTime;
    uint64_t generationTime;
    uint64_t memoryUsage;
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        for (const auto& segment : segments) {
            XXH64_update(&hash_state, &segment, sizeof(segment));
        }
        for (const auto& joint : joints) {
            XXH64_update(&hash_state, &joint, sizeof(joint));
        }
        for (const auto& leg : legs) {
            XXH64_update(&hash_state, &leg, sizeof(leg));
        }
        XXH64_update(&hash_state, &cockpit, sizeof(cockpit));
        for (const auto& weapon : weapons) {
            XXH64_update(&hash_state, &weapon, sizeof(weapon));
        }
        XXH64_update(&hash_state, &sensorArray, sizeof(sensorArray));
        return XXH64_digest(&hash_state);
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
    std::chrono::system_clock::time_point lastUpdate;
    uint64_t frameCount = 0;
    float averageFrameTime = 0.0f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &params.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &bundle.hashKey(), sizeof(uint64_t));
        XXH64_update(&hash_state, &position, sizeof(position));
        XXH64_update(&hash_state, &rotation, sizeof(rotation));
        return XXH64_digest(&hash_state);
    }
};

} // namespace Mechs
} // namespace MagiTech
