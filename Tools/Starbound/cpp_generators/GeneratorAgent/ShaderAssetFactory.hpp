#pragma once
#include <future>
#include <optional>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "ShaderAssetTypes.hpp"

namespace MagiTech {
namespace ShaderAssets {

// Forward declarations for generator functions
namespace TemplateGen {
    std::string expand(const std::string& t, const std::vector<std::string>& d, const std::vector<std::string>& i);
}
namespace CompileGen {
    ShaderHandle compile(const std::string& src, ShaderStage s, ShaderLang l, CompileTarget t);
}
namespace ReflectionGen {
    ReflectionData inspect(const ShaderHandle& module);
}
namespace PipelineGen {
    PipelineStateHandle create(const PipelineParams& pp, const ReflectionData& r);
}

// Simple hash combiner
inline uint64_t hashCombine(uint64_t h1, uint64_t h2) {
    return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2));
}

class ShaderAssetFactory {
    ConcurrentLRUCache<uint64_t, ShaderAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;

public:
    ShaderAssetFactory() = default;
    ~ShaderAssetFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    std::future<ShaderAssetBundle> generateAsync(
        const ShaderParams& sp,
        std::optional<PipelineParams> pp = std::nullopt,
        CompileTarget target = CompileTarget::SPIRV
    );
};

} // namespace ShaderAssets
} // namespace MagiTech
