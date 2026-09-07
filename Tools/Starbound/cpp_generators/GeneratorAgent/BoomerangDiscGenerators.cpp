#include "BoomerangDiscFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace BoomerangDiscs {

namespace MeshGen {
    MeshHandle buildBoomerang(const BoomerangParams& p) {
        Log::info("Building boomerang mesh for: {}", p.id);
        return 1;
    }
    MeshHandle buildDisc(const ReturningDiscParams& p) {
        Log::info("Building disc mesh for: {}", p.id);
        return 2;
    }
}
namespace PathGen {
    SplineHandle buildReturnPath(float returnDelay, float arcHeight) {
        Log::info("Building return path spline");
        return 1;
    }
}
namespace TrailGen {
    MeshHandle buildRibbon(const BoomerangParams& p) {
        Log::info("Building trail ribbon for boomerang: {}", p.id);
        return 3;
    }
    MeshHandle buildRimGlow(const ReturningDiscParams& p) {
        Log::info("Building rim glow for disc: {}", p.id);
        return 4;
    }
}
namespace ParticleGen {
    ParticleHandle buildAirGust(const BoomerangParams& p) {
        Log::info("Building air gust FX for: {}", p.id);
        return 1;
    }
    ParticleHandle buildGroundDust(const ReturningDiscParams& p) {
        Log::info("Building ground dust FX for: {}", p.id);
        return 2;
    }
}
namespace ShaderGen {
    ShaderHandle buildSpinShader(float spinRateRPM) {
        Log::info("Building spin shader");
        return 1;
    }
}

} // namespace BoomerangDiscs
} // namespace MagiTech
