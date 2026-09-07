#pragma once

namespace MagiTech {
namespace Cosmic {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

class AssetBundle {
public:
    MeshHandle    mesh;
    TextureHandle texture;
    ShaderHandle  shader;
    EffectHandle  fx;
};

} // namespace Cosmic
} // namespace MagiTech
