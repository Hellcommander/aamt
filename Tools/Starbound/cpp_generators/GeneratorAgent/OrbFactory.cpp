#include "OrbFactory.hpp"
#include "OrbGenerators.hpp"

namespace MagiTech {
namespace Orbs {

OrbFactory::OrbFactory() {}

OrbFactory::~OrbFactory() {
    shutdown();
}

void OrbFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void OrbFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<OrbBundle> OrbFactory::generateAsync(const OrbParams& p) {
    auto key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        OrbBundle b;
        b.mesh    = MeshGen::buildOrbMesh(p);
        b.texture = TextureGen::buildOrbTexture(p);
        b.shader  = ShaderGen::buildOrbShader(p);
        b.effects = EffectsGen::buildOrbEffects(p);
        m_cache.insert(p.hashKey(), b);
        return b;
    });
}

} // namespace Orbs
} // namespace MagiTech
