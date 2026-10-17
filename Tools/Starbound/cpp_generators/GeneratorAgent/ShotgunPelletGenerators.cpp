#include "ShotgunPelletFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace ShotgunPellets {

namespace MeshGen {
    MeshHandle buildPellet(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Building pellet mesh for: {}", p.id);
        return 1;
    }
}
namespace SpreadGen {
    std::vector<glm::vec3> generateDirections(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Generating {} spread directions for: {}", p.pelletCount, p.id);
        return std::vector<glm::vec3>(p.pelletCount, {0,0,1});
    }
}
namespace ComputeGen {
    ComputeBufferHandle createInstanceBuffer(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Creating GPU instance buffer for: {}", p.id);
        return 1;
    }
}
namespace TrailGen {
    ShaderHandle buildTrailShader(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Building trail shader for: {}", p.id);
        return 2;
    }
}
namespace ShaderGen {
    ShaderHandle buildPelletShader(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Building pellet instance shader for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildImpactDecal(const ShotgunPelletParams& p) {
        Log::info("ShotgunPellet", "Building impact decal for: {}", p.id);
        return 1;
    }
}

} // namespace ShotgunPellets
} // namespace MagiTech
