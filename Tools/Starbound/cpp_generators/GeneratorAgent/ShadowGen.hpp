#pragma once

#include "LightTypes.hpp"
#include "LightGen.hpp"
#include "GPUDeviceInterface.hpp"
#include <algorithm>
#include <bit>

namespace mt::light {

struct ShadowConfig {
    bool       enabled{false};
    uint32_t   resolution{0};  // per-slice resolution (power of two)
    uint32_t   layers{0};      // depth slices: 6 for point lights (cube), cascades for directional, 1 otherwise
    uint32_t   cascades{0};
    float      bias{0.0f};
    float      normalBias{0.0f};
    GpuTexture map{};          // depth array render target
    GpuSampler sampler{};      // depth-compare (PCF) sampler
};

// Allocates per-light shadow resources and marks the registered light as shadow casting.
class ShadowGen {
public:
    static constexpr uint32_t kMinResolution = 128;
    static constexpr uint32_t kMaxResolution = 8192;
    static constexpr uint32_t kMaxCascades = 4;

    static ShadowConfig configure(LightHandle handle, LightType type, const ShadowParams& sp) {
        ShadowConfig cfg{};
        if (!sp.castShadows || sp.resolution <= 0) {
            LightGen::setFlag(handle, LightFlags::CastsShadows, false);
            return cfg;
        }

        cfg.resolution = std::bit_ceil(std::clamp(static_cast<uint32_t>(sp.resolution), kMinResolution, kMaxResolution));
        cfg.cascades = type == LightType::Directional
                           ? std::clamp(static_cast<uint32_t>(std::max(sp.cascades, 1)), 1u, kMaxCascades)
                           : 1u;
        cfg.layers = layerCount(type, cfg.cascades);
        cfg.bias = std::max(sp.bias, 0.0f);
        cfg.normalBias = std::max(sp.normalBias, 0.0f);

        auto& device = GPUDeviceInterface::getInstance();
        cfg.map = device.createDepthTexture(cfg.resolution, cfg.resolution, cfg.layers);
        cfg.sampler = device.createSampler(true, true, true);
        cfg.enabled = cfg.map != 0 && cfg.sampler != 0;
        if (!cfg.enabled) {
            release(cfg);
            return ShadowConfig{};
        }

        LightGen::setFlag(handle, LightFlags::CastsShadows, true);
        return cfg;
    }

    // Resolution actually used at a given LOD level (LOD resolutions only ever lower it).
    static uint32_t resolutionForLOD(const ShadowConfig& cfg, int lodResolution) {
        if (!cfg.enabled) return 0;
        if (lodResolution <= 0) return cfg.resolution;
        return std::min(cfg.resolution, std::bit_ceil(std::clamp(static_cast<uint32_t>(lodResolution),
                                                                 kMinResolution, kMaxResolution)));
    }

    static void release(ShadowConfig& cfg) {
        auto& device = GPUDeviceInterface::getInstance();
        if (cfg.map) device.destroyTexture(cfg.map);
        if (cfg.sampler) device.destroySampler(cfg.sampler);
        cfg.map = 0;
        cfg.sampler = 0;
        cfg.enabled = false;
    }

private:
    static uint32_t layerCount(LightType type, uint32_t cascades) {
        switch (type) {
            case LightType::Point:       return 6;        // cube map faces
            case LightType::Directional: return cascades; // cascaded shadow maps
            case LightType::Spot:
            case LightType::Area:
            default:                     return 1;
        }
    }
};

} // namespace mt::light
