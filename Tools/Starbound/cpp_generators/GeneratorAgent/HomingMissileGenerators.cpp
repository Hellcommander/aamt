#include "HomingMissileFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace HomingMissiles {

namespace MeshGen {
    MeshHandle buildMissile(const HomingMissileParams& p) {
        Log::info("Building missile mesh for: {}", p.id);
        return 1;
    }
}
namespace PathGen {
    SplineHandle buildGuidanceSpline(const HomingMissileParams& p) {
        Log::info("Building guidance spline for: {}", p.id);
        return 1;
    }
}
namespace TrailGen {
    MeshHandle buildDynamicRibbon(const HomingMissileParams& p) {
        Log::info("Building trail ribbon for: {}", p.id);
        return 2;
    }
}
namespace ParticleGen {
    ParticleHandle buildExhaustFlame(const HomingMissileParams& p) {
        Log::info("Building exhaust flame for: {}", p.id);
        return 1;
    }
    ParticleHandle buildExhaustSmoke(const HomingMissileParams& p) {
        Log::info("Building exhaust smoke for: {}", p.id);
        return 2;
    }
}
namespace ShaderGen {
    ShaderHandle buildMissileShader(const HomingMissileParams& p) {
        Log::info("Building missile shader for: {}", p.id);
        return 1;
    }
}

} // namespace HomingMissiles
} // namespace MagiTech
