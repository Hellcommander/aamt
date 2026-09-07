#include "AcidLiquidProjectileFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace AcidLiquidProjectiles {

namespace MeshGen {
    MeshHandle buildDroplet(const LiquidProjectileParams& p) {
        Log::info("Building droplet mesh for: {}", p.id);
        return 1;
    }
}
namespace ParticleGen {
    ParticleHandle buildMist(const LiquidProjectileParams& p) {
        Log::info("Building mist particles for: {}", p.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildLiquidShader(const LiquidProjectileParams& p) {
        Log::info("Building liquid shader for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildSplatter(const LiquidProjectileParams& p) {
        Log::info("Building splatter decal for: {}", p.id);
        return 1;
    }
}
namespace PhysicsGen {
    PhysicsHandle buildFluidSystem(const LiquidProjectileParams& p) {
        Log::info("Building fluid physics for: {}", p.id);
        return 1;
    }
}

} // namespace AcidLiquidProjectiles
} // namespace MagiTech
