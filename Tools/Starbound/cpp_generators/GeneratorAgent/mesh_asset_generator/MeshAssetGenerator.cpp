#include "MeshAssetGenerator.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <algorithm>
#include <initializer_list>
#include <optional>
#include <random>
#include <sstream>

namespace MagiTech::GeneratorAgent {

namespace {

// Builds the base mesh for an asset with the mt::MeshGenerator.
std::shared_ptr<mt::Mesh> buildBaseMesh(const MeshAssetParams& params) {
    const mt::MeshParams& mp = params.meshParams;

    if (params.type == "terrain" || mp.type == "Terrain") {
        mt::TerrainParams terrain;
        terrain.size = glm::vec2(mp.dimensions.x, mp.dimensions.z);
        terrain.resolution = glm::vec2(static_cast<float>(mp.subdivisions), static_cast<float>(mp.subdivisions));
        terrain.noiseScale = mp.noiseFrequency;
        terrain.seed = mp.seed;
        if (mp.dimensions.y > 0.0f) {
            terrain.heightScale = mp.dimensions.y; // presets store the height range in dimensions.y
        }
        return mt::MeshGenerator::generateTerrain(terrain);
    }

    if (params.type == "implicit" || mp.type == "SDF" || mp.type == "Implicit") {
        // Implicit surfaces: a signed distance field meshed with marching cubes.
        mt::SDFParams sdf;
        sdf.type = mt::SDFParams::SDFType::Sphere;
        sdf.dimensions = mp.dimensions;
        const float res = static_cast<float>(std::max(mp.subdivisions, 4));
        sdf.resolution = glm::vec3(res);
        sdf.isoThreshold = mp.isoThreshold;
        return mt::MeshGenerator::generateSDF(sdf);
    }

    if (mp.type == "Torus") {
        // dimensions = (2 * major, 2 * minor, 2 * major), see MeshAssetPresets::torus
        const uint32_t majorSegments = static_cast<uint32_t>(std::max(mp.subdivisions, 3));
        const uint32_t minorSegments = std::max<uint32_t>(majorSegments / 2, 3);
        return mt::MeshGenerator::generateTorus(mp.dimensions.x * 0.5f, mp.dimensions.y * 0.5f,
                                                majorSegments, minorSegments);
    }

    // Cube / Sphere / Cylinder / Plane (and anything else) go through the generic entry point.
    return mt::MeshGenerator::generateFromParams(mp);
}

} // namespace

MeshAssetGenerator::MeshAssetGenerator()
    : m_initialized(false)
    , m_cachingEnabled(true)
    , m_performanceMonitoringEnabled(false)
    , m_validationLevel(1)
    , m_threadCount(4)
    , m_maxGenerationTime(5.0f)
    , m_maxLoadTime(1.0f)
    , m_maxCacheSize(1000)
    , m_maxMemoryUsage(100 * 1024 * 1024) {
}

MeshAssetGenerator::~MeshAssetGenerator() {
    shutdown();
}

void MeshAssetGenerator::initialize(uint32_t threadCount) {
    if (m_initialized) return;

    m_stats.reset();

    // Set up default configuration (also sizes the worker pool)
    nlohmann::json defaultConfig = {
        {"threadCount", threadCount},
        {"maxCacheSize", m_maxCacheSize},
        {"maxMemoryUsage", m_maxMemoryUsage},
        {"maxGenerationTime", m_maxGenerationTime},
        {"validationLevel", m_validationLevel},
        {"enableCaching", m_cachingEnabled},
        {"enablePerformanceMonitoring", m_performanceMonitoringEnabled}
    };
    setConfig(defaultConfig);

    m_pool.start(m_threadCount);
    m_initialized = true;
}

void MeshAssetGenerator::shutdown() {
    if (!m_initialized) return;

    // Finish queued async jobs before tearing down state they use
    m_pool.stop();

    // Clear cache
    clearCache();

    // Reset stats
    resetStats();

    m_initialized = false;
}

void MeshAssetGenerator::setConfig(const nlohmann::json& config) {
    if (config.contains("threadCount")) {
        // Applied the next time the worker pool starts (initialize()).
        m_threadCount = std::max<uint32_t>(1, config["threadCount"].get<uint32_t>());
    }
    if (config.contains("maxCacheSize")) {
        m_maxCacheSize = config["maxCacheSize"].get<size_t>();
    }
    if (config.contains("maxMemoryUsage")) {
        m_maxMemoryUsage = config["maxMemoryUsage"].get<size_t>();
    }
    if (config.contains("maxGenerationTime")) {
        m_maxGenerationTime = config["maxGenerationTime"].get<float>();
    }
    if (config.contains("maxLoadTime")) {
        m_maxLoadTime = config["maxLoadTime"].get<float>();
    }
    if (config.contains("validationLevel")) {
        m_validationLevel = std::clamp(config["validationLevel"].get<int>(), 0, 2);
    }
    if (config.contains("enableCaching")) {
        m_cachingEnabled = config["enableCaching"].get<bool>();
    }
    if (config.contains("enablePerformanceMonitoring")) {
        m_performanceMonitoringEnabled = config["enablePerformanceMonitoring"].get<bool>();
    }
}

nlohmann::json MeshAssetGenerator::getConfig() const {
    return {
        {"threadCount", m_threadCount},
        {"maxCacheSize", m_maxCacheSize},
        {"maxMemoryUsage", m_maxMemoryUsage},
        {"maxGenerationTime", m_maxGenerationTime},
        {"maxLoadTime", m_maxLoadTime},
        {"validationLevel", m_validationLevel},
        {"enableCaching", m_cachingEnabled},
        {"enablePerformanceMonitoring", m_performanceMonitoringEnabled}
    };
}

MeshAssetBundle MeshAssetGenerator::generateSync(const MeshAssetParams& params) {
    if (!m_initialized) {
        MeshAssetBundle bundle;
        bundle.isValid = false;
        bundle.errorMessage = "MeshAssetGenerator not initialized";
        return bundle;
    }

    // Check cache first
    if (m_cachingEnabled) {
        std::optional<MeshAssetBundle> cached;
        {
            std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
            auto it = m_assetCache.find(params.id);
            if (it != m_assetCache.end()) {
                ++m_assetAccessCount[params.id];
                cached = it->second;
            }
        }
        if (cached) {
            {
                std::lock_guard<std::mutex> lock(m_statsMutex);
                m_stats.cachedAssets++;
            }
            emitCacheHitEvent(params.id);
            return *cached;
        }
        emitCacheMissEvent(params.id);
    }

    // Validate parameters
    if (m_validationLevel > 0 && !validateParams(params)) {
        MeshAssetBundle bundle;
        bundle.assetId = params.id;
        bundle.assetType = params.type;
        bundle.isValid = false;
        bundle.errorMessage = "Invalid mesh asset parameters";
        updateStats(bundle, 0.0);
        emitAssetFailedEvent(params.id, bundle.errorMessage);
        return bundle;
    }

    // Generate asset
    auto startTime = std::chrono::high_resolution_clock::now();
    MeshAssetBundle bundle = generateAssetInternal(params);
    auto endTime = std::chrono::high_resolution_clock::now();

    double generationTime = std::chrono::duration<double>(endTime - startTime).count();
    bundle.generationTime = generationTime;

    // Post-generation validation of the result
    if (bundle.isValid && params.validateResult && m_validationLevel > 0) {
        auto problems = validateAsset(bundle);
        // Level 1 reports problems, level 2 rejects the asset.
        if (!problems.empty()) {
            std::string joined;
            for (const auto& p : problems) {
                if (!joined.empty()) joined += "; ";
                joined += p;
            }
            if (m_validationLevel >= 2) {
                bundle.isValid = false;
                bundle.errorMessage = "Asset validation failed: " + joined;
            } else {
                Log::warn("MeshAsset", "Asset '{}' validation warnings: {}", params.id, joined);
            }
        }
    }

    if (m_performanceMonitoringEnabled && generationTime > m_maxGenerationTime) {
        Log::warn("MeshAsset", "Asset '{}' took {:.3f}s (threshold {:.3f}s)", params.id, generationTime, m_maxGenerationTime);
    }

    // Update statistics
    updateStats(bundle, generationTime);

    // Cache result if requested
    if (bundle.isValid && params.cacheResult && m_cachingEnabled) {
        std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
        m_assetCache[params.id] = bundle;
        m_assetAccessCount[params.id] = 1;
        cleanupCache();
    }

    // Emit events
    if (bundle.isValid) {
        emitAssetGeneratedEvent(bundle);
    } else {
        emitAssetFailedEvent(params.id, bundle.errorMessage);
    }

    return bundle;
}

std::future<MeshAssetBundle> MeshAssetGenerator::generateAsync(const MeshAssetParams& params) {
    {
        std::lock_guard<std::mutex> lock(m_statsMutex);
        m_stats.totalAsyncJobs++;
    }
    return m_pool.enqueue([this, params]() {
        MeshAssetBundle bundle = generateSync(params);
        std::lock_guard<std::mutex> lock(m_statsMutex);
        if (bundle.isValid) {
            m_stats.completedJobs++;
        } else {
            m_stats.failedJobs++;
        }
        return bundle;
    });
}

std::vector<std::future<MeshAssetBundle>> MeshAssetGenerator::generateBatch(
    const std::vector<MeshAssetParams>& params) {
    std::vector<std::future<MeshAssetBundle>> futures;
    futures.reserve(params.size());

    for (const auto& param : params) {
        futures.push_back(generateAsync(param));
    }

    return futures;
}

bool MeshAssetGenerator::isAssetLoaded(const std::string& assetId) const {
    std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
    return m_assetCache.find(assetId) != m_assetCache.end();
}

MeshAssetBundle MeshAssetGenerator::getAsset(const std::string& assetId) const {
    // Exclusive lock: the access counter is updated as well.
    std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
    auto it = m_assetCache.find(assetId);
    if (it != m_assetCache.end()) {
        m_assetAccessCount[assetId]++;
        return it->second;
    }

    MeshAssetBundle bundle;
    bundle.isValid = false;
    bundle.errorMessage = "Asset not found: " + assetId;
    return bundle;
}

void MeshAssetGenerator::unloadAsset(const std::string& assetId) {
    std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
    m_assetCache.erase(assetId);
    m_assetAccessCount.erase(assetId);
}

void MeshAssetGenerator::unloadAllAssets() {
    std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
    m_assetCache.clear();
    m_assetAccessCount.clear();
}

void MeshAssetGenerator::enableCaching(bool enable) {
    m_cachingEnabled = enable;
}

void MeshAssetGenerator::clearCache() {
    std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
    m_assetCache.clear();
    m_assetAccessCount.clear();
}

void MeshAssetGenerator::setCacheSize(size_t maxSize) {
    std::unique_lock<std::shared_mutex> lock(m_cacheMutex);
    m_maxCacheSize = maxSize;
    cleanupCache();
}

size_t MeshAssetGenerator::getCacheSize() const {
    std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
    return m_assetCache.size();
}

size_t MeshAssetGenerator::getMaxCacheSize() const {
    return m_maxCacheSize;
}

double MeshAssetGenerator::getCacheHitRate() const {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    if (m_stats.cacheHits + m_stats.cacheMisses == 0) return 0.0;
    return static_cast<double>(m_stats.cacheHits) / static_cast<double>(m_stats.cacheHits + m_stats.cacheMisses);
}

void MeshAssetGenerator::enablePerformanceMonitoring(bool enable) {
    m_performanceMonitoringEnabled = enable;
}

void MeshAssetGenerator::setPerformanceThresholds(float maxGenerationTime, float maxLoadTime) {
    m_maxGenerationTime = maxGenerationTime;
    m_maxLoadTime = maxLoadTime;
}

MeshAssetStats MeshAssetGenerator::getStats() const {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    return m_stats;
}

void MeshAssetGenerator::resetStats() {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    m_stats.reset();
}

void MeshAssetGenerator::logPerformanceMetrics() {
    const auto stats = getStats();
    Log::info("MeshAsset",
              "assets total={} generated={} cached={} failed={} | async jobs={} done={} failed={} | "
              "avg generation {:.4f}s | cache {} entries, hit rate {:.1f}% | memory {} bytes",
              stats.totalAssets, stats.generatedAssets, stats.cachedAssets, stats.failedAssets,
              stats.totalAsyncJobs, stats.completedJobs, stats.failedJobs,
              stats.averageGenerationTime, getCacheSize(), getCacheHitRate() * 100.0,
              getTotalMemoryUsage());
}

bool MeshAssetGenerator::validateParams(const MeshAssetParams& params) const {
    if (params.id.empty()) return false;
    if (params.type.empty()) return false;
    if (params.maxMemoryUsage > m_maxMemoryUsage) return false;
    if (params.maxGenerationTime > m_maxGenerationTime) return false;
    if (m_validationLevel >= 2 && !MeshAssetUtils::validateMeshParams(params)) return false;

    return true;
}

std::vector<std::string> MeshAssetGenerator::validateAsset(const MeshAssetBundle& bundle) const {
    std::vector<std::string> errors;

    if (!bundle.isValid) {
        errors.push_back("Bundle is not valid: " + bundle.errorMessage);
        return errors;
    }

    if (!bundle.mesh) {
        errors.push_back("No mesh generated");
    } else if (!bundle.mesh->isValid()) {
        errors.push_back("Generated mesh is invalid");
    }

    if (bundle.memoryUsage > m_maxMemoryUsage) {
        errors.push_back("Memory usage exceeds limit");
    }

    if (bundle.generationTime > m_maxGenerationTime) {
        errors.push_back("Generation time exceeds limit");
    }

    if (!bundle.uvPacking.uvs.empty() && !mt::UVGen::validateUVs(bundle.uvPacking)) {
        errors.push_back("UV atlas contains invalid coordinates");
    }

    return errors;
}

void MeshAssetGenerator::setValidationLevel(int level) {
    m_validationLevel = std::clamp(level, 0, 2);
}

std::vector<std::string> MeshAssetGenerator::getAvailableAssetTypes() const {
    return {
        "primitive", "terrain", "procedural", "implicit", "sculpted", "custom"
    };
}

std::vector<std::string> MeshAssetGenerator::getLoadedAssetIds() const {
    std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
    std::vector<std::string> ids;
    ids.reserve(m_assetCache.size());
    for (const auto& pair : m_assetCache) {
        ids.push_back(pair.first);
    }
    return ids;
}

size_t MeshAssetGenerator::getTotalMemoryUsage() const {
    std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
    size_t total = 0;
    for (const auto& pair : m_assetCache) {
        total += pair.second.memoryUsage;
    }
    return total;
}

void MeshAssetGenerator::onAssetGenerated(std::function<void(const MeshAssetBundle&)> callback) {
    std::lock_guard<std::mutex> lock(m_callbackMutex);
    m_assetGeneratedCallbacks.push_back(std::move(callback));
}

void MeshAssetGenerator::onAssetFailed(std::function<void(const std::string&, const std::string&)> callback) {
    std::lock_guard<std::mutex> lock(m_callbackMutex);
    m_assetFailedCallbacks.push_back(std::move(callback));
}

void MeshAssetGenerator::onCacheHit(std::function<void(const std::string&)> callback) {
    std::lock_guard<std::mutex> lock(m_callbackMutex);
    m_cacheHitCallbacks.push_back(std::move(callback));
}

void MeshAssetGenerator::onCacheMiss(std::function<void(const std::string&)> callback) {
    std::lock_guard<std::mutex> lock(m_callbackMutex);
    m_cacheMissCallbacks.push_back(std::move(callback));
}

// Private methods

MeshAssetBundle MeshAssetGenerator::generateAssetInternal(const MeshAssetParams& params) {
    MeshAssetBundle bundle;
    bundle.assetId = params.id;
    bundle.assetType = params.type;

    try {
        bundle.mesh = buildBaseMesh(params);

        if (!bundle.mesh || !bundle.mesh->isValid()) {
            bundle.isValid = false;
            bundle.errorMessage = "Failed to generate mesh";
            return bundle;
        }

        if (bundle.mesh->name.empty()) {
            bundle.mesh->name = params.id;
        }

        // Optimize mesh if requested
        if (params.optimizeMesh) {
            bundle.mesh->optimize();
        }

        // Generate UVs if requested. The packing keeps one UV per triangle corner
        // (triangles numbered across submeshes), see mt::AtlasPacking.
        if (params.meshParams.generateUVs &&
            params.uvParams.atlasSize.x > 0 && params.uvParams.atlasSize.y > 0) {
            bundle.uvPacking = mt::UVGen::generateUVs(*bundle.mesh, params.uvParams);
        }

        // Generate material if requested
        if (!params.materialParams.id.empty()) {
            bundle.materialHandle = mt::MaterialGen::createMaterial(params.materialParams);
            if (bundle.materialHandle.valid()) {
                const auto material = bundle.materialHandle.get();
                for (const auto& map : {material->albedoMap, material->normalMap, material->metallicMap,
                                        material->roughnessMap, material->aoMap, material->emissiveMap}) {
                    if (map && map->valid()) {
                        bundle.textures.push_back(map);
                    }
                }
                bundle.mesh->materials.push_back(std::make_shared<mt::MaterialHandle>(bundle.materialHandle));
            }
        }

        // Generate LODs if requested
        if (!params.lodParams.baseMeshId.empty()) {
            for (float ratio : params.lodParams.targetRatios) {
                auto lodMesh = bundle.mesh->createLOD(ratio, params.lodParams.preserveBorders);
                if (!lodMesh) continue;
                bundle.lods.push_back(lodMesh);
                bundle.lodHandles.emplace_back(lodMesh);
            }
            bundle.mesh->lods = bundle.lods;
            bundle.mesh->lodScreenSizes = params.lodParams.screenSizes;
        }

        bundle.meshHandle = mt::MeshHandle(bundle.mesh);

        // Calculate memory usage (base mesh plus LODs)
        bundle.memoryUsage = bundle.mesh->getMemoryUsage();

        bundle.isValid = true;

    } catch (const std::exception& e) {
        bundle.isValid = false;
        bundle.errorMessage = std::string("Exception during generation: ") + e.what();
    }

    return bundle;
}

void MeshAssetGenerator::updateStats(const MeshAssetBundle& bundle, double generationTime) {
    std::lock_guard<std::mutex> lock(m_statsMutex);

    m_stats.totalAssets++;
    if (bundle.isValid) {
        m_stats.generatedAssets++;
        m_stats.averageGenerationTime =
            (m_stats.averageGenerationTime * static_cast<double>(m_stats.generatedAssets - 1) + generationTime) /
            static_cast<double>(m_stats.generatedAssets);
        m_stats.totalMemoryUsage += static_cast<double>(bundle.memoryUsage);
    } else {
        m_stats.failedAssets++;
    }
}

void MeshAssetGenerator::emitAssetGeneratedEvent(const MeshAssetBundle& bundle) {
    std::vector<std::function<void(const MeshAssetBundle&)>> callbacks;
    {
        std::lock_guard<std::mutex> lock(m_callbackMutex);
        callbacks = m_assetGeneratedCallbacks;
    }
    for (const auto& callback : callbacks) {
        try {
            callback(bundle);
        } catch (const std::exception& e) {
            Log::warn("MeshAsset", "onAssetGenerated callback threw: {}", e.what());
        }
    }
}

void MeshAssetGenerator::emitAssetFailedEvent(const std::string& assetId, const std::string& error) {
    std::vector<std::function<void(const std::string&, const std::string&)>> callbacks;
    {
        std::lock_guard<std::mutex> lock(m_callbackMutex);
        callbacks = m_assetFailedCallbacks;
    }
    for (const auto& callback : callbacks) {
        try {
            callback(assetId, error);
        } catch (const std::exception& e) {
            Log::warn("MeshAsset", "onAssetFailed callback threw: {}", e.what());
        }
    }
}

void MeshAssetGenerator::emitCacheHitEvent(const std::string& assetId) {
    {
        std::lock_guard<std::mutex> lock(m_statsMutex);
        m_stats.cacheHits++;
    }
    std::vector<std::function<void(const std::string&)>> callbacks;
    {
        std::lock_guard<std::mutex> lock(m_callbackMutex);
        callbacks = m_cacheHitCallbacks;
    }
    for (const auto& callback : callbacks) {
        try {
            callback(assetId);
        } catch (const std::exception& e) {
            Log::warn("MeshAsset", "onCacheHit callback threw: {}", e.what());
        }
    }
}

void MeshAssetGenerator::emitCacheMissEvent(const std::string& assetId) {
    {
        std::lock_guard<std::mutex> lock(m_statsMutex);
        m_stats.cacheMisses++;
    }
    std::vector<std::function<void(const std::string&)>> callbacks;
    {
        std::lock_guard<std::mutex> lock(m_callbackMutex);
        callbacks = m_cacheMissCallbacks;
    }
    for (const auto& callback : callbacks) {
        try {
            callback(assetId);
        } catch (const std::exception& e) {
            Log::warn("MeshAsset", "onCacheMiss callback threw: {}", e.what());
        }
    }
}

void MeshAssetGenerator::cleanupCache() {
    if (m_assetCache.size() <= m_maxCacheSize) return;

    // Evict the least used assets
    std::vector<std::pair<std::string, size_t>> accessCounts;
    accessCounts.reserve(m_assetAccessCount.size());
    for (const auto& pair : m_assetAccessCount) {
        accessCounts.push_back(pair);
    }

    std::sort(accessCounts.begin(), accessCounts.end(),
        [](const auto& a, const auto& b) { return a.second < b.second; });

    size_t toRemove = m_assetCache.size() - m_maxCacheSize;
    for (size_t i = 0; i < toRemove && i < accessCounts.size(); ++i) {
        m_assetCache.erase(accessCounts[i].first);
        m_assetAccessCount.erase(accessCounts[i].first);
    }
}

std::string MeshAssetGenerator::generateUniqueAssetId() const {
    return MeshAssetUtils::generateAssetId("mesh");
}

} // namespace MagiTech::GeneratorAgent
