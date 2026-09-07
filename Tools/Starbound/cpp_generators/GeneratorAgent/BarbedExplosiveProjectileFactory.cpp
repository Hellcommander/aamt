#include "BarbedExplosiveProjectileFactory.hpp"

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

void BarbedExplosiveProjectileFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void BarbedExplosiveProjectileFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<BarbedExplosiveProjectileBundle> BarbedExplosiveProjectileFactory::generateAsync(
    const GeometryParams& gp,
    const ExplosionParams& ep,
    const VisualParams& vp)
{
    return m_pool.enqueue([=]() {
        BarbedExplosiveProjectileBundle b;
        b.lods = MeshGen::buildBarbedMesh(gp);
        b.material = MaterialGen::buildMaterial(vp);
        b.explosionEffect = ExplosionGen::buildExplosion(ep);
        return b;
    });
}

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
