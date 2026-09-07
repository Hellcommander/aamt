#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace HomingMissiles {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using SplineHandle = uint32_t;

struct HomingMissileParams {
    std::string id = "sidewinder_v1";
    // Geometry
    float noseLength = 0.3f;
    float bodyRadius = 0.1f;
    int bodySegments = 16;

    // Fins
    int finCount = 4;
    float finSpan = 0.2f;
    float finThickness = 0.01f;

    // Guidance
    float maxTurnRateDeg = 90.0f;
    float speed = 25.0f;

    // Trail
    float trailLength = 2.0f;
    float trailWidth = 0.15f;

    // Exhaust Particles
    glm::vec4 flameColor = {1.0f, 0.7f, 0.2f, 1.0f};
    glm::vec4 smokeColor = {0.3f, 0.3f, 0.3f, 0.7f};
    float flameLifetime = 0.1f;
    float smokeLifetime = 1.5f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(HomingMissileParams));
        return XXH64_digest(&hash_state);
    }
};

struct MissileAssetBundle {
    MeshHandle missileMesh;
    SplineHandle guidancePath;
    MeshHandle trailMesh;
    ShaderHandle bodyShader;
    ParticleHandle flameExhaust;
    ParticleHandle smokeExhaust;
};

} // namespace HomingMissiles
} // namespace MagiTech
