#pragma once
#include <future>
#include <vector>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "ShotgunPelletTypes.hpp"

namespace MagiTech {
namespace ShotgunPellets {

// Forward declarations of generator functions
namespace MeshGen {
    MeshHandle buildPellet(const ShotgunPelletParams& p);
}
namespace SpreadGen {
    std::vector<glm::vec3> generateDirections(const ShotgunPelletParams& p);
}
namespace ComputeGen {
    ComputeBufferHandle createInstanceBuffer(const ShotgunPelletParams& p);
}
namespace TrailGen {
    ShaderHandle buildTrailShader(const ShotgunPelletParams& p); // Trails are often shader-based
}
namespace ShaderGen {
    ShaderHandle buildPelletShader(const ShotgunPelletParams& p);
}
namespace DecalGen {
    DecalHandle buildImpactDecal(const ShotgunPelletParams& p);
}

class ShotgunPelletFactory {
public:
    ShotgunPelletFactory() : m_initialized(false) {}
    ~ShotgunPelletFactory() { shutdown(); }

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

    std::future<ShotgunAssetBundle> generateAsync(const ShotgunPelletParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            ShotgunAssetBundle b;
            b.pelletMesh = MeshGen::buildPellet(p);
            b.pelletShader = ShaderGen::buildPelletShader(p);
            b.instanceBuffer = ComputeGen::createInstanceBuffer(p);
            b.impactDecal = DecalGen::buildImpactDecal(p);
            // Spread patterns and trails are typically handled at runtime, not pre-baked into a bundle.
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, ShotgunAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace ShotgunPellets
} // namespace MagiTech
