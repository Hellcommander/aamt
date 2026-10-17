#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <memory>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace MechAssets {

// Field-wise hashing helpers (structs contain strings/containers, so they must
// never be hashed as raw memory).
namespace HashDetail {
    template <typename T>
    inline void pod(XXH64_state_t& s, const T& v) noexcept { XXH64_update(&s, &v, sizeof(T)); }
    inline void str(XXH64_state_t& s, const std::string& v) noexcept {
        const uint64_t n = v.size();
        XXH64_update(&s, &n, sizeof(n));
        XXH64_update(&s, v.data(), v.size());
    }
    template <typename T>
    inline void vec(XXH64_state_t& s, const std::vector<T>& v) noexcept {
        const uint64_t n = v.size();
        XXH64_update(&s, &n, sizeof(n));
        if (!v.empty()) XXH64_update(&s, v.data(), v.size() * sizeof(T));
    }
    // Hash an unordered map independently of its iteration order.
    template <typename V>
    inline void map(XXH64_state_t& s, const std::unordered_map<std::string, V>& m) noexcept {
        uint64_t combined = 0;
        for (const auto& [k, val] : m) {
            XXH64_state_t e;
            XXH64_reset(&e, 0);
            str(e, k);
            pod(e, val);
            combined ^= XXH64_digest(&e);
        }
        const uint64_t n = m.size();
        pod(s, n);
        pod(s, combined);
    }
}

// GPU Handle Types for OpenStarbound Integration
using MeshHandle = uint32_t;
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
        HashDetail::str(hash_state, id);
        HashDetail::pod(hash_state, type);
        HashDetail::str(hash_state, meshPath);
        HashDetail::str(hash_state, attachBone);
        HashDetail::pod(hash_state, attachOffset);
        HashDetail::pod(hash_state, attachRotation);
        HashDetail::pod(hash_state, mass);
        HashDetail::pod(hash_state, weldToParent);
        for(const auto& child : childModules) {
            HashDetail::str(hash_state, child);
        }
        HashDetail::pod(hash_state, colliderType);
        HashDetail::pod(hash_state, colliderSize);
        HashDetail::pod(hash_state, generateCollision);
        HashDetail::pod(hash_state, enableLOD);
        HashDetail::vec(hash_state, lodScreenSizes);
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
        HashDetail::str(hash_state, name);
        HashDetail::pod(hash_state, fromForm);
        HashDetail::pod(hash_state, toForm);
        HashDetail::pod(hash_state, duration);
        HashDetail::pod(hash_state, curveType);
        HashDetail::vec(hash_state, customCurve);
        HashDetail::map(hash_state, moduleTransforms);
        HashDetail::map(hash_state, moduleScales);
        HashDetail::map(hash_state, moduleOpacities);
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
        HashDetail::str(hash_state, jointName);
        HashDetail::pod(hash_state, type);
        HashDetail::pod(hash_state, axis);
        HashDetail::pod(hash_state, limits);
        HashDetail::pod(hash_state, stiffness);
        HashDetail::pod(hash_state, damping);
        HashDetail::pod(hash_state, enableMotor);
        HashDetail::pod(hash_state, motorTargetVelocity);
        HashDetail::pod(hash_state, motorMaxForce);
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
        HashDetail::pod(hash_state, totalMass);
        HashDetail::map(hash_state, moduleMasses);
        for(const auto& joint : joints) {
            HashDetail::pod(hash_state, joint.hashKey());
        }
        HashDetail::pod(hash_state, centerOfMass);
        HashDetail::pod(hash_state, enableGravity);
        HashDetail::pod(hash_state, enableCollision);
        HashDetail::pod(hash_state, linearDamping);
        HashDetail::pod(hash_state, angularDamping);
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
        HashDetail::pod(hash_state, quality);
        HashDetail::pod(hash_state, screenSize);
        HashDetail::pod(hash_state, meshDecimateRatio);
        HashDetail::pod(hash_state, morphDetailRatio);
        HashDetail::pod(hash_state, preserveBorders);
        HashDetail::pod(hash_state, preserveUVSeams);
        HashDetail::pod(hash_state, maxTriangles);
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
        HashDetail::str(hash_state, name);
        HashDetail::str(hash_state, description);
        HashDetail::str(hash_state, skeletonTemplate);
        HashDetail::pod(hash_state, enableGPUAcceleration);
        HashDetail::pod(hash_state, enableHotReload);

        for(const auto& module : modules) {
            HashDetail::pod(hash_state, module.hashKey());
        }
        for(const auto& profile : morphProfiles) {
            HashDetail::pod(hash_state, profile.hashKey());
        }
        HashDetail::pod(hash_state, physicsRig.hashKey());
        for(const auto& lod : lods) {
            HashDetail::pod(hash_state, lod.hashKey());
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
        HashDetail::pod(hash_state, handle);
        HashDetail::str(hash_state, id);
        HashDetail::pod(hash_state, type);
        HashDetail::vec(hash_state, lodMeshes);
        HashDetail::vec(hash_state, morphTargets);
        HashDetail::pod(hash_state, physicsBody);
        HashDetail::pod(hash_state, localTransform);
        HashDetail::pod(hash_state, worldTransform);
        HashDetail::pod(hash_state, isVisible);
        HashDetail::pod(hash_state, isActive);
        return XXH64_digest(&hash_state);
    }
};

// Mech Asset Structure
struct MechAsset {
    MechHandle handle = 0;
    std::string name;
    SkeletonHandle skeleton = 0;
    std::vector<ModuleData> modules;
    std::vector<MorphProfile> morphProfiles;
    PhysicsRigHandle physicsRig = 0;
    std::vector<LODDefinition> lods;
    MechPackHandle packHandle = 0;
    
    // Performance tracking
    std::chrono::system_clock::time_point creationTime;
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    bool gpuAccelerated = false;

    MechAsset() = default;
    MechAsset(const MechAsset& other) { *this = other; }
    // Copies all data; the atomic counters are copied by value (used by hot reload,
    // which replaces an asset's contents in place so existing handles stay valid).
    MechAsset& operator=(const MechAsset& other) {
        if (this != &other) {
            handle = other.handle;
            name = other.name;
            skeleton = other.skeleton;
            modules = other.modules;
            morphProfiles = other.morphProfiles;
            physicsRig = other.physicsRig;
            lods = other.lods;
            packHandle = other.packHandle;
            creationTime = other.creationTime;
            cacheHits.store(other.cacheHits.load());
            cacheMisses.store(other.cacheMisses.load());
            gpuAccelerated = other.gpuAccelerated;
        }
        return *this;
    }

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        HashDetail::pod(hash_state, handle);
        HashDetail::str(hash_state, name);
        HashDetail::pod(hash_state, skeleton);
        HashDetail::pod(hash_state, physicsRig);
        HashDetail::pod(hash_state, packHandle);
        for(const auto& module : modules) {
            HashDetail::pod(hash_state, module.hashKey());
        }
        for(const auto& profile : morphProfiles) {
            HashDetail::pod(hash_state, profile.hashKey());
        }
        for(const auto& lod : lods) {
            HashDetail::pod(hash_state, lod.hashKey());
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
        HashDetail::pod(hash_state, currentForm);
        HashDetail::pod(hash_state, targetForm);
        HashDetail::pod(hash_state, morphProgress);
        HashDetail::pod(hash_state, morphDuration);
        HashDetail::pod(hash_state, isMorphing);
        HashDetail::pod(hash_state, isActive);
        HashDetail::pod(hash_state, position);
        HashDetail::pod(hash_state, rotation);
        HashDetail::pod(hash_state, velocity);
        HashDetail::pod(hash_state, angularVelocity);
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
