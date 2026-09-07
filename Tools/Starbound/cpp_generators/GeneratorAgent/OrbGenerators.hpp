#pragma once

#include "OrbTypes.hpp"

namespace MagiTech {
namespace Orbs {

namespace MeshGen {
    MeshHandle buildOrbMesh(const OrbParams& p);
}

namespace TextureGen {
    TextureHandle buildOrbTexture(const OrbParams& p);
}

namespace ShaderGen {
    ShaderHandle buildOrbShader(const OrbParams& p);
}

namespace EffectsGen {
    EffectHandle buildOrbEffects(const OrbParams& p);
}

} // namespace Orbs
} // namespace MagiTech
