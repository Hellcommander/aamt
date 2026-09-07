#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace BeamNets {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;

struct BeamNetParams {
    std::string id = "laser_grid_v1";

    // Grid Dimensions
    int rows = 5;
    int columns = 5;
    float cellWidth = 2.0f;
    float cellHeight = 2.0f;

    // Beam Appearance
    float beamThickness = 0.1f;
    glm::vec4 beamColor = {0.2f, 0.8f, 1.0f, 0.9f};
    float glowIntensity = 2.0f;
    float flickerFrequency = 5.0f;

    // Weaving Animation (for nets)
    float weaveAmplitude = 0.2f;
    float weaveSpeed = 3.0f;

    // Duration & Lifetime
    float deploymentDelay = 0.5f;
    float activeDuration = 10.0f;
    bool retractOnExpire = true;

    // Impact & Interaction
    bool enableSparks = true;
    float sparkRate = 50.0f;
    float sparkLifetime = 0.3f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(BeamNetParams));
        return XXH64_digest(&hash_state);
    }
};

struct BeamNetAssetBundle {
    MeshHandle netMesh;
    ShaderHandle beamShader;
    ParticleHandle sparkParticles;
    DecalHandle scorchDecal;
};

} // namespace BeamNets
} // namespace MagiTech
