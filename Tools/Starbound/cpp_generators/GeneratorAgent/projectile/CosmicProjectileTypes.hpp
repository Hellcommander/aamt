#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Cosmic {

struct CosmicProjectileParams {
    std::string id, type, trailType, impactEffect, damageType;
    float length, radius, noiseIntensity, noiseScale, flickerRate, trailLength, homingStrength;
    int fragmentation;
    glm::vec3 colorCore, colorEdge;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, type.c_str(), type.length());
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &colorCore, sizeof(colorCore));
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        return XXH64_digest(&hash_state);
    }
};

} // namespace Cosmic
} // namespace MagiTech
