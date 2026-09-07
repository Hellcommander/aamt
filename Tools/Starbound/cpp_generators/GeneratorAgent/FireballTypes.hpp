#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Fireballs {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleSystemHandle = uint32_t;
using DecalHandle = uint32_t;
using PhysicsHandle = uint32_t;

struct FireballParams {
    std::string id = "default_fireball";

    // Core Geometry
    float coreRadius = 0.5f;
    int coreLatitudeSegs = 16;
    int coreLongitudeSegs = 16;

    // Flame Envelope
    float flameHeight = 2.0f;
    float flameTaper = 0.8f;
    int flameRadialSegs = 24;
    int flameHeightSegs = 8;

    // Particle FX
    int emberCount = 100;
    glm::vec4 emberColor = {1.0f, 0.5f, 0.0f, 1.0f};
    float emberLifetime = 1.5f;
    float emberSpeedMin = 1.0f;
    float emberSpeedMax = 3.0f;

    int smokeTrailCount = 50;
    glm::vec4 smokeColor = {0.1f, 0.1f, 0.1f, 0.5f};
    float smokeLifetime = 3.0f;
    float smokeSpawnRate = 20.0f;

    // Explosion
    float explosionRadius = 3.0f;
    glm::vec4 explosionColor = {1.0f, 0.6f, 0.2f, 1.0f};
    float explosionDuration = 0.3f;

    // Impact Decals
    int scorchDecalCount = 3;
    float scorchRadius = 1.5f;
    float scorchFadeTime = 10.0f;

    // Behavior
    float initialSpeed = 20.0f;
    float gravityScale = 0.2f;
    bool arcTrajectory = true;

    // Visual Tweak
    float heatDistortionStrength = 0.02f;
    float flameNoiseScale = 5.0f;
    float flameNoiseSpeed = 2.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(FireballParams));
        return XXH64_digest(&hash_state);
    }
};

struct FireballAssetBundle {
    MeshHandle coreMesh;
    MeshHandle flameMesh;
    ParticleSystemHandle emberParticles;
    ParticleSystemHandle smokeParticles;
    ShaderHandle fireShader;
    DecalHandle scorchDecal;
    PhysicsHandle physicsData;
};

} // namespace Fireballs
} // namespace MagiTech
