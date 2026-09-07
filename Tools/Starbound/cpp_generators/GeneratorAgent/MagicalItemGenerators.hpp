#pragma once

#include "MagicalItemTypes.hpp"

namespace MagiTech {
namespace MagicalItems {

namespace MeshGen {
    MeshHandle buildItemMesh(const MagicalItemParams& p);
}

namespace TextureGen {
    TextureHandle buildItemTexture(const MagicalItemParams& p);
}

namespace ShaderGen {
    ShaderHandle buildItemShader(const MagicalItemParams& p);
}

namespace EffectsGen {
    EffectHandle buildItemEffects(const MagicalItemParams& p);
}

} // namespace MagicalItems
} // namespace MagiTech
