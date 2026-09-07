#pragma once

#include "CosmicAssetBundle.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>

namespace MagiTech {
namespace Cosmic {

// Forward declarations for the generator namespaces
template<typename P>
struct MeshGen {
    static MeshHandle build(const P& p);
};

template<typename P>
struct TextureGen {
    static TextureHandle build(const P& p);
};

template<typename P>
struct ShaderGen {
    static ShaderHandle build(const P& p);
};

template<typename P>
struct EffectsGen {
    static EffectHandle build(const P& p);
};


template<typename P>
class CosmicFactory {
public:
    CosmicFactory() : m_initialized(false) {}
    ~CosmicFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    std::future<AssetBundle> generateAsync(const P& p) {
        uint64_t key = p.hashKey();
        
        if (auto existing = m_cache.find(key)) {
            return std::async(std::launch::deferred, [existing]{ return *existing; });
        }

        return m_pool.enqueue([p, this]() {
            AssetBundle b;
            b.mesh    = MeshGen<P>::build(p);
            b.texture = TextureGen<P>::build(p);
            b.shader  = ShaderGen<P>::build(p);
            b.fx      = EffectsGen<P>::build(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, AssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace Cosmic
} // namespace MagiTech
