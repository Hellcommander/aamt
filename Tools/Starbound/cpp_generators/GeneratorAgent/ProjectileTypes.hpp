#pragma once

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
    std::string id, projType, trailEffect, impactEffect, damageType;
    float length, radius, trailLength, speed, gravityInfluence, homingStrength;
    glm::vec3 colorCore, colorEdge;
    int shapeDetail, fragmentationCount;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, projType.c_str(), projType.length());
        XXH64_update(&hash_state, &colorCore, sizeof(colorCore));
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &speed, sizeof(speed));
        XXH64_update(&hash_state, damageType.c_str(), damageType.length());
        XXH64_update(&hash_state, &shapeDetail, sizeof(shapeDetail));
        return XXH64_digest(&hash_state);
    }
};

struct ProjectileBundle {
    MeshHandle    mesh;
    TextureHandle texture;
    ShaderHandle  shader;
    EffectHandle  trailEffect;
    EffectHandle  impactEffect;
};

} // namespace Projectiles
} // namespace MagiTech
