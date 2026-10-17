#pragma once
#include <string>
#include <type_traits>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace PlasmaDiscs {

namespace detail {
    // Field-wise hashing: hashing raw struct bytes would include padding and
    // std::string heap pointers, which makes cache keys non-deterministic.
    inline void hashField(XXH64_state_t& s, const std::string& v) noexcept {
        const uint64_t len = v.size();
        XXH64_update(&s, &len, sizeof(len));
        XXH64_update(&s, v.data(), v.size());
    }
    template <typename T>
    inline void hashField(XXH64_state_t& s, const T& v) noexcept {
        static_assert(std::is_trivially_copyable_v<T>, "hash members field by field");
        XXH64_update(&s, &v, sizeof(T));
    }
    template <typename... Ts>
    inline uint64_t hashFields(const Ts&... fields) noexcept {
        XXH64_state_t s;
        XXH64_reset(&s, 0);
        (hashField(s, fields), ...);
        return XXH64_digest(&s);
    }
} // namespace detail


using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using TrailHandle = uint32_t;

struct PlasmaDiscParams {
    std::string id = "energy_disc_v1";

    // Geometry
    float outerRadius = 1.0f;
    float innerRadius = 0.5f;
    float thickness = 0.1f;
    int radialSegments = 32;

    // Spin & Motion Blur
    float spinRateRPM = 1000.0f;
    float motionBlurStrength = 0.8f;
    bool enableBlur = true;

    // Emissive Rim
    glm::vec4 rimColor = {0.1f, 0.8f, 1.0f, 1.0f};
    float rimIntensity = 2.5f;
    float rimFalloff = 2.0f;
    float flickerFrequency = 8.0f;

    // Trails
    bool enableTrail = true;
    float trailLength = 0.5f;
    float trailWidth = 1.0f; // As wide as the disc
    glm::vec4 trailColor = {0.1f, 0.8f, 1.0f, 0.5f};

    // Impact Sparks
    int sparkCount = 100;
    glm::vec4 sparkColor = {0.8f, 0.9f, 1.0f, 1.0f};
    float sparkLifetime = 0.8f;
    float sparkSpeedMin = 10.0f;
    float sparkSpeedMax = 20.0f;

    uint64_t hashKey() const noexcept {
        return detail::hashFields(id, outerRadius, innerRadius, thickness, radialSegments, spinRateRPM, motionBlurStrength, enableBlur, rimColor, rimIntensity, rimFalloff, flickerFrequency, enableTrail, trailLength, trailWidth, trailColor, sparkCount, sparkColor, sparkLifetime, sparkSpeedMin, sparkSpeedMax);
    }
};

struct PlasmaDiscAssetBundle {
    MeshHandle discMesh = 0;
    ShaderHandle discShader = 0;
    TrailHandle trail = 0;
    ParticleHandle sparkParticles = 0;
};

} // namespace PlasmaDiscs
} // namespace MagiTech
