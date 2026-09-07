#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "BeamNetTypes.hpp"

namespace MagiTech {
namespace BeamNets {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildBeamGrid(const BeamNetParams& p);
}
namespace ShaderGen {
    ShaderHandle buildBeamShader(const BeamNetParams& p);
}
namespace ParticleGen {
    ParticleHandle buildIntersectionSparks(const BeamNetParams& p);
}
namespace DecalGen {
    DecalHandle buildScorchDecal(const BeamNetParams& p);
}

class BeamNetFactory {
public:
    BeamNetFactory() : m_initialized(false) {}
    ~BeamNetFactory() { shutdown(); }

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

    std::future<BeamNetAssetBundle> generateAsync(const BeamNetParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            BeamNetAssetBundle b;
            b.netMesh = MeshGen::buildBeamGrid(p);
            b.beamShader = ShaderGen::buildBeamShader(p);
            b.sparkParticles = ParticleGen::buildIntersectionSparks(p);
            b.scorchDecal = DecalGen::buildScorchDecal(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, BeamNetAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace BeamNets
} // namespace MagiTech
