#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "CockpitTypes.hpp"

namespace MagiTech {
namespace Cockpits {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildSeat(const CockpitParams& p);
    MeshHandle buildCanopy(const CockpitParams& p);
    MeshHandle buildConsole(const CockpitParams& p);
    MeshHandle buildGauges(const CockpitParams& p);
    MeshHandle buildHUD(const CockpitParams& p);
}
namespace ShaderGen {
    ShaderHandle buildGlassShader(const CockpitParams& p);
    ShaderHandle buildScreenShader(const CockpitParams& p);
}
namespace AnimGen {
    AnimationHandle buildCanopyAnimation(const CockpitParams& p);
}
namespace DecalGen {
    DecalHandle buildUIDecals(const CockpitParams& p);
}
namespace PhysGen {
    PhysicsHandle buildCollision(const CockpitParams& p);
}

class CockpitFactory {
public:
    CockpitFactory() : m_initialized(false) {}
    ~CockpitFactory() { shutdown(); }

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

    std::future<CockpitAssetBundle> generateAsync(const CockpitParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            CockpitAssetBundle b;
            b.seatMesh = MeshGen::buildSeat(p);
            b.canopyMesh = MeshGen::buildCanopy(p);
            b.consoleMesh = MeshGen::buildConsole(p);
            b.gaugeMesh = MeshGen::buildGauges(p);
            if(p.holographicHUD) b.hudMesh = MeshGen::buildHUD(p);
            
            b.glassShader = ShaderGen::buildGlassShader(p);
            b.screenShader = ShaderGen::buildScreenShader(p);
            
            if(p.canopyAnimEnabled) b.canopyAnimation = AnimGen::buildCanopyAnimation(p);
            
            b.uiDecals = DecalGen::buildUIDecals(p);
            b.collisionVolume = PhysGen::buildCollision(p);
            
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, CockpitAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace Cockpits
} // namespace MagiTech
