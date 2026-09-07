#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "AcidLiquidProjectileTypes.hpp"

namespace MagiTech {
namespace AcidLiquidProjectiles {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildDroplet(const LiquidProjectileParams& p);
}
namespace ParticleGen {
    ParticleHandle buildMist(const LiquidProjectileParams& p);
}
namespace ShaderGen {
    ShaderHandle buildLiquidShader(const LiquidProjectileParams& p);
}
namespace DecalGen {
    DecalHandle buildSplatter(const LiquidProjectileParams& p);
}
namespace PhysicsGen {
    PhysicsHandle buildFluidSystem(const LiquidProjectileParams& p);
}

class AcidLiquidProjectileFactory {
public:
    AcidLiquidProjectileFactory() : m_initialized(false) {}
    ~AcidLiquidProjectileFactory() { shutdown(); }

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

    std::future<LiquidAssetBundle> generateAsync(const LiquidProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            LiquidAssetBundle b;
            b.dropletMesh = MeshGen::buildDroplet(p);
            b.liquidShader = ShaderGen::buildLiquidShader(p);
            b.mistParticles = ParticleGen::buildMist(p);
            b.splatterDecal = DecalGen::buildSplatter(p);
            b.fluidPhysics = PhysicsGen::buildFluidSystem(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, LiquidAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace AcidLiquidProjectiles
} // namespace MagiTech
