#pragma once

#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Beams {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using EffectHandle = uint32_t;

struct BeamParams {
    std::string id, beamType;
    glm::vec3   colorInner, colorOuter;
    float length, width, noiseIntensity;
    float noiseScale, flickerRate, scrollSpeed;
    int   segments, detailLevel;
    std::string muzzleEffect, impactEffect, collisionDecal;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, beamType.c_str(), beamType.length());
        XXH64_update(&hash_state, &length, sizeof(length));
        XXH64_update(&hash_state, &width, sizeof(width));
        XXH64_update(&hash_state, &segments, sizeof(segments));
        XXH64_update(&hash_state, &noiseIntensity, sizeof(noiseIntensity));
        return XXH64_digest(&hash_state);
    }
};

struct BeamBundle {
    MeshHandle    ribbonMesh;
    TextureHandle beamTex;
    ShaderHandle  beamShader;
    EffectHandle  muzzleFX, impactFX;
};

} // namespace Beams
} // namespace MagiTech
