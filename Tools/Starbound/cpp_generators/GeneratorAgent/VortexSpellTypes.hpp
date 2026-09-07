#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace VortexSpells {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;

struct VortexSpellParams {
    std::string id = "twister_v1";

    // Geometry
    float baseRadius = 2.0f;
    float topRadius = 8.0f;
    float height = 15.0f;
    int radialSegments = 24;
    int heightSegments = 30;

    // Swirl Dynamics
    float swirlSpeed = 2.5f;
    float upwardSpeed = 5.0f;
    float noiseAmplitude = 0.5f;
    float noiseFrequency = 0.2f;

    // Particle Debris
    int dustParticleCount = 500;
    float dustLifetime = 4.0f;
    glm::vec4 dustColor = {0.6f, 0.5f, 0.4f, 0.7f};

    // Visual FX
    float lightScattering = 0.3f;
    glm::vec4 vortexColor = {0.8f, 0.8f, 0.8f, 0.4f};

    // Ground Interaction
    float groundCrackRadius = 2.5f;
    float groundCrackLifetime = 12.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(VortexSpellParams));
        return XXH64_digest(&hash_state);
    }
};

struct VortexSpellAssetBundle {
    MeshHandle vortexMesh;
    ParticleHandle dustParticles;
    ParticleHandle debrisParticles;
    MeshHandle windRibbons;
    ShaderHandle vortexShader;
    DecalHandle groundDecal;
};

} // namespace VortexSpells
} // namespace MagiTech
