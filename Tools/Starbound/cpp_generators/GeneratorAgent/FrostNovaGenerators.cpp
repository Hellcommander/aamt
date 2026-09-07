#include "FrostNovaFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace FrostNovas {

namespace MeshGen {
    MeshHandle buildNovaRing(const FrostNovaParams& p) {
        Log::info("Building nova ring mesh for: {}", p.id);
        return 1;
    }
    MeshHandle buildIceShard(const FrostNovaParams& p) {
        Log::info("Building ice shard mesh for: {}", p.id);
        return 2;
    }
}
namespace ParticleGen {
    ParticleHandle buildFrostAura(const FrostNovaParams& p) {
        Log::info("Building frost aura particles for: {}", p.id);
        return 1;
    }
    ParticleHandle buildCrystalSparkles(const FrostNovaParams& p) {
        Log::info("Building crystal sparkle particles for: {}", p.id);
        return 2;
    }
}
namespace ShaderGen {
    ShaderHandle buildFrostShader(const FrostNovaParams& p) {
        Log::info("Building frost shader for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildFrostbiteDecal(const FrostNovaParams& p) {
        Log::info("Building frostbite decal for: {}", p.id);
        return 1;
    }
}

} // namespace FrostNovas
} // namespace MagiTech
