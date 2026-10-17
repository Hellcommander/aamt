#pragma once
#include <string>
#include <type_traits>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace VortexSpells {

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

struct VortexSpellParams {
    std::string id = "twister_v1";

    // Geometry
    float baseRadius = 2.0f;
    float topRadius = 8.0f;
    float height = 15.0f;
    int radialSegments = 24;
    int heightSegments = 30;

    // Swirl Dynamics
    float swirlSpeed = 2.5f;
    float upwardSpeed = 5.0f;
    float noiseAmplitude = 0.5f;
    float noiseFrequency = 0.2f;

    // Particle Debris
    int dustParticleCount = 500;
    float dustLifetime = 4.0f;
    glm::vec4 dustColor = {0.6f, 0.5f, 0.4f, 0.7f};

    // Visual FX
    float lightScattering = 0.3f;
    glm::vec4 vortexColor = {0.8f, 0.8f, 0.8f, 0.4f};

    // Ground Interaction
    float groundCrackRadius = 2.5f;
    float groundCrackLifetime = 12.0f;

    uint64_t hashKey() const noexcept {
        return detail::hashFields(id, baseRadius, topRadius, height, radialSegments, heightSegments, swirlSpeed, upwardSpeed, noiseAmplitude, noiseFrequency, dustParticleCount, dustLifetime, dustColor, lightScattering, vortexColor, groundCrackRadius, groundCrackLifetime);
    }
};

struct VortexSpellAssetBundle {
    MeshHandle vortexMesh = 0;
    ParticleHandle dustParticles = 0;
    ParticleHandle debrisParticles = 0;
    MeshHandle windRibbons = 0;
    ShaderHandle vortexShader = 0;
    DecalHandle groundDecal = 0;
};

} // namespace VortexSpells
} // namespace MagiTech
