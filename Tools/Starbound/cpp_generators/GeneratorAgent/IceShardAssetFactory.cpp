#include "IceShardAssetFactory.hpp"

namespace MagiTech {
namespace IceShards {

void IceShardAssetFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void IceShardAssetFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<IceShardBundle> IceShardAssetFactory::generateAsync(
    const IceShardParams& s,
    const FrostTrailParams& t,
    const FrostVFXParams& v,
    const FrostParticleParams& p,
    const FrostLightParams& l,
    const FrostAudioParams& a,
    const FrostCollisionParams& c)
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

    return m_pool.enqueue([=]() {
        IceShardBundle b;
        b.shardMeshes = ShardGeometryGen::build(s);
        b.trailMesh = FrostTrailGen::build(t, s);
        b.vfxShader = ShaderGen::build(v);
        if (p.enableParticles) { b.particleSys = ParticleGen::buildIceFrost(p); }
        if (l.enableLight) { b.light = LightGen::build(l); }
        if (a.playOnCast) {
            b.audioWhoosh = AudioGen::load(a.whooshFile, a.volume);
            b.audioCrack = AudioGen::load(a.crackFile, a.volume);
        }
        if (c.enableCollider) { b.collider = CollisionGen::build(c, s); }
        
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace IceShards
} // namespace MagiTech
