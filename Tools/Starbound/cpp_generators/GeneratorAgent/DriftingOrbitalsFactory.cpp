#include "DriftingOrbitalsFactory.hpp"

namespace MagiTech {
namespace DriftingOrbitals {

void DriftingOrbitalsFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void DriftingOrbitalsFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<DriftingOrbitalsAssetBundle> DriftingOrbitalsFactory::generateAsync(const DriftingOrbitalParams& p) {
    uint64_t key = p.hashKey();
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool.enqueue([=]() {
        DriftingOrbitalsAssetBundle b;

        b.orbitalMeshes.reserve(p.orbCount);
        for(int i = 0; i < p.orbCount; ++i) {
            b.orbitalMeshes.push_back(MeshGen::buildOrb(p));
        }

        if (p.enableTrails) {
            b.trailMeshes.reserve(p.orbCount);
            for(int i = 0; i < p.orbCount; ++i) {
                b.trailMeshes.push_back(TrailGen::build(p));
            }
        }
        
        b.pulseParticleSystem = ParticleGen::buildPulse(p);
        b.orbitalShader = ShaderGen::buildOrbitalShader(p);
        
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace DriftingOrbitals
} // namespace MagiTech
