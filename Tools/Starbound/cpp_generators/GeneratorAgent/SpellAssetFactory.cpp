#include "SpellAssetFactory.hpp"
#include <stdexcept>

namespace MagiTech {
namespace SpellProjectiles {

void SpellAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized = true;
}

void SpellAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.reset();
    m_initialized = false;
}

std::future<SpellAssetBundle> SpellAssetFactory::generateAsync(
    const SpellParams&    s,
    const TrailParams&    t,
    const VFXParams&      v,
    const ParticleParams& p,
    const LightParams&    l,
    const AudioParams&    a,
    const CollisionParams&c)
{
    uint64_t key = s.hashKey();
    key = hashCombine(key, t.hashKey());
    key = hashCombine(key, v.hashKey());
    key = hashCombine(key, p.hashKey());
    key = hashCombine(key, l.hashKey());
    key = hashCombine(key, a.hashKey());
    key = hashCombine(key, c.hashKey());

    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool->enqueue([=]() {
        SpellAssetBundle b;
        
        // Generate core geometry
        b.geometry = GeometryGen::build(s);
        
        // Generate trail mesh if enabled
        if (t.enableTrail) {
            b.trailMesh = TrailGen::build(t, s);
        }
        
        // Generate VFX shader
        b.vfxShader = ShaderGen::build(v);
        
        // Generate particle system if enabled
        if (p.enableParticles) {
            b.particleSystem = ParticleGen::build(p);
        }
        
        // Generate dynamic light if enabled
        if (l.enableLight) {
            b.dynamicLight = LightGen::build(l);
        }
        
        // Generate audio cue if enabled
        if (a.playOnCast) {
            b.audioCue = AudioGen::build(a);
        }
        
        // Generate collision if enabled
        if (c.enableCollider) {
            b.collider = CollisionGen::build(c, s);
        }
        
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace SpellProjectiles
} // namespace MagiTech
