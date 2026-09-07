#include "AtlasAssetFactory.hpp"
#include "core/utils/HashCombine.hpp"
#include <future>

namespace MagiTech {
namespace AtlasAssets {

void AtlasAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.init(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void AtlasAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

uint64_t hashSprites(const std::vector<SpriteParams>& sprites) {
    XXH64_state_t s; XXH64_reset(&s, 0);
    for(const auto& p : sprites) {
        auto h = p.hashKey();
        XXH64_update(&s, &h, sizeof(h));
    }
    return XXH64_digest(&s);
}

std::future<AtlasBundle> AtlasAssetFactory::generateAsync(
    const std::vector<SpriteParams>& sprites,
    const AtlasParams& ap,
    const MaterialParams& mp,
    const LODParams& lp)
{
    uint64_t key = hashCombine(hashSprites(sprites), ap.hashKey(), mp.hashKey(), lp.hashKey());
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }

    return m_pool.enqueue([=]() {
        AtlasBundle b;
        auto imported = SpriteImportGen::import(sprites);
        auto layout = LayoutGen::createLayout(imported, ap);
        b.atlasTex = PackingGen::packSprites(imported, layout, ap);
        if (ap.generateMipmaps) {
            MipGen::generate(b.atlasTex, ap.mipLevels);
        }
        b.uvMap = layout.uvMap;
        b.material = MaterialGen::buildMaterial(mp, b.atlasTex);
        b.lodData = LODGen::compute(lp, b.atlasTex);

        m_cache.insert(key, b);
        return b;
    });
}

} // namespace AtlasAssets
} // namespace MagiTech
