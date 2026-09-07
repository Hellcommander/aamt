#pragma once

#include "ProjectileTypes.hpp"

namespace MagiTech {
namespace Projectiles {

namespace MeshGen {
    MeshHandle buildMesh(const ProjectileParams& p);
}

namespace TextureGen {
    TextureHandle buildTexture(const ProjectileParams& p);
}

namespace ShaderGen {
    ShaderHandle buildShader(const ProjectileParams& p);
}

namespace EffectsGen {
    EffectHandle buildTrail(const ProjectileParams& p);
    EffectHandle buildImpact(const ProjectileParams& p);
}

} // namespace Projectiles
} // namespace MagiTech
