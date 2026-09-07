#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "BlackholeProjectileTypes.hpp"

namespace MagiTech {
namespace BlackholeProjectiles {

// Forward declare generator functions
namespace MeshGen {
    MeshHandle buildEventHorizon(const BlackholeProjectileParams& p);
    MeshHandle buildAccretionDisk(const BlackholeProjectileParams& p);
    MeshHandle buildWarpTrail(const BlackholeProjectileParams& p);
}
namespace ShaderGen {
    ShaderHandle buildWarpShader(const BlackholeProjectileParams& p);
}
namespace TextureGen {
    TextureHandle buildDiskTexture(const BlackholeProjectileParams& p);
}
namespace ParticleGen {
    ParticleHandle buildVortex(const BlackholeProjectileParams& p);
}
namespace AudioGen {
    AudioHandle buildRumble(const BlackholeProjectileParams& p);
}

class BlackholeProjectileFactory {
public:
    BlackholeProjectileFactory() : m_initialized(false) {}
    ~BlackholeProjectileFactory() { shutdown(); }

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

    std::future<BlackholeAssetBundle> generateAsync(const BlackholeProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            BlackholeAssetBundle b;
            b.coreMesh = MeshGen::buildEventHorizon(p);
            b.diskMesh = MeshGen::buildAccretionDisk(p);
            b.trailMesh = MeshGen::buildWarpTrail(p);
            b.warpShader = ShaderGen::buildWarpShader(p);
            b.diskTexture = TextureGen::buildDiskTexture(p);
            b.vortexParticles = ParticleGen::buildVortex(p);
            b.sfx = AudioGen::buildRumble(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, BlackholeAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace BlackholeProjectiles
} // namespace MagiTech
