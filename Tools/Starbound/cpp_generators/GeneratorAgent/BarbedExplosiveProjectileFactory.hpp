#pragma once
#include <future>
#include "core/threading/ThreadPool.hpp"
#include "BarbedExplosiveProjectileTypes.hpp"

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

// Forward declarations for generator functions
namespace MeshGen {
    std::vector<MeshHandle> buildBarbedMesh(const GeometryParams& p);
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const VisualParams& p);
}
namespace ExplosionGen {
    ExplosionHandle buildExplosion(const ExplosionParams& p);
}

class BarbedExplosiveProjectileFactory {
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    BarbedExplosiveProjectileFactory() = default;
    ~BarbedExplosiveProjectileFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<BarbedExplosiveProjectileBundle> generateAsync(
        const GeometryParams& gp,
        const ExplosionParams& ep,
        const VisualParams& vp
    );
};

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
