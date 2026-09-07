#pragma once
#include <future>
#include "core/threading/ThreadPool.hpp"
#include "SnakeSpellTypes.hpp"

namespace MagiTech {
namespace SnakeSpells {

// Forward declarations for generator functions
namespace SnakeMeshGen {
    MeshHandle buildSplineMesh(const SnakeBodyParams& b);
}
namespace MotionSim {
    SimulationHandle setupSnake(const SnakeBodyParams& b, const MotionParams& m);
}
namespace ScaleVFXGen {
    MaterialSetup setup(int segments, const ScaleVFXParams& v);
}
namespace ParticleGen {
    ParticleHandle buildVenomAndSmoke(const ParticleParams& p);
}
namespace AudioGen {
    AudioBundle loadSnakeAudio(const AudioParams& a);
}
namespace CollisionGen {
    ColliderHandle buildCapsuleChain(int segments, const CollisionParams& c, float segmentLength);
}

class SnakeSpellFactory {
    std::unique_ptr<MultithreadBusPlugin> m_pool;
    bool m_initialized = false;

public:
    SnakeSpellFactory() = default;
    ~SnakeSpellFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<SnakeBundle> generateAsync(
        const SnakeBodyParams& b,
        const MotionParams& m,
        const ScaleVFXParams& v,
        const ParticleParams& p,
        const AudioParams& a,
        const CollisionParams& c
    );
};

} // namespace SnakeSpells
} // namespace MagiTech
