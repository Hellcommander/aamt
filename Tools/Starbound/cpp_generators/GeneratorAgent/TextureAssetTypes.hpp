#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace TextureAssets {

using TextureHandle = uint32_t;
using MipmapHandle = uint32_t;

// Forward declaration for UDIM structure
struct UDIMLayout;

enum class TextureType { Noise, Mask, PBR, Atlas, TrimSheet };

struct TextureParams {
    std::string id = "default_texture";
    TextureType type = TextureType::Noise;
    glm::ivec2 resolution = { 256, 256 };
    float uvScale = 1.0f;
    int seed = 0;
    bool seamless = false;

    uint64_t hashKey() const;
};

struct NoiseParams {
    std::string noiseType = "Perlin";
    int octaves = 4;
    float frequency = 1.0f;
    float lacunarity = 2.0f;
    float gain = 0.5f;

    uint64_t hashKey() const;
};

struct MaskParams {
    std::vector<std::pair<float, glm::vec4>> stops;
    bool invert = false;
    bool gaussianBlur = false;
    float blurRadius = 1.0f;

    uint64_t hashKey() const;
};

struct PBRParams {
    glm::vec4 baseColorTint = {1.0f, 1.0f, 1.0f, 1.0f};
    float metallic = 0.0f;
    float roughness = 0.5f;
    float ambientOcclusion = 1.0f;
    bool bakeHeight = false;
    float heightScale = 0.01f;

    uint64_t hashKey() const;
};

struct AtlasParams {
    std::vector<TextureHandle> sources;
    int padding = 4;
    int maxWidth = 4096;
    int maxHeight = 4096;
    bool generateUDIM = false;

    uint64_t hashKey() const;
};

struct CompressionParams {
    std::string format = "PNG";
    int quality = 90;
    bool generateMipmaps = true;
    bool sRGB = true;

    uint64_t hashKey() const;
};

struct TextureAssetBundle {
    TextureHandle texture;
    MipmapHandle mipmaps;
    std::optional<UDIMLayout> udim;
};

// Placeholder for UDIM layout data
struct UDIMLayout {};

} // namespace TextureAssets
} // namespace MagiTech
