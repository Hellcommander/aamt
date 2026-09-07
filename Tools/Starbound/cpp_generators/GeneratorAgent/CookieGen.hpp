#pragma once

#include "LightTypes.hpp"
#include "GPUDeviceInterface.hpp"
#include <unordered_map>
#include <mutex>
#include <string>

namespace mt::light {

struct CookieConfig { uint32_t tex{}; uint32_t sampler{}; };

// Very small texture cache that hands out incremental handles.
// Replace with actual renderer texture manager later.
class CookieGen {
public:
    static CookieConfig apply(LightHandle /*handle*/, const CookieParams& cp) {
        CookieConfig cfg{};
        if (!cp.useCookie || cp.texturePath.empty()) return cfg;

        uint32_t texHandle = getOrLoad(cp.texturePath);
        cfg.tex = texHandle;
        cfg.sampler = g_gpuDevice.createSampler(true, true); // Linear filtering, clamp to edge
        return cfg;
    }
private:
    static uint32_t getOrLoad(const std::string& path) {
        std::lock_guard<std::mutex> lock(m_mtx);
        auto it = m_cache.find(path);
        if (it != m_cache.end()) return it->second;
        
        // Use real GPU device interface
        uint32_t newHandle = g_gpuDevice.createTexture2D(path, true);
        if (newHandle != 0) {
            m_cache[path] = newHandle;
        }
        return newHandle;
    }

    static inline std::unordered_map<std::string, uint32_t> m_cache;
    static inline std::mutex m_mtx;
    static inline uint32_t m_nextId = 1000;
};

} // namespace mt::light
