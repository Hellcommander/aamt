#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "SpellProjectileTypes.hpp"

namespace MagiTech {
namespace SpellProjectiles {

// Forward declarations for generator functions
namespace GeometryGen {
    MeshHandle build(const SpellParams& s);
}
namespace TrailGen {
    MeshHandle build(const TrailParams& t, const SpellParams& s);
}
namespace ShaderGen {
    ShaderHandle build(const VFXParams& v);
}
namespace ParticleGen {
    ParticleHandle build(const ParticleParams& p);
}
namespace LightGen {
    LightHandle build(const LightParams& l);
}
namespace AudioGen {
    AudioHandle build(const AudioParams& a);
}
namespace CollisionGen {
    ColliderHandle build(const CollisionParams& c, const SpellParams& s);
}

// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class SpellAssetFactory {
    ConcurrentLRUCache<uint64_t, SpellAssetBundle> m_cache;
    std::unique_ptr<MultithreadBusPlugin> m_pool;
    bool m_initialized = false;

public:
    SpellAssetFactory() = default;
    ~SpellAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<SpellAssetBundle> generateAsync(
        const SpellParams&    s,
        const TrailParams&    t,
        const VFXParams&      v,
        const ParticleParams& p,
        const LightParams&    l,
        const AudioParams&    a,
        const CollisionParams&c
    );
};

} // namespace SpellProjectiles
} // namespace MagiTech
