#include "BeamNetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace BeamNets {

namespace MeshGen {
    MeshHandle buildBeamGrid(const BeamNetParams& p) {
        Log::info("Building beam grid mesh for: {}", p.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildBeamShader(const BeamNetParams& p) {
        Log::info("Building beam shader for: {}", p.id);
        return 1;
    }
}
namespace ParticleGen {
    ParticleHandle buildIntersectionSparks(const BeamNetParams& p) {
        Log::info("Building intersection spark particles for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildScorchDecal(const BeamNetParams& p) {
        Log::info("Building scorch decal for: {}", p.id);
        return 1;
    }
}

} // namespace BeamNets
} // namespace MagiTech
