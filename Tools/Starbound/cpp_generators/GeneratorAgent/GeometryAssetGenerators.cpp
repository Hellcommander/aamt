#include "GeometryAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Geometry {

#define LOG_GEO_GEN(Action, Id) Log::info("GeometryGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t PrimitiveParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(PrimitiveParams) - sizeof(std::string));
    XXH64_update(&s, shape.c_str(), shape.length());
    return XXH64_digest(&s);
}
uint64_t ExtrusionParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(ExtrusionParams) - 2 * sizeof(std::vector<glm::vec2>));
    XXH64_update(&s, profile.data(), profile.size() * sizeof(glm::vec2));
    XXH64_update(&s, path.data(), path.size() * sizeof(glm::vec3));
    return XXH64_digest(&s);
}
uint64_t LSystemParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(LSystemParams) - 2 * sizeof(std::string));
    XXH64_update(&s, axiom.c_str(), axiom.length());
    for(const auto& rule : rules) {
        XXH64_update(&s, &rule.first, sizeof(char));
        XXH64_update(&s, rule.second.c_str(), rule.second.length());
    }
    return XXH64_digest(&s);
}
uint64_t SurfaceParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(SurfaceParams) - sizeof(std::string));
    XXH64_update(&s, func.c_str(), func.length());
    return XXH64_digest(&s);
}
uint64_t BooleanParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(BooleanParams) - sizeof(std::string));
    XXH64_update(&s, op.c_str(), op.length());
    return XXH64_digest(&s);
}
uint64_t LODParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, screenSizes.data(), screenSizes.size() * sizeof(float));
    XXH64_update(&s, simplificationFactors.data(), simplificationFactors.size() * sizeof(float));
    return XXH64_digest(&s);
}


// Generator stubs
namespace PrimitiveGen {
    MeshHandle build(const PrimitiveParams& p) { LOG_GEO_GEN(BuildPrimitive, p.shape); static MeshHandle h = 1; return h++; }
}
namespace ExtrusionGen {
    MeshHandle build(const ExtrusionParams& p) { LOG_GEO_GEN(BuildExtrusion, p.path.size()); static MeshHandle h = 100; return h++; }
}
namespace LSystemGen {
    MeshHandle build(const LSystemParams& p) { LOG_GEO_GEN(BuildLSystem, p.axiom); static MeshHandle h = 200; return h++; }
}
namespace SurfaceGen {
    MeshHandle build(const SurfaceParams& p) { LOG_GEO_GEN(BuildSurface, p.func); static MeshHandle h = 300; return h++; }
}
namespace BooleanGen {
    MeshHandle build(const BooleanParams& p) { LOG_GEO_GEN(BuildBoolean, p.op); static MeshHandle h = 400; return h++; }
}
namespace UVGen {
    void generateAuto(MeshHandle mesh) { LOG_GEO_GEN(GenerateUVs, mesh); }
}
namespace LODGen {
    LODData compute(const LODParams& lp, const std::vector<MeshHandle>& ms) {
        LOG_GEO_GEN(ComputeLODs, ms.size());
        LODData data;
        data.thresholds = lp.screenSizes;
        return data;
    }
}

} // namespace Geometry
} // namespace MagiTech
