#pragma once

#include "StatusEffectTypes.hpp"

namespace MagiTech {
namespace StatusEffects {

namespace ShaderGen {
    ShaderHandle build(const StatusEffectParams& s);
}

namespace TextureGen {
    TextureHandle build(const StatusEffectParams& s);
}

namespace MeshGen {
    MeshHandle build(const StatusEffectParams& s);
}

namespace ParticleGen {
    ParticleHandle build(const StatusEffectParams& s);
}

namespace IconGen {
    TextureHandle build(const StatusEffectParams& s, const UIParams& u);
}

} // namespace StatusEffects
} // namespace MagiTech
