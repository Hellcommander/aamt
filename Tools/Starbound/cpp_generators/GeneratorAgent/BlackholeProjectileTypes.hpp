#pragma once
#include <cstdint>
#include <initializer_list>
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

    // Basic sanity check used by the Lua bindings before generation.
    bool validate() const noexcept {
        return coreRadius > 0.0f && diskInnerRadius > 0.0f && diskOuterRadius > diskInnerRadius;
    }

    uint64_t hashKey() const noexcept {
        // Hash the id contents and every numeric field (hashing the raw struct
        // would hash the std::string's internal pointer instead of its text).
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.data(), id.size());
        const float floats[] = {coreRadius, diskInnerRadius, diskOuterRadius, diskTilt,
                                warpIntensity, warpScale, spinSpeed, trailLength,
                                vortexLifetime, starSuckRadius,
                                starAbsorbColor.r, starAbsorbColor.g, starAbsorbColor.b, starAbsorbColor.a,
                                lensFlareIntensity, soundDepth, soundPitch};
        XXH64_update(&hash_state, floats, sizeof(floats));
        XXH64_update(&hash_state, &particleVortexCount, sizeof(particleVortexCount));
        return XXH64_digest(&hash_state);
    }
};

struct BlackholeAssetBundle {
    MeshHandle coreMesh = 0;
    MeshHandle diskMesh = 0;
    MeshHandle trailMesh = 0;
    ShaderHandle warpShader = 0;
    TextureHandle diskTexture = 0;
    ParticleHandle vortexParticles = 0;
    AudioHandle sfx = 0;

    // Number of non-null asset handles in the bundle.
    int getAssetCount() const noexcept {
        int count = 0;
        for (uint32_t h : {coreMesh, diskMesh, trailMesh, warpShader, diskTexture, vortexParticles, sfx})
            if (h != 0) ++count;
        return count;
    }
};

} // namespace BlackholeProjectiles
} // namespace MagiTech
