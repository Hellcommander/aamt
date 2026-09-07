#include "PlasmaDiscFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace PlasmaDiscs {

namespace MeshGen {
    MeshHandle buildDisc(const PlasmaDiscParams& p) {
        Log::info("Building plasma disc mesh for: {}", p.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildDiscShader(const PlasmaDiscParams& p) {
        Log::info("Building plasma disc shader for: {}", p.id);
        return 1;
    }
}
namespace TrailGen {
    TrailHandle buildDiscTrail(const PlasmaDiscParams& p) {
        Log::info("Building plasma disc trail for: {}", p.id);
        return 1;
    }
}
namespace ParticleGen {
    ParticleHandle buildImpactSparks(const PlasmaDiscParams& p) {
        Log::info("Building impact spark particles for: {}", p.id);
        return 1;
    }
}

} // namespace PlasmaDiscs
} // namespace MagiTech
