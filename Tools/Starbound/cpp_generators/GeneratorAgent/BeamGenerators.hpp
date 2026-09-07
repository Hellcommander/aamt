#pragma once

#include "BeamTypes.hpp"

namespace MagiTech {
namespace Beams {

namespace MeshGen {
    MeshHandle buildBeamRibbon(const BeamParams& p);
}

namespace TextureGen {
    TextureHandle buildBeamTexture(const BeamParams& p);
}

namespace ShaderGen {
    ShaderHandle buildBeamShader(const BeamParams& p);
}

namespace EffectsGen {
    EffectHandle buildMuzzle(const BeamParams& p);
    EffectHandle buildImpact(const BeamParams& p);
}

} // namespace Beams
} // namespace MagiTech
