#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "SnakeMechTypes.hpp"

namespace MagiTech {
namespace SnakeMechs {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildMech(const SnakeMechParams& p);
}
namespace RigGen {
    SkeletonHandle buildSkeleton(const SnakeMechParams& p);
}
namespace AnimGen {
    AnimationHandle buildWaveAnimation(const SnakeMechParams& p);
}
namespace ShaderGen {
    ShaderHandle buildMechShader(const SnakeMechParams& p);
}
namespace ParticleGen {
    ParticleHandle buildJointSparks(const SnakeMechParams& p);
}
namespace PhysGen {
    PhysicsHandle buildPhysicsAsset(const SnakeMechParams& p);
}


class SnakeMechFactory {
public:
    SnakeMechFactory() : m_initialized(false) {}
    ~SnakeMechFactory() { shutdown(); }

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

    std::future<SnakeMechAssetBundle> generateAsync(const SnakeMechParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            SnakeMechAssetBundle b;
            b.segmentMesh = MeshGen::buildMech(p);
            b.skeleton = RigGen::buildSkeleton(p);
            b.proceduralAnimation = AnimGen::buildWaveAnimation(p);
            b.materialShader = ShaderGen::buildMechShader(p);
            b.sparkParticles = ParticleGen::buildJointSparks(p);
            b.physicsAsset = PhysGen::buildPhysicsAsset(p);
            m_cache.insert(key, b);
            return b;
        });
    }

private:
    ConcurrentLRUCache<uint64_t, SnakeMechAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
};

} // namespace SnakeMechs
} // namespace MagiTech
