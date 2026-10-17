#include "LightAssetFactory.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <chrono>
#include <exception>
#include <future>
#include <stdexcept>
#include <thread>

namespace mt::light {

// ---------------------------------------------------------------------------------------------------------------------
LightAssetFactory::LightAssetFactory(size_t cacheCapacity, size_t workerThreads)
    : m_cache(cacheCapacity == 0 ? 1 : cacheCapacity) {
    m_metrics.reset();

    size_t threads = workerThreads;
    if (threads == 0) {
        const unsigned hw = std::thread::hardware_concurrency();
        threads = std::clamp<size_t>(hw > 1 ? hw - 1 : 1, 1, 4);
    }
    m_threadPool.start(threads);
    m_initialized = true;
}

LightAssetFactory::~LightAssetFactory() {
    // Queued builds reference this factory: finish them before any member is destroyed.
    m_threadPool.stop();
    m_initialized = false;
}

uint64_t LightAssetFactory::makeKey(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                    const VolumetricParams& vp, const FlickerParams& fp, const LODParams& lodp) const {
    return hashCombine(hashParams(lp), hashParams(sp), hashParams(cp), hashParams(vp), hashParams(fp), hashParams(lodp));
}

void LightAssetFactory::optimizeParams(const LODData& lod, LightParams& lp, ShadowParams& sp, CookieParams& cp,
                                       VolumetricParams& vp, FlickerParams& fp) {
    // The most detailed LOD level bounds what the light can ever display.
    if (!lod.levels.empty()) {
        const LightLODLevel& top = lod.levels.front();
        if (top.shadowRes <= 0) {
            sp.castShadows = false;
        } else {
            sp.resolution = std::min(sp.resolution, top.shadowRes);
        }
        if (!top.cookie) cp.useCookie = false;
        if (!top.volumetric) vp.density = 0.0f;
    }

    // Volumetric shafts are opt-in per light.
    if (!lp.volumetric) vp.density = 0.0f;

    // A light that emits nothing needs no shadows, shafts or flicker.
    const float maxChannel = std::max({lp.color.r, lp.color.g, lp.color.b});
    if (lp.intensity <= 0.0f || maxChannel <= 0.0f) {
        sp.castShadows = false;
        vp.density = 0.0f;
        fp.enabled = false;
    }

    // Lights with no reach cannot illuminate anything (directional lights have no range).
    if (lp.type != LightType::Directional && lp.range <= 0.0f) {
        sp.castShadows = false;
        vp.density = 0.0f;
    }
}

void LightAssetFactory::releaseResources(LightBundle& b) {
    auto& device = GPUDeviceInterface::getInstance();
    if (b.descSet) device.destroyDescriptorSet(b.descSet);
    if (b.lightUBO) device.destroyBuffer(b.lightUBO);
    if (b.cullPipeline) device.destroyPipeline(b.cullPipeline);
    if (b.renderPipeline) device.destroyPipeline(b.renderPipeline);
    ShadowGen::release(b.shadows);
    CookieGen::release(b.cookie);
    VolumetricGen::release(b.volume);
    LightGen::destroy(b.handle);
    b.descSet = 0;
    b.lightUBO = 0;
    b.cullPipeline = 0;
    b.renderPipeline = 0;
    b.flicker = FlickerConfig{};
    b.handle = 0;
}

LightBundle LightAssetFactory::buildBundle(const LightParams& lpIn, const ShadowParams& spIn, const CookieParams& cpIn,
                                           const VolumetricParams& vpIn, const FlickerParams& fpIn,
                                           const LODParams& lodp) {
    // Scratch bundle from the pool (avoids re-allocating the LOD tables for every build).
    auto scratch = m_bundlePool.acquire();
    LightBundle& b = *scratch;
    b = LightBundle{};

    LightParams lp = lpIn;
    ShadowParams sp = spIn;
    CookieParams cp = cpIn;
    VolumetricParams vp = vpIn;
    FlickerParams fp = fpIn;

    // 1. LOD table, then strip features no LOD level can show
    b.lod = LightLODGen::compute(lodp);
    optimizeParams(b.lod, lp, sp, cp, vp, fp);
    b.type = lp.type;

    try {
        // 2. CPU side constructs
        b.handle  = LightGen::build(lp);
        b.shadows = ShadowGen::configure(b.handle, lp.type, sp);
        b.cookie  = CookieGen::apply(b.handle, cp);
        b.volume  = VolumetricGen::setup(b.handle, vp);
        b.flicker = FlickerGen::attach(b.handle, fp);

        // 3. GPU resources
        const GPUResourceConfig gpuConfig =
            GPUResourceGen::apply(b.handle, lp, b.shadows, b.cookie, b.volume, b.flicker);
        if (gpuConfig.ubo == 0 || gpuConfig.descriptorSet == 0) {
            throw std::runtime_error("failed to allocate GPU resources for light '" + lp.id + "'");
        }
        b.lightUBO = gpuConfig.ubo;
        b.descSet = gpuConfig.descriptorSet;
        b.cullPipeline = GpuCullingGen::buildClusterCuller(b.lod);
        b.renderPipeline = LightShaderGen::compileLightingPipeline(lp.type, b.cookie.enabled,
                                                                   b.volume.enabled ? b.volume.density : 0.0f);
        if (b.cullPipeline == 0 || b.renderPipeline == 0) {
            throw std::runtime_error("failed to create pipelines for light '" + lp.id + "'");
        }
    } catch (...) {
        releaseResources(b);
        m_bundlePool.release(std::move(scratch));
        throw;
    }

    b.creationTime = std::chrono::steady_clock::now();
    LightBundle result = b;
    m_bundlePool.release(std::move(scratch));

    {
        std::lock_guard<std::mutex> lock(m_liveMutex);
        m_liveHandles.insert(result.handle);
    }
    return result;
}

LightBundle LightAssetFactory::completeRequest(uint64_t key, const LightParams& lp, const ShadowParams& sp,
                                               const CookieParams& cp, const VolumetricParams& vp,
                                               const FlickerParams& fp, const LODParams& lodp) {
    auto takeWaiters = [&]() {
        std::vector<std::promise<LightBundle>> waiters;
        std::lock_guard<std::mutex> lock(m_inflightMutex);
        auto it = m_inflight.find(key);
        if (it != m_inflight.end()) {
            waiters = std::move(it->second);
            m_inflight.erase(it);
        }
        return waiters;
    };

    LightBundle bundle;
    try {
        bundle = buildBundle(lp, sp, cp, vp, fp, lodp);
    } catch (...) {
        const std::exception_ptr error = std::current_exception();
        for (auto& waiter : takeWaiters()) waiter.set_exception(error);
        throw;
    }

    bundle.cacheKey = key;
    // Publish to the cache before leaving the in-flight table so later requests always find one of the two.
    m_cache.insert(key, bundle);
    for (auto& waiter : takeWaiters()) waiter.set_value(bundle);
    return bundle;
}

std::future<LightBundle> LightAssetFactory::generateAsync(const LightParams& lp, const ShadowParams& sp,
                                                          const CookieParams& cp, const VolumetricParams& vp,
                                                          const FlickerParams& fp, const LODParams& lodp) {
    const uint64_t key = makeKey(lp, sp, cp, vp, fp, lodp);
    std::promise<LightBundle> promise;
    std::future<LightBundle> result = promise.get_future();

    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
        promise.set_value(*hit);
        return result;
    }

    bool owner = false;
    {
        std::lock_guard<std::mutex> lock(m_inflightMutex);
        if (auto hit = m_cache.find(key)) { // finished between the first lookup and taking the lock
            m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
            promise.set_value(*hit);
            return result;
        }
        auto [it, inserted] = m_inflight.try_emplace(key);
        it->second.push_back(std::move(promise));
        owner = inserted;
    }
    m_metrics.cacheMisses.fetch_add(1, std::memory_order_relaxed);

    if (owner) {
        m_metrics.asyncGenerations.fetch_add(1, std::memory_order_relaxed);
        m_threadPool.enqueue([this, key, lp, sp, cp, vp, fp, lodp]() {
            try {
                completeRequest(key, lp, sp, cp, vp, fp, lodp);
            } catch (const std::exception& e) {
                // Already delivered to every waiting future; log for diagnostics.
                MagiTech::Log::error("LightFactory", "generating light '{}' failed: {}", lp.id, e.what());
            } catch (...) {
                MagiTech::Log::error("LightFactory", "generating light '{}' failed: unknown error", lp.id);
            }
        });
    }
    return result;
}

LightBundle LightAssetFactory::generateSync(const LightParams& lp, const ShadowParams& sp, const CookieParams& cp,
                                            const VolumetricParams& vp, const FlickerParams& fp,
                                            const LODParams& lodp) {
    const uint64_t key = makeKey(lp, sp, cp, vp, fp, lodp);
    if (auto hit = m_cache.find(key)) {
        m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
        return *hit;
    }

    std::future<LightBundle> joined;
    bool owner = false;
    {
        std::lock_guard<std::mutex> lock(m_inflightMutex);
        if (auto hit = m_cache.find(key)) {
            m_metrics.cacheHits.fetch_add(1, std::memory_order_relaxed);
            return *hit;
        }
        auto it = m_inflight.find(key);
        if (it != m_inflight.end()) {
            // Someone is already building this light: wait for that build instead of duplicating it.
            std::promise<LightBundle> promise;
            joined = promise.get_future();
            it->second.push_back(std::move(promise));
        } else {
            m_inflight.try_emplace(key);
            owner = true;
        }
    }
    m_metrics.cacheMisses.fetch_add(1, std::memory_order_relaxed);

    if (!owner) return joined.get();

    m_metrics.syncGenerations.fetch_add(1, std::memory_order_relaxed);
    return completeRequest(key, lp, sp, cp, vp, fp, lodp);
}

std::future<std::vector<LightBundle>> LightAssetFactory::generateBatchAsync(const std::vector<LightRequest>& requests) {
    m_metrics.batchProcessings.fetch_add(1, std::memory_order_relaxed);

    // Every request is scheduled on the worker pool right away (identical ones coalesce)...
    std::vector<std::future<LightBundle>> futures;
    futures.reserve(requests.size());
    for (const auto& request : requests) {
        const auto& [lp, sp, cp, vp, fp, lodp] = request;
        futures.push_back(generateAsync(lp, sp, cp, vp, fp, lodp));
    }

    // ...and collected on a separate thread, so no pool worker ever blocks on other pool tasks.
    return std::async(std::launch::async, [futures = std::move(futures)]() mutable {
        std::vector<LightBundle> results;
        results.reserve(futures.size());
        for (auto& future : futures) {
            results.push_back(future.get());
        }
        return results;
    });
}

bool LightAssetFactory::releaseBundle(const LightBundle& bundle) {
    if (bundle.handle == 0) return false;
    {
        std::lock_guard<std::mutex> lock(m_liveMutex);
        if (m_liveHandles.erase(bundle.handle) == 0) return false; // unknown or already released
    }
    if (bundle.cacheKey != 0) m_cache.erase(bundle.cacheKey);
    LightBundle copy = bundle;
    releaseResources(copy);
    return true;
}

void LightAssetFactory::clearCache() {
    m_cache.clear();
    m_metrics.reset();
}

size_t LightAssetFactory::getCacheSize() const {
    return m_cache.size();
}

double LightAssetFactory::getCacheHitRate() const {
    return m_metrics.getCacheHitRate();
}

void LightAssetFactory::preloadCommonLights() {
    // Preload common light configurations for better cache performance
    std::vector<LightRequest> commonLights;

    // Point light with shadows
    {
        LightParams lp{};
        lp.id = "common_point_shadowed";
        lp.type = LightType::Point;
        lp.position = {0.0f, 0.0f, 0.0f};
        lp.color = {1.0f, 1.0f, 1.0f};
        lp.intensity = 1.0f;
        lp.range = 10.0f;

        ShadowParams sp{};
        sp.castShadows = true;
        sp.resolution = 1024;

        commonLights.emplace_back(lp, sp, CookieParams{}, VolumetricParams{}, FlickerParams{}, LODParams{});
    }

    // Spot light with cookie
    {
        LightParams lp{};
        lp.id = "common_spot_cookie";
        lp.type = LightType::Spot;
        lp.position = {0.0f, 5.0f, 0.0f};
        lp.direction = {0.0f, -1.0f, 0.0f};
        lp.color = {1.0f, 0.8f, 0.6f};
        lp.intensity = 2.0f;
        lp.range = 15.0f;
        lp.outerAngle = 45.0f;
        lp.innerAngle = 45.0f * (1.0f - 0.1f); // 10% edge blend

        ShadowParams sp{};
        sp.castShadows = false;

        CookieParams cp{};
        cp.useCookie = true;
        cp.texturePath = "textures/cookies/spotlight_cookie.png";

        commonLights.emplace_back(lp, sp, cp, VolumetricParams{}, FlickerParams{}, LODParams{});
    }

    // Generate all common lights asynchronously and wait for completion
    auto future = generateBatchAsync(commonLights);
    try {
        future.get();
    } catch (const std::exception& e) {
        MagiTech::Log::warn("LightFactory", "preloading common lights failed: {}", e.what());
    }
}

void LightAssetFactory::warmupCache() {
    // Warm up the cache with frequently used light configurations
    preloadCommonLights();
}

bool LightAssetFactory::shouldUseAsync(const LightParams& lp) const {
    // Spot / area lights with a large, bright footprint need shadow, cookie and pipeline work that is worth
    // moving off the calling thread; small point / directional lights build quickly enough inline.
    const bool isComplex = (lp.type == LightType::Spot || lp.type == LightType::Area) &&
                           lp.intensity > 2.0f && lp.range > 10.0f;
    return isComplex || lp.volumetric;
}

} // namespace mt::light
