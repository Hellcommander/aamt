#include "TextureAssetFactory.hpp"
#include "core/Log.hpp"
#include "vendor/xxhash/xxhash.h"
#include <atomic>

namespace MagiTech {
namespace TextureAssets {

#define LOG_TEX_GEN(Asset, Id) Log::info("TextureGen", "Building Texture Asset {}: {}", #Asset, Id)

namespace {
    // Field-wise hashing (raw struct bytes would include padding and heap pointers).
    struct Hasher {
        XXH64_state_t state;
        Hasher() { XXH64_reset(&state, 0); }
        template <typename T>
        Hasher& pod(const T& v) { XXH64_update(&state, &v, sizeof(T)); return *this; }
        Hasher& str(const std::string& v) {
            pod(static_cast<uint64_t>(v.size()));
            XXH64_update(&state, v.data(), v.size());
            return *this;
        }
        uint64_t digest() { return XXH64_digest(&state); }
    };
}

// Hash function implementations
uint64_t TextureParams::hashKey() const {
    return Hasher().str(id).pod(type).pod(resolution.x).pod(resolution.y)
                   .pod(uvScale).pod(seed).pod(seamless).digest();
}
uint64_t NoiseParams::hashKey() const {
    return Hasher().str(noiseType).pod(octaves).pod(frequency).pod(lacunarity).pod(gain).digest();
}
uint64_t MaskParams::hashKey() const {
    Hasher h;
    h.pod(static_cast<uint64_t>(stops.size()));
    for (const auto& [position, color] : stops) {
        h.pod(position).pod(color.r).pod(color.g).pod(color.b).pod(color.a);
    }
    return h.pod(invert).pod(gaussianBlur).pod(blurRadius).digest();
}
uint64_t PBRParams::hashKey() const {
    return Hasher().pod(baseColorTint.r).pod(baseColorTint.g).pod(baseColorTint.b).pod(baseColorTint.a)
                   .pod(metallic).pod(roughness).pod(ambientOcclusion).pod(bakeHeight).pod(heightScale).digest();
}
uint64_t AtlasParams::hashKey() const {
    Hasher h;
    h.pod(static_cast<uint64_t>(sources.size()));
    for (TextureHandle src : sources) h.pod(src);
    return h.pod(padding).pod(maxWidth).pod(maxHeight).pod(generateUDIM).digest();
}
uint64_t CompressionParams::hashKey() const {
    return Hasher().str(format).pod(quality).pod(generateMipmaps).pod(sRGB).digest();
}

namespace NoiseGen {
    TextureHandle build(const NoiseParams& np, const glm::ivec2& res, int seed, bool seamless) {
        LOG_TEX_GEN(Noise, np.noiseType);
        // Implement noise generation (Perlin, Simplex, etc.)
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace NoiseGen

namespace MaskGen {
    TextureHandle build(const MaskParams& mp, const glm::ivec2& res) {
        LOG_TEX_GEN(Mask, "CustomMask");
        // Implement mask generation from stops/blur
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace MaskGen

namespace PBRGen {
    TextureHandle build(const PBRParams& pp, const glm::ivec2& res) {
        LOG_TEX_GEN(PBR, "MaterialMap");
        // Implement PBR channel packing
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace PBRGen

namespace AtlasGen {
    TextureHandle pack(const AtlasParams& ap) {
        LOG_TEX_GEN(Atlas, "TextureAtlas");
        // Implement texture packing
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace AtlasGen

namespace CompressGen {
    MipmapHandle apply(const CompressionParams& cp, const TextureHandle& src) {
        Log::info("TextureGen", "Applying compression ({}) to texture {}", cp.format, src);
        // Implement texture compression and mipmap generation
        static std::atomic<uint32_t> nextHandle{1};
        return nextHandle++;
    }
} // namespace CompressGen

} // namespace TextureAssets
} // namespace MagiTech
