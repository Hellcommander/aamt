#pragma once

#include "SpaceObjectTypes.hpp"
#include "core/modules/cosmic_generator/CosmicFactory.hpp"

namespace MagiTech {
namespace Cosmic {

template<>
struct MeshGen<SpaceObjectParams> {
    static MeshHandle build(const SpaceObjectParams& p);
};

template<>
struct TextureGen<SpaceObjectParams> {
    static TextureHandle build(const SpaceObjectParams& p);
};

template<>
struct ShaderGen<SpaceObjectParams> {
    static ShaderHandle build(const SpaceObjectParams& p);
};

template<>
struct EffectsGen<SpaceObjectParams> {
    static EffectHandle build(const SpaceObjectParams& p);
};

} // namespace Cosmic
} // namespace MagiTech
