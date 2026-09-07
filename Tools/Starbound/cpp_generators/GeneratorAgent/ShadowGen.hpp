#pragma once

#include "LightTypes.hpp"
#include "core/GPULightingSystem.hpp"

namespace mt::light {

struct ShadowConfig { uint32_t map{}; uint32_t sampler{}; };

class ShadowGen {
public:
    static ShadowConfig configure(LightHandle handle, const ShadowParams& sp) {
        ShadowConfig cfgReturn{};
        if (!sp.castShadows) return cfgReturn;

        if (!g_gpu_lighting_system) {
            initializeGPULightingSystem();
        }
        // Update global GPU lighting settings
        auto cfg = g_gpu_lighting_system->getConfig();
        cfg.enable_shadows = true;
        cfg.shadow_resolution = static_cast<float>(sp.resolution);
        cfg.shadow_cascade_count = static_cast<uint32_t>(sp.cascades);
        g_gpu_lighting_system->setConfig(cfg);

        // No per-light map handle yet – the shadow pass will allocate per-frame.
        // We leave map & sampler = 0 for now.
        return cfgReturn;
    }
};

} // namespace mt::light
