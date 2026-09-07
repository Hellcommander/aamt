#pragma once

#include "BehaviorTypes.hpp"
#include "core/modules/segmented_creature_generator/ProceduralFactory.hpp"

namespace MagiTech {
namespace SegmentedCreatures {

// AI is generated from behavior, not creature params
template<>
struct AIGen<BehaviorParams> {
    static AIHandle build(const BehaviorParams& p);
};

// Other generators are not used for behavior params
template<> struct MeshGen<BehaviorParams> { static MeshHandle build(const BehaviorParams& p) { return 0; } };
template<> struct TextureGen<BehaviorParams> { static TextureHandle build(const BehaviorParams& p) { return 0; } };
template<> struct RigGen<BehaviorParams> { static SkeletonHandle build(const BehaviorParams& p) { return 0; } };
template<> struct AnimGen<BehaviorParams> { static AnimationHandle build(const BehaviorParams& p) { return 0; } };


} // namespace SegmentedCreatures
} // namespace MagiTech
