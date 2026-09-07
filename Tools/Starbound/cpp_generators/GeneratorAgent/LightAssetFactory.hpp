#pragma once

#include "LightTypes.hpp"
#include "ShadowGen.hpp"
#include "CookieGen.hpp"
#include "GPUResourceGen.hpp"
#include "VolumetricGen.hpp"
#include "FlickerGen.hpp"
#include "GpuCullingGen.hpp"
#include "ShaderGen.hpp"
#include "LODGen.hpp"
#include "GPUDeviceInterface.hpp"
#include <future>
#include <unordered_map>
#include <mutex>
#include <shared_mutex>
#include <optional>
#include <memory>
#include <vector>
#include <chrono>
#include <atomic>

namespace mt {
    class ThreadPoolManager; // forward declared project-wide thread pool
}

namespace mt::light {

// ---------------------------------------------------------------------------------------------------------------------
// GPU handle stubs (replace with engine specific types)
// ---------------------------------------------------------------------------------------------------------------------
using LightHandle        = uint32_t;
using GpuDescriptorSet   = uint32_t;
using GpuBuffer          = uint32_t;
using GpuComputePipeline = uint32_t;
using GpuPipeline        = uint32_t;

// ---------------------------------------------------------------------------------------------------------------------
// Performance monitoring structures
// ---------------------------------------------------------------------------------------------------------------------
struct PerformanceMetrics {
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> asyncGenerations{0};
    std::atomic<uint64_t> syncGenerations{0};
    std::atomic<uint64_t> batchProcessings{0};
    std::chrono::high_resolution_clock::time_point lastReset;
    
    double getCacheHitRate() const {
        uint64_t total = cacheHits.load() + cacheMisses.load();
        return total > 0 ? static_cast<double>(cacheHits.load()) / total : 0.0;
    }
    
    void reset() {
        cacheHits = 0;
        cacheMisses = 0;
        asyncGenerations = 0;
        syncGenerations = 0;
        batchProcessings = 0;
        lastReset = std::chrono::high_resolution_clock::now();
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// Memory pool for LightBundle objects
// ---------------------------------------------------------------------------------------------------------------------
template<typename T>
class ObjectPool {
    std::vector<std::unique_ptr<T>> m_pool;
    std::mutex m_mutex;
    size_t m_maxSize;
    
public:
    explicit ObjectPool(size_t maxSize = 100) : m_maxSize(maxSize) {}
    
    std::unique_ptr<T> acquire() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_pool.empty()) {
            return std::make_unique<T>();
        }
        auto obj = std::move(m_pool.back());
        m_pool.pop_back();
        return obj;
    }
    
    void release(std::unique_ptr<T> obj) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_pool.size() < m_maxSize) {
            m_pool.push_back(std::move(obj));
        }
    }
};

struct VolumetricConfig { struct { uint32_t map{}; uint32_t sampler{}; } effect; };
struct FlickerConfig { bool enabled{}; };
struct LODData       { std::vector<float> screenSizes; std::vector<int> shadowRes; std::vector<bool> vol; std::vector<bool> cookie; };

// ---------------------------------------------------------------------------------------------------------------------
// High-level bundle returned to callers (Lua/editor/engine)
// ---------------------------------------------------------------------------------------------------------------------
struct LightBundle {
    LightHandle         handle{};      // CPU handle registered with renderer
    ShadowConfig        shadows{};
    CookieConfig        cookie{};
    VolumetricConfig    volume{};
    FlickerConfig       flicker{};
    GpuDescriptorSet    descSet{};     // GPU descriptor set with resources
    GpuBuffer           lightUBO{};    // GPU uniform buffer holding parameters
    GpuComputePipeline  cullPipeline{};// Cluster culling compute pipeline
    GpuPipeline         renderPipeline{};// Graphics pipeline for shading
    LODData             lod{};
    
    // Performance tracking
    std::chrono::high_resolution_clock::time_point creationTime;
    
    LightBundle() {
        creationTime = std::chrono::high_resolution_clock::now();
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// Optimized ConcurrentLRU with better performance characteristics
// ---------------------------------------------------------------------------------------------------------------------

template <typename Key, typename Value, size_t Capacity = 256>
class OptimizedLRUCache {
    using Pair = std::pair<Key, Value>;
    mutable std::shared_mutex m_rwMutex; // Read-write lock for better concurrency
    std::list<Pair>    list;
    std::unordered_map<Key, typename std::list<Pair>::iterator> map;
    std::atomic<size_t> m_hitCount{0};
    std::atomic<size_t> m_missCount{0};
    
public:
    std::optional<Value> find(const Key& k) {
        std::shared_lock<std::shared_mutex> lock(m_rwMutex);
        auto it = map.find(k);
        if (it == map.end()) {
            m_missCount.fetch_add(1, std::memory_order_relaxed);
            return std::nullopt;
        }
        
        // Move to front (MRU) - this requires exclusive access
        lock.unlock();
        std::unique_lock<std::shared_mutex> writeLock(m_rwMutex);
        
        // Double-check after acquiring write lock
        it = map.find(k);
        if (it == map.end()) {
            m_missCount.fetch_add(1, std::memory_order_relaxed);
            return std::nullopt;
        }
        
        list.splice(list.begin(), list, it->second);
        m_hitCount.fetch_add(1, std::memory_order_relaxed);
        return it->second->second;
    }
    
    void insert(const Key& k, const Value& v) {
        std::unique_lock<std::shared_mutex> lock(m_rwMutex);
        
        auto it = map.find(k);
        if (it != map.end()) {
            it->second->second = v;         // update existing
            list.splice(list.begin(), list, it->second);
            return;
        }
        
        list.emplace_front(k, v);
        map[k] = list.begin();
        
        if (list.size() > Capacity) {
            auto last = list.end(); --last;
            map.erase(last->first);
            list.pop_back();
        }
    }
    
    void clear() {
        std::unique_lock<std::shared_mutex> lock(m_rwMutex);
        list.clear();
        map.clear();
    }
    
    size_t getHitCount() const { return m_hitCount.load(std::memory_order_relaxed); }
    size_t getMissCount() const { return m_missCount.load(std::memory_order_relaxed); }
    double getHitRate() const {
        size_t total = getHitCount() + getMissCount();
        return total > 0 ? static_cast<double>(getHitCount()) / total : 0.0;
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// LightAssetFactory — thread-safe, asynchronous asset creation & caching with optimizations
// ---------------------------------------------------------------------------------------------------------------------
class LightAssetFactory {
public:
    LightAssetFactory();
    ~LightAssetFactory();

    // Core generation methods
    std::future<LightBundle> generateAsync(const LightParams& lp,
                                           const ShadowParams& sp,
                                           const CookieParams& cp,
                                           const VolumetricParams& vp,
                                           const FlickerParams& fp,
                                           const LODParams& lodp);

    LightBundle generateSync(const LightParams& lp,
                             const ShadowParams& sp,
                             const CookieParams& cp,
                             const VolumetricParams& vp,
                             const FlickerParams& fp,
                             const LODParams& lodp);

    // Batch processing for multiple lights
    std::future<std::vector<LightBundle>> generateBatchAsync(
        const std::vector<std::tuple<LightParams, ShadowParams, CookieParams, VolumetricParams, FlickerParams, LODParams>>& requests);

    // Performance monitoring
    PerformanceMetrics getPerformanceMetrics() const { return m_metrics; }
    void resetPerformanceMetrics() { m_metrics.reset(); }
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    double getCacheHitRate() const;
    bool isInitialized() const { return m_initialized; }

    // Preloading and warmup
    void preloadCommonLights();
    void warmupCache();

private:
    // Internal helpers (implemented in .cpp)
    LightBundle buildBundle(const LightParams& lp,
                            const ShadowParams& sp,
                            const CookieParams& cp,
                            const VolumetricParams& vp,
                            const FlickerParams& fp,
                            const LODParams& lodp);

    uint64_t makeKey(const LightParams&, const ShadowParams&, const CookieParams&, const VolumetricParams&, const FlickerParams&, const LODParams&) const;

    // Optimization helpers
    void optimizeBundle(LightBundle& bundle);
    void prefetchRelatedAssets(const LightParams& lp);
    bool shouldUseAsync(const LightParams& lp) const;

private:
    OptimizedLRUCache<uint64_t, LightBundle, 1024> m_cache; // Increased capacity
    std::shared_ptr<mt::ThreadPoolManager>         m_threadPool;
    ObjectPool<LightBundle>                         m_bundlePool;
    PerformanceMetrics                              m_metrics;
    bool                                            m_initialized{true};
    
    // Async texture loading cache
    std::unordered_map<std::string, std::future<uint32_t>> m_textureCache;
    std::mutex m_textureCacheMutex;
};

// Global singleton (like other factories)
extern LightAssetFactory g_lightFactory;

} // namespace mt::light
