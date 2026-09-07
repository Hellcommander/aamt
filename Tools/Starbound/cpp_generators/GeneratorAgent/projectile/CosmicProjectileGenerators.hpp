#pragma once

#include "CosmicProjectileTypes.hpp"
#include "core/modules/cosmic_generator/CosmicFactory.hpp"

namespace MagiTech {
namespace Cosmic {

template<>
struct MeshGen<CosmicProjectileParams> {
    static MeshHandle build(const CosmicProjectileParams& p);
};

template<>
struct TextureGen<CosmicProjectileParams> {
    static TextureHandle build(const CosmicProjectileParams& p);
};

template<>
struct ShaderGen<CosmicProjectileParams> {
    static ShaderHandle build(const CosmicProjectileParams& p);
};

template<>
struct EffectsGen<CosmicProjectileParams> {
    static EffectHandle build(const CosmicProjectileParams& p);
};

} // namespace Cosmic
} // namespace MagiTech
