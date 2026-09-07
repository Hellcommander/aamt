#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace BoomerangDiscs {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using SplineHandle = uint32_t;

struct BoomerangParams {
    std::string id = "sky_reaper_v1";
    // Shape
    float armSpan = 0.8f;
    float armThickness = 0.05f;
    int twistCount = 1;

    // Flight
    float spinRateRPM = 1200.0f;
    float returnDelay = 1.0f;
    float returnArcHeight = 2.0f;

    // Trail
    float trailLength = 1.0f;
    float trailWidth = 0.1f;
    glm::vec4 trailColor = {0.8f, 0.9f, 1.0f, 0.5f};

    // Impact
    float groundBounceDamping = 0.6f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(BoomerangParams));
        return XXH64_digest(&hash_state);
    }
};

struct ReturningDiscParams {
    std::string id = "chakram_of_light";
    // Shape
    float discRadius = 0.3f;
    float discThickness = 0.03f;
    int radialSegments = 32;

    // Flight
    float spinRateRPM = 1500.0f;
    float boomerangAngleDeg = 15.0f;
    float returnDelay = 1.2f;
    float returnArcHeight = 1.5f;

    // Trail
    float rimGlowWidth = 0.02f;
    glm::vec4 rimGlowColor = {0.2f, 1.0f, 0.8f, 1.0f};

    // Impact
    bool spawnDustOnHit = true;
    int maxDustParticles = 50;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ReturningDiscParams));
        return XXH64_digest(&hash_state);
    }
};

struct BoomerangAssetBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    SplineHandle flightPath;
    MeshHandle trailMesh;
    ParticleHandle airGustFX;
};

struct DiscAssetBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    SplineHandle flightPath;
    MeshHandle rimGlowMesh;
    ParticleHandle dustImpactFX;
};


} // namespace BoomerangDiscs
} // namespace MagiTech
