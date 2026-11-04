#include "AnimationAssetLuaBindings.hpp"
#include "AnimationAssetFactory.hpp"
#include <memory>
#include <mutex>
#include <optional>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace AnimationAssets {

static std::vector<std::pair<std::future<AnimationAssetBundle>, std::string>> pendingAssets;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<AnimationAssetFactory>& factorySlot() {
    static std::shared_ptr<AnimationAssetFactory> f;
    return f;
}
} // namespace

void AnimationAssetLuaBindings::setFactory(std::shared_ptr<AnimationAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<AnimationAssetFactory> AnimationAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<AnimationAssetFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
            auto factory = AnimationAssetLuaBindings::factory();
            std::optional<BlendSpaceParams> blend = b ? std::optional<BlendSpaceParams>(*b) : std::nullopt;
            std::optional<ProcLayerParams> layer = l ? std::optional<ProcLayerParams>(*l) : std::nullopt;
            pendingAssets.emplace_back(factory->generateAsync(s, c, blend, layer), c.id);
        }
    );
}

void AnimationAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                it->first.get();
                lua["print"]("Animation asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("AnimationAssets", "Animation asset {} failed: {}", it->second, e.what());
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace AnimationAssets
} // namespace MagiTech
