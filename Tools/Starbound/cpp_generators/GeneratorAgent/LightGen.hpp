#pragma once

#include "LightTypes.hpp"
#include "core/GPULightingSystem.hpp"

namespace mt::light {

// LightGen bridges param structs to the underlying GPULightingSystem
class LightGen {
public:
    static LightHandle build(const LightParams& p) {
        using LS = GPULightingSystem;
        GPULight gpuLight;
        switch (p.type) {
            case LightType::Point: {
                gpuLight = createPointLight({0,0,0}, p.color, p.intensity, p.range);
                break;
            }
            case LightType::Spot: {
                gpuLight = createSpotLight({0,0,0}, {0,-1,0}, p.color, p.intensity, p.range, p.outerAngle);
                break;
            }
            case LightType::Directional: {
                gpuLight = createDirectionalLight({0,-1,0}, p.color, p.intensity);
                break;
            }
            case LightType::Area: {
                gpuLight = createAreaLight({0,0,0}, p.areaSize, p.color, p.intensity);
                break;
            }
        }
        if (p.dynamic) {
            addFlickerEffect(gpuLight, 0.0f, 0.0f); // will be overridden later
        }
        if (!g_gpu_lighting_system) {
            initializeGPULightingSystem();
        }
        uint32_t id = g_gpu_lighting_system->addLight(gpuLight);
        return id;
    }
};

} // namespace mt::light
