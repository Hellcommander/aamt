#pragma once

namespace MagiTech {
namespace SegmentedCreatures {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using AIHandle = uint32_t;

class AssetBundle {
public:
    MeshHandle      mesh;
    TextureHandle   texture;
    SkeletonHandle  skeleton;
    AnimationHandle anim;
    AIHandle        ai;
};

} // namespace SegmentedCreatures
} // namespace MagiTech
