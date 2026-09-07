#include "SpaceObjectGenerators.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Cosmic {

MeshHandle MeshGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    Log::info("Building space object mesh for: {}", p.id);
    // Placeholder implementation
    return 1;
}

TextureHandle TextureGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    Log::info("Building space object texture for: {}", p.id);
    // Placeholder implementation
    return 1;
}

ShaderHandle ShaderGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    Log::info("Building space object shader for: {}", p.id);
    // Placeholder implementation
    return 1;
}

EffectHandle EffectsGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    Log::info("Building space object effect for: {}", p.id);
    // Placeholder implementation
    return 1;
}

} // namespace Cosmic
} // namespace MagiTech
