#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <array>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"
#include "vendor/yaml-cpp/yaml.h"

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
    ModuleType type;
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
    glm::vec3 canopyTint = {0.2f, 0.6f, 1.0f, 0.3f};
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
    AnimationType type;
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
    LODQuality quality;
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
    
    // Metadata
    QuadMechDefinition definition;
    uint64_t hashKey;
    
    uint64_t hashKey() const;
};

struct QuadMechInstance {
    QuadMechAsset* asset = nullptr;
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
    uint64_t fileHash;
    bool isValid = true;
    
    uint64_t hashKey() const;
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

template<typename T>
uint64_t hashCombine(uint64_t seed, const T& value) {
    return seed ^ (std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
}

// Hash function implementations
uint64_t ModuleDefinition::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(ModuleDefinition) - sizeof(std::string) * 4);
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, meshPath.c_str(), meshPath.length());
    XXH64_update(&s, attachBone.c_str(), attachBone.length());
    XXH64_update(&s, materialOverride.c_str(), materialOverride.length());
    return XXH64_digest(&s);
}

uint64_t CockpitDefinition::hashKey() const {
    return XXH64(this, sizeof(CockpitDefinition), 0);
}

uint64_t EnergyRunes::hashKey() const {
    return XXH64(this, sizeof(EnergyRunes), 0);
}

uint64_t EnergyCore::hashKey() const {
    return XXH64(this, sizeof(EnergyCore), 0);
}

uint64_t CanopyMaterial::hashKey() const {
    return XXH64(this, sizeof(CanopyMaterial), 0);
}

uint64_t MagitechMaterials::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    uint64_t hash = energyRunes.hashKey();
    hash = hashCombine(hash, energyCore.hashKey());
    hash = hashCombine(hash, canopy.hashKey());
    return hash;
}

uint64_t AnimationDefinition::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(AnimationDefinition) - sizeof(std::string) * 2);
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, path.c_str(), path.length());
    return XXH64_digest(&s);
}

uint64_t JointLimit::hashKey() const {
    return XXH64(this, sizeof(JointLimit), 0);
}

uint64_t PhysicsDefinition::hashKey() const {
    return XXH64(this, sizeof(PhysicsDefinition), 0);
}

uint64_t LODDefinition::hashKey() const {
    return XXH64(this, sizeof(LODDefinition), 0);
}

uint64_t QuadMechDefinition::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(QuadMechDefinition) - sizeof(std::vector<ModuleDefinition>) - sizeof(CockpitDefinition) - sizeof(MagitechMaterials) - sizeof(std::vector<AnimationDefinition>) - sizeof(PhysicsDefinition) - sizeof(std::vector<LODDefinition>) - sizeof(std::string) * 4);
    XXH64_update(&s, name.c_str(), name.length());
    XXH64_update(&s, version.c_str(), version.length());
    XXH64_update(&s, author.c_str(), author.length());
    XXH64_update(&s, description.c_str(), description.length());
    
    // Hash vectors
    for (const auto& module : modules) {
        XXH64_update(&s, &module.hashKey(), sizeof(uint64_t));
    }
    for (const auto& anim : animations) {
        XXH64_update(&s, &anim.hashKey(), sizeof(uint64_t));
    }
    for (const auto& lod : lods) {
        XXH64_update(&s, &lod.hashKey(), sizeof(uint64_t));
    }
    
    // Hash complex objects
    XXH64_update(&s, &cockpit.hashKey(), sizeof(uint64_t));
    XXH64_update(&s, &magitechMaterials.hashKey(), sizeof(uint64_t));
    XXH64_update(&s, &physics.hashKey(), sizeof(uint64_t));
    
    return XXH64_digest(&s);
}

uint64_t QuadMechAsset::hashKey() const {
    return definition.hashKey();
}

uint64_t QuadMechInstance::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(QuadMechInstance) - sizeof(QuadMechAsset*) - sizeof(std::string) - sizeof(std::vector<PhysicsBodyHandle>));
    XXH64_update(&s, currentAnimation.c_str(), currentAnimation.length());
    return XXH64_digest(&s);
}

uint64_t MechPackage::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(MechPackage) - sizeof(std::string) * 4 - sizeof(std::unordered_map<LODQuality, std::string>) * 2 - sizeof(std::unordered_map<std::string, std::string>));
    XXH64_update(&s, name.c_str(), name.length());
    XXH64_update(&s, version.c_str(), version.length());
    XXH64_update(&s, definitionPath.c_str(), definitionPath.length());
    XXH64_update(&s, skeletonPath.c_str(), skeletonPath.length());
    return XXH64_digest(&s);
}

uint64_t EditorState::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(EditorState) - sizeof(std::string) - sizeof(QuadMechDefinition));
    XXH64_update(&s, currentMechName.c_str(), currentMechName.length());
    return XXH64_digest(&s);
}

uint64_t CacheEntry::hashKey() const {
    return asset.hashKey();
}

} // namespace QuadMech
} // namespace MagiTech 
