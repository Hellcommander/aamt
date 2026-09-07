#include "AnimationAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace AnimationAssets {

#define LOG_GEN(Asset, Id) Log::info("Building Animation Asset {}: {}", #Asset, Id)

namespace SkeletonGen {
    SkeletonHandle buildSkeleton(const SkeletonParams& p) {
        LOG_GEN(Skeleton, p.id);
        // Build bone hierarchy, compute bind poses and inverse bind matrices
        static uint32_t nextSkeletonId = 1;
        return nextSkeletonId++;
    }
} // namespace SkeletonGen

namespace ClipGen {
    ClipHandle buildClip(const AnimationClipParams& c, const SkeletonParams& s) {
        LOG_GEN(Clip, c.id);
        // Sample keyframes, apply interpolation, handle root motion, and compress
        static uint32_t nextClipId = 1;
        return nextClipId++;
    }
} // namespace ClipGen

namespace BlendSpaceGen {
    BlendSpaceHandle build(const BlendSpaceParams& b, const SkeletonParams& s) {
        LOG_GEN(BlendSpace, b.id);
        // Precompute blend weights and sample positions for 1D/2D blend spaces
        static uint32_t nextBlendSpaceId = 1;
        return nextBlendSpaceId++;
    }
} // namespace BlendSpaceGen

namespace ProcLayerGen {
    ProcLayerHandle build(const ProcLayerParams& l, const SkeletonParams& s) {
        Log::info("Building Procedural Animation Layer");
        // Setup IK chains, noise generators, aim constraints, etc.
        static uint32_t nextProcLayerId = 1;
        return nextProcLayerId++;
    }
} // namespace ProcLayerGen

} // namespace AnimationAssets
} // namespace MagiTech
