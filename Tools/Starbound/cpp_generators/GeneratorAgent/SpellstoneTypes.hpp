#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Spellstones {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

struct SpellstoneParams {
    std::string id, stoneType, runePattern;
    std::string beamTexture, idleEffect, castEffect;
    float baseRadius, height, glowIntensity;
    float beamWidth, beamLength;
    glm::vec3 glowColor, beamColor;
    int facets, detailLevel;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, stoneType.c_str(), stoneType.length());
        XXH64_update(&hash_state, runePattern.c_str(), runePattern.length());
        XXH64_update(&hash_state, &baseRadius, sizeof(baseRadius));
        XXH64_update(&hash_state, &facets, sizeof(facets));
        XXH64_update(&hash_state, &beamColor, sizeof(beamColor));
        return XXH64_digest(&hash_state);
    }
};

struct SpellstoneBundle {
    MeshHandle    bodyMesh;
    TextureHandle surfaceTex;
    ShaderHandle  bodyShader;
    EffectHandle  idleFX, castFX;
};

} // namespace Spellstones
} // namespace MagiTech
