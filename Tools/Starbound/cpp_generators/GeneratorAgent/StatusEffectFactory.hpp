#pragma once

#include "StatusEffectTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>
#include <vector>

namespace MagiTech {
namespace StatusEffects {

// Forward declarations for the generator namespaces
namespace ShaderGen {
    ShaderHandle build(const StatusEffectParams& s);
}

namespace TextureGen {
    TextureHandle build(const StatusEffectParams& s);
}

namespace MeshGen {
    MeshHandle build(const StatusEffectParams& s);
}

namespace ParticleGen {
    ParticleHandle build(const StatusEffectParams& s);
}

namespace IconGen {
    TextureHandle build(const StatusEffectParams& s, const UIParams& u);
}

class StatusEffectFactory {
public:
    StatusEffectFactory();
    ~StatusEffectFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    // Async generation
    std::future<EffectBundle> generateAsync(const StatusEffectParams& s, const UIParams& u);
    
    // Synchronous generation for immediate use
    EffectBundle generateSync(const StatusEffectParams& s, const UIParams& u);
    
    // JSON loading
    std::future<EffectBundle> generateFromJson(const std::string& effectJsonPath, const std::string& uiJsonPath);
    std::future<EffectBundle> generateFromParams(const StatusEffectParams& effectParams, const UIParams& uiParams);
    
    // Batch generation
    std::vector<std::future<EffectBundle>> generateBatch(const std::vector<std::pair<StatusEffectParams, UIParams>>& params);
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    size_t getCacheCapacity() const;
    
    // Validation
    bool validateEffectParams(const StatusEffectParams& params);
    std::string getEffectValidationErrors(const StatusEffectParams& params);
    bool validateUIParams(const UIParams& params);
    std::string getUIValidationErrors(const UIParams& params);

private:
    ConcurrentLRUCache<uint64_t, EffectBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
};

// Global factory instance
extern StatusEffectFactory g_effectFactory;

} // namespace StatusEffects
} // namespace MagiTech
