#pragma once
#include <future>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "DroneMinionTypes.hpp"

namespace MagiTech {
namespace DroneMinions {

// Forward declarations for generator functions
namespace MeshGen {
    MeshHandle buildDroneBody(const DroneMinionParams& p);
    MeshHandle buildDroneRotors(const DroneMinionParams& p);
}
namespace TextureGen {
    TextureHandle buildDroneTexture(const DroneMinionParams& p);
}
namespace ShaderGen {
    ShaderHandle buildDroneShader(const DroneMinionParams& p);
}
namespace ParticleGen {
    ParticleHandle buildThruster(const DroneMinionParams& p);
    ParticleHandle buildJointSparks(const DroneMinionParams& p);
}
namespace PhysGen {
    PhysicsHandle buildFlightModel(const DroneMinionParams& p);
}
namespace AIGen {
    AIHandle buildDroneAI(const DroneMinionParams& p);
}
namespace IconGen {
    TextureHandle buildDroneIcon(const DroneMinionParams& p);
}

class DroneMinionFactory {
    ConcurrentLRUCache<uint64_t, DroneMinionBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    DroneMinionFactory() = default;
    ~DroneMinionFactory() { shutdown(); }

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

    std::future<DroneMinionBundle> generateAsync(const DroneMinionParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }

        return m_pool.enqueue([=]() {
            DroneMinionBundle b;
            b.bodyMesh = MeshGen::buildDroneBody(p);
            b.rotorMesh = MeshGen::buildDroneRotors(p);
            b.bodyTexture = TextureGen::buildDroneTexture(p);
            b.bodyShader = ShaderGen::buildDroneShader(p);
            b.thrusterFX = ParticleGen::buildThruster(p);
            b.jointSparks = ParticleGen::buildJointSparks(p);
            b.flightPhysics = PhysGen::buildFlightModel(p);
            b.aiController = AIGen::buildDroneAI(p);
            b.icon = IconGen::buildDroneIcon(p);
            m_cache.insert(key, b);
            return b;
        });
    }
};

} // namespace DroneMinions
} // namespace MagiTech
