#include "MagicalItemFactory.hpp"
#include "MagicalItemGenerators.hpp"

namespace MagiTech {
namespace MagicalItems {

MagicalItemFactory::MagicalItemFactory() {}

MagicalItemFactory::~MagicalItemFactory() {
    shutdown();
}

void MagicalItemFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void MagicalItemFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<MagicalItemBundle> MagicalItemFactory::generateAsync(const MagicalItemParams& p) {
    uint64_t key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        MagicalItemBundle b;
        b.mesh    = MeshGen::buildItemMesh(p);
        b.texture = TextureGen::buildItemTexture(p);
        b.shader  = ShaderGen::buildItemShader(p);
        b.effects = EffectsGen::buildItemEffects(p);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace MagicalItems
} // namespace MagiTech
