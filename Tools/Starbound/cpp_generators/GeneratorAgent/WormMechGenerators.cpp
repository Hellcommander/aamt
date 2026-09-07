#include "WormMechFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace WormMechs {

namespace MeshGen {
    MeshHandle buildWormMech(const WormMechParams& p) {
        Log::info("Building worm mech mesh for: {}", p.id);
        return 1;
    }
}
namespace TextureGen {
    TextureHandle buildWormMech(const WormMechParams& p) {
        Log::info("Building worm mech texture for: {}", p.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildWormMech(const WormMechParams& p) {
        Log::info("Building worm mech shader for: {}", p.id);
        return 1;
    }
}
namespace RigGen {
    SkeletonHandle buildWormMech(const WormMechParams& p) {
        Log::info("Building worm mech skeleton for: {}", p.id);
        return 1;
    }
}
namespace AnimGen {
    AnimationHandle buildProfile(const std::string& profile, int segCount) {
        Log::info("Building animation profile '{}' for {} segments", profile, segCount);
        return 1;
    }
}
namespace CockpitGen {
    MeshHandle build(const WormMechParams& p) {
        Log::info("Building cockpit mesh for: {}", p.id);
        return 101;
    }
    TextureHandle buildTexture(const WormMechParams& p) {
        Log::info("Building cockpit texture for: {}", p.id);
        return 101;
    }
}
namespace ParticleGen {
    ParticleHandle buildExhaust(const WormMechParams& p) {
        Log::info("Building exhaust particles for: {}", p.id);
        return 1;
    }
}
namespace IconGen {
    TextureHandle buildMechIcon(const WormMechParams& m, const UIParams& u) {
        Log::info("Building mech icon for: {}", m.id);
        return 201;
    }
}

} // namespace WormMechs
} // namespace MagiTech
