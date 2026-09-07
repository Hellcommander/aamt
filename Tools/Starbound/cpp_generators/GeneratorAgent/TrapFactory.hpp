#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "TrapTypes.hpp"

namespace MagiTech {
namespace Traps {

namespace MeshGen {
    MeshHandle buildTrap(const TrapParams& t);
}
namespace TextureGen {
    TextureHandle buildTrap(const TrapParams& t);
}
namespace ShaderGen {
    ShaderHandle buildTrap(const TrapParams& t);
}
namespace PhysGen {
    PhysicsHandle buildTrap(const TrapParams& t, const BehaviorParams& b);
}
namespace ParticleGen {
    ParticleHandle buildTrapFX(const TrapParams& t);
}
namespace AudioGen {
    AudioHandle buildTrapSFX(const TrapParams& t);
}
namespace IconGen {
    TextureHandle buildTrapIcon(const TrapParams& t, const BehaviorParams& b);
}

class TrapFactory {
public:
    TrapFactory() : m_initialized(false) {}
    ~TrapFactory() { shutdown(); }

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
    
    std::future<TrapAssetBundle> generateAsync(const TrapParams& t, const BehaviorParams& b) {
        uint64_t key = t.hashKey() ^ b.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            TrapAssetBundle out;
            out.mesh = MeshGen::buildTrap(t);
            out.texture = TextureGen::buildTrap(t);
            out.shader = ShaderGen::buildTrap(t);
            out.physics = PhysGen::buildTrap(t, b);
            out.particleFX = ParticleGen::buildTrapFX(t);
            out.sfx = AudioGen::buildTrapSFX(t);
            out.icon = IconGen::buildTrapIcon(t, b);
            m_cache.insert(key, out);
            return out;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, TrapAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace Traps
} // namespace MagiTech
