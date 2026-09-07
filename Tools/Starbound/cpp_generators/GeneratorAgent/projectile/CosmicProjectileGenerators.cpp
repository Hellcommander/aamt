#include "CosmicProjectileGenerators.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Cosmic {

MeshHandle MeshGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("Building cosmic projectile mesh for: {}", p.id);
    // Placeholder implementation
    return 1;
}

TextureHandle TextureGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("Building cosmic projectile texture for: {}", p.id);
    // Placeholder implementation
    return 1;
}

ShaderHandle ShaderGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("Building cosmic projectile shader for: {}", p.id);
    // Placeholder implementation
    return 1;
}

EffectHandle EffectsGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("Building cosmic projectile effect for: {}", p.id);
    // Placeholder implementation
    return 1;
}

} // namespace Cosmic
} // namespace MagiTech
