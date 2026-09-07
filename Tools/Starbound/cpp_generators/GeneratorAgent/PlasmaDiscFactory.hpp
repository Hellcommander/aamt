#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "PlasmaDiscTypes.hpp"

namespace MagiTech {
namespace PlasmaDiscs {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildDisc(const PlasmaDiscParams& p);
}
namespace ShaderGen {
    ShaderHandle buildDiscShader(const PlasmaDiscParams& p);
}
namespace TrailGen {
    TrailHandle buildDiscTrail(const PlasmaDiscParams& p);
}
namespace ParticleGen {
    ParticleHandle buildImpactSparks(const PlasmaDiscParams& p);
}

class PlasmaDiscFactory {
public:
    PlasmaDiscFactory() : m_initialized(false) {}
    ~PlasmaDiscFactory() { shutdown(); }

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

    std::future<PlasmaDiscAssetBundle> generateAsync(const PlasmaDiscParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            PlasmaDiscAssetBundle b;
            b.discMesh = MeshGen::buildDisc(p);
            b.discShader = ShaderGen::buildDiscShader(p);
            if (p.enableTrail) {
                b.trail = TrailGen::buildDiscTrail(p);
            }
            b.sparkParticles = ParticleGen::buildImpactSparks(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, PlasmaDiscAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace PlasmaDiscs
} // namespace MagiTech
