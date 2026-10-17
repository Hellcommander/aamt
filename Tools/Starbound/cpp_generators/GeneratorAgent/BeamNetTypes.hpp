#pragma once
#include <string>
#include <type_traits>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace BeamNets {

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
using DecalHandle = uint32_t;

struct BeamNetParams {
    std::string id = "laser_grid_v1";

    // Grid Dimensions
    int rows = 5;
    int columns = 5;
    float cellWidth = 2.0f;
    float cellHeight = 2.0f;

    // Beam Appearance
    float beamThickness = 0.1f;
    glm::vec4 beamColor = {0.2f, 0.8f, 1.0f, 0.9f};
    float glowIntensity = 2.0f;
    float flickerFrequency = 5.0f;

    // Weaving Animation (for nets)
    float weaveAmplitude = 0.2f;
    float weaveSpeed = 3.0f;

    // Duration & Lifetime
    float deploymentDelay = 0.5f;
    float activeDuration = 10.0f;
    bool retractOnExpire = true;

    // Impact & Interaction
    bool enableSparks = true;
    float sparkRate = 50.0f;
    float sparkLifetime = 0.3f;

    uint64_t hashKey() const noexcept {
        return detail::hashFields(id, rows, columns, cellWidth, cellHeight, beamThickness, beamColor, glowIntensity, flickerFrequency, weaveAmplitude, weaveSpeed, deploymentDelay, activeDuration, retractOnExpire, enableSparks, sparkRate, sparkLifetime);
    }
};

struct BeamNetAssetBundle {
    MeshHandle netMesh = 0;
    ShaderHandle beamShader = 0;
    ParticleHandle sparkParticles = 0;
    DecalHandle scorchDecal = 0;
};

} // namespace BeamNets
} // namespace MagiTech
