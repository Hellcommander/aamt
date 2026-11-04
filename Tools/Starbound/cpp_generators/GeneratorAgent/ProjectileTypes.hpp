#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Projectiles {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

struct ProjectileParams {
    std::string id;
    std::string projType = "bullet";       // "arrow", "fireball", "shard", "laser", "bolt", "bullet"
    std::string trailEffect;               // particle system name; empty = no trail
    std::string impactEffect;              // particle system name; empty = no impact effect
    std::string damageType = "physical";
    float length = 0.5f;
    float radius = 0.05f;
    float trailLength = 0.0f;
    float speed = 30.0f;
    float gravityInfluence = 1.0f;
    float homingStrength = 0.0f;
    glm::vec3 colorCore{1.0f};
    glm::vec3 colorEdge{0.6f};
    int shapeDetail = 1;                   // 0..3 mesh / texture resolution level
    int fragmentationCount = 0;

    // Every field that changes the generated assets takes part in the cache key
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, projType.c_str(), projType.length());
        XXH64_update(&hash_state, trailEffect.c_str(), trailEffect.length());
        XXH64_update(&hash_state, impactEffect.c_str(), impactEffect.length());
        XXH64_update(&hash_state, damageType.c_str(), damageType.length());
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &trailLength, sizeof(trailLength));
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, &gravityInfluence, sizeof(gravityInfluence));
        XXH64_update(&hash_state, &homingStrength, sizeof(homingStrength));
        XXH64_update(&hash_state, &colorCore, sizeof(colorCore));
        XXH64_update(&hash_state, &colorEdge, sizeof(colorEdge));
        XXH64_update(&hash_state, &shapeDetail, sizeof(shapeDetail));
        XXH64_update(&hash_state, &fragmentationCount, sizeof(fragmentationCount));
        return XXH64_digest(&hash_state);
    }
};

struct ProjectileBundle {
    MeshHandle    mesh = 0;
    TextureHandle texture = 0;
    ShaderHandle  shader = 0;
    EffectHandle  trailEffect = 0;
    EffectHandle  impactEffect = 0;
};

} // namespace Projectiles
} // namespace MagiTech
