#pragma once

#include "LightTypes.hpp"
#include "LightGen.hpp"
#include "GPUDeviceInterface.hpp"
#include "core/Log.hpp"
#include <string>

namespace mt::light {

struct CookieConfig {
    bool       enabled{false};
    GpuTexture tex{};
    GpuSampler sampler{};
    Vec2       uvScale{1.0f, 1.0f};
    Vec2       uvOffset{0.0f, 0.0f};
};

// Loads light cookie (projected mask) textures. Textures are shared and reference counted by
// GPUDeviceInterface, so the same cookie file is decoded only once.
class CookieGen {
public:
    static CookieConfig apply(LightHandle handle, const CookieParams& cp) {
        CookieConfig cfg{};
        if (!cp.useCookie || cp.texturePath.empty()) {
            LightGen::setFlag(handle, LightFlags::Cookie, false);
            return cfg;
        }

        auto& device = GPUDeviceInterface::getInstance();
        cfg.tex = device.createTexture2D(cp.texturePath, true);
        if (cfg.tex == 0) {
            MagiTech::Log::warn("LightCookie", "cookie texture '{}' unavailable; light {} renders without cookie",
                                cp.texturePath, handle);
            LightGen::setFlag(handle, LightFlags::Cookie, false);
            return CookieConfig{};
        }
        cfg.sampler = device.createSampler(true, true); // linear filtering, clamp to edge
        cfg.uvScale = cp.uvScale;
        cfg.uvOffset = cp.uvOffset;
        cfg.enabled = true;
        LightGen::setFlag(handle, LightFlags::Cookie, true);
        return cfg;
    }

    static void release(CookieConfig& cfg) {
        auto& device = GPUDeviceInterface::getInstance();
        if (cfg.tex) device.destroyTexture(cfg.tex);
        if (cfg.sampler) device.destroySampler(cfg.sampler);
        cfg = CookieConfig{};
    }
};

} // namespace mt::light
