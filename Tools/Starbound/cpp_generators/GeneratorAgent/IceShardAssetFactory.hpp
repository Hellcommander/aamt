#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "IceShardTypes.hpp"

namespace MagiTech {
namespace IceShards {

// Forward declarations for generator functions
namespace ShardGeometryGen {
    std::vector<MeshHandle> build(const IceShardParams& s);
}
namespace FrostTrailGen {
    MeshHandle build(const FrostTrailParams& t, const IceShardParams& s);
}
namespace ShaderGen {
    ShaderHandle build(const FrostVFXParams& v);
}
namespace ParticleGen {
    ParticleHandle buildIceFrost(const FrostParticleParams& p);
}
namespace LightGen {
    LightHandle build(const FrostLightParams& l);
}
namespace AudioGen {
    AudioHandle load(const std::string& file, float vol);
}
namespace CollisionGen {
    ColliderHandle build(const FrostCollisionParams& c, const IceShardParams& s);
}

// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class IceShardAssetFactory {
    ConcurrentLRUCache<uint64_t, IceShardBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    IceShardAssetFactory() = default;
    ~IceShardAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<IceShardBundle> generateAsync(
        const IceShardParams& s,
        const FrostTrailParams& t,
        const FrostVFXParams& v,
        const FrostParticleParams& p,
        const FrostLightParams& l,
        const FrostAudioParams& a,
        const FrostCollisionParams& c
    );
};

} // namespace IceShards
} // namespace MagiTech
