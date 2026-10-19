#pragma once

#include "SegmentedCreatureParams.hpp"
#include <chrono>
#include <cstdint>
#include <string>

namespace MagiTech {
namespace SegmentedCreatures {

// Handles index the shared CreatureAssets::AssetStore (MonsterCreatureAssets.hpp); 0 means "none".
using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using AIHandle = uint32_t;

/**
 * Result of one factory generation. Creature bundles fill the visual assets, the material
 * maps and `params`; behaviour bundles carry only `ai` (all other handles stay 0).
 */
class AssetBundle {
public:
    // Core assets
    MeshHandle      mesh = 0;
    TextureHandle   texture = 0;
    SkeletonHandle  skeleton = 0;
    AnimationHandle anim = 0;
    AIHandle        ai = 0;

    // Additional material maps (creature bundles)
    TextureHandle normalMap = 0;
    TextureHandle roughnessMap = 0;
    TextureHandle metallicMap = 0;
    TextureHandle emissiveMap = 0;   // 0 when the creature does not glow
    TextureHandle aoMap = 0;

    // Metadata
    SegmentedCreatureGenerationResult result;
    SegmentedCreatureParams params;   // creature parameters the bundle was generated from (creature bundles)
    std::string assetPath;
    std::chrono::system_clock::time_point creationTime{};

    /** True when only the behaviour slot is used (bundle produced by BehaviorFactory). */
    bool isBehaviorOnly() const { return mesh == 0 && texture == 0 && skeleton == 0 && anim == 0; }

    bool isValid() const {
        if (ai == 0) return false;
        return isBehaviorOnly() || (mesh != 0 && texture != 0 && skeleton != 0 && anim != 0);
    }

    std::string getInfo() const {
        return "SegmentedCreatureAssetBundle{mesh=" + std::to_string(mesh) +
               ", texture=" + std::to_string(texture) +
               ", skeleton=" + std::to_string(skeleton) +
               ", anim=" + std::to_string(anim) +
               ", ai=" + std::to_string(ai) + "}";
    }
};

// Name used by the former creature_assets types.
using SegmentedCreatureAssetBundle = AssetBundle;

} // namespace SegmentedCreatures
} // namespace MagiTech
