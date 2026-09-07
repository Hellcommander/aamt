#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace AtlasAssets {

using TextureHandle = uint32_t;
using MaterialHandle = uint32_t;
using UVRect = glm::vec4; // x, y, w, h

struct SpriteParams {
    std::string id;
    std::string path;
    bool trim = true;
    glm::vec4 border = {0,0,0,0};
    uint64_t hashKey() const;
};

struct AtlasParams {
    std::string id;
    int maxWidth = 2048;
    int maxHeight = 2048;
    int padding = 4;
    bool allowRotation = true;
    bool generateMipmaps = true;
    int mipLevels = 8;
    uint64_t hashKey() const;
};

struct MaterialParams {
    std::string shader;
    bool alphaTest = true;
    float alphaThreshold = 0.5f;
    uint64_t hashKey() const;
};

struct LODParams {
    std::vector<float> screenSizes;
    std::vector<int> atlasResolutions;
    uint64_t hashKey() const;
};

struct LODData {
    std::vector<float> screenSizes;
    std::vector<TextureHandle> lodAtlases;
};

struct ImportedSprite {
    std::string id;
    // placeholder for pixel data
    std::vector<uint8_t> pixelData;
    int width;
    int height;
};

struct AtlasLayout {
    std::unordered_map<std::string, UVRect> uvMap;
    int atlasWidth;
    int atlasHeight;
};

struct AtlasBundle {
    TextureHandle atlasTex = 0;
    std::unordered_map<std::string, UVRect> uvMap;
    MaterialHandle material = 0;
    LODData lodData;
};

} // namespace AtlasAssets
} // namespace MagiTech
