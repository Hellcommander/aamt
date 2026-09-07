#pragma once

#include <string_view>
#include <cstdint>
#include <glm/glm.hpp>
#include "xxhash.h" // Assuming xxhash is available

namespace MagiTech {
namespace DynamicAssets {

using float3 = glm::vec3;
using TextureHandle = uint32_t;
using MeshHandle = uint32_t;

struct SpellstoneParams {
    std::string_view id;
    float3   hueStart, hueEnd;
    int      facets, frames;
    float    pulseSpeed, glowIntensity, size;
    
    constexpr uint64_t constexprKey() const noexcept {
        // A simplified version for now, as string_view can't be used in a constexpr context like this
        // A full implementation might require passing a char array or using a compile-time string hashing library
        return XXH64(id.data(), id.size(), 0);
    }
};

class AssetBundle { 
public:
    TextureHandle tex; 
    MeshHandle    mesh; 
};

} // namespace DynamicAssets
} // namespace MagiTech
