#pragma once
#include <future>
#include "core/threading/ThreadPool.hpp"
#include "core/ConcurrentLRU.hpp"
#include "GrappleHookTypes.hpp"

namespace MagiTech {
namespace GrappleHooks {

// Forward declarations for generator functions
namespace HookGen {
    MeshHandle buildHook(const HookParams& hp);
}
namespace ChainGen {
    std::vector<MeshHandle> buildChain(const ChainParams& cp);
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const MaterialParams& mp);
}
namespace PhysicsGen {
    PhysicsAsset buildPhysics(const std::vector<MeshHandle>& links, const PhysicsParams& pp);
}
namespace LODGen {
    LODData compute(const LODParams& lp, MeshHandle hook, const std::vector<MeshHandle>& links);
}
namespace ShaderGen {
    ShaderHandle buildGrappleShader(const MaterialParams& mp);
}

class GrappleAssetFactory {
    ConcurrentLRU<uint64_t, GrappleBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    GrappleAssetFactory() = default;
    ~GrappleAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    std::future<GrappleBundle> generateAsync(
        const HookParams& hp,
        const ChainParams& cp,
        const MaterialParams& mp,
        const PhysicsParams& pp,
        const LODParams& lp
    );
};

} // namespace GrappleHooks
} // namespace MagiTech
