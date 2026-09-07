#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "DriftingOrbitalsTypes.hpp"

namespace MagiTech {
namespace DriftingOrbitals {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildOrb(const DriftingOrbitalParams& p);
}
namespace TrailGen {
    MeshHandle build(const DriftingOrbitalParams& p);
}
namespace ParticleGen {
    ParticleHandle buildPulse(const DriftingOrbitalParams& p);
}
namespace ShaderGen {
    ShaderHandle buildOrbitalShader(const DriftingOrbitalParams& p);
}

class DriftingOrbitalsFactory {
    ConcurrentLRUCache<uint64_t, DriftingOrbitalsAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    DriftingOrbitalsFactory() = default;
    ~DriftingOrbitalsFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<DriftingOrbitalsAssetBundle> generateAsync(const DriftingOrbitalParams& p);
};

} // namespace DriftingOrbitals
} // namespace MagiTech
