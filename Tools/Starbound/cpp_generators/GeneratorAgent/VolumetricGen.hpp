#pragma once

#include "LightTypes.hpp"
#include "LightGen.hpp"
#include "GPUDeviceInterface.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <mutex>
#include <numbers>
#include <vector>
#include <glm/common.hpp>

namespace mt::light {

struct VolumetricConfig {
    struct Effect {
        GpuTexture map{};     // tileable 3D density noise (R8)
        GpuSampler sampler{}; // linear, wrap
    };

    bool   enabled{false};
    Effect effect{};
    float  density{0.0f};
    Vec3   scatterColor{1.0f, 1.0f, 1.0f};
    float  anisotropy{0.0f}; // Henyey-Greenstein g, clamped to (-1, 1)
};

// Volumetric light shafts (fog, smoke, dust). All volumetric lights share one procedurally generated,
// tileable 3D noise volume; density / colour / phase anisotropy are per light (uploaded via the light UBO).
class VolumetricGen {
public:
    static constexpr uint32_t kNoiseSize = 32;   // texels per axis
    static constexpr uint32_t kNoisePeriod = 8;  // lattice cells per axis (tiles seamlessly)

    static VolumetricConfig setup(LightHandle handle, const VolumetricParams& vp) {
        VolumetricConfig cfg{};
        if (vp.density <= 0.0f) {
            LightGen::setFlag(handle, LightFlags::Volumetric, false);
            return cfg; // no volumetric effect
        }

        auto& device = GPUDeviceInterface::getInstance();
        cfg.effect.map = acquireNoiseTexture();
        cfg.effect.sampler = device.createSampler(true, false); // linear filtering, wrap
        if (cfg.effect.map == 0 || cfg.effect.sampler == 0) {
            release(cfg);
            LightGen::setFlag(handle, LightFlags::Volumetric, false);
            return VolumetricConfig{};
        }

        cfg.enabled = true;
        cfg.density = vp.density;
        cfg.scatterColor = glm::max(vp.scatterColor, Vec3(0.0f));
        cfg.anisotropy = std::clamp(vp.anisotropy, -0.99f, 0.99f);
        LightGen::setFlag(handle, LightFlags::Volumetric, true);
        return cfg;
    }

    static void release(VolumetricConfig& cfg) {
        auto& device = GPUDeviceInterface::getInstance();
        if (cfg.effect.map) device.destroyTexture(cfg.effect.map);
        if (cfg.effect.sampler) device.destroySampler(cfg.effect.sampler);
        cfg = VolumetricConfig{};
    }

    // Henyey-Greenstein phase function (per steradian) for the CPU side / tooling.
    static float henyeyGreenstein(float cosTheta, float g) {
        const float g2 = g * g;
        const float denom = std::pow(std::max(1.0f + g2 - 2.0f * g * cosTheta, 1e-6f), 1.5f);
        return (1.0f - g2) / (4.0f * std::numbers::pi_v<float> * denom);
    }

    // Generates the tileable density volume: two octaves of trilinear value noise, R8.
    static std::vector<uint8_t> createVolumetricNoise() {
        const uint32_t n = kNoiseSize;
        std::vector<uint8_t> texels(static_cast<size_t>(n) * n * n);
        for (uint32_t z = 0; z < n; ++z) {
            for (uint32_t y = 0; y < n; ++y) {
                for (uint32_t x = 0; x < n; ++x) {
                    const float fx = static_cast<float>(x) / n, fy = static_cast<float>(y) / n,
                                fz = static_cast<float>(z) / n;
                    float v = 0.65f * valueNoise(fx, fy, fz, kNoisePeriod, 0x1234u) +
                              0.35f * valueNoise(fx, fy, fz, kNoisePeriod * 2, 0xBEEFu);
                    v = std::clamp(v, 0.0f, 1.0f);
                    texels[(static_cast<size_t>(z) * n + y) * n + x] = static_cast<uint8_t>(v * 255.0f + 0.5f);
                }
            }
        }
        return texels;
    }

private:
    // Shared noise texture: retained per user, regenerated if every user released it.
    static GpuTexture acquireNoiseTexture() {
        static std::mutex mutex;
        static GpuTexture shared = 0;
        std::lock_guard<std::mutex> lock(mutex);
        auto& device = GPUDeviceInterface::getInstance();
        if (shared != 0 && device.retainTexture(shared)) return shared;
        // Handles are never reused, so a released texture can be detected safely by retainTexture() failing.
        shared = device.createTexture3D(createVolumetricNoise(), kNoiseSize, kNoiseSize, kNoiseSize, 1);
        return shared;
    }

    static float lattice(int32_t x, int32_t y, int32_t z, uint32_t period, uint32_t seed) {
        const uint32_t p = period;
        uint32_t h = (static_cast<uint32_t>(x) % p) * 73856093u ^ (static_cast<uint32_t>(y) % p) * 19349663u ^
                     (static_cast<uint32_t>(z) % p) * 83492791u ^ seed;
        h ^= h >> 13; h *= 0x5bd1e995u; h ^= h >> 15;
        return static_cast<float>(h & 0xFFFFu) / 65535.0f;
    }

    // Periodic trilinear value noise over [0,1)^3 with `period` lattice cells per axis.
    static float valueNoise(float x, float y, float z, uint32_t period, uint32_t seed) {
        const float px = x * period, py = y * period, pz = z * period;
        const auto ix = static_cast<int32_t>(std::floor(px)), iy = static_cast<int32_t>(std::floor(py)),
                   iz = static_cast<int32_t>(std::floor(pz));
        auto fade = [](float t) { return t * t * (3.0f - 2.0f * t); };
        const float tx = fade(px - ix), ty = fade(py - iy), tz = fade(pz - iz);
        auto lerp = [](float a, float b, float t) { return a + (b - a) * t; };
        const float c00 = lerp(lattice(ix, iy, iz, period, seed), lattice(ix + 1, iy, iz, period, seed), tx);
        const float c10 = lerp(lattice(ix, iy + 1, iz, period, seed), lattice(ix + 1, iy + 1, iz, period, seed), tx);
        const float c01 = lerp(lattice(ix, iy, iz + 1, period, seed), lattice(ix + 1, iy, iz + 1, period, seed), tx);
        const float c11 =
            lerp(lattice(ix, iy + 1, iz + 1, period, seed), lattice(ix + 1, iy + 1, iz + 1, period, seed), tx);
        return lerp(lerp(c00, c10, ty), lerp(c01, c11, ty), tz);
    }
};

} // namespace mt::light
