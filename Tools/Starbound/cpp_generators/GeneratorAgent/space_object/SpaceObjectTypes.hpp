#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Cosmic {

struct SpaceObjectParams {
    std::string id;
    std::string objectType = "planet";     // "planet", "moon", "asteroid", "star", "nebula"
    float radius = 1.0f;
    float surfaceRoughness = 0.3f;         // 0..1 relief amplitude (fraction of radius * 0.2)
    float craterDensity = 0.2f;            // 0..1, scales the number of craters
    int detailLevel = 3;                   // 0..5 mesh subdivision level
    int ringDetail = 64;                   // ring segments when ringSystem is set
    int starCount = 0;                     // background stars emitted around the object
    bool ringSystem = false;
    bool nebulaVolumetrics = false;        // layered volume slices instead of a single shell
    float starBrightness = 1.0f;
    std::vector<glm::vec3> colorPalette;   // low-to-high colour ramp; empty = neutral greys

    // Every field that changes the generated assets takes part in the cache key
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, objectType.c_str(), objectType.length());
        XXH64_update(&hash_state, &radius, sizeof(radius));
        XXH64_update(&hash_state, &surfaceRoughness, sizeof(surfaceRoughness));
        XXH64_update(&hash_state, &craterDensity, sizeof(craterDensity));
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        XXH64_update(&hash_state, &ringDetail, sizeof(ringDetail));
        XXH64_update(&hash_state, &starCount, sizeof(starCount));
        XXH64_update(&hash_state, &ringSystem, sizeof(ringSystem));
        XXH64_update(&hash_state, &nebulaVolumetrics, sizeof(nebulaVolumetrics));
        XXH64_update(&hash_state, &starBrightness, sizeof(starBrightness));
        if (!colorPalette.empty()) {
            XXH64_update(&hash_state, colorPalette.data(), colorPalette.size() * sizeof(glm::vec3));
        }
        return XXH64_digest(&hash_state);
    }
};

} // namespace Cosmic
} // namespace MagiTech
