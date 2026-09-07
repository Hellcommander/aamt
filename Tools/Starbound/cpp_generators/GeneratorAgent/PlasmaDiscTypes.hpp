#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace PlasmaDiscs {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using TrailHandle = uint32_t;

struct PlasmaDiscParams {
    std::string id = "energy_disc_v1";

    // Geometry
    float outerRadius = 1.0f;
    float innerRadius = 0.5f;
    float thickness = 0.1f;
    int radialSegments = 32;

    // Spin & Motion Blur
    float spinRateRPM = 1000.0f;
    float motionBlurStrength = 0.8f;
    bool enableBlur = true;

    // Emissive Rim
    glm::vec4 rimColor = {0.1f, 0.8f, 1.0f, 1.0f};
    float rimIntensity = 2.5f;
    float rimFalloff = 2.0f;
    float flickerFrequency = 8.0f;

    // Trails
    bool enableTrail = true;
    float trailLength = 0.5f;
    float trailWidth = 1.0f; // As wide as the disc
    glm::vec4 trailColor = {0.1f, 0.8f, 1.0f, 0.5f};

    // Impact Sparks
    int sparkCount = 100;
    glm::vec4 sparkColor = {0.8f, 0.9f, 1.0f, 1.0f};
    float sparkLifetime = 0.8f;
    float sparkSpeedMin = 10.0f;
    float sparkSpeedMax = 20.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(PlasmaDiscParams));
        return XXH64_digest(&hash_state);
    }
};

struct PlasmaDiscAssetBundle {
    MeshHandle discMesh;
    ShaderHandle discShader;
    TrailHandle trail;
    ParticleHandle sparkParticles;
};

} // namespace PlasmaDiscs
} // namespace MagiTech
