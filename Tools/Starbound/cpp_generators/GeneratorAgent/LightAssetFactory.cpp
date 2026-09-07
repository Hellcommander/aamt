#include "LightAssetFactory.hpp"
#include "LightGen.hpp"
#include <future>
#include <chrono>
#include <algorithm>
#include <shared_mutex>

// ---------------------------------------------------------------------------------------------------------------------
// Stub generator modules — replace with real engine code *or* include actual module headers if they exist.
// Only minimal placeholders to allow successful compilation of this factory in isolation.
// ---------------------------------------------------------------------------------------------------------------------
namespace mt::light::ShadowGen  { inline ShadowConfig  configure(LightHandle, const ShadowParams&)  { return {}; } }
namespace mt::light::CookieGen  { inline CookieConfig  apply    (LightHandle, const CookieParams&)  { return {}; } }

// ---------------------------------------------------------------------------------------------------------------------
namespace mt::light {

// Forward declaration for hypothetical ThreadPoolManager implementation.
namespace {
    // Minimal single-thread pool fallback if engine pool not yet integrated.
    struct FallbackThreadPool : std::enable_shared_from_this<FallbackThreadPool> {
        template <typename Fn>
        std::future<decltype(std::declval<Fn>()())> enqueue(Fn&& fn) {
            using Ret = decltype(fn());
            return std::async(std::launch::async, std::forward<Fn>(fn));
        }
    };
}

// Global singleton instance
LightAssetFactory g_lightFactory;

// ---------------------------------------------------------------------------------------------------------------------
LightAssetFactory::LightAssetFactory() {
    // Attempt to acquire engine-wide thread pool via dependency injection later.
    if (!m_threadPool) {
        m_threadPool = std::make_shared<FallbackThreadPool>();
    }
    
    // Initialize performance metrics
    m_metrics.reset();
    
    // Initialize GPU device interface (will be set by external renderer)
    // g_gpuDevice.initialize(renderer); // Called externally
}

LightAssetFactory::~LightAssetFactory() = default;

uint64_t LightAssetFactory::makeKey(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                    const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp) const {
    return hashCombine(hashParams(lp), hashParams(sp), hashParams(cp), hashParams(vp), hashParams(fp), hashParams(lodp));
}

LightBundle LightAssetFactory::buildBundle(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                           const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp) {
    // Use object pool for better memory management
    auto bundlePtr = m_bundlePool.acquire();
    LightBundle& b = *bundlePtr;
    
    // 1. CPU side constructs
    b.handle  = LightGen::build(lp);
    b.shadows = ShadowGen::configure(b.handle, sp);
    b.cookie  = CookieGen::apply(b.handle, cp);
    b.volume  = VolumetricGen::setup(b.handle, vp);
    b.flicker = FlickerGen::attach(b.handle, fp);

    // 2. GPU resources
    auto gpuConfig = GPUResourceGen::apply(b.handle, lp, b.shadows, b.cookie, b.volume, b.flicker);
    b.lightUBO = gpuConfig.ubo;
    b.descSet = gpuConfig.descriptorSet;
    b.cullPipeline   = GpuCullingGen::buildClusterCuller(lodp);
    b.renderPipeline = ShaderGen::compileLightingPipeline(lp.type, cp.useCookie, vp.density);

    // 3. LOD data
    b.lod = LODGen::compute(lodp);
    
    // 4. Optimize the bundle
    optimizeBundle(b);
    
    // Prefetch related assets for better cache performance
    prefetchRelatedAssets(lp);

    return b;
}

std::future<LightBundle> LightAssetFactory::generateAsync(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                                          const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp) {
    uint64_t key = makeKey(lp, sp, cp, vp, fp, lodp);

    if (auto hit = m_cache.find(key)) {
        // Return cached bundle via deferred future (executes immediately)
        m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
        return std::async(std::launch::deferred, [bundle = *hit]() { return bundle; });
    }

    m_metrics.cacheMisses.fetch_add(1, std::memory_order_relaxed);
    m_metrics.asyncGenerations.fetch_add(1, std::memory_order_relaxed);

    // Execute through thread pool
    return m_threadPool->enqueue([this, lp, sp, cp, vp, fp, lodp, key]() {
        LightBundle bundle = buildBundle(lp, sp, cp, vp, fp, lodp);
        m_cache.insert(key, bundle);
        return bundle;
    });
}

LightBundle LightAssetFactory::generateSync(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                            const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp) {
    uint64_t key = makeKey(lp, sp, cp, vp, fp, lodp);
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
        return *hit;
    }

    m_metrics.cacheMisses.fetch_add(1, std::memory_order_relaxed);
    m_metrics.syncGenerations.fetch_add(1, std::memory_order_relaxed);

    LightBundle bundle = buildBundle(lp, sp, cp, vp, fp, lodp);
    m_cache.insert(key, bundle);
    return bundle;
}

std::future<std::vector<LightBundle>> LightAssetFactory::generateBatchAsync(
    const std::vector<std::tuple<LightParams, ShadowParams, CookieParams, VolumetricParams, FlickerParams, LODParams>>& requests) {
    
    m_metrics.batchProcessings.fetch_add(1, std::memory_order_relaxed);
    
    return m_threadPool->enqueue([this, requests]() {
        std::vector<LightBundle> results;
        results.reserve(requests.size());
        
        // Process requests in parallel using thread pool
        std::vector<std::future<LightBundle>> futures;
        futures.reserve(requests.size());
        
        for (const auto& request : requests) {
            const auto& [lp, sp, cp, vp, fp, lodp] = request;
            futures.push_back(generateAsync(lp, sp, cp, vp, fp, lodp));
        }
        
        // Collect results
        for (auto& future : futures) {
            results.push_back(future.get());
        }
        
        return results;
    });
}

void LightAssetFactory::clearCache() { 
    m_cache.clear(); 
    m_metrics.reset();
}

size_t LightAssetFactory::getCacheSize() const {
    // This would need to be implemented in OptimizedLRUCache
    return 0; // Placeholder
}

double LightAssetFactory::getCacheHitRate() const {
    return m_cache.getHitRate();
}

void LightAssetFactory::preloadCommonLights() {
    // Preload common light configurations for better cache performance
    std::vector<std::tuple<LightParams, ShadowParams, CookieParams, VolumetricParams, FlickerParams, LODParams>> commonLights;
    
    // Point light with shadows
    {
        LightParams lp{};
        lp.type = LightType::Point;
        lp.position = {0, 0, 0};
        lp.color = {1, 1, 1};
        lp.intensity = 1.0f;
        lp.range = 10.0f;
        
        ShadowParams sp{};
        sp.enabled = true;
        sp.resolution = 1024;
        
        CookieParams cp{};
        VolumetricParams vp{};
        FlickerParams fp{};
        LODParams lodp{};
        
        commonLights.emplace_back(lp, sp, cp, vp, fp, lodp);
    }
    
    // Spot light with cookie
    {
        LightParams lp{};
        lp.type = LightType::Spot;
        lp.position = {0, 5, 0};
        lp.direction = {0, -1, 0};
        lp.color = {1, 0.8f, 0.6f};
        lp.intensity = 2.0f;
        lp.range = 15.0f;
        lp.spotAngle = 45.0f;
        lp.spotBlend = 0.1f;
        
        ShadowParams sp{};
        sp.enabled = false;
        
        CookieParams cp{};
        cp.useCookie = true;
        cp.texturePath = "textures/cookies/spotlight_cookie.png";
        
        VolumetricParams vp{};
        FlickerParams fp{};
        LODParams lodp{};
        
        commonLights.emplace_back(lp, sp, cp, vp, fp, lodp);
    }
    
    // Generate all common lights asynchronously
    auto future = generateBatchAsync(commonLights);
    future.wait(); // Wait for completion
}

void LightAssetFactory::warmupCache() {
    // Warm up the cache with frequently used light configurations
    preloadCommonLights();
}

void LightAssetFactory::optimizeBundle(LightBundle& bundle) {
    // Apply optimizations based on light type and parameters
    // This could include:
    // - LOD-based feature disabling
    // - Memory layout optimization
    // - GPU resource optimization
    // - Shader variant selection
}

void LightAssetFactory::prefetchRelatedAssets(const LightParams& lp) {
    // Prefetch related assets that are likely to be used together
    // This could include:
    // - Similar light configurations
    // - Common texture assets
    // - Shader variants
}

bool LightAssetFactory::shouldUseAsync(const LightParams& lp) const {
    // Determine if async generation is beneficial based on light complexity
    // Factors to consider:
    // - Light type complexity
    // - Number of features enabled
    // - Expected generation time
    // - Current system load
    
    // Simple heuristic: use async for complex lights
    bool isComplex = (lp.type == LightType::Spot || lp.type == LightType::Area) && 
                     lp.intensity > 2.0f && lp.range > 10.0f;
    
    return isComplex;
}

} // namespace mt::light
