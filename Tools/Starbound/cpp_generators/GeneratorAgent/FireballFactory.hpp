#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "FireballTypes.hpp"

namespace MagiTech {
namespace Fireballs {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildCore(const FireballParams& p);
    MeshHandle buildFlames(const FireballParams& p);
}
namespace ParticleGen {
    ParticleSystemHandle buildEmbers(const FireballParams& p);
    ParticleSystemHandle buildSmokeTrail(const FireballParams& p);
}
namespace ShaderGen {
    ShaderHandle buildFireShader(const FireballParams& p);
}
namespace DecalGen {
    DecalHandle buildScorchMark(const FireballParams& p);
}
namespace PhysGen {
    PhysicsHandle buildBehavior(const FireballParams& p);
}

class FireballFactory {
public:
    FireballFactory() : m_initialized(false) {}
    ~FireballFactory() { shutdown(); }

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

    std::future<FireballAssetBundle> generateAsync(const FireballParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            FireballAssetBundle b;
            b.coreMesh = MeshGen::buildCore(p);
            b.flameMesh = MeshGen::buildFlames(p);
            b.emberParticles = ParticleGen::buildEmbers(p);
            b.smokeParticles = ParticleGen::buildSmokeTrail(p);
            b.fireShader = ShaderGen::buildFireShader(p);
            b.scorchDecal = DecalGen::buildScorchMark(p);
            b.physicsData = PhysGen::buildBehavior(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, FireballAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace Fireballs
} // namespace MagiTech
