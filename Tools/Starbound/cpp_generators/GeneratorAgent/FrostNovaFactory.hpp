#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "FrostNovaTypes.hpp"

namespace MagiTech {
namespace FrostNovas {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildNovaRing(const FrostNovaParams& p);
    MeshHandle buildIceShard(const FrostNovaParams& p);
}
namespace ParticleGen {
    ParticleHandle buildFrostAura(const FrostNovaParams& p);
    ParticleHandle buildCrystalSparkles(const FrostNovaParams& p);
}
namespace ShaderGen {
    ShaderHandle buildFrostShader(const FrostNovaParams& p);
}
namespace DecalGen {
    DecalHandle buildFrostbiteDecal(const FrostNovaParams& p);
}


class FrostNovaFactory {
public:
    FrostNovaFactory() : m_initialized(false) {}
    ~FrostNovaFactory() { shutdown(); }

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

    std::future<FrostNovaAssetBundle> generateAsync(const FrostNovaParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            FrostNovaAssetBundle b;
            b.ringMesh = MeshGen::buildNovaRing(p);
            b.shardMesh = MeshGen::buildIceShard(p);
            b.auraParticles = ParticleGen::buildFrostAura(p);
            b.sparkleParticles = ParticleGen::buildCrystalSparkles(p);
            b.frostShader = ShaderGen::buildFrostShader(p);
            b.frostDecal = DecalGen::buildFrostbiteDecal(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, FrostNovaAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace FrostNovas
} // namespace MagiTech
