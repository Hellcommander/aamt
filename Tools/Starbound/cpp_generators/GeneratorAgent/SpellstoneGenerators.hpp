#pragma once

#include "SpellstoneTypes.hpp"

namespace MagiTech {
namespace Spellstones {

namespace MeshGen {
    MeshHandle buildBody(const SpellstoneParams& p);
}

namespace TextureGen {
    TextureHandle buildSurface(const SpellstoneParams& p);
}

namespace ShaderGen {
    ShaderHandle buildBodyShader(const SpellstoneParams& p);
    ShaderHandle buildBeamShader(const SpellstoneParams& p);
}

namespace EffectsGen {
    EffectHandle buildIdle(const SpellstoneParams& p);
    EffectHandle buildBeam(const SpellstoneParams& p);
}

} // namespace Spellstones
} // namespace MagiTech
