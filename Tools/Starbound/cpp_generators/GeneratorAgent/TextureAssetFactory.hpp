#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "TextureAssetTypes.hpp"

namespace MagiTech {
namespace TextureAssets {

// Forward declarations for generator functions
namespace NoiseGen {
    TextureHandle build(const NoiseParams& np, const glm::ivec2& res, int seed, bool seamless);
}
namespace MaskGen {
    TextureHandle build(const MaskParams& mp, const glm::ivec2& res);
}
namespace PBRGen {
    TextureHandle build(const PBRParams& pp, const glm::ivec2& res);
}
namespace AtlasGen {
    TextureHandle pack(const AtlasParams& ap);
}
namespace CompressGen {
    MipmapHandle apply(const CompressionParams& cp, const TextureHandle& src);
}

// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class TextureAssetFactory {
    ConcurrentLRUCache<uint64_t, TextureAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    TextureAssetFactory() = default;
    ~TextureAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    std::future<TextureAssetBundle> generateAsync(
        const TextureParams& t,
        std::optional<NoiseParams> n = std::nullopt,
        std::optional<MaskParams> m = std::nullopt,
        std::optional<PBRParams> p = std::nullopt,
        std::optional<AtlasParams> a = std::nullopt,
        std::optional<CompressionParams> c = std::nullopt
    );
};

} // namespace TextureAssets
} // namespace MagiTech
