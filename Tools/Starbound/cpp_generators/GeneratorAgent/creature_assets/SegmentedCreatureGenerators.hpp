#pragma once

#include "SegmentedCreatureTypes.hpp"
#include "core/modules/segmented_creature_generator/ProceduralFactory.hpp"

namespace MagiTech {
namespace SegmentedCreatures {

template<>
struct MeshGen<SegmentedCreatureParams> {
    static MeshHandle build(const SegmentedCreatureParams& p);
};

template<>
struct TextureGen<SegmentedCreatureParams> {
    static TextureHandle build(const SegmentedCreatureParams& p);
};

template<>
struct RigGen<SegmentedCreatureParams> {
    static SkeletonHandle build(const SegmentedCreatureParams& p);
};

template<>
struct AnimGen<SegmentedCreatureParams> {
    static AnimationHandle build(const SegmentedCreatureParams& p);
};

template<>
struct AIGen<SegmentedCreatureParams> {
    static AIHandle build(const SegmentedCreatureParams& p);
};


} // namespace SegmentedCreatures
} // namespace MagiTech
