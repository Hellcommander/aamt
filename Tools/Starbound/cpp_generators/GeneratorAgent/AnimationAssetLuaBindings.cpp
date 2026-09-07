#include "AnimationAssetLuaBindings.hpp"
#include "AnimationAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace AnimationAssets {

static std::vector<std::pair<std::future<AnimationAssetBundle>, std::string>> pendingAssets;

void AnimationAssetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SkeletonParams>("SkeletonParams",
        sol::constructors<SkeletonParams()>(),
        "id", &SkeletonParams::id,
        "bones", &SkeletonParams::bones,
        "parentIndices", &SkeletonParams::parentIndices,
        "rootPosition", &SkeletonParams::rootPosition,
        "rootRotation", &SkeletonParams::rootRotation
    );

    lua.new_enum("InterpType",
        "Linear", InterpType::Linear,
        "Bezier", InterpType::Bezier,
        "Hermite", InterpType::Hermite,
        "CatmullRom", InterpType::CatmullRom
    );

    lua.new_usertype<AnimationClipParams>("AnimationClipParams",
        sol::constructors<AnimationClipParams()>(),
        "id", &AnimationClipParams::id,
        "skeletonId", &AnimationClipParams::skeletonId,
        "duration", &AnimationClipParams::duration,
        "sampleRate", &AnimationClipParams::sampleRate,
        "interp", &AnimationClipParams::interp,
        "loop", &AnimationClipParams::loop,
        "enableRootMotion", &AnimationClipParams::enableRootMotion,
        "compress", &AnimationClipParams::compress,
        "compressionTolerance", &AnimationClipParams::compressionTolerance
    );

    lua.new_enum("BlendSpaceType",
        "Blend1D", BlendSpaceType::Blend1D,
        "Blend2D", BlendSpaceType::Blend2D
    );

    lua.new_usertype<BlendSpaceParams>("BlendSpaceParams",
        sol::constructors<BlendSpaceParams()>(),
        "id", &BlendSpaceParams::id,
        "type", &BlendSpaceParams::type,
        "clipIds", &BlendSpaceParams::clipIds,
        "sampleCoords", &BlendSpaceParams::sampleCoords
    );

    lua.new_usertype<ProcLayerParams>("ProcLayerParams",
        sol::constructors<ProcLayerParams()>(),
        "enableIK", &ProcLayerParams::enableIK,
        "ikEndEffector", &ProcLayerParams::ikEndEffector,
        "ikTargetOffset", &ProcLayerParams::ikTargetOffset,
        "enableNoise", &ProcLayerParams::enableNoise,
        "noiseFreq", &ProcLayerParams::noiseFreq,
        "enableAim", &ProcLayerParams::enableAim,
        "aimBone", &ProcLayerParams::aimBone,
        "aimTarget", &ProcLayerParams::aimTarget
    );

    lua.new_usertype<AnimationAssetBundle>("AnimationAssetBundle",
        sol::no_constructor,
        "skeleton", &AnimationAssetBundle::skeleton,
        "clip", &AnimationAssetBundle::clip,
        "blendSpace", &AnimationAssetBundle::blendSpace,
        "procLayer", &AnimationAssetBundle::procLayer
    );

    lua.set_function("spawn_anim_asset",
        [&](const SkeletonParams& s, const AnimationClipParams& c,
            sol::optional<BlendSpaceParams> b, sol::optional<ProcLayerParams> l) {
            auto factory = MainPlugin::instance().getAnimationAssetFactory();
            pendingAssets.emplace_back(factory->generateAsync(s, c, b, l), c.id);
        }
    );
}

void AnimationAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Animation asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace AnimationAssets
} // namespace MagiTech
