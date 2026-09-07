#pragma once

#include <string>
#include <vector>
#include "xxhash.h"

namespace MagiTech {
namespace Rooms {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using MaterialHandle = uint32_t;
using LightHandle = uint32_t;

struct RoomParams {
    std::string id, theme, floorTile, wallTile, ceilingTile, backgroundStyle;
    std::vector<std::string> props, trapTypes;
    int width, height, secretCount, lightCount, detailLevel;
    float propDensity, trapDensity;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, theme.c_str(), theme.length());
        XXH64_update(&hash_state, &width, sizeof(width));
        XXH64_update(&hash_state, &height, sizeof(height));
        XXH64_update(&hash_state, &propDensity, sizeof(propDensity));
        XXH64_update(&hash_state, &trapDensity, sizeof(trapDensity));
        XXH64_update(&hash_state, &detailLevel, sizeof(detailLevel));
        return XXH64_digest(&hash_state);
    }
};

struct RoomBundle {
    MeshHandle     geometry;
    TextureHandle  tileset;
    MaterialHandle material;
    LightHandle    lights;
};

} // namespace Rooms
} // namespace MagiTech
