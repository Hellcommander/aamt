#pragma once

#include "LightTypes.hpp"
#include "LightGen.hpp"
#include "ShadowGen.hpp"
#include "CookieGen.hpp"
#include "VolumetricGen.hpp"
#include "FlickerGen.hpp"
#include "GPUResourceGen.hpp"
#include "GpuCullingGen.hpp"
#include "LightShaderGen.hpp"
#include "LightLODGen.hpp"
#include "GPUDeviceInterface.hpp"
#include "GeneratorConcurrency.hpp"
#include <atomic>
#include <chrono>
#include <cstdint>
#include <future>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace mt::light {

// ---------------------------------------------------------------------------------------------------------------------
// Performance monitoring
// ---------------------------------------------------------------------------------------------------------------------
struct PerformanceSnapshot {
    uint64_t cacheHits{};
    uint64_t cacheMisses{};
    uint64_t asyncGenerations{};
    uint64_t syncGenerations{};
    uint64_t batchProcessings{};
    double   cacheHitRate{};
    double   secondsSinceReset{};
};

struct PerformanceMetrics {
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> asyncGenerations{0};
    std::atomic<uint64_t> syncGenerations{0};
    std::atomic<uint64_t> batchProcessings{0};
    std::atomic<int64_t>  lastResetNs{0};

    double getCacheHitRate() const {
        const uint64_t hits = cacheHits.load();
        const uint64_t total = hits + cacheMisses.load();
        return total > 0 ? static_cast<double>(hits) / static_cast<double>(total) : 0.0;
    }

    void reset() {
        cacheHits = 0;
        cacheMisses = 0;
        asyncGenerations = 0;
        syncGenerations = 0;
        batchProcessings = 0;
        lastResetNs = nowNs();
    }

    PerformanceSnapshot snapshot() const {
        PerformanceSnapshot s;
        s.cacheHits = cacheHits.load();
        s.cacheMisses = cacheMisses.load();
        s.asyncGenerations = asyncGenerations.load();
        s.syncGenerations = syncGenerations.load();
        s.batchProcessings = batchProcessings.load();
        s.cacheHitRate = getCacheHitRate();
        s.secondsSinceReset = static_cast<double>(nowNs() - lastResetNs.load()) * 1e-9;
        return s;
    }

    static int64_t nowNs() {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
                   std::chrono::steady_clock::now().time_since_epoch())
            .count();
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// Memory pool for LightBundle scratch objects
// ---------------------------------------------------------------------------------------------------------------------
template <typename T>
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
        if (!obj) return;
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_pool.size() < m_maxSize) {
            m_pool.push_back(std::move(obj));
        }
    }
};

// ---------------------------------------------------------------------------------------------------------------------
// High-level bundle returned to callers (Lua/editor/engine)
// ---------------------------------------------------------------------------------------------------------------------
struct LightBundle {
    LightHandle         handle{};        // light registered with WorldExLighting::GPULightingSystem
    LightType           type{LightType::Point};
    ShadowConfig        shadows{};
    CookieConfig        cookie{};
    VolumetricConfig    volume{};
    FlickerConfig       flicker{};
    GpuDescriptorSet    descSet{};       // descriptor set binding the light's resources
    GpuBuffer           lightUBO{};      // uniform buffer holding the LightUBO block
    GpuComputePipeline  cullPipeline{};  // cluster culling compute pipeline
    GpuPipeline         renderPipeline{};// lighting pipeline variant for this light
    LODData             lod{};
    uint64_t            cacheKey{};      // key of this bundle in the factory cache

    // Performance tracking
    std::chrono::steady_clock::time_point creationTime{std::chrono::steady_clock::now()};
};

using LightRequest = std::tuple<LightParams, ShadowParams, CookieParams, VolumetricParams, FlickerParams, LODParams>;

// ---------------------------------------------------------------------------------------------------------------------
// LightAssetFactory: thread-safe, asynchronous light asset creation & caching.
//
// Bundles are shared assets: identical requests return the same bundle (same light handle and GPU resources).
// Concurrent identical requests are coalesced into one build. releaseBundle() frees a bundle's resources for
// every holder and removes it from the cache.
// ---------------------------------------------------------------------------------------------------------------------
class LightAssetFactory {
public:
    explicit LightAssetFactory(size_t cacheCapacity = 1024, size_t workerThreads = 0);
    ~LightAssetFactory();

    LightAssetFactory(const LightAssetFactory&) = delete;
    LightAssetFactory& operator=(const LightAssetFactory&) = delete;

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
    std::future<std::vector<LightBundle>> generateBatchAsync(const std::vector<LightRequest>& requests);

    // Frees the bundle's light and GPU resources and evicts it from the cache. Returns false if nothing was freed.
    bool releaseBundle(const LightBundle& bundle);

    // Performance monitoring
    PerformanceSnapshot getPerformanceMetrics() const { return m_metrics.snapshot(); }
    void resetPerformanceMetrics() { m_metrics.reset(); }

    // Cache management (clearing forgets cached bundles; their holders keep the resources)
    void clearCache();
    size_t getCacheSize() const;
    double getCacheHitRate() const;
    bool isInitialized() const { return m_initialized.load(); }

    // Preloading and warmup
    void preloadCommonLights();
    void warmupCache();

    // True when a light is expensive enough that callers should prefer generateAsync over generateSync.
    bool shouldUseAsync(const LightParams& lp) const;

private:
    LightBundle buildBundle(const LightParams& lp,
                            const ShadowParams& sp,
                            const CookieParams& cp,
                            const VolumetricParams& vp,
                            const FlickerParams& fp,
                            const LODParams& lodp);

    // Builds (or fails) the request owned by this caller and fulfils every coalesced waiter.
    LightBundle completeRequest(uint64_t key, const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp);

    uint64_t makeKey(const LightParams&, const ShadowParams&, const CookieParams&, const VolumetricParams&,
                     const FlickerParams&, const LODParams&) const;

    // Drops features that the most detailed LOD level (or the light itself) can never show.
    static void optimizeParams(const LODData& lod, LightParams& lp, ShadowParams& sp, CookieParams& cp,
                               VolumetricParams& vp, FlickerParams& fp);
    static void releaseResources(LightBundle& bundle);

private:
    MagiTech::ConcurrentLRUCache<uint64_t, LightBundle> m_cache;
    MagiTech::GeneratorTaskPool                         m_threadPool;
    ObjectPool<LightBundle>                             m_bundlePool;
    PerformanceMetrics                                  m_metrics;
    std::atomic<bool>                                   m_initialized{false};

    // Requests currently being built: every caller waiting for the same key gets a promise here.
    std::mutex m_inflightMutex;
    std::unordered_map<uint64_t, std::vector<std::promise<LightBundle>>> m_inflight;

    // Lights built by this factory and not yet released (guards against double releases of shared resources).
    std::mutex m_liveMutex;
    std::unordered_set<LightHandle> m_liveHandles;
};

} // namespace mt::light
