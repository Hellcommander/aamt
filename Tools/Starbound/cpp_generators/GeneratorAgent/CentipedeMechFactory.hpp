#pragma once
#include <future>
#include <optional>
#include "core/threading/ThreadPool.hpp"
#include "CentipedeMechTypes.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace CentipedeMechs {

// Forward declarations for generator functions
namespace SegmentGen {
    std::vector<MeshHandle> buildSegments(const MechParams& m, const LegParams& l);
}
namespace JointGen {
    std::vector<MeshHandle> buildJoints(int count, float radius);
}
namespace LegGen {
    std::vector<LegHandle> buildAllLegs(int segments, const LegParams& p);
}
namespace CockpitGen {
    CockpitHandle buildCockpit(const CockpitParams& c);
}
namespace WeaponGen {
    WeaponHandle buildHardpoints(const HardpointParams& h);
}
namespace SensorGen {
    SensorHandle buildRadar(bool enabled, float range);
}
namespace MaterialGen {
    MaterialSet assignMechMaterials(const glm::vec4& base);
}
namespace VFXGen {
    VFXBundle buildDamageAndThrusterFX(int segments);
}
namespace AudioGen {
    AudioBundle buildMechSounds();
}
namespace CollisionGen {
    ColliderHandle buildMechCollider(const MechParams& m, const LegParams& l);
}

class CentipedeMechFactory {
    std::unique_ptr<MultithreadBusPlugin> m_pool;
    bool m_initialized = false;

public:
    CentipedeMechFactory() = default;
    ~CentipedeMechFactory() { shutdown(); }

    void initialize(size_t num_threads);
    void shutdown();

    std::future<MechBundle> generateAsync(
        const MechParams& m,
        const LegParams& l,
        const CockpitParams& c,
        const HardpointParams& h
    );
};

} // namespace CentipedeMechs
} // namespace MagiTech
