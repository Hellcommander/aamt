#pragma once

#include "LightTypes.hpp"
#include "GPUDeviceInterface.hpp"
#include <vector>
#include <memory>

namespace mt::light {

struct GPUResourceConfig {
    GpuBuffer ubo{};
    GpuDescriptorSet descriptorSet{};
    std::vector<uint8_t> uboData;
};

// Handles GPU resource allocation and descriptor set creation
class GPUResourceGen {
public:
    static GPUResourceConfig apply(LightHandle handle, 
                                 const LightParams& lp,
                                 const ShadowConfig& sc,
                                 const CookieConfig& cc,
                                 const VolumetricConfig& vc,
                                 const FlickerConfig& fc) {
        GPUResourceConfig cfg{};
        
        // Pack all light data into UBO
        cfg.uboData = packUBOData(lp, sc, cc, vc, fc);
        
        // Allocate uniform buffer
        cfg.ubo = allocateUBO(cfg.uboData.size());
        
        // Build descriptor set
        cfg.descriptorSet = buildDescriptorSet(handle, cfg.ubo, sc, cc, vc);
        
        return cfg;
    }

private:
    static std::vector<uint8_t> packUBOData(const LightParams& lp,
                                           const ShadowConfig& sc,
                                           const CookieConfig& cc,
                                           const VolumetricConfig& vc,
                                           const FlickerConfig& fc) {
        std::vector<uint8_t> data;
        data.reserve(256); // Estimate size
        
        // Pack LightParams
        data.insert(data.end(), (uint8_t*)&lp.position, (uint8_t*)&lp.position + sizeof(glm::vec3));
        data.insert(data.end(), (uint8_t*)&lp.direction, (uint8_t*)&lp.direction + sizeof(glm::vec3));
        data.insert(data.end(), (uint8_t*)&lp.color, (uint8_t*)&lp.color + sizeof(glm::vec3));
        data.insert(data.end(), (uint8_t*)&lp.intensity, (uint8_t*)&lp.intensity + sizeof(float));
        data.insert(data.end(), (uint8_t*)&lp.range, (uint8_t*)&lp.range + sizeof(float));
        data.insert(data.end(), (uint8_t*)&lp.spotAngle, (uint8_t*)&lp.spotAngle + sizeof(float));
        data.insert(data.end(), (uint8_t*)&lp.spotBlend, (uint8_t*)&lp.spotBlend + sizeof(float));
        data.insert(data.end(), (uint8_t*)&lp.type, (uint8_t*)&lp.type + sizeof(LightType));
        
        // Pack ShadowConfig
        data.insert(data.end(), (uint8_t*)&sc.enabled, (uint8_t*)&sc.enabled + sizeof(bool));
        data.insert(data.end(), (uint8_t*)&sc.resolution, (uint8_t*)&sc.resolution + sizeof(uint32_t));
        data.insert(data.end(), (uint8_t*)&sc.map, (uint8_t*)&sc.map + sizeof(uint32_t));
        data.insert(data.end(), (uint8_t*)&sc.sampler, (uint8_t*)&sc.sampler + sizeof(uint32_t));
        
        // Pack CookieConfig
        data.insert(data.end(), (uint8_t*)&cc.tex, (uint8_t*)&cc.tex + sizeof(uint32_t));
        data.insert(data.end(), (uint8_t*)&cc.sampler, (uint8_t*)&cc.sampler + sizeof(uint32_t));
        
        // Pack VolumetricConfig
        data.insert(data.end(), (uint8_t*)&vc.effect.map, (uint8_t*)&vc.effect.map + sizeof(uint32_t));
        data.insert(data.end(), (uint8_t*)&vc.effect.sampler, (uint8_t*)&vc.effect.sampler + sizeof(uint32_t));
        
        // Pack FlickerConfig
        data.insert(data.end(), (uint8_t*)&fc.enabled, (uint8_t*)&fc.enabled + sizeof(bool));
        
        return data;
    }
    
    static GpuBuffer allocateUBO(size_t size) {
        return g_gpuDevice.createUniformBuffer(size);
    }
    
    static GpuDescriptorSet buildDescriptorSet(LightHandle handle,
                                             GpuBuffer ubo,
                                             const ShadowConfig& sc,
                                             const CookieConfig& cc,
                                             const VolumetricConfig& vc) {
        return g_gpuDevice.createDescriptorSet(ubo, sc.map, cc.tex, vc.effect.map);
    }
};

} // namespace mt::light 
