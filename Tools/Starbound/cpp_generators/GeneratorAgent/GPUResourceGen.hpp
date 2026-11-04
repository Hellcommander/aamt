#pragma once

#include "LightTypes.hpp"
#include "ShadowGen.hpp"
#include "CookieGen.hpp"
#include "VolumetricGen.hpp"
#include "FlickerGen.hpp"
#include "GPUDeviceInterface.hpp"
#include <cmath>
#include <cstring>
#include <vector>
#include <glm/geometric.hpp>
#include <glm/trigonometric.hpp>
#include <glm/vec4.hpp>

namespace mt::light {

// std140 layout of the per-light uniform block. Must match the `LightBlock` declared by LightShaderGen.
struct LightUBO {
    glm::vec4  positionType;   // xyz position, w = LightType
    glm::vec4  directionRange; // xyz direction, w = range
    glm::vec4  colorIntensity; // rgb colour, a = intensity
    glm::vec4  spotArea;       // x = cos(inner), y = cos(outer), z/w = area size
    glm::vec4  shadow;         // x = enabled, y = resolution, z = bias, w = normal bias
    glm::vec4  cookieUV;       // xy = uv scale, zw = uv offset
    glm::vec4  volumetric;     // x = density, y = anisotropy, z = enabled, w = shadow cascades
    glm::vec4  scatterColor;   // rgb scatter colour, a = cookie enabled
    glm::vec4  flicker;        // x = enabled, y = frequency, z = min scale, w = max scale
    glm::uvec4 extra;          // x = flicker pattern, y = flicker seed, z = shadow layers, w = light handle
};
static_assert(sizeof(LightUBO) == 160, "LightUBO must match the std140 LightBlock layout");

struct GPUResourceConfig {
    GpuBuffer            ubo{};
    GpuDescriptorSet     descriptorSet{};
    std::vector<uint8_t> uboData;
};

// Packs light data into a uniform buffer and binds all of the light's resources in a descriptor set.
class GPUResourceGen {
public:
    static GPUResourceConfig apply(LightHandle handle,
                                   const LightParams& lp,
                                   const ShadowConfig& sc,
                                   const CookieConfig& cc,
                                   const VolumetricConfig& vc,
                                   const FlickerConfig& fc) {
        GPUResourceConfig cfg{};
        cfg.uboData = packUBOData(handle, lp, sc, cc, vc, fc);
        cfg.ubo = allocateUBO(cfg.uboData);
        if (cfg.ubo == 0) return cfg;

        cfg.descriptorSet = buildDescriptorSet(cfg.ubo, sc, cc, vc);
        if (cfg.descriptorSet == 0) {
            GPUDeviceInterface::getInstance().destroyBuffer(cfg.ubo);
            cfg.ubo = 0;
        }
        return cfg;
    }

    static LightUBO makeUBO(LightHandle handle, const LightParams& lp, const ShadowConfig& sc, const CookieConfig& cc,
                            const VolumetricConfig& vc, const FlickerConfig& fc) {
        LightUBO u{};
        const Vec3 dir = glm::length(lp.direction) > 1e-6f ? glm::normalize(lp.direction) : Vec3(0.0f, -1.0f, 0.0f);
        const float outer = std::max(lp.outerAngle, 0.0f);
        const float inner = std::min(std::max(lp.innerAngle, 0.0f), outer);

        u.positionType = glm::vec4(lp.position, static_cast<float>(static_cast<uint32_t>(lp.type)));
        u.directionRange = glm::vec4(dir, lp.range);
        u.colorIntensity = glm::vec4(lp.color, lp.intensity);
        u.spotArea = glm::vec4(std::cos(glm::radians(inner)), std::cos(glm::radians(outer)), lp.areaSize.x,
                               lp.areaSize.y);
        u.shadow = glm::vec4(sc.enabled ? 1.0f : 0.0f, static_cast<float>(sc.resolution), sc.bias, sc.normalBias);
        u.cookieUV = glm::vec4(cc.uvScale, cc.uvOffset);
        u.volumetric = glm::vec4(vc.density, vc.anisotropy, vc.enabled ? 1.0f : 0.0f, static_cast<float>(sc.cascades));
        u.scatterColor = glm::vec4(vc.scatterColor, cc.enabled ? 1.0f : 0.0f);
        u.flicker = glm::vec4(fc.enabled ? 1.0f : 0.0f, fc.frequency, fc.minScale, fc.maxScale);
        u.extra = glm::uvec4(static_cast<uint32_t>(fc.pattern), fc.seed, sc.layers, handle);
        return u;
    }

private:
    static std::vector<uint8_t> packUBOData(LightHandle handle, const LightParams& lp, const ShadowConfig& sc,
                                            const CookieConfig& cc, const VolumetricConfig& vc,
                                            const FlickerConfig& fc) {
        const LightUBO u = makeUBO(handle, lp, sc, cc, vc, fc);
        std::vector<uint8_t> data(sizeof(LightUBO));
        std::memcpy(data.data(), &u, sizeof(LightUBO));
        return data;
    }

    static GpuBuffer allocateUBO(const std::vector<uint8_t>& data) {
        return GPUDeviceInterface::getInstance().createUniformBuffer(data.size(), data.data());
    }

    static GpuDescriptorSet buildDescriptorSet(GpuBuffer ubo,
                                               const ShadowConfig& sc,
                                               const CookieConfig& cc,
                                               const VolumetricConfig& vc) {
        DescriptorSetDesc desc;
        desc.uniformBuffer = ubo;
        desc.shadowMap = sc.map;
        desc.shadowSampler = sc.sampler;
        desc.cookieTexture = cc.tex;
        desc.cookieSampler = cc.sampler;
        desc.volumeTexture = vc.effect.map;
        desc.volumeSampler = vc.effect.sampler;
        return GPUDeviceInterface::getInstance().createDescriptorSet(desc);
    }
};

} // namespace mt::light
