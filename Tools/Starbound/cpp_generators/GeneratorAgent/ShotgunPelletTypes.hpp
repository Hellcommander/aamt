#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ShotgunPellets {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;
using ComputeBufferHandle = uint32_t;

enum class SpreadPattern { Uniform, Gaussian };

struct ShotgunPelletParams {
    std::string id = "flak_cannon_v1";
    // Spread & Count
    int pelletCount = 20;
    float spreadAngleDeg = 15.0f;
    SpreadPattern spreadPattern = SpreadPattern::Uniform;

    // Pellet Geometry
    float pelletRadius = 0.02f;
    float pelletLength = 0.04f;
    int radialSegments = 8;

    // Physics
    float initialSpeedMin = 80.0f;
    float initialSpeedMax = 100.0f;
    float gravityScale = 0.5f;
    float drag = 0.1f;

    // Trail (optional)
    bool enableTrail = true;
    float trailLength = 0.2f;
    float trailWidth = 0.01f;
    glm::vec4 trailColor = {1.0f, 0.8f, 0.5f, 0.6f};

    // Impact Effects
    int maxDecals = 3;
    float decalRadius = 0.5f;
    float decalLifetime = 10.0f;
    glm::vec4 decalColor = {0.1f, 0.1f, 0.1f, 1.0f};

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ShotgunPelletParams));
        return XXH64_digest(&hash_state);
    }
};

struct ShotgunAssetBundle {
    MeshHandle pelletMesh;
    ShaderHandle pelletShader;
    ComputeBufferHandle instanceBuffer;
    DecalHandle impactDecal;
};

} // namespace ShotgunPellets
} // namespace MagiTech
