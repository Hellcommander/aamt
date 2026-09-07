#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace AnimationAssets {

using SkeletonHandle = uint32_t;
using ClipHandle = uint32_t;
using BlendSpaceHandle = uint32_t;
using ProcLayerHandle = uint32_t;
using BoneID = uint32_t;

struct SkeletonParams {
    std::string id = "default_skeleton";
    std::vector<std::string> bones;
    std::vector<int> parentIndices;
    glm::vec3 rootPosition = {0.0f, 0.0f, 0.0f};
    glm::quat rootRotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        for(const auto& bone : bones) {
            XXH64_update(&hash_state, bone.c_str(), bone.length());
        }
        XXH64_update(&hash_state, parentIndices.data(), parentIndices.size() * sizeof(int));
        XXH64_update(&hash_state, &rootPosition, sizeof(rootPosition));
        XXH64_update(&hash_state, &rootRotation, sizeof(rootRotation));
        return XXH64_digest(&hash_state);
    }
};

enum class InterpType { Linear, Bezier, Hermite, CatmullRom };

struct AnimationClipParams {
    std::string id = "default_clip";
    std::string skeletonId;
    float duration = 1.0f;
    float sampleRate = 30.0f;
    InterpType interp = InterpType::Linear;
    bool loop = false;
    bool enableRootMotion = false;
    bool compress = false;
    float compressionTolerance = 0.1f;
    
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(AnimationClipParams) - (2*sizeof(std::string)));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, skeletonId.c_str(), skeletonId.length());
        return XXH64_digest(&hash_state);
    }
};

enum class BlendSpaceType { Blend1D, Blend2D };

struct BlendSpaceParams {
    std::string id = "default_blendspace";
    BlendSpaceType type = BlendSpaceType::Blend1D;
    std::vector<std::string> clipIds;
    std::vector<glm::vec2> sampleCoords;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &type, sizeof(type));
        for(const auto& clipId : clipIds) {
            XXH64_update(&hash_state, clipId.c_str(), clipId.length());
        }
        XXH64_update(&hash_state, sampleCoords.data(), sampleCoords.size() * sizeof(glm::vec2));
        return XXH64_digest(&hash_state);
    }
};

struct ProcLayerParams {
    bool   enableIK = false;         
    BoneID ikEndEffector = 0;    
    glm::vec3   ikTargetOffset = {0,0,0};   
    bool   enableNoise = false;      
    float  noiseFreq = 0.1f;        
    bool   enableAim = false;        
    BoneID aimBone = 0;          
    glm::vec3   aimTarget = {0,0,1};

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(ProcLayerParams));
        return XXH64_digest(&hash_state);
    }
};

struct AnimationAssetBundle {
    SkeletonHandle skeleton;
    ClipHandle clip;
    BlendSpaceHandle blendSpace;
    ProcLayerHandle procLayer;
};

} // namespace AnimationAssets
} // namespace MagiTech
