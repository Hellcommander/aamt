#pragma once

#include "LightTypes.hpp"
#include "LightGen.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numbers>

namespace mt::light {

struct FlickerConfig {
    bool                   enabled{false};
    float                  frequency{0.0f};  // Hz
    float                  minScale{1.0f};   // intensity multiplier range
    float                  maxScale{1.0f};
    FlickerParams::Pattern pattern{FlickerParams::Pattern::Sine};
    uint32_t               seed{0};          // decorrelates lights using the same parameters
};

// Light flickering (fire, candles, electrical interference).
// attach() configures the effect and writes speed / amount into the registered GPULight's animation
// channel (consumed by GPULightingSystem::processLightAnimations); evaluate() gives the exact CPU-side
// intensity multiplier for a pattern at a point in time.
class FlickerGen {
public:
    static FlickerConfig attach(LightHandle handle, const FlickerParams& fp) {
        FlickerConfig cfg{};
        const float lo = std::max(0.0f, std::min(fp.amplitude.x, fp.amplitude.y));
        const float hi = std::max(0.0f, std::max(fp.amplitude.x, fp.amplitude.y));

        if (!fp.enabled || fp.frequency <= 0.0f || hi - lo <= 1e-6f) {
            LightGen::modify(handle, [](WorldExLighting::GPULight& light) {
                light.animation.x = 0.0f;
                light.animation.y = 0.0f;
                light.params.w = static_cast<float>(LightGen::flagsOf(light) & ~LightFlags::Flicker);
            });
            return cfg; // no flicker effect
        }

        cfg.enabled = true;
        cfg.frequency = fp.frequency;
        cfg.minScale = lo;
        cfg.maxScale = hi;
        cfg.pattern = fp.pattern;
        cfg.seed = mix(handle * 0x9E3779B9u + static_cast<uint32_t>(fp.pattern));

        LightGen::modify(handle, [&cfg](WorldExLighting::GPULight& light) {
            // Animation channel: x = flicker speed, y = flicker amount (relative to base intensity)
            light.animation.x = cfg.frequency;
            light.animation.y = 0.5f * (cfg.maxScale - cfg.minScale) * light.color.a;
            light.params.w = static_cast<float>(LightGen::flagsOf(light) | LightFlags::Flicker);
        });
        return cfg;
    }

    // Intensity multiplier in [minScale, maxScale] at `timeSeconds` (1.0 when the effect is disabled).
    static float evaluate(const FlickerConfig& cfg, float timeSeconds) {
        if (!cfg.enabled) return 1.0f;
        float n = 0.0f; // normalized signal in [-1, 1]
        switch (cfg.pattern) {
            case FlickerParams::Pattern::Sine:
                n = std::sin(2.0f * std::numbers::pi_v<float> * cfg.frequency * timeSeconds);
                break;
            case FlickerParams::Pattern::Perlin:
                n = calculateNoiseFlicker(timeSeconds * cfg.frequency, cfg.seed);
                break;
            case FlickerParams::Pattern::Random: {
                // Sample-and-hold random level, changing `frequency` times per second.
                const auto step = static_cast<int64_t>(std::floor(timeSeconds * cfg.frequency));
                n = hashSigned(static_cast<uint32_t>(step) ^ cfg.seed);
                break;
            }
        }
        const float t = std::clamp(0.5f * n + 0.5f, 0.0f, 1.0f);
        return cfg.minScale + (cfg.maxScale - cfg.minScale) * t;
    }

private:
    static uint32_t mix(uint32_t x) {
        x ^= x >> 16; x *= 0x7FEB352Du;
        x ^= x >> 15; x *= 0x846CA68Bu;
        x ^= x >> 16;
        return x;
    }

    // Uniform value in [-1, 1] derived from an integer.
    static float hashSigned(uint32_t x) {
        return static_cast<float>(mix(x) & 0xFFFFFFu) / static_cast<float>(0xFFFFFF) * 2.0f - 1.0f;
    }

    // 1D gradient (Perlin) noise in roughly [-1, 1].
    static float gradientNoise(float t, uint32_t seed) {
        const float cell = std::floor(t);
        const float f = t - cell;
        const auto i = static_cast<uint32_t>(static_cast<int64_t>(cell));
        const float g0 = hashSigned(i ^ seed);
        const float g1 = hashSigned((i + 1u) ^ seed);
        const float v0 = g0 * f;
        const float v1 = g1 * (f - 1.0f);
        const float u = f * f * f * (f * (f * 6.0f - 15.0f) + 10.0f); // quintic fade
        return 2.0f * (v0 + u * (v1 - v0));
    }

    // Two-octave fractal noise: natural-looking flame flicker.
    static float calculateNoiseFlicker(float t, uint32_t seed) {
        const float n = gradientNoise(t, seed) * 0.7f + gradientNoise(t * 2.3f + 17.0f, seed ^ 0x5bd1e995u) * 0.3f;
        return std::clamp(n, -1.0f, 1.0f);
    }
};

} // namespace mt::light
