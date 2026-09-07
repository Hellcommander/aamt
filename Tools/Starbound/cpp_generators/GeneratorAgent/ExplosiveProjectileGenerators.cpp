#include "ExplosiveProjectileFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace ExplosiveProjectiles {

namespace MeshGen {
    MeshHandle buildProjectile(const ExplosiveProjectileParams& p) {
        Log::info("Building projectile mesh for: {}", p.id);
        return 1;
    }
    MeshHandle buildFragment(const ExplosiveProjectileParams& p) {
        Log::info("Building fragment mesh for: {}", p.id);
        return 2;
    }
}
namespace ParticleGen {
    ParticleHandle buildMotorTrail(const ExplosiveProjectileParams& p) {
        Log::info("Building motor trail particles for: {}", p.id);
        return 1;
    }
    ParticleHandle buildSmokeTrail(const ExplosiveProjectileParams& p) {
        Log::info("Building smoke trail particles for: {}", p.id);
        return 2;
    }
    ParticleHandle buildExplosionFlash(const ExplosiveProjectileParams& p) {
        Log::info("Building explosion flash particles for: {}", p.id);
        return 3;
    }
    ParticleHandle buildDebris(const ExplosiveProjectileParams& p) {
        Log::info("Building debris particles for: {}", p.id);
        return 4;
    }
}
namespace ShaderGen {
    ShaderHandle buildProjectileShader(const ExplosiveProjectileParams& p) {
        Log::info("Building projectile shader for: {}", p.id);
        return 1;
    }
}
namespace DecalGen {
    DecalHandle buildScorchDecal(const ExplosiveProjectileParams& p) {
        Log::info("Building scorch decal for: {}", p.id);
        return 1;
    }
}

} // namespace ExplosiveProjectiles
} // namespace MagiTech
