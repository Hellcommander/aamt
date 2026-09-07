#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "HomingMissileTypes.hpp"

namespace MagiTech {
namespace HomingMissiles {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildMissile(const HomingMissileParams& p);
}
namespace PathGen {
    SplineHandle buildGuidanceSpline(const HomingMissileParams& p);
}
namespace TrailGen {
    MeshHandle buildDynamicRibbon(const HomingMissileParams& p);
}
namespace ParticleGen {
    ParticleHandle buildExhaustFlame(const HomingMissileParams& p);
    ParticleHandle buildExhaustSmoke(const HomingMissileParams& p);
}
namespace ShaderGen {
    ShaderHandle buildMissileShader(const HomingMissileParams& p);
}

class HomingMissileFactory {
public:
    HomingMissileFactory() : m_initialized(false) {}
    ~HomingMissileFactory() { shutdown(); }

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

    std::future<MissileAssetBundle> generateAsync(const HomingMissileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            MissileAssetBundle b;
            b.missileMesh = MeshGen::buildMissile(p);
            b.guidancePath = PathGen::buildGuidanceSpline(p);
            b.trailMesh = TrailGen::buildDynamicRibbon(p);
            b.bodyShader = ShaderGen::buildMissileShader(p);
            b.flameExhaust = ParticleGen::buildExhaustFlame(p);
            b.smokeExhaust = ParticleGen::buildExhaustSmoke(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, MissileAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace HomingMissiles
} // namespace MagiTech
