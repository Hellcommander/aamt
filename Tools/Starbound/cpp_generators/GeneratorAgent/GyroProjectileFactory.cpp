#include "GyroProjectileFactory.hpp"

namespace MagiTech {
namespace GyroProjectiles {

void GyroProjectileFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void GyroProjectileFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<GyroAssetBundle> GyroProjectileFactory::generateAsync(
    const GyroParams& g,
    const FlightParams& f,
    const TrailParams& t,
    const VFXParams& v,
    const ParticleParams& p,
    const AudioParams& a,
    const CollisionParams& c)
{
    uint64_t key = g.hashKey();
    key = hashCombine(key, f.hashKey());
    key = hashCombine(key, t.hashKey());
    key = hashCombine(key, v.hashKey());
    key = hashCombine(key, p.hashKey());
    key = hashCombine(key, a.hashKey());
    key = hashCombine(key, c.hashKey());

    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool.enqueue([=]() {
        GyroAssetBundle b;
        b.mesh = MeshGen::buildGyroMesh(g);
        b.flightSim = FlightSim::setupGyro(g, f);
        if (t.enableTrail) { b.trailMesh = TrailGen::buildGyroTrail(t); }
        b.vfxShader = ShaderGen::buildVFX(v);
        if (p.enableParticles) { b.particleSys = ParticleGen::buildGyroParticles(p); }
        if (a.playOnLaunch) {
            b.humAudio = AudioGen::load(a.humFile, a.volume, a.pitchVariance);
            b.impactAudio = AudioGen::load(a.impactFile, a.volume);
        }
        if (c.enableCollider) { b.collider = CollisionGen::buildGyroCollider(c); }

        m_cache.insert(key, b);
        return b;
    });
}

} // namespace GyroProjectiles
} // namespace MagiTech
