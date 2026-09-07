#include "SnakeMechFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace SnakeMechs {

namespace MeshGen {
    MeshHandle buildMech(const SnakeMechParams& p) {
        Log::info("Building snake mech mesh for: {}", p.id);
        return 1;
    }
}
namespace RigGen {
    SkeletonHandle buildSkeleton(const SnakeMechParams& p) {
        Log::info("Building snake mech skeleton for: {}", p.id);
        return 1;
    }
}
namespace AnimGen {
    AnimationHandle buildWaveAnimation(const SnakeMechParams& p) {
        Log::info("Building snake mech wave animation for: {}", p.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildMechShader(const SnakeMechParams& p) {
        Log::info("Building snake mech shader for: {}", p.id);
        return 1;
    }
}
namespace ParticleGen {
    ParticleHandle buildJointSparks(const SnakeMechParams& p) {
        Log::info("Building joint spark particles for: {}", p.id);
        return 1;
    }
}
namespace PhysGen {
    PhysicsHandle buildPhysicsAsset(const SnakeMechParams& p) {
        Log::info("Building snake mech physics asset for: {}", p.id);
        return 1;
    }
}

} // namespace SnakeMechs
} // namespace MagiTech
