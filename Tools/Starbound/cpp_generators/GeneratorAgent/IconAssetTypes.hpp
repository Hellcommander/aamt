#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"
#include "core/modules/texture_asset_generator/TextureAssetTypes.hpp"

namespace MagiTech {
namespace IconAssets {

using TextureHandle = uint32_t;

enum class IconType { Primitive, SVG, Bitmap, SDF };
enum class PrimitiveShape { Circle, Square, Triangle, Star, Custom, Heart }; // Added Heart

struct IconParams {
    std::string id = "default_icon";
    IconType type = IconType::Primitive;
    PrimitiveShape shape = PrimitiveShape::Circle;
    std::string svgPath;
    glm::ivec2 size = { 64, 64 };
    float strokeWidth = 1.0f;
    glm::vec4 fillColor = { 1.0f, 1.0f, 1.0f, 1.0f };
    glm::vec4 strokeColor = { 0.0f, 0.0f, 0.0f, 1.0f };
    bool generateSDF = false;
    float sdfPadding = 4.0f;

    uint64_t hashKey() const;
};

struct AtlasParams {
    std::string id = "default_atlas";
    glm::ivec2 iconSize = { 64, 64 };
    int columns = 8;
    int rows = 8;
    int padding = 2;
    bool generateMips = false;
    std::optional<TextureAssets::CompressionParams> compress;

    uint64_t hashKey() const;
};

struct IconAsset {
    TextureHandle bitmap = 0;
    TextureHandle sdf = 0;
};

struct IconAtlas {
    TextureHandle atlasTexture = 0;
    std::vector<glm::vec4> uvRects; // x, y, w, h
};

} // namespace IconAssets
} // namespace MagiTech
