#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace FrostNovas {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;

struct FrostNovaParams {
    std::string id = "glacial_burst_v1";

    // Nova Ring
    float ringRadius = 10.0f;
    float ringThickness = 0.5f;
    float expansionDuration = 0.3f;

    // Frost Aura Particles
    int auraParticleCount = 200;
    float auraLifetime = 1.5f;
    float auraSpawnRate = 600.0f;

    // Ice Shards
    int shardCount = 12;
    float shardMinLength = 0.8f;
    float shardMaxLength = 1.2f;
    float shardMinWidth = 0.1f;
    float shardMaxWidth = 0.2f;
    float shardSpeedMin = 15.0f;
    float shardSpeedMax = 20.0f;
    float shardSpreadAngleDeg = 360.0f; // Full circle spread

    // Impact Decals
    float frostDecalRadius = 1.0f;
    float frostDecalDuration = 8.0f;

    // Visual FX
    glm::vec4 ringColor = {0.5f, 0.8f, 1.0f, 0.8f};
    glm::vec4 shardColor = {0.8f, 0.9f, 1.0f, 1.0f};
    float refractionStrength = 0.05f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(FrostNovaParams));
        return XXH64_digest(&hash_state);
    }
};

struct FrostNovaAssetBundle {
    MeshHandle ringMesh;
    MeshHandle shardMesh;
    ParticleHandle auraParticles;
    ParticleHandle sparkleParticles;
    ShaderHandle frostShader;
    DecalHandle frostDecal;
};

} // namespace FrostNovas
} // namespace MagiTech
