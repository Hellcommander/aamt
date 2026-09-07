#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <optional>

// Assuming glm is in the include path
#include <glm/glm.hpp>


namespace MagiTech {
namespace Procedural {

// From user prompt
enum class SpellType {
    Projectile,
    AOE,
    Beam,
    Aura
};

// Using float3 from user prompt. It's an alias for glm::vec3
using float3 = glm::vec3;

struct SpellAssetParams {
    uint64_t    seed = 0;
    SpellType   type = SpellType::Projectile;
    int         durationFrames = 1;
    int         texWidth = 256, texHeight = 256;
    float3      colorStart = float3(1.0f, 0.0f, 0.0f);
    float3      colorEnd = float3(1.0f, 1.0f, 0.0f);
    float       noiseScale = 1.0f;
    float       swirlStrength = 0.5f;
    float       meshRadius = 1.0f;
    float       meshThickness = 0.1f;
    int         meshDetail = 16;       // tessellation level
    
    // Additional parameters from prompt
    float       curlNoiseIntensity = 1.0f;
    int         fractalDepth = 3;
    float       emissionRate = 100.0f;

    // A way to uniquely identify this set of parameters
    uint64_t getHash() const {
        // This is a simple hashing function. For a real implementation,
        // a more robust hashing mechanism like xxHash or MurmurHash3 on the raw bytes
        // of the struct would be better to avoid collisions and provide good distribution.
        uint64_t hash = seed;
        hash ^= static_cast<uint64_t>(type) << 8;
        hash ^= static_cast<uint64_t>(durationFrames) << 16;
        hash ^= static_cast<uint64_t>(texWidth) << 24;
        hash ^= static_cast<uint64_t>(texHeight) << 32;
        
        auto hash_float = [](float f) { return std::hash<float>{}(f); };

        hash ^= hash_float(colorStart.x) << 0;
        hash ^= hash_float(colorStart.y) << 1;
        hash ^= hash_float(colorStart.z) << 2;
        hash ^= hash_float(colorEnd.x) << 3;
        hash ^= hash_float(colorEnd.y) << 4;
        hash ^= hash_float(colorEnd.z) << 5;
        hash ^= hash_float(noiseScale) << 6;
        hash ^= hash_float(swirlStrength) << 7;
        hash ^= hash_float(meshRadius) << 8;
        hash ^= hash_float(meshThickness) << 9;
        hash ^= static_cast<uint64_t>(meshDetail) << 40;
        hash ^= hash_float(curlNoiseIntensity) << 10;
        hash ^= static_cast<uint64_t>(fractalDepth) << 48;
        hash ^= hash_float(emissionRate) << 11;

        return hash;
    }
};

// Also from user prompt
// These should be handles to GPU resources.
// Looking at EnhancedRenderer.hpp, it uses uint32_t for handles.
using TextureHandle = uint32_t;
using MeshHandle = uint32_t;

struct AssetBundle {
    TextureHandle texHandle;
    MeshHandle    meshHandle;
    int           lastUsedFrame;
    // other metadata could go here, e.g. animation data handle
};

} // namespace Procedural
} // namespace MagiTech
