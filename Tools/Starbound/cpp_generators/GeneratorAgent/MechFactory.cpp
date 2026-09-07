#include "MechFactory.hpp"
#include "MechGenerators.hpp"

namespace MagiTech {
namespace Mechs {

MechFactory::MechFactory() {}

MechFactory::~MechFactory() {
    shutdown();
}

void MechFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void MechFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<MechBundle> MechFactory::generateAsync(MechParams p) {
    uint64_t key = p.hashKey();
    
    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [hit]{ return *hit; });
    }
    
    return m_pool.enqueue([p, this]{
        auto mesh     = MeshGenerator::buildMechMesh(p);
        auto tex      = TextureGenerator::buildMechSkin(p);
        auto skel     = SkeletonGenerator::buildRig(p);
        MechBundle b{mesh, tex, skel};
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace Mechs
} // namespace MagiTech
