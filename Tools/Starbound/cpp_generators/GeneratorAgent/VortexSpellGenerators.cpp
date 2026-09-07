#include "VortexSpellFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace VortexSpells {

namespace MeshGen {
    MeshHandle buildVortexMesh(const VortexSpellParams& p) {
        Log::info("Building vortex mesh for: {}", p.id);
        return 1;
    }
    MeshHandle buildWindRibbons(const VortexSpellParams& p) {
        Log::info("Building wind ribbons for: {}", p.id);
        return 2;
    }
}
namespace ParticleGen {
    ParticleHandle buildDustCloud(const VortexSpellParams& p) {
        Log::info("Building dust cloud particles for: {}", p.id);
        return 1;
    }
    ParticleHandle buildDebris(const VortexSpellParams& p) {
        Log::info("Building debris particles for: {}", p.id);
        return 2;
    }
}
namespace ShaderGen {
    ShaderHandle buildVortexShader(const VortexSpellParams& p) {
        Log::info("Building vortex shader for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildGroundCracks(const VortexSpellParams& p) {
        Log::info("Building ground crack decals for: {}", p.id);
        return 1;
    }
}

} // namespace VortexSpells
} // namespace MagiTech
