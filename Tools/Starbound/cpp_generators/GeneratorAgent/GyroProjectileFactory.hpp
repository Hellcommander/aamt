#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "GyroProjectileTypes.hpp"

namespace MagiTech {
namespace GyroProjectiles {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildGyroMesh(const GyroParams& g);
}
namespace FlightSim {
    SimulationHandle setupGyro(const GyroParams& g, const FlightParams& f);
}
namespace TrailGen {
    MeshHandle buildGyroTrail(const TrailParams& t);
}
namespace ShaderGen {
    ShaderHandle buildVFX(const VFXParams& v);
}
namespace ParticleGen {
    ParticleHandle buildGyroParticles(const ParticleParams& p);
}
namespace AudioGen {
    AudioHandle load(const std::string& file, float vol, float pitchVar = 0.0f);
}
namespace CollisionGen {
    ColliderHandle buildGyroCollider(const CollisionParams& c);
}

// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class GyroProjectileFactory {
    ConcurrentLRUCache<uint64_t, GyroAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    GyroProjectileFactory() = default;
    ~GyroProjectileFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<GyroAssetBundle> generateAsync(
        const GyroParams& g,
        const FlightParams& f,
        const TrailParams& t,
        const VFXParams& v,
        const ParticleParams& p,
        const AudioParams& a,
        const CollisionParams& c
    );
};

} // namespace GyroProjectiles
} // namespace MagiTech
