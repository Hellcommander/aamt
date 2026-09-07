#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Cosmic {

struct SpaceObjectParams {
    std::string id, objectType;
    float radius, surfaceRoughness, craterDensity;
    int detailLevel, ringDetail, starCount;
    bool ringSystem, nebulaVolumetrics;
    float starBrightness;
    std::vector<glm::vec3> colorPalette;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, objectType.c_str(), objectType.length());
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        XXH64_update(&hash_state, &surfaceRoughness, sizeof(surfaceRoughness));
        return XXH64_digest(&hash_state);
    }
};

} // namespace Cosmic
} // namespace MagiTech
