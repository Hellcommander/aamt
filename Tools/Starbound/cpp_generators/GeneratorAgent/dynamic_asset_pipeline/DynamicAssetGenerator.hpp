#pragma once

#include "DynamicAssetTypes.hpp"

namespace MagiTech {
namespace DynamicAssets {

class TextureGenerator {
public:
    static TextureHandle makeAnimatedGlow(const SpellstoneParams& p);
};

class MeshGenerator {
public:
    static MeshHandle makeFacetedGem(const SpellstoneParams& p);
};

} // namespace DynamicAssets
} // namespace MagiTech
