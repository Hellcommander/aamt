#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace GasGrenades {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using ParticleHandle = uint32_t;
using PhysicsHandle = uint32_t;
using AudioHandle = uint32_t;

enum class CloudType { Smoke, Poison, TearGas, Corrosive };

struct GasGrenadeParams {
    std::string id = "default_smoke";

    // Fuse & Activation
    float fuseTime = 3.0f;
    bool proximityTrigger = false;

    // Canister Geometry
    float bodyRadius = 0.08f;
    float bodyHeight = 0.2f; // Set to 0 for a sphere
    int seamSegments = 12;

    // Cloud Properties
    CloudType cloudType = CloudType::Smoke;
    float cloudRadius = 5.0f;
    float cloudDuration = 15.0f;
    float density = 0.8f;
    float turbulence = 1.2f;
    float swirlSpeed = 0.5f;
    float riseSpeed = 0.3f;

    // Particle Field
    float particleSpawnRate = 200.0f;
    glm::vec2 particleSizeRange = {0.5f, 1.5f};
    glm::vec2 particleLifeRange = {5.0f, 10.0f};
    glm::vec4 particleColor = {0.8f, 0.8f, 0.8f, 0.5f};
    float particleNoiseScale = 2.0f;
    float particleNoiseSpeed = 1.0f;

    // Ground Decals
    float decalRadius = 2.0f;
    float decalDuration = 20.0f;

    // Audio
    float hissVolume = 0.7f;
    float hissPitch = 1.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(GasGrenadeParams));
        return XXH64_digest(&hash_state);
    }
};

struct UIParams {
    int iconSize = 64;
    glm::vec4 borderColor = {1.0f, 1.0f, 1.0f, 1.0f};
    bool flashOnSelect = true;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(UIParams));
        return XXH64_digest(&hash_state);
    }
};

struct GrenadeBundle {
    MeshHandle bodyMesh;
    ShaderHandle cloudShader;
    TextureHandle bodyTexture;
    ParticleHandle cloudParticles;
    PhysicsHandle triggerPhysics;
    AudioHandle sfxHiss;
    TextureHandle iconTexture;
};

} // namespace GasGrenades
} // namespace MagiTech
