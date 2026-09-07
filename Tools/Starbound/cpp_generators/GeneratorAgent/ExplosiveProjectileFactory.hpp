#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "ExplosiveProjectileTypes.hpp"

namespace MagiTech {
namespace ExplosiveProjectiles {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildProjectile(const ExplosiveProjectileParams& p);
    MeshHandle buildFragment(const ExplosiveProjectileParams& p);
}
namespace ParticleGen {
    ParticleHandle buildMotorTrail(const ExplosiveProjectileParams& p);
    ParticleHandle buildSmokeTrail(const ExplosiveProjectileParams& p);
    ParticleHandle buildExplosionFlash(const ExplosiveProjectileParams& p);
    ParticleHandle buildDebris(const ExplosiveProjectileParams& p);
}
namespace ShaderGen {
    ShaderHandle buildProjectileShader(const ExplosiveProjectileParams& p);
}
namespace DecalGen {
    DecalHandle buildScorchDecal(const ExplosiveProjectileParams& p);
}

class ExplosiveProjectileFactory {
public:
    ExplosiveProjectileFactory() : m_initialized(false) {}
    ~ExplosiveProjectileFactory() { shutdown(); }

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

    std::future<ExplosiveAssetBundle> generateAsync(const ExplosiveProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            ExplosiveAssetBundle b;
            b.projectileMesh = MeshGen::buildProjectile(p);
            b.fragmentMesh = MeshGen::buildFragment(p); // A generic shard mesh for instancing
            b.motorTrail = ParticleGen::buildMotorTrail(p);
            b.smokeTrail = ParticleGen::buildSmokeTrail(p);
            b.explosionFlash = ParticleGen::buildExplosionFlash(p);
            b.debrisParticles = ParticleGen::buildDebris(p);
            b.materialShader = ShaderGen::buildProjectileShader(p);
            b.scorchDecal = DecalGen::buildScorchDecal(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, ExplosiveAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace ExplosiveProjectiles
} // namespace MagiTech
