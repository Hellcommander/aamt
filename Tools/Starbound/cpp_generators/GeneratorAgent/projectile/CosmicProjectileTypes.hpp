#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Cosmic {

struct CosmicProjectileParams {
    std::string id;
    std::string type = "comet";            // visual style, e.g. "comet", "meteor", "starshard"
    std::string trailType = "streak";      // "none", "streak", "sparkle", "smoke"
    std::string impactEffect = "burst";    // "none", "burst", "shatter"
    std::string damageType = "cosmic";
    float length = 1.0f;
    float radius = 0.25f;
    float noiseIntensity = 0.3f;
    float noiseScale = 2.0f;
    float flickerRate = 4.0f;
    float trailLength = 1.5f;
    float homingStrength = 0.0f;
    int fragmentation = 0;
    glm::vec3 colorCore{1.0f, 0.9f, 0.6f};
    glm::vec3 colorEdge{0.4f, 0.2f, 1.0f};

    // Every field that changes the generated assets takes part in the cache key
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, type.c_str(), type.length());
        XXH64_update(&hash_state, trailType.c_str(), trailType.length());
        XXH64_update(&hash_state, impactEffect.c_str(), impactEffect.length());
        XXH64_update(&hash_state, damageType.c_str(), damageType.length());
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        XXH64_update(&hash_state, &noiseScale, sizeof(noiseScale));
        XXH64_update(&hash_state, &flickerRate, sizeof(flickerRate));
        XXH64_update(&hash_state, &trailLength, sizeof(trailLength));
        XXH64_update(&hash_state, &homingStrength, sizeof(homingStrength));
        XXH64_update(&hash_state, &fragmentation, sizeof(fragmentation));
        XXH64_update(&hash_state, &colorCore, sizeof(colorCore));
        XXH64_update(&hash_state, &colorEdge, sizeof(colorEdge));
        return XXH64_digest(&hash_state);
    }
};

} // namespace Cosmic
} // namespace MagiTech
