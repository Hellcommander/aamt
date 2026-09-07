#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"
#include "core/utils/Observable.hpp"

namespace MagiTech {
namespace WormMechs {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using SkeletonHandle = uint32_t;
using AnimationHandle = uint32_t;
using ParticleHandle = uint32_t;
using SegmentHandle = uint32_t;

struct WormMechParams {
    std::string id = "sand_serpent_mkI";
    int segmentCount = 25;
    float segmentLength = 1.2f;
    float segmentRadius = 0.5f;
    std::string taperProfile = "linear";
    std::string segmentShape = "cylinder";
    float jointFlexibility = 0.7f;
    bool armorPlating = true;
    int platingDetailLevel = 2;
    glm::vec3 colorPrimary = {0.2f, 0.3f, 0.35f};
    glm::vec3 colorSecondary = {0.8f, 0.6f, 0.4f};
    float noiseDetail = 0.3f;
    float textureScale = 1.5f;
    std::string cockpitType = "internal";
    int cockpitSegmentIndex = 5;
    float cockpitRadius = 0.8f;
    glm::vec3 cockpitOrientation = {0.0f, 1.0f, 0.0f};
    std::string animationProfile = "mech_slither";
    std::string aiProfile = "patrol";

    bool operator!=(const WormMechParams& other) const {
        return id != other.id ||
               segmentCount != other.segmentCount ||
               segmentLength != other.segmentLength ||
               segmentRadius != other.segmentRadius ||
               taperProfile != other.taperProfile ||
               segmentShape != other.segmentShape ||
               jointFlexibility != other.jointFlexibility ||
               armorPlating != other.armorPlating ||
               platingDetailLevel != other.platingDetailLevel ||
               colorPrimary != other.colorPrimary ||
               colorSecondary != other.colorSecondary ||
               noiseDetail != other.noiseDetail ||
               textureScale != other.textureScale ||
               cockpitType != other.cockpitType ||
               cockpitSegmentIndex != other.cockpitSegmentIndex ||
               cockpitRadius != other.cockpitRadius ||
               cockpitOrientation != other.cockpitOrientation ||
               animationProfile != other.animationProfile ||
               aiProfile != other.aiProfile;
    }

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(WormMechParams));
        return XXH64_digest(&hash_state);
    }
};

struct UIParams {
    int iconSize = 64;
    glm::vec4 borderColor = {1.0f, 1.0f, 1.0f, 0.9f};
    std::string backgroundShape = "hexagon";
    bool flashOnSelect = true;

    bool operator!=(const UIParams& other) const {
        return iconSize != other.iconSize ||
               borderColor != other.borderColor ||
               backgroundShape != other.backgroundShape ||
               flashOnSelect != other.flashOnSelect;
    }

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(UIParams));
        return XXH64_digest(&hash_state);
    }
};

struct MechAssetBundle {
    MeshHandle mesh;
    TextureHandle texture;
    ShaderHandle shader;
    SkeletonHandle skeleton;
    AnimationHandle animation;
    MeshHandle cockpitMesh;
    TextureHandle cockpitTexture;
    ParticleHandle exhaustFX;
    TextureHandle icon;
};

// Represents a live, in-world instance of a mech
class DynamicWormMech {
public:
    void applyBundle(const MechAssetBundle& bundle);
    void setSegmentCount(int n);
    void updateLOD(const glm::vec3& cameraPos);

    MagiTech::Utils::Observable<WormMechParams> params;
private:
    void addSegment(int index);
    void removeSegment(SegmentHandle handle);
    void updateSpline();
    
    std::vector<SegmentHandle> m_segments;
    int m_currentDetailLevel = -1;
};


} // namespace WormMechs
} // namespace MagiTech
