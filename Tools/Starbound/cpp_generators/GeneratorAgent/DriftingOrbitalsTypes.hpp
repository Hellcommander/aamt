#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace DriftingOrbitals {

using MeshHandle = uint32_t;
using ParticleHandle = uint32_t;
using ShaderHandle = uint32_t;

struct DriftingOrbitalParams {
    std::string id = "default_orbitals";

    // Orbit Configuration
    int    orbCount = 8;
    float  orbitRadiusMin = 2.0f;
    float  orbitRadiusMax = 3.0f;
    float  orbitSpeedMin = 0.5f;
    float  orbitSpeedMax = 1.5f;
    float  radialOscillationAmp = 0.2f;
    float  radialOscillationFreq = 1.0f;

    // Orbital Objects
    float  orbScaleMin = 0.1f;
    float  orbScaleMax = 0.3f;
    int    orbMeshDetail = 16;

    // Trail & Glow
    bool   enableTrails = true;
    float  trailLength = 1.0f;
    float  trailWidth = 0.1f;
    glm::vec4  trailColor = {1.0f, 0.8f, 0.2f, 1.0f};

    // Magnetic Pulse
    float  pulseInterval = 2.0f;
    float  pulseRadius = 5.0f;
    float  pulseStrength = 1.0f;
    glm::vec4  pulseColor = {0.2f, 0.8f, 1.0f, 1.0f};

    uint64_t hashKey() const {
        XXH64_state_t s;
        XXH64_reset(&s, 0);
        XXH64_update(&s, this, sizeof(DriftingOrbitalParams) - sizeof(std::string));
        XXH64_update(&s, id.c_str(), id.length());
        return XXH64_digest(&s);
    }
};

struct DriftingOrbitalsAssetBundle {
    std::vector<MeshHandle> orbitalMeshes;
    std::vector<MeshHandle> trailMeshes;
    ParticleHandle pulseParticleSystem;
    ShaderHandle orbitalShader;
};

} // namespace DriftingOrbitals
} // namespace MagiTech
