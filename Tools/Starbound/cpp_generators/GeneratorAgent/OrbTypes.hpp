#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Orbs {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

struct OrbParams {
    std::string id = "default";
    std::string orbType = "gravitational";
    float       radius = 0.5f;
    glm::vec3   coreColor = {0.1f, 0.6f, 0.9f};
    glm::vec3   shellColor = {1.0f, 1.0f, 1.0f};
    std::string runePattern = "arcaneRunes";
    int         runeDensity = 32;
    float       auraIntensity = 1.5f;
    std::string trailEffect = "sparkle";
    float       gravitationalPull = 0.2f;
    std::string spellAffinity = "teleportation";
    int         detailLevel = 2;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, orbType.c_str(), orbType.length());
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &coreColor, sizeof(coreColor));
        XXH64_update(&hash_state, &shellColor, sizeof(shellColor));
        XXH64_update(&hash_state, runePattern.c_str(), runePattern.length());
        XXH64_update(&hash_state, &runeDensity, sizeof(runeDensity));
        XXH64_update(&hash_state, &auraIntensity, sizeof(auraIntensity));
        XXH64_update(&hash_state, trailEffect.c_str(), trailEffect.length());
        XXH64_update(&hash_state, &gravitationalPull, sizeof(gravitationalPull));
        XXH64_update(&hash_state, spellAffinity.c_str(), spellAffinity.length());
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        return XXH64_digest(&hash_state);
    }
};

struct OrbBundle {
    MeshHandle     mesh;
    TextureHandle  texture;
    ShaderHandle   shader;
    EffectHandle   effects;
};

} // namespace Orbs
} // namespace MagiTech
