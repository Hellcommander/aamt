#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <memory>
#include <atomic>
#include <chrono>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace MechAssets {

// GPU Handle Types for OpenStarbound Integration
using MechHandle = uint32_t;
using ModuleHandle = uint32_t;
using SkeletonHandle = uint32_t;
using MorphTargetHandle = uint32_t;
using PhysicsRigHandle = uint32_t;
using MechPackHandle = uint32_t;

// Mech Module Types
enum class ModuleType {
    CHASSIS, ARM, LEG, WEAPON, SHIELD, THRUSTER, SENSOR, COCKPIT, UTILITY
};

// Form Types
enum class FormType {
    WALKER, FLYER, TANK, SWIMMER, CLIMBER, STEALTH, COMBAT, UTILITY
};

// Morph Curve Types
enum class MorphCurveType {
    LINEAR, EASE_IN, EASE_OUT, EASE_IN_OUT, SMOOTHSTEP, CUSTOM
};

// LOD Quality Levels
enum class LODQuality {
    ULTRA_HIGH, HIGH, MEDIUM, LOW, ULTRA_LOW
};

// Physics Collider Types
enum class ColliderType {
    CAPSULE, BOX, SPHERE, CONVEX_HULL, MESH
};

// Joint Constraint Types
enum class JointType {
    HINGE, BALL, PRISMATIC, FIXED, SPRING
};

// Module Definition
struct ModuleDefinition {
    std::string id;
    ModuleType type;
    std::string meshPath;
    std::string attachBone;
    glm::vec3 attachOffset = glm::vec3(0.0f);
    glm::vec3 attachRotation = glm::vec3(0.0f);
    float mass = 100.0f;
    bool weldToParent = true;
    std::vector<std::string> childModules;
    
    // Physics properties
    ColliderType colliderType = ColliderType::CAPSULE;
    glm::vec3 colliderSize = glm::vec3(1.0f);
    bool generateCollision = true;
    
    // LOD settings
    bool enableLOD = true;
    std::vector<float> lodScreenSizes = {0.1f, 0.05f, 0.02f, 0.01f};
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ModuleDefinition) - (4*sizeof(std::string)) - sizeof(std::vector<std::string>) - sizeof(std::vector<float>));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, meshPath.c_str(), meshPath.length());
        XXH64_update(&hash_state, attachBone.c_str(), attachBone.length());
        for(const auto& child : childModules) {
            XXH64_update(&hash_state, child.c_str(), child.length());
        }
        XXH64_update(&hash_state, lodScreenSizes.data(), lodScreenSizes.size() * sizeof(float));
        return XXH64_digest(&hash_state);
    }
};

// Morph Profile Definition
struct MorphProfile {
    std::string name;
    FormType fromForm;
    FormType toForm;
    float duration = 1.0f;
    MorphCurveType curveType = MorphCurveType::EASE_IN_OUT;
    std::vector<float> customCurve; // For custom curve interpolation
    
    // Module-specific morph settings
    std::unordered_map<std::string, glm::vec3> moduleTransforms;
    std::unordered_map<std::string, glm::vec3> moduleScales;
    std::unordered_map<std::string, float> moduleOpacities;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MorphProfile) - (2*sizeof(std::string)) - sizeof(std::vector<float>) - (3*sizeof(std::unordered_map<std::string, glm::vec3>)) - sizeof(std::unordered_map<std::string, float>));
        XXH64_update(&hash_state, name.c_str(), name.length());
        for(const auto& transform : moduleTransforms) {
            XXH64_update(&hash_state, transform.first.c_str(), transform.first.length());
            XXH64_update(&hash_state, &transform.second, sizeof(glm::vec3));
        }
        for(const auto& scale : moduleScales) {
            XXH64_update(&hash_state, scale.first.c_str(), scale.first.length());
            XXH64_update(&hash_state, &scale.second, sizeof(glm::vec3));
        }
        for(const auto& opacity : moduleOpacities) {
            XXH64_update(&hash_state, opacity.first.c_str(), opacity.first.length());
            XXH64_update(&hash_state, &opacity.second, sizeof(float));
        }
        XXH64_update(&hash_state, customCurve.data(), customCurve.size() * sizeof(float));
        return XXH64_digest(&hash_state);
    }
};

// Joint Constraint Definition
struct JointConstraint {
    std::string jointName;
    JointType type;
    glm::vec3 axis = glm::vec3(0.0f, 1.0f, 0.0f);
    glm::vec2 limits = glm::vec2(-180.0f, 180.0f); // min, max angles
    float stiffness = 1000.0f;
    float damping = 100.0f;
    bool enableMotor = false;
    float motorTargetVelocity = 0.0f;
    float motorMaxForce = 1000.0f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(JointConstraint) - sizeof(std::string));
        XXH64_update(&hash_state, jointName.c_str(), jointName.length());
        return XXH64_digest(&hash_state);
    }
};

// Physics Rig Definition
struct PhysicsRigDefinition {
    float totalMass = 1000.0f;
    std::unordered_map<std::string, float> moduleMasses;
    std::vector<JointConstraint> joints;
    glm::vec3 centerOfMass = glm::vec3(0.0f);
    bool enableGravity = true;
    bool enableCollision = true;
    float linearDamping = 0.1f;
    float angularDamping = 0.1f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(PhysicsRigDefinition) - sizeof(std::unordered_map<std::string, float>) - sizeof(std::vector<JointConstraint>));
        for(const auto& mass : moduleMasses) {
            XXH64_update(&hash_state, mass.first.c_str(), mass.first.length());
            XXH64_update(&hash_state, &mass.second, sizeof(float));
        }
        for(const auto& joint : joints) {
            XXH64_update(&hash_state, &joint, sizeof(JointConstraint));
        }
        return XXH64_digest(&hash_state);
    }
};

// LOD Definition
struct LODDefinition {
    LODQuality quality;
    float screenSize;
    float meshDecimateRatio = 0.0f;
    float morphDetailRatio = 1.0f;
    bool preserveBorders = true;
    bool preserveUVSeams = true;
    int maxTriangles = 10000;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(LODDefinition));
        return XXH64_digest(&hash_state);
    }
};

// Mech Definition Parameters
struct MechDefinitionParams {
    std::string name;
    std::string description;
    std::vector<ModuleDefinition> modules;
    std::vector<MorphProfile> morphProfiles;
    PhysicsRigDefinition physicsRig;
    std::vector<LODDefinition> lods;
    std::string skeletonTemplate;
    bool enableGPUAcceleration = true;
    bool enableHotReload = true;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MechDefinitionParams) - (3*sizeof(std::string)) - (3*sizeof(std::vector<ModuleDefinition>)) - sizeof(std::vector<MorphProfile>) - sizeof(PhysicsRigDefinition) - sizeof(std::vector<LODDefinition>));
        XXH64_update(&hash_state, name.c_str(), name.length());
        XXH64_update(&hash_state, description.c_str(), description.length());
        XXH64_update(&hash_state, skeletonTemplate.c_str(), skeletonTemplate.length());
        
        for(const auto& module : modules) {
            XXH64_update(&hash_state, &module.hashKey(), sizeof(uint64_t));
        }
        for(const auto& profile : morphProfiles) {
            XXH64_update(&hash_state, &profile.hashKey(), sizeof(uint64_t));
        }
        XXH64_update(&hash_state, &physicsRig.hashKey(), sizeof(uint64_t));
        for(const auto& lod : lods) {
            XXH64_update(&hash_state, &lod.hashKey(), sizeof(uint64_t));
        }
        return XXH64_digest(&hash_state);
    }
};

// Module Data Structure
struct ModuleData {
    ModuleHandle handle;
    std::string id;
    ModuleType type;
    std::vector<MeshHandle> lodMeshes;
    std::vector<MorphTargetHandle> morphTargets;
    PhysicsRigHandle physicsBody;
    glm::mat4 localTransform;
    glm::mat4 worldTransform;
    bool isVisible = true;
    bool isActive = true;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ModuleData) - sizeof(std::string) - sizeof(std::vector<MeshHandle>) - sizeof(std::vector<MorphTargetHandle>));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, lodMeshes.data(), lodMeshes.size() * sizeof(MeshHandle));
        XXH64_update(&hash_state, morphTargets.data(), morphTargets.size() * sizeof(MorphTargetHandle));
        return XXH64_digest(&hash_state);
    }
};

// Mech Asset Structure
struct MechAsset {
    MechHandle handle;
    std::string name;
    SkeletonHandle skeleton;
    std::vector<ModuleData> modules;
    std::vector<MorphProfile> morphProfiles;
    PhysicsRigHandle physicsRig;
    std::vector<LODDefinition> lods;
    MechPackHandle packHandle;
    
    // Performance tracking
    std::chrono::system_clock::time_point creationTime;
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    bool gpuAccelerated = false;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MechAsset) - (2*sizeof(std::string)) - sizeof(std::vector<ModuleData>) - sizeof(std::vector<MorphProfile>) - sizeof(std::vector<LODDefinition>) - sizeof(std::chrono::system_clock::time_point) - (2*sizeof(std::atomic<uint64_t>)) - sizeof(bool));
        XXH64_update(&hash_state, name.c_str(), name.length());
        for(const auto& module : modules) {
            XXH64_update(&hash_state, &module.hashKey(), sizeof(uint64_t));
        }
        for(const auto& profile : morphProfiles) {
            XXH64_update(&hash_state, &profile.hashKey(), sizeof(uint64_t));
        }
        for(const auto& lod : lods) {
            XXH64_update(&hash_state, &lod.hashKey(), sizeof(uint64_t));
        }
        return XXH64_digest(&hash_state);
    }
};

// Mech Instance State
struct MechInstanceState {
    FormType currentForm = FormType::WALKER;
    FormType targetForm = FormType::WALKER;
    float morphProgress = 0.0f;
    float morphDuration = 1.0f;
    bool isMorphing = false;
    bool isActive = true;
    glm::vec3 position = glm::vec3(0.0f);
    glm::quat rotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    glm::vec3 velocity = glm::vec3(0.0f);
    glm::vec3 angularVelocity = glm::vec3(0.0f);
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MechInstanceState));
        return XXH64_digest(&hash_state);
    }
};

// Performance Metrics
struct MechPerformanceMetrics {
    std::atomic<uint64_t> totalInstances{0};
    std::atomic<uint64_t> activeInstances{0};
    std::atomic<uint64_t> morphingInstances{0};
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> totalProcessingTime{0};
    std::atomic<uint64_t> peakMemoryUsage{0};
    std::atomic<uint64_t> gpuMemoryUsage{0};
    
    void reset() {
        totalInstances = 0;
        activeInstances = 0;
        morphingInstances = 0;
        cacheHits = 0;
        cacheMisses = 0;
        totalProcessingTime = 0;
        peakMemoryUsage = 0;
        gpuMemoryUsage = 0;
    }
    
    double getCacheHitRate() const {
        uint64_t total = cacheHits.load() + cacheMisses.load();
        return total > 0 ? static_cast<double>(cacheHits.load()) / total : 0.0;
    }
    
    double getAverageProcessingTime() const {
        uint64_t instances = totalInstances.load();
        return instances > 0 ? static_cast<double>(totalProcessingTime.load()) / instances : 0.0;
    }
};

// Mech Pack Header (64 bytes)
struct MechPackHeader {
    uint32_t magic = 0x4D454348; // "MECH"
    uint32_t version = 1;
    uint32_t moduleCount;
    uint32_t morphProfileCount;
    uint32_t lodCount;
    uint32_t reserved[11];
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MechPackHeader));
        return XXH64_digest(&hash_state);
    }
};

} // namespace MechAssets
} // namespace MagiTech 
