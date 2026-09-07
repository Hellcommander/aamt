#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "GasGrenadeTypes.hpp"

namespace MagiTech {
namespace GasGrenades {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildGasGrenadeBody(const GasGrenadeParams& p);
}
namespace TextureGen {
    TextureHandle buildGasGrenadeTexture(const GasGrenadeParams& p);
}
namespace ShaderGen {
    ShaderHandle buildGasCloudShader(const GasGrenadeParams& p);
}
namespace ParticleGen {
    ParticleHandle buildGasCloud(const GasGrenadeParams& p);
}
namespace PhysGen {
    PhysicsHandle buildGasPhysics(const GasGrenadeParams& p);
}
namespace AudioGen {
    AudioHandle buildGasHiss(const GasGrenadeParams& p);
}
namespace IconGen {
    TextureHandle buildGasIcon(const GasGrenadeParams& p, const UIParams& u);
}

inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class GasGrenadeFactory {
    ConcurrentLRUCache<uint64_t, GrenadeBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    GasGrenadeFactory() = default;
    ~GasGrenadeFactory() { shutdown(); }

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

    std::future<GrenadeBundle> generateAsync(const GasGrenadeParams& p, const UIParams& u) {
        uint64_t key = hashCombine(p.hashKey(), u.hashKey());
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }

        return m_pool.enqueue([=]() {
            GrenadeBundle b;
            b.bodyMesh = MeshGen::buildGasGrenadeBody(p);
            b.bodyTexture = TextureGen::buildGasGrenadeTexture(p);
            b.cloudShader = ShaderGen::buildGasCloudShader(p);
            b.cloudParticles = ParticleGen::buildGasCloud(p);
            b.triggerPhysics = PhysGen::buildGasPhysics(p);
            b.sfxHiss = AudioGen::buildGasHiss(p);
            b.iconTexture = IconGen::buildGasIcon(p, u);
            m_cache.insert(key, b);
            return b;
        });
    }
};

} // namespace GasGrenades
} // namespace MagiTech
