#include "GrappleAssetFactory.hpp"
#include "core/utils/HashCombine.hpp"
#include <future>

namespace MagiTech {
namespace GrappleHooks {

void GrappleAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.init(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void GrappleAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<GrappleBundle> GrappleAssetFactory::generateAsync(
    const HookParams& hp,
    const ChainParams& cp,
    const MaterialParams& mp,
    const PhysicsParams& pp,
    const LODParams& lp)
{
    uint64_t key = hashCombine(hp.hashKey(), cp.hashKey(), mp.hashKey(), pp.hashKey(), lp.hashKey());
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=]() { return *hit; });
    }

    return m_pool.enqueue([=]() {
        GrappleBundle b;
        b.hookMesh = HookGen::buildHook(hp);
        b.chainMeshes = ChainGen::buildChain(cp);
        b.material = MaterialGen::buildMaterial(mp);
        if (pp.enablePhysics) {
            b.physics = PhysicsGen::buildPhysics(b.chainMeshes, pp);
        }
        b.lodData = LODGen::compute(lp, b.hookMesh, b.chainMeshes);
        b.shader = ShaderGen::buildGrappleShader(mp);
        
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace GrappleHooks
} // namespace MagiTech
