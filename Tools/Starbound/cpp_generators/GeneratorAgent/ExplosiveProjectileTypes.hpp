#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ExplosiveProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;

struct ExplosiveProjectileParams {
    std::string id = "rocket_v1";

    // Geometry
    float noseLength = 0.5f;
    float bodyLength = 1.0f;
    float bodyRadius = 0.1f;
    int finCount = 4;
    float finSpan = 0.2f;
    float finThickness = 0.02f;

    // Propulsion
    float motorThrust = 100.0f;
    float motorDuration = 2.0f;
    glm::vec4 flameColor = {1.0f, 0.6f, 0.2f, 1.0f};
    float flameLifetime = 0.5f;

    // Explosion
    float explosionRadius = 8.0f;
    glm::vec4 explosionColor = {1.0f, 0.5f, 0.0f, 1.0f};
    float flashDuration = 0.2f;
    bool proximityDetonate = false;

    // Fragmentation
    int fragmentCount = 50;
    float fragmentMinScale = 0.05f;
    float fragmentMaxScale = 0.15f;
    float fragmentSpeedMin = 30.0f;
    float fragmentSpeedMax = 50.0f;
    float fragmentSpreadAngleDeg = 360.0f;

    // Smoke & Debris
    glm::vec4 smokeColor = {0.2f, 0.2f, 0.2f, 0.8f};
    float smokeLifetime = 5.0f;
    float debrisLifetime = 3.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ExplosiveProjectileParams));
        return XXH64_digest(&hash_state);
    }
};

struct ExplosiveAssetBundle {
    MeshHandle projectileMesh;
    ParticleHandle motorTrail;
    ParticleHandle smokeTrail;
    ParticleHandle explosionFlash;
    MeshHandle fragmentMesh;
    ParticleHandle debrisParticles;
    ShaderHandle materialShader;
    DecalHandle scorchDecal;
};

} // namespace ExplosiveProjectiles
} // namespace MagiTech
