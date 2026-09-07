#include "ProjectileFactory.hpp"
#include "ProjectileGenerators.hpp"

namespace MagiTech {
namespace Projectiles {

ProjectileFactory::ProjectileFactory() {}

ProjectileFactory::~ProjectileFactory() {
    shutdown();
}

void ProjectileFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void ProjectileFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<ProjectileBundle> ProjectileFactory::generateAsync(const ProjectileParams& p) {
    uint64_t key = p.hashKey();
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([p, this] {
        ProjectileBundle b;
        b.mesh         = MeshGen::buildMesh(p);
        b.texture      = TextureGen::buildTexture(p);
        b.shader       = ShaderGen::buildShader(p);
        b.trailEffect  = EffectsGen::buildTrail(p);
        b.impactEffect = EffectsGen::buildImpact(p);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace Projectiles
} // namespace MagiTech
