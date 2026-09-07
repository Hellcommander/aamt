#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Traps {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using TextureHandle = uint32_t;
using PhysicsHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;

struct TrapParams {
    std::string id = "spike_floor_01";
    std::string trapType = "spike_floor";
    glm::vec3 size = {2.0f, 2.0f, 0.5f};
    std::string activationType = "pressure_plate";
    float triggerDelay = 0.3f;
    float resetTime = 5.0f;
    bool autoReset = true;
    std::string damageType = "physical";
    int damageValue = 25;
    float damageRadius = 1.0f;
    float effectDuration = 4.0f;
    int spikeCount = 12;
    float spikeHeight = 0.6f;
    float swingAngle = 90.0f;
    float swingSpeed = 120.0f;
    float jetHeight = 3.0f;
    float jetWidth = 0.5f;
    float gasRadius = 2.5f;
    float gasDensity = 0.8f;
    float pitDepth = 2.0f;
    std::string acidType = "green_toxic";

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, trapType.c_str(), trapType.length());
        XXH64_update(&hash_state, &size, sizeof(size));
        XXH64_update(&hash_state, &damageValue, sizeof(damageValue));
        XXH64_update(&hash_state, &spikeCount, sizeof(spikeCount));
        return XXH64_digest(&hash_state);
    }
};

struct BehaviorParams {
    float detectionRange = 3.0f;
    bool resetOnPlayerLeave = true;
    bool randomizeInterval = false;
    float minTriggerInterval = 1.0f;
    float maxTriggerInterval = 3.0f;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, &detectionRange, sizeof(detectionRange));
        XXH64_update(&hash_state, &resetOnPlayerLeave, sizeof(resetOnPlayerLeave));
        XXH64_update(&hash_state, &minTriggerInterval, sizeof(minTriggerInterval));
        return XXH64_digest(&hash_state);
    }
};

struct TrapAssetBundle {
    MeshHandle mesh;
    ShaderHandle shader;
    TextureHandle texture;
    PhysicsHandle physics;
    ParticleHandle particleFX;
    AudioHandle sfx;
    TextureHandle icon;
};

} // namespace Traps
} // namespace MagiTech
