#include "DynamicAssetManager.hpp"
#include "DynamicAssetGenerator.hpp"

namespace MagiTech {
namespace DynamicAssets {

DynamicAssetManager::DynamicAssetManager() {}

DynamicAssetManager::~DynamicAssetManager() {
    shutdown();
}

void DynamicAssetManager::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void DynamicAssetManager::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<AssetBundle> DynamicAssetManager::generateAsync(const SpellstoneParams& p) {
    uint64_t key = p.constexprKey();
    
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [hit]{ return *hit; });
    }
    
    return m_pool.enqueue([p, this]{
        auto tex  = TextureGenerator::makeAnimatedGlow(p);
        auto mesh = MeshGenerator::makeFacetedGem(p);
        AssetBundle b{tex, mesh};
        m_cache.insert(p.constexprKey(), b);
        return b;
    });
}

} // namespace DynamicAssets
} // namespace MagiTech
