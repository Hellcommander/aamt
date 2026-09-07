#include "DriftingOrbitalsFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace DriftingOrbitals {

#define LOG_ORBITAL_GEN(Action, Id) Log::info("OrbitalGen - {}: {}", #Action, Id)

namespace MeshGen {
    MeshHandle buildOrb(const DriftingOrbitalParams& p) {
        LOG_ORBITAL_GEN(BuildingOrbMesh, p.id);
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace MeshGen

namespace TrailGen {
    MeshHandle build(const DriftingOrbitalParams& p) {
        LOG_ORBITAL_GEN(BuildingTrail, p.id);
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace TrailGen

namespace ParticleGen {
    ParticleHandle buildPulse(const DriftingOrbitalParams& p) {
        LOG_ORBITAL_GEN(BuildingPulseParticles, p.id);
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace ParticleGen

namespace ShaderGen {
    ShaderHandle buildOrbitalShader(const DriftingOrbitalParams& p) {
        LOG_ORBITAL_GEN(BuildingOrbitalShader, p.id);
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace ShaderGen

} // namespace DriftingOrbitals
} // namespace MagiTech
