#include "StatusEffectFactory.hpp"
#include "StatusEffectGenerators.hpp"

namespace MagiTech {
namespace StatusEffects {

// A simple hash combine function
template <class T>
inline void hash_combine(std::size_t& seed, const T& v) {
    std::hash<T> hasher;
    seed ^= hasher(v) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

StatusEffectFactory::StatusEffectFactory() {}

StatusEffectFactory::~StatusEffectFactory() {
    shutdown();
}

void StatusEffectFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
}

void StatusEffectFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<EffectBundle> StatusEffectFactory::generateAsync(const StatusEffectParams& s, const UIParams& u) {
    uint64_t key = s.hashKey();
    hash_combine(key, u.hashKey());
    
    if (auto existing = m_cache.find(key)) {
        return std::async(std::launch::deferred, [existing]{ return *existing; });
    }

    return m_pool.enqueue([s, u, this, key] {
        EffectBundle b;
        b.shader    = ShaderGen::build(s);
        b.texture   = TextureGen::build(s);
        b.mesh      = MeshGen::build(s);
        b.particles = ParticleGen::build(s);
        b.icon      = IconGen::build(s, u);
        m_cache.insert(key, b);
        return b;
    });
}

} // namespace StatusEffects
} // namespace MagiTech
