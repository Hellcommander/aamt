#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "IconAssetTypes.hpp"

namespace MagiTech {
namespace IconAssets {

// Forward declarations for generator functions
namespace PrimitiveGen {
    TextureHandle build(PrimitiveShape s, const glm::ivec2& size, const glm::vec4& fill, const glm::vec4& stroke, float strokeW);
}
namespace SVGGen {
    TextureHandle render(const std::string& path, const glm::ivec2& size, const glm::vec4& fill, const glm::vec4& stroke, float strokeW);
}
namespace SDFGen {
    TextureHandle generate(const TextureHandle& src, float padding);
}
namespace AtlasGen {
    TextureHandle packIcons(const std::vector<TextureHandle>& icons, const AtlasParams& ap, const glm::ivec2& iconSize);
    std::vector<glm::vec4> computeUVs(size_t count, int columns, int rows, const glm::ivec2& atlasSize, const glm::ivec2& iconSize, int padding);
}
// TextureLoader would likely be a separate utility
namespace TextureLoader {
    TextureHandle load(const std::string& path);
}


// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}
template <typename T>
uint64_t hashVector(const std::vector<T>& vec) {
    uint64_t seed = vec.size();
    for(const auto& i : vec) {
        seed = hashCombine(seed, i.hashKey());
    }
    return seed;
}

class IconAssetFactory {
    ConcurrentLRUCache<uint64_t, IconAsset> m_cache;
    ConcurrentLRUCache<uint64_t, IconAtlas> m_atlasCache;
    std::unique_ptr<MultithreadBusPlugin> m_pool;
    bool m_initialized = false;

public:
    IconAssetFactory() = default;
    ~IconAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<IconAsset> generateIconAsync(const IconParams& p);
    std::future<IconAtlas> generateAtlasAsync(const std::vector<IconParams>& icons, const AtlasParams& ap);
};

} // namespace IconAssets
} // namespace MagiTech
