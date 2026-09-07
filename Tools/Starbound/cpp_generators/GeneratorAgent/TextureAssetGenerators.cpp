#include "TextureAssetFactory.hpp"
#include "core/Log.hpp"
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace TextureAssets {

#define LOG_TEX_GEN(Asset, Id) Log::info("Building Texture Asset {}: {}", #Asset, Id)

// Hash function implementations
uint64_t TextureParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(TextureParams) - sizeof(std::string));
    XXH64_update(&hash_state, id.c_str(), id.length());
    return XXH64_digest(&hash_state);
}
uint64_t NoiseParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(NoiseParams) - sizeof(std::string));
    XXH64_update(&hash_state, noiseType.c_str(), noiseType.length());
    return XXH64_digest(&hash_state);
}
uint64_t MaskParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(MaskParams) - sizeof(std::vector<std::pair<float, glm::vec4>>));
    XXH64_update(&hash_state, stops.data(), stops.size() * sizeof(std::pair<float, glm::vec4>));
    return XXH64_digest(&hash_state);
}
uint64_t PBRParams::hashKey() const {
    return XXH64(this, sizeof(PBRParams), 0);
}
uint64_t AtlasParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(AtlasParams) - sizeof(std::vector<TextureHandle>));
    XXH64_update(&hash_state, sources.data(), sources.size() * sizeof(TextureHandle));
    return XXH64_digest(&hash_state);
}
uint64_t CompressionParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(CompressionParams) - sizeof(std::string));
    XXH64_update(&hash_state, format.c_str(), format.length());
    return XXH64_digest(&hash_state);
}

namespace NoiseGen {
    TextureHandle build(const NoiseParams& np, const glm::ivec2& res, int seed, bool seamless) {
        LOG_TEX_GEN(Noise, np.noiseType);
        // Implement noise generation (Perlin, Simplex, etc.)
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace NoiseGen

namespace MaskGen {
    TextureHandle build(const MaskParams& mp, const glm::ivec2& res) {
        LOG_TEX_GEN(Mask, "CustomMask");
        // Implement mask generation from stops/blur
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace MaskGen

namespace PBRGen {
    TextureHandle build(const PBRParams& pp, const glm::ivec2& res) {
        LOG_TEX_GEN(PBR, "MaterialMap");
        // Implement PBR channel packing
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace PBRGen

namespace AtlasGen {
    TextureHandle pack(const AtlasParams& ap) {
        LOG_TEX_GEN(Atlas, "TextureAtlas");
        // Implement texture packing
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace AtlasGen

namespace CompressGen {
    MipmapHandle apply(const CompressionParams& cp, const TextureHandle& src) {
        Log::info("Applying compression ({}) to texture {}", cp.format, src);
        // Implement texture compression and mipmap generation
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace CompressGen

} // namespace TextureAssets
} // namespace MagiTech
