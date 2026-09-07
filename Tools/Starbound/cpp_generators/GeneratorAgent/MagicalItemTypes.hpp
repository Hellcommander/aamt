#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace MagicalItems {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

struct MagicalItemParams {
    std::string id, itemType, coreCrystal, shaftMaterial, gripWrap;
    std::string runePattern, elementalAffinity, auraEffect, muzzleFlash;
    std::vector<std::string> recoilMounts;
    float length;
    int runeDensity, gemCount, barrelCount, chamberCapacity, detailLevel;
    glm::vec3 colorPrimary, colorAccent;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, itemType.c_str(), itemType.length());
        XXH64_update(&hash_state, coreCrystal.c_str(), coreCrystal.length());
        XXH64_update(&hash_state, shaftMaterial.c_str(), shaftMaterial.length());
        XXH64_update(&hash_state, gripWrap.c_str(), gripWrap.length());
        XXH64_update(&hash_state, runePattern.c_str(), runePattern.length());
        XXH64_update(&hash_state, elementalAffinity.c_str(), elementalAffinity.length());
        XXH64_update(&hash_state, auraEffect.c_str(), auraEffect.length());
        XXH64_update(&hash_state, muzzleFlash.c_str(), muzzleFlash.length());
        for (const auto& mount : recoilMounts) {
            XXH64_update(&hash_state, mount.c_str(), mount.length());
        }
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &runeDensity, sizeof(runeDensity));
        XXH64_update(&hash_state, &gemCount, sizeof(gemCount));
        XXH64_update(&hash_state, &barrelCount, sizeof(barrelCount));
        XXH64_update(&hash_state, &chamberCapacity, sizeof(chamberCapacity));
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorAccent, sizeof(colorAccent));
        return XXH64_digest(&hash_state);
    }
};

struct MagicalItemBundle {
    MeshHandle    mesh;
    TextureHandle texture;
    ShaderHandle  shader;
    EffectHandle  effects;
};

} // namespace MagicalItems
} // namespace MagiTech
