#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace AcidLiquidProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;
using PhysicsHandle = uint32_t;

struct LiquidProjectileParams {
    std::string id = "venom_spit_v1";
    // Geometry
    float baseRadius = 0.2f;
    int radialSegments = 12;
    float lengthVariance = 0.5f;

    // Fluid Dynamics
    float viscosity = 0.8f;
    float surfaceTension = 0.7f;
    float gravityScale = 1.0f;

    // Emitter Settings
    float emissionRate = 30.0f;
    float dropletSpeedMin = 15.0f;
    float dropletSpeedMax = 20.0f;
    float dropletSizeMin = 0.05f;
    float dropletSizeMax = 0.15f;

    // Impact & Splatter
    int splatterCount = 10;
    float splatterRadius = 1.5f;
    float splatterLifetime = 8.0f;

    // Visual FX
    glm::vec4 liquidColor = {0.2f, 0.9f, 0.1f, 0.8f};
    float refractionStrength = 0.1f;
    float sheenIntensity = 0.9f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(LiquidProjectileParams));
        return XXH64_digest(&hash_state);
    }
};

struct LiquidAssetBundle {
    MeshHandle dropletMesh;
    ShaderHandle liquidShader;
    ParticleHandle mistParticles;
    DecalHandle splatterDecal;
    PhysicsHandle fluidPhysics;
};

} // namespace AcidLiquidProjectiles
} // namespace MagiTech
