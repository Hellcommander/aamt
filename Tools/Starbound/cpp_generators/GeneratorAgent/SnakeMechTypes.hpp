#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace SnakeMechs {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using PhysicsHandle = uint32_t;

struct SnakeMechParams {
    std::string id = "viper_mk1";

    // Segmentation
    int segmentCount = 15;
    float segmentLength = 1.0f;
    float segmentRadius = 0.4f;
    float connectorGap = 0.1f;

    // Joint Mechanics
    float maxBendAngleDeg = 45.0f;
    float bendStiffness = 100.0f;

    // Armor & Details
    bool enablePlating = true;
    int platesPerSegment = 6;
    float plateThickness = 0.05f;
    glm::vec4 platingColor = {0.3f, 0.3f, 0.35f, 1.0f};

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

    // LOD & Performance
    bool rebuildOnLOD = false;
    int lodCount = 3;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(SnakeMechParams));
        return XXH64_digest(&hash_state);
    }
};

struct SnakeMechAssetBundle {
    MeshHandle segmentMesh;
    SkeletonHandle skeleton;
    AnimationHandle proceduralAnimation;
    ShaderHandle materialShader;
    ParticleHandle sparkParticles;
    PhysicsHandle physicsAsset;
};

} // namespace SnakeMechs
} // namespace MagiTech
