#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace BlackholeProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;

struct BlackholeProjectileParams {
    std::string id = "void_spiral";
    float coreRadius = 0.5f;
    float diskInnerRadius = 0.6f;
    float diskOuterRadius = 1.2f;
    float diskTilt = 15.0f;
    float warpIntensity = 1.0f;
    float warpScale = 2.5f;
    float spinSpeed = 2.0f;
    float trailLength = 1.5f;
    int particleVortexCount = 80;
    float vortexLifetime = 1.0f;
    float starSuckRadius = 2.0f;
    glm::vec4 starAbsorbColor = {0.0f, 0.0f, 0.0f, 1.0f};
    float lensFlareIntensity = 1.5f;
    float soundDepth = 0.8f;
    float soundPitch = 0.5f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(BlackholeProjectileParams));
        return XXH64_digest(&hash_state);
    }
};

struct BlackholeAssetBundle {
    MeshHandle coreMesh;
    MeshHandle diskMesh;
    MeshHandle trailMesh;
    ShaderHandle warpShader;
    TextureHandle diskTexture;
    ParticleHandle vortexParticles;
    AudioHandle sfx;
};

} // namespace BlackholeProjectiles
} // namespace MagiTech
