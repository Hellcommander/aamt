#pragma once

#include <string>
#include <vector>
#include <array>
#include <map>
#include <cstdint>
#include <functional>
#include <glm/glm.hpp>
#include "xxhash.h"
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech {
namespace SegmentedWeapons {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using SkeletonHandle = uint32_t;
using PhysicsHandle = uint32_t;

// Enums for weapon parameters
enum class WeaponType {
    WHIP,
    CHAIN,
    FLAIL,
    NUNCHAKU,
    ROPE
};

enum class SegmentShape {
    CYLINDER,
    BOX,
    SPHERE,
    CUSTOM_MESH
};

enum class TaperProfile {
    NONE,
    LINEAR,
    EXPONENTIAL,
    CUSTOM_CURVE
};

enum class MaterialType {
    LEATHER,
    STEEL,
    ROPE,
    CHAIN_METAL
};

enum class EndAttachment {
    NONE,
    WEIGHT,
    SPIKE,
    HOOK,
    BLADE
};

struct ArticulationLimits {
    float twist = 45.0f;
    float swing = 60.0f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &twist, sizeof(twist));
        XXH64_update(&hash_state, &swing, sizeof(swing));
        return XXH64_digest(&hash_state);
    }
};

struct SegmentedWeaponParams {
    std::string id = "default_whip";
    WeaponType weaponType = WeaponType::WHIP;
    int segmentCount = 16;
    float segmentLength = 0.3f;
    float segmentRadius = 0.02f;
    SegmentShape segmentShape = SegmentShape::CYLINDER;
    TaperProfile taperProfile = TaperProfile::NONE;
    float jointFlexibility = 0.9f;
    ArticulationLimits articulationLimits;
    MaterialType materialType = MaterialType::LEATHER;
    glm::vec3 colorPrimary = {0.15f, 0.05f, 0.02f};
    glm::vec3 colorSecondary = {0.9f, 0.7f, 0.5f};
    float noiseDetail = 0.3f;
    float textureScale = 2.0f;
    bool ornamentation = true;
    EndAttachment endAttachment = EndAttachment::BLADE;
    
    // Additional parameters
    float segmentSpacing = 0.05f;
    bool enableJoints = true;
    float jointDamping = 0.2f;
    bool enableCollision = true;
    float collisionRadius = 0.025f;
    bool enablePhysics = true;
    float physicsMass = 0.1f;
    
    // Custom curve for taper profile
    std::vector<float> customTaperCurve;
    
    // Metadata
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;
    
    // Performance settings
    bool enableCaching = true;
    bool enableHotReload = true;
    bool enableParallelProcessing = true;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &weaponType, sizeof(weaponType));
        XXH64_update(&hash_state, &segmentCount, sizeof(segmentCount));
        XXH64_update(&hash_state, &segmentLength, sizeof(segmentLength));
        XXH64_update(&hash_state, &segmentRadius, sizeof(segmentRadius));
        XXH64_update(&hash_state, &segmentShape, sizeof(segmentShape));
        XXH64_update(&hash_state, &taperProfile, sizeof(taperProfile));
        XXH64_update(&hash_state, &jointFlexibility, sizeof(jointFlexibility));
        XXH64_update(&hash_state, &articulationLimits, sizeof(articulationLimits));
        XXH64_update(&hash_state, &materialType, sizeof(materialType));
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorSecondary, sizeof(colorSecondary));
        XXH64_update(&hash_state, &noiseDetail, sizeof(noiseDetail));
        XXH64_update(&hash_state, &textureScale, sizeof(textureScale));
        XXH64_update(&hash_state, &ornamentation, sizeof(ornamentation));
        XXH64_update(&hash_state, &endAttachment, sizeof(endAttachment));
        return XXH64_digest(&hash_state);
    }
};

struct PhysicsParams {
    float massPerSegment = 0.1f;
    float damping = 0.2f;
    float restitution = 0.1f;
    float collisionRadius = 0.025f;
    int solverIterations = 8;
    float gravityInfluence = 1.0f;
    
    // Additional physics parameters
    float friction = 0.5f;
    float rollingFriction = 0.1f;
    float spinningFriction = 0.1f;
    bool enableGravity = true;
    bool enableCollisionDetection = true;
    float maxLinearVelocity = 100.0f;
    float maxAngularVelocity = 10.0f;
    
    // Joint parameters
    float jointDamping = 0.2f;
    float jointFriction = 0.1f;
    bool enableJointLimits = true;
    float jointLimitSoftness = 0.5f;
    float jointLimitBias = 0.3f;
    float jointLimitRelaxation = 1.0f;
    
    // Metadata
    std::string physicsName;
    std::string description;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &massPerSegment, sizeof(massPerSegment));
        XXH64_update(&hash_state, &damping, sizeof(damping));
        XXH64_update(&hash_state, &restitution, sizeof(restitution));
        XXH64_update(&hash_state, &collisionRadius, sizeof(collisionRadius));
        XXH64_update(&hash_state, &solverIterations, sizeof(solverIterations));
        XXH64_update(&hash_state, &gravityInfluence, sizeof(gravityInfluence));
        XXH64_update(&hash_state, &friction, sizeof(friction));
        XXH64_update(&hash_state, &rollingFriction, sizeof(rollingFriction));
        XXH64_update(&hash_state, &spinningFriction, sizeof(spinningFriction));
        XXH64_update(&hash_state, &enableGravity, sizeof(enableGravity));
        XXH64_update(&hash_state, &enableCollisionDetection, sizeof(enableCollisionDetection));
        XXH64_update(&hash_state, &maxLinearVelocity, sizeof(maxLinearVelocity));
        XXH64_update(&hash_state, &maxAngularVelocity, sizeof(maxAngularVelocity));
        XXH64_update(&hash_state, &jointDamping, sizeof(jointDamping));
        XXH64_update(&hash_state, &jointFriction, sizeof(jointFriction));
        XXH64_update(&hash_state, &enableJointLimits, sizeof(enableJointLimits));
        XXH64_update(&hash_state, &jointLimitSoftness, sizeof(jointLimitSoftness));
        XXH64_update(&hash_state, &jointLimitBias, sizeof(jointLimitBias));
        XXH64_update(&hash_state, &jointLimitRelaxation, sizeof(jointLimitRelaxation));
        return XXH64_digest(&hash_state);
    }
};

struct AssetBundle {
    MeshHandle      mesh;
    TextureHandle   texture;
    SkeletonHandle  skeleton;
    PhysicsHandle   physics;
};

// Utility functions for parameter conversion
namespace ParamUtils {
    // Convert string to enum
    WeaponType parseWeaponType(const std::string& str);
    SegmentShape parseSegmentShape(const std::string& str);
    TaperProfile parseTaperProfile(const std::string& str);
    MaterialType parseMaterialType(const std::string& str);
    EndAttachment parseEndAttachment(const std::string& str);
    
    // Convert enum to string
    std::string weaponTypeToString(WeaponType type);
    std::string segmentShapeToString(SegmentShape shape);
    std::string taperProfileToString(TaperProfile profile);
    std::string materialTypeToString(MaterialType type);
    std::string endAttachmentToString(EndAttachment attachment);
    
    // JSON serialization
    nlohmann::json toJson(const SegmentedWeaponParams& params);
    SegmentedWeaponParams fromJson(const nlohmann::json& json);
    
    nlohmann::json toJson(const PhysicsParams& params);
    PhysicsParams fromJson(const nlohmann::json& json);
}

} // namespace SegmentedWeapons
} // namespace MagiTech
