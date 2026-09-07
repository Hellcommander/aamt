#include "SpellstoneFactory.hpp"
#include "SpellstoneGenerators.hpp"

namespace MagiTech {
namespace Spellstones {

SpellstoneFactory::SpellstoneFactory() {}

SpellstoneFactory::~SpellstoneFactory() {
    shutdown();
}

void SpellstoneFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void SpellstoneFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<SpellstoneBundle> SpellstoneFactory::generateAsync(const SpellstoneParams& p) {
    uint64_t key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        SpellstoneBundle b;
        b.bodyMesh   = MeshGen::buildBody(p);
        b.surfaceTex = TextureGen::buildSurface(p);
        b.bodyShader = ShaderGen::buildBodyShader(p);
        b.idleFX     = EffectsGen::buildIdle(p);
        b.castFX     = EffectsGen::buildBeam(p);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace Spellstones
} // namespace MagiTech
