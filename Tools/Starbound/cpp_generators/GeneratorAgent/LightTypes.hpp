#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <glm/vec2.hpp>
#include <glm/vec3.hpp>
#include <xxhash.h>

namespace mt::light {

// ---------------------------------------------------------------------------------------------------------------------
// Basic math aliases (assumes glm is available project-wide)
// ---------------------------------------------------------------------------------------------------------------------
using Vec2 = glm::vec2;
using Vec3 = glm::vec3;

// ---------------------------------------------------------------------------------------------------------------------
// Enumerations & Parameter Schemas
// ---------------------------------------------------------------------------------------------------------------------

// GPU / CPU light categories.
// Must stay in sync with shader enum in light_common.glsl.
enum class LightType : uint32_t { Directional = 0, Point = 1, Spot = 2, Area = 3 };

struct LightParams {
    std::string id;          // unique asset identifier
    LightType   type;        // light category
    Vec3        color{};     // RGB radiance (linear space)
    float       intensity{}; // luminous power (candela / lux depending on engine)
    float       range{};     // attenuation range (non-directional)
    float       innerAngle{};// spot light: inner cone (deg)
    float       outerAngle{};// spot light: outer cone (deg)
    Vec2        areaSize{};  // area light width / height
    bool        volumetric{};// enable volumetric shafts
    bool        dynamic{};   // participates in runtime animations / movement

    // Hash key for use in caches
    uint64_t hashKey() const {
        XXH64_state_t* state = XXH64_createState();
        XXH64_reset(state, 0);
        XXH64_update(state, id.data(), id.size());
        XXH64_update(state, &type, sizeof(type));
        XXH64_update(state, &color, sizeof(color));
        XXH64_update(state, &intensity, sizeof(intensity));
        XXH64_update(state, &range, sizeof(range));
        XXH64_update(state, &innerAngle, sizeof(innerAngle));
        XXH64_update(state, &outerAngle, sizeof(outerAngle));
        XXH64_update(state, &areaSize, sizeof(areaSize));
        XXH64_update(state, &volumetric, sizeof(volumetric));
        XXH64_update(state, &dynamic, sizeof(dynamic));
        uint64_t h = XXH64_digest(state);
        XXH64_freeState(state);
        return h;
    }
};

struct ShadowParams {
    bool  castShadows{true};
    int   resolution{1024};
    int   cascades{1}; // directional lights only
    float bias{0.002f};
    float normalBias{0.005f};

    uint64_t hashKey() const {
        return XXH3_64bits(this, sizeof(ShadowParams));
    }
};

struct CookieParams {
    bool        useCookie{false};
    std::string texturePath; // relative asset path
    Vec2        uvScale{1.0f, 1.0f};
    Vec2        uvOffset{0.0f, 0.0f};

    uint64_t hashKey() const { return XXH3_64bits(this, sizeof(CookieParams)); }
};

struct VolumetricParams {
    float density{0.0f};
    Vec3  scatterColor{1.0f, 1.0f, 1.0f};
    float anisotropy{0.0f};

    uint64_t hashKey() const { return XXH3_64bits(this, sizeof(VolumetricParams)); }
};

struct FlickerParams {
    enum class Pattern : uint32_t { Sine = 0, Perlin = 1, Random = 2 };

    bool  enabled{false};
    float frequency{4.0f};
    Vec2  amplitude{0.8f, 1.2f};
    Pattern pattern{Pattern::Perlin};

    uint64_t hashKey() const { return XXH3_64bits(this, sizeof(FlickerParams)); }
};

struct LODParams {
    std::vector<float> screenSizes;   // per LOD screen size thresholds (normalized)
    std::vector<int>   shadowRes;     // per LOD shadow resolution
    std::vector<bool>  volumetricOn;  // per LOD volumetric toggle
    std::vector<bool>  cookieOn;      // per LOD cookie toggle

    uint64_t hashKey() const {
        // Simpler hash: hash of vector sizes + contents via XXH state
        XXH64_state_t* state = XXH64_createState();
        XXH64_reset(state, 0);
        auto vecHash = [&](auto&& v){
            size_t sz = v.size();
            XXH64_update(state, &sz, sizeof(sz));
            if(!v.empty())
                XXH64_update(state, v.data(), sizeof(typename std::decay<decltype(v[0])>::type) * v.size());
        };
        vecHash(screenSizes);
        vecHash(shadowRes);
        vecHash(volumetricOn);
        vecHash(cookieOn);
        uint64_t h = XXH64_digest(state);
        XXH64_freeState(state);
        return h;
    }
};

// Convenience helpers --------------------------------------------------------------------------------------------------

inline uint64_t hashCombine(uint64_t a, uint64_t b) { return XXH3_64bits(&a, sizeof(a)); /* crude but fine for cache */ }

template <typename T, typename... Rest>
inline uint64_t hashCombine(uint64_t a, uint64_t b, Rest... rest) {
    return hashCombine(hashCombine(a, b), rest...);
}

template <typename T>
inline uint64_t hashParams(const T& p) { return p.hashKey(); }

} // namespace mt::light
