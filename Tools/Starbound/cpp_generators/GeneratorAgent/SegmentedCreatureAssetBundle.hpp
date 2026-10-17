#pragma once

#include <cstdint>

namespace MagiTech {
namespace SegmentedCreatures {

// Handles index the shared CreatureAssets::AssetStore (MonsterCreatureAssets.hpp); 0 means "none".
using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using AIHandle = uint32_t;

class AssetBundle {
public:
    MeshHandle      mesh = 0;
    TextureHandle   texture = 0;
    SkeletonHandle  skeleton = 0;
    AnimationHandle anim = 0;
    AIHandle        ai = 0;
};

} // namespace SegmentedCreatures
} // namespace MagiTech
