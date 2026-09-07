#pragma once
#include <future>
#include <vector>
#include "core/threading/ThreadPool.hpp"
#include "core/ConcurrentLRU.hpp"
#include "AtlasAssetTypes.hpp"

namespace MagiTech {
namespace AtlasAssets {

// Forward declarations for generator functions
namespace SpriteImportGen {
    std::vector<ImportedSprite> import(const std::vector<SpriteParams>& sprites);
}
namespace LayoutGen {
    AtlasLayout createLayout(const std::vector<ImportedSprite>& sprites, const AtlasParams& ap);
}
namespace PackingGen {
    TextureHandle packSprites(const std::vector<ImportedSprite>& sprites, const AtlasLayout& layout, const AtlasParams& ap);
}
namespace MipGen {
    void generate(const TextureHandle& atlas, int levels);
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const MaterialParams& mp, const TextureHandle& atlas);
}
namespace LODGen {
    LODData compute(const LODParams& lp, const TextureHandle& base);
}

class AtlasAssetFactory {
    ConcurrentLRU<uint64_t, AtlasBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    AtlasAssetFactory() = default;
    ~AtlasAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<AtlasBundle> generateAsync(
        const std::vector<SpriteParams>& sprites,
        const AtlasParams& ap,
        const MaterialParams& mp,
        const LODParams& lp
    );
};

} // namespace AtlasAssets
} // namespace MagiTech
