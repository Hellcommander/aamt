#pragma once
#include <future>
#include <vector>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "ClusterBombTypes.hpp"

namespace MagiTech {
namespace ClusterBombs {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildBombCasing(const ClusterBombParams& p);
    MeshHandle buildFragment(const ClusterBombParams& p);
}
namespace PhysicsGen {
    PhysicsHandle buildFuse(const ClusterBombParams& p);
}
namespace FragmentGen {
    std::vector<FragmentAsset> generateFragments(const ClusterBombParams& p);
}
namespace ParticleGen {
    ParticleHandle buildExplosionCore(const ClusterBombParams& p);
    ParticleHandle buildSmokeRing(const ClusterBombParams& p);
    ParticleHandle buildDebris(const ClusterBombParams& p);
}
namespace ShaderGen {
    ShaderHandle buildCasingShader(const ClusterBombParams& p);
}

class ClusterBombFactory {
public:
    ClusterBombFactory() : m_initialized(false) {}
    ~ClusterBombFactory() { shutdown(); }

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

    std::future<BombAssetBundle> generateAsync(const ClusterBombParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            BombAssetBundle b;
            b.casingMesh = MeshGen::buildBombCasing(p);
            b.casingShader = ShaderGen::buildCasingShader(p);
            b.fuseHandle = PhysicsGen::buildFuse(p);
            b.explosionCoreFX = ParticleGen::buildExplosionCore(p);
            b.smokeRingFX = ParticleGen::buildSmokeRing(p);
            b.debrisFX = ParticleGen::buildDebris(p);
            // Note: Fragments are generated separately on detonation, not cached here.
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, BombAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace ClusterBombs
} // namespace MagiTech
