#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "BoomerangDiscTypes.hpp"

namespace MagiTech {
namespace BoomerangDiscs {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildBoomerang(const BoomerangParams& p);
    MeshHandle buildDisc(const ReturningDiscParams& p);
}
namespace PathGen {
    SplineHandle buildReturnPath(float returnDelay, float arcHeight);
}
namespace TrailGen {
    MeshHandle buildRibbon(const BoomerangParams& p);
    MeshHandle buildRimGlow(const ReturningDiscParams& p);
}
namespace ParticleGen {
    ParticleHandle buildAirGust(const BoomerangParams& p);
    ParticleHandle buildGroundDust(const ReturningDiscParams& p);
}
namespace ShaderGen {
    ShaderHandle buildSpinShader(float spinRateRPM);
}

class BoomerangDiscFactory {
public:
    BoomerangDiscFactory() : m_initialized(false) {}
    ~BoomerangDiscFactory() { shutdown(); }

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

    std::future<BoomerangAssetBundle> generateBoomerangAsync(const BoomerangParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_boomerangCache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            BoomerangAssetBundle b;
            b.mesh = MeshGen::buildBoomerang(p);
            b.shader = ShaderGen::buildSpinShader(p.spinRateRPM);
            b.flightPath = PathGen::buildReturnPath(p.returnDelay, p.returnArcHeight);
            b.trailMesh = TrailGen::buildRibbon(p);
            b.airGustFX = ParticleGen::buildAirGust(p);
            m_boomerangCache.insert(key, b);
            return b;
        });
    }

    std::future<DiscAssetBundle> generateDiscAsync(const ReturningDiscParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_discCache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            DiscAssetBundle b;
            b.mesh = MeshGen::buildDisc(p);
            b.shader = ShaderGen::buildSpinShader(p.spinRateRPM);
            b.flightPath = PathGen::buildReturnPath(p.returnDelay, p.returnArcHeight);
            b.rimGlowMesh = TrailGen::buildRimGlow(p);
            b.dustImpactFX = ParticleGen::buildGroundDust(p);
            m_discCache.insert(key, b);
            return b;
        });
    }


private:
    ConcurrentLRUCache<uint64_t, BoomerangAssetBundle> m_boomerangCache;
    ConcurrentLRUCache<uint64_t, DiscAssetBundle> m_discCache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace BoomerangDiscs
} // namespace MagiTech
