#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ClusterBombs {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using PhysicsHandle = uint32_t;

struct ClusterBombParams {
    std::string id = "hornet_nest_v1";
    // Casing Geometry
    float shellRadius = 0.4f;
    int shellSegments = 24;
    float fuseLength = 0.1f;
    float fuseThickness = 0.02f;

    // Detonation Control
    float detonationDelay = 3.0f;
    bool proximityFuse = false;

    // Fragmentation
    int fragmentCount = 50;
    float fragmentMinScale = 0.8f;
    float fragmentMaxScale = 1.2f;
    float spreadAngleDeg = 45.0f;
    float spawnSpeedMin = 20.0f;
    float spawnSpeedMax = 35.0f;

    // Visual FX
    glm::vec4 explosionColor = {1.0f, 0.5f, 0.1f, 1.0f};
    float explosionRadius = 5.0f;
    float smokeLifetime = 4.0f;
    float debrisLifetime = 2.5f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ClusterBombParams));
        return XXH64_digest(&hash_state);
    }
};

struct BombAssetBundle {
    MeshHandle casingMesh;
    ShaderHandle casingShader;
    PhysicsHandle fuseHandle;
    ParticleHandle explosionCoreFX;
    ParticleHandle smokeRingFX;
    ParticleHandle debrisFX;
};

// Represents the spawned fragments, which might be another asset type
struct FragmentAsset {
    MeshHandle mesh;
    PhysicsHandle physics;
};

} // namespace ClusterBombs
} // namespace MagiTech
