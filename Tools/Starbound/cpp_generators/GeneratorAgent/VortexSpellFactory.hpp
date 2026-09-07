#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "VortexSpellTypes.hpp"

namespace MagiTech {
namespace VortexSpells {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildVortexMesh(const VortexSpellParams& p);
    MeshHandle buildWindRibbons(const VortexSpellParams& p);
}
namespace ParticleGen {
    ParticleHandle buildDustCloud(const VortexSpellParams& p);
    ParticleHandle buildDebris(const VortexSpellParams& p);
}
namespace ShaderGen {
    ShaderHandle buildVortexShader(const VortexSpellParams& p);
}
namespace DecalGen {
    DecalHandle buildGroundCracks(const VortexSpellParams& p);
}

class VortexSpellFactory {
public:
    VortexSpellFactory() : m_initialized(false) {}
    ~VortexSpellFactory() { shutdown(); }

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

    std::future<VortexSpellAssetBundle> generateAsync(const VortexSpellParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            VortexSpellAssetBundle b;
            b.vortexMesh = MeshGen::buildVortexMesh(p);
            b.dustParticles = ParticleGen::buildDustCloud(p);
            b.debrisParticles = ParticleGen::buildDebris(p);
            b.windRibbons = MeshGen::buildWindRibbons(p);
            b.vortexShader = ShaderGen::buildVortexShader(p);
            b.groundDecal = DecalGen::buildGroundCracks(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, VortexSpellAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace VortexSpells
} // namespace MagiTech
