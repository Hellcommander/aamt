#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <array>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <type_traits>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace QuadMech {

// Handle Types
using MeshHandle = uint32_t;
using MaterialHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using PhysicsBodyHandle = uint32_t;
using ModuleHandle = uint32_t;

// LOD Quality Levels
enum class LODQuality {
    HIGH = 0,
    MEDIUM = 1,
    LOW = 2,
    ULTRA_LOW = 3
};

// Module Types
enum class ModuleType {
    CHASSIS,
    LEG_FRONT_LEFT,
    LEG_FRONT_RIGHT,
    LEG_BACK_LEFT,
    LEG_BACK_RIGHT,
    HEAD,
    COCKPIT,
    WEAPON_LEFT,
    WEAPON_RIGHT,
    ENERGY_CORE
};

// Animation Types
enum class AnimationType {
    WALK,
    TROT,
    GALLOP,
    COCKPIT_OPEN,
    COCKPIT_CLOSE,
    PILOT_ENTRY,
    PILOT_EXIT,
    IDLE,
    ATTACK,
    DEFEND
};

// Physics Joint Types
enum class JointType {
    BALL,
    HINGE,
    PRISMATIC,
    FIXED
};

// ============================================================================
// MODULE DEFINITIONS
// ============================================================================

struct ModuleDefinition {
    std::string id;
    ModuleType type = ModuleType::CHASSIS;
    std::string meshPath;
    std::string attachBone;
    glm::vec3 offset = {0, 0, 0};
    glm::vec3 scale = {1, 1, 1};
    glm::vec3 rotation = {0, 0, 0};
    
    // Physics properties
    float mass = 100.0f;
    glm::vec3 inertia = {1, 1, 1};
    
    // Material overrides
    std::string materialOverride;
    
    uint64_t hashKey() const;
};

struct CockpitDefinition {
    glm::vec3 seatPosition = {0, 0.8f, 0};
    glm::vec4 canopyTint = {0.2f, 0.6f, 1.0f, 0.3f}; // RGBA
    std::string canopyMaterial = "canopy_mat";
    std::vector<glm::vec3> hudAnchorPoints;
    float transparency = 0.3f;
    bool enableHologram = true;
    
    uint64_t hashKey() const;
};

// ============================================================================
// MAGITECH MATERIALS
// ============================================================================

struct EnergyRunes {
    glm::vec3 emissiveColor = {0.1f, 0.6f, 1.0f};
    glm::vec2 glowIntensity = {0.5f, 2.0f}; // min, max
    float animationRate = 1.0f;
    float pulseFrequency = 2.0f;
    bool enableFlicker = true;
    float flickerIntensity = 0.3f;
    
    uint64_t hashKey() const;
};

struct EnergyCore {
    glm::vec3 coreColor = {0.8f, 0.2f, 0.1f};
    float energyLevel = 1.0f;
    float pulseRate = 3.0f;
    bool enableArcs = true;
    float arcIntensity = 0.7f;
    int arcCount = 4;
    
    uint64_t hashKey() const;
};

struct CanopyMaterial {
    glm::vec4 tint = {0.2f, 0.6f, 1.0f, 0.3f};
    float transparency = 0.3f;
    float reflectivity = 0.8f;
    bool enableScratches = true;
    float scratchDensity = 0.1f;
    
    uint64_t hashKey() const;
};

struct MagitechMaterials {
    EnergyRunes energyRunes;
    EnergyCore energyCore;
    CanopyMaterial canopy;
    
    uint64_t hashKey() const;
};

// ============================================================================
// ANIMATION DEFINITIONS
// ============================================================================

struct AnimationDefinition {
    std::string id;
    AnimationType type = AnimationType::IDLE;
    std::string path;
    float speed = 1.0f;
    bool loop = true;
    float blendTime = 0.2f;
    
    // Quadraped-specific parameters
    float gaitPhase = 0.0f; // For walk/trot/gallop
    float strideLength = 1.0f;
    float legLift = 0.3f;
    
    uint64_t hashKey() const;
};

// ============================================================================
// PHYSICS DEFINITIONS
// ============================================================================

struct JointLimit {
    glm::vec2 swing = {45.0f, 45.0f}; // min, max degrees
    glm::vec2 twist = {30.0f, 30.0f}; // min, max degrees
    float damping = 0.1f;
    float friction = 0.2f;
    
    uint64_t hashKey() const;
};

struct PhysicsDefinition {
    float totalMass = 1500.0f;
    std::unordered_map<std::string, float> moduleMass;
    std::unordered_map<std::string, JointLimit> jointLimits;
    bool enableCCD = true;
    float collisionMargin = 0.01f;
    
    uint64_t hashKey() const;
};

// ============================================================================
// LOD DEFINITIONS
// ============================================================================

struct LODDefinition {
    LODQuality quality = LODQuality::HIGH;
    float meshDecimate = 0.0f; // 0.0 = no decimation, 1.0 = max decimation
    float materialDetail = 1.0f; // 0.0 = simplified, 1.0 = full detail
    int maxBones = 100;
    bool enableMorphTargets = true;
    
    uint64_t hashKey() const;
};

// ============================================================================
// QUAD MECH DEFINITION
// ============================================================================

struct QuadMechDefinition {
    std::string name;
    std::string version = "1.0.0";
    
    // Module definitions
    std::vector<ModuleDefinition> modules;
    CockpitDefinition cockpit;
    
    // Magitech styling
    MagitechMaterials magitechMaterials;
    
    // Animations
    std::vector<AnimationDefinition> animations;
    
    // Physics
    PhysicsDefinition physics;
    
    // LODs
    std::vector<LODDefinition> lods;
    
    // Metadata
    std::string author;
    std::string description;
    std::vector<std::string> tags;
    
    uint64_t hashKey() const;
};

// ============================================================================
// RUNTIME ASSETS
// ============================================================================

struct ModuleEntry {
    std::array<MeshHandle, 4> lodMeshes = {0, 0, 0, 0}; // HIGH, MEDIUM, LOW, ULTRA_LOW
    std::array<MaterialHandle, 4> lodMaterials = {0, 0, 0, 0};
    PhysicsBodyHandle physicsBody = 0;
    glm::mat4 transform = glm::mat4(1.0f);
};

struct QuadMechAsset {
    std::unordered_map<std::string, ModuleEntry> modules;
    SkeletonHandle skeleton = 0;
    std::unordered_map<std::string, AnimationHandle> animations;
    PhysicsBodyHandle rootBody = 0;
    
    // Magitech effects
    MaterialHandle energyRunesMaterial = 0;
    MaterialHandle energyCoreMaterial = 0;
    MaterialHandle canopyMaterial = 0;
    
    // Metadata (the asset's cache/identity hash is definition.hashKey())
    QuadMechDefinition definition;
    
    uint64_t hashKey() const;
};

struct QuadMechInstance {
    std::string id; // assigned by QuadMechLoader (empty for unmanaged instances)
    // Shared with the factory cache so the instance stays valid after eviction.
    std::shared_ptr<const QuadMechAsset> asset;
    glm::mat4 transform = glm::mat4(1.0f);
    float currentAnimationTime = 0.0f;
    std::string currentAnimation = "idle";
    LODQuality currentLOD = LODQuality::HIGH;
    
    // Magitech runtime state
    float energyLevel = 1.0f;
    float runeGlowIntensity = 1.0f;
    bool cockpitOpen = false;
    bool pilotInside = false;
    
    // Physics state
    std::vector<PhysicsBodyHandle> physicsBodies;
    // Force/torque accumulated since the physics step last consumed them (world space).
    glm::vec3 accumulatedForce = {0, 0, 0};
    glm::vec3 accumulatedTorque = {0, 0, 0};
    
    uint64_t hashKey() const;
};

// ============================================================================
// PACKAGE STRUCTURE
// ============================================================================

struct MechPackage {
    std::string name;
    std::string version;
    
    // File paths within package
    std::string definitionPath;
    std::string skeletonPath;
    std::string physicsPath;
    std::string metadataPath;
    
    // LOD-specific paths
    std::unordered_map<LODQuality, std::string> meshPaths;
    std::unordered_map<LODQuality, std::string> materialPaths;
    std::unordered_map<std::string, std::string> animationPaths;
    
    uint64_t hashKey() const;
};

// ============================================================================
// EDITOR STATE
// ============================================================================

struct EditorState {
    std::string currentMechName;
    QuadMechDefinition currentDefinition;
    bool isDirty = false;
    float previewTime = 0.0f;
    LODQuality previewLOD = LODQuality::HIGH;
    
    // UI state
    bool showModulePanel = true;
    bool showMaterialPanel = true;
    bool showAnimationPanel = true;
    bool showPhysicsPanel = true;
    bool showLODPanel = true;
    
    uint64_t hashKey() const;
};

// ============================================================================
// CACHE & HOT-RELOAD
// ============================================================================

struct CacheEntry {
    QuadMechAsset asset;
    std::chrono::system_clock::time_point lastModified;
    uint64_t fileHash = 0;
    bool isValid = true;
    
    uint64_t hashKey() const;
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

template<typename T>
uint64_t hashCombine(uint64_t seed, const T& value) {
    return seed ^ (std::hash<T>{}(value) + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2));
}

// Field-by-field XXH64 accumulator. Hashing whole structs as raw memory would
// pick up padding bytes and the heap pointers inside std::string / containers,
// so every hashKey() below feeds its fields individually.
class QuadMechHasher {
public:
    QuadMechHasher() { XXH64_reset(&m_state, 0); }

    template<typename T>
    QuadMechHasher& add(const T& value) {
        static_assert(std::is_trivially_copyable_v<T>, "add() needs a trivially copyable type");
        if constexpr (std::is_same_v<T, bool>) {
            const uint8_t b = value ? 1 : 0;
            XXH64_update(&m_state, &b, sizeof(b));
        } else {
            XXH64_update(&m_state, &value, sizeof(T));
        }
        return *this;
    }

    QuadMechHasher& add(const std::string& s) {
        const uint64_t len = s.size();
        XXH64_update(&m_state, &len, sizeof(len)); // length prefix keeps "ab"+"c" != "a"+"bc"
        XXH64_update(&m_state, s.data(), s.size());
        return *this;
    }

    uint64_t digest() const { return XXH64_digest(&m_state); }

private:
    XXH64_state_t m_state;
};

// Sorted keys of an unordered map, for order-independent hashing.
template<typename Map>
std::vector<typename Map::key_type> sortedKeys(const Map& m) {
    std::vector<typename Map::key_type> keys;
    keys.reserve(m.size());
    for (const auto& [k, v] : m) keys.push_back(k);
    std::sort(keys.begin(), keys.end());
    return keys;
}

// Hash function implementations
inline uint64_t ModuleDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(id).add(type).add(meshPath).add(attachBone)
     .add(offset).add(scale).add(rotation)
     .add(mass).add(inertia).add(materialOverride);
    return h.digest();
}

inline uint64_t CockpitDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(seatPosition).add(canopyTint).add(canopyMaterial);
    h.add(static_cast<uint64_t>(hudAnchorPoints.size()));
    for (const auto& p : hudAnchorPoints) h.add(p);
    h.add(transparency).add(enableHologram);
    return h.digest();
}

inline uint64_t EnergyRunes::hashKey() const {
    QuadMechHasher h;
    h.add(emissiveColor).add(glowIntensity).add(animationRate)
     .add(pulseFrequency).add(enableFlicker).add(flickerIntensity);
    return h.digest();
}

inline uint64_t EnergyCore::hashKey() const {
    QuadMechHasher h;
    h.add(coreColor).add(energyLevel).add(pulseRate)
     .add(enableArcs).add(arcIntensity).add(arcCount);
    return h.digest();
}

inline uint64_t CanopyMaterial::hashKey() const {
    QuadMechHasher h;
    h.add(tint).add(transparency).add(reflectivity)
     .add(enableScratches).add(scratchDensity);
    return h.digest();
}

inline uint64_t MagitechMaterials::hashKey() const {
    uint64_t hash = energyRunes.hashKey();
    hash = hashCombine(hash, energyCore.hashKey());
    hash = hashCombine(hash, canopy.hashKey());
    return hash;
}

inline uint64_t AnimationDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(id).add(type).add(path)
     .add(speed).add(loop).add(blendTime)
     .add(gaitPhase).add(strideLength).add(legLift);
    return h.digest();
}

inline uint64_t JointLimit::hashKey() const {
    QuadMechHasher h;
    h.add(swing).add(twist).add(damping).add(friction);
    return h.digest();
}

inline uint64_t PhysicsDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(totalMass);
    for (const auto& k : sortedKeys(moduleMass)) h.add(k).add(moduleMass.at(k));
    for (const auto& k : sortedKeys(jointLimits)) h.add(k).add(jointLimits.at(k).hashKey());
    h.add(enableCCD).add(collisionMargin);
    return h.digest();
}

inline uint64_t LODDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(quality).add(meshDecimate).add(materialDetail)
     .add(maxBones).add(enableMorphTargets);
    return h.digest();
}

inline uint64_t QuadMechDefinition::hashKey() const {
    QuadMechHasher h;
    h.add(name).add(version).add(author).add(description);

    h.add(static_cast<uint64_t>(modules.size()));
    for (const auto& module : modules) h.add(module.hashKey());
    h.add(static_cast<uint64_t>(animations.size()));
    for (const auto& anim : animations) h.add(anim.hashKey());
    h.add(static_cast<uint64_t>(lods.size()));
    for (const auto& lod : lods) h.add(lod.hashKey());
    h.add(static_cast<uint64_t>(tags.size()));
    for (const auto& tag : tags) h.add(tag);

    h.add(cockpit.hashKey());
    h.add(magitechMaterials.hashKey());
    h.add(physics.hashKey());
    return h.digest();
}

inline uint64_t QuadMechAsset::hashKey() const {
    return definition.hashKey();
}

inline uint64_t QuadMechInstance::hashKey() const {
    QuadMechHasher h;
    h.add(transform).add(currentAnimationTime).add(currentAnimation).add(currentLOD)
     .add(energyLevel).add(runeGlowIntensity).add(cockpitOpen).add(pilotInside);
    return h.digest();
}

inline uint64_t MechPackage::hashKey() const {
    QuadMechHasher h;
    h.add(name).add(version).add(definitionPath).add(skeletonPath)
     .add(physicsPath).add(metadataPath);
    for (const auto& q : sortedKeys(meshPaths)) h.add(q).add(meshPaths.at(q));
    for (const auto& q : sortedKeys(materialPaths)) h.add(q).add(materialPaths.at(q));
    for (const auto& k : sortedKeys(animationPaths)) h.add(k).add(animationPaths.at(k));
    return h.digest();
}

inline uint64_t EditorState::hashKey() const {
    QuadMechHasher h;
    h.add(currentMechName).add(currentDefinition.hashKey())
     .add(isDirty).add(previewTime).add(previewLOD)
     .add(showModulePanel).add(showMaterialPanel).add(showAnimationPanel)
     .add(showPhysicsPanel).add(showLODPanel);
    return h.digest();
}

inline uint64_t CacheEntry::hashKey() const {
    return asset.hashKey();
}

} // namespace QuadMech
} // namespace MagiTech
