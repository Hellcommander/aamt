#include "BeamFactory.hpp"
#include "BeamGenerators.hpp"

namespace MagiTech {
namespace Beams {

BeamFactory::BeamFactory() {}

BeamFactory::~BeamFactory() {
    shutdown();
}

void BeamFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void BeamFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<BeamBundle> BeamFactory::generateAsync(const BeamParams& p) {
    uint64_t key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        BeamBundle b;
        b.ribbonMesh = MeshGen::buildBeamRibbon(p);
        b.beamTex    = TextureGen::buildBeamTexture(p);
        b.beamShader = ShaderGen::buildBeamShader(p);
        b.muzzleFX   = EffectsGen::buildMuzzle(p);
        b.impactFX   = EffectsGen::buildImpact(p);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace Beams
} // namespace MagiTech
