#include "MeshAssetGenerator.hpp"
#include <chrono>
#include <algorithm>
#include <random>
#include <sstream>

namespace MagiTech::GeneratorAgent {

MeshAssetGenerator::MeshAssetGenerator()
    : m_initialized(false)
    , m_cachingEnabled(true)
    , m_performanceMonitoringEnabled(false)
    , m_validationLevel(1)
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
    
    // Initialize mesh systems
    // Note: In a real implementation, you would initialize OpenGL context here
    
    m_initialized = true;
    m_stats.reset();
    
    // Set up default configuration
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
}

void MeshAssetGenerator::shutdown() {
    if (!m_initialized) return;
    
    // Clean up async jobs
    cleanupAsyncJobs();
    
    // Clear cache
    clearCache();
    
    // Reset stats
    resetStats();
    
    m_initialized = false;
}

void MeshAssetGenerator::setConfig(const nlohmann::json& config) {
    if (config.contains("threadCount")) {
        // Thread count would be used for thread pool initialization
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
        m_validationLevel = config["validationLevel"].get<int>();
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
        std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
        auto it = m_assetCache.find(params.id);
        if (it != m_assetCache.end()) {
            emitCacheHitEvent(params.id);
            return it->second;
        }
    }
    
    emitCacheMissEvent(params.id);
    
    // Validate parameters
    if (m_validationLevel > 0 && !validateParams(params)) {
        MeshAssetBundle bundle;
        bundle.isValid = false;
        bundle.errorMessage = "Invalid mesh asset parameters";
        return bundle;
    }
    
    // Generate asset
    auto startTime = std::chrono::high_resolution_clock::now();
    MeshAssetBundle bundle = generateAssetInternal(params);
    auto endTime = std::chrono::high_resolution_clock::now();
    
    double generationTime = std::chrono::duration<double>(endTime - startTime).count();
    bundle.generationTime = generationTime;
    
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
    return std::async(std::launch::async, [this, params]() {
        return generateSync(params);
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
    std::shared_lock<std::shared_mutex> lock(m_cacheMutex);
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
    return static_cast<double>(m_stats.cacheHits) / (m_stats.cacheHits + m_stats.cacheMisses);
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
    auto stats = getStats();
    // In a real implementation, you would log to a file or console
    // For now, we'll just update the stats
}

bool MeshAssetGenerator::validateParams(const MeshAssetParams& params) const {
    if (params.id.empty()) return false;
    if (params.type.empty()) return false;
    if (params.maxMemoryUsage > m_maxMemoryUsage) return false;
    if (params.maxGenerationTime > m_maxGenerationTime) return false;
    
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
    }
    
    if (bundle.memoryUsage > m_maxMemoryUsage) {
        errors.push_back("Memory usage exceeds limit");
    }
    
    if (bundle.generationTime > m_maxGenerationTime) {
        errors.push_back("Generation time exceeds limit");
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
    m_assetGeneratedCallbacks.push_back(callback);
}

void MeshAssetGenerator::onAssetFailed(std::function<void(const std::string&, const std::string&)> callback) {
    m_assetFailedCallbacks.push_back(callback);
}

void MeshAssetGenerator::onCacheHit(std::function<void(const std::string&)> callback) {
    m_cacheHitCallbacks.push_back(callback);
}

void MeshAssetGenerator::onCacheMiss(std::function<void(const std::string&)> callback) {
    m_cacheMissCallbacks.push_back(callback);
}

// Private methods

MeshAssetBundle MeshAssetGenerator::generateAssetInternal(const MeshAssetParams& params) {
    MeshAssetBundle bundle;
    bundle.assetId = params.id;
    bundle.assetType = params.type;
    
    try {
        // Generate mesh based on type
        if (params.type == "primitive") {
            bundle.mesh = MeshGenerator::generateFromParams(params.meshParams);
        } else if (params.type == "terrain") {
            TerrainParams terrainParams;
            terrainParams.size = glm::vec2(params.meshParams.dimensions.x, params.meshParams.dimensions.z);
            terrainParams.resolution = glm::vec2(params.meshParams.subdivisions, params.meshParams.subdivisions);
            terrainParams.noiseScale = params.meshParams.noiseFrequency;
            terrainParams.seed = params.meshParams.seed;
            bundle.mesh = MeshGenerator::generateTerrain(terrainParams);
        } else if (params.type == "procedural") {
            bundle.mesh = MeshGenerator::generateFromParams(params.meshParams);
        } else {
            // Default to primitive
            bundle.mesh = MeshGenerator::generateFromParams(params.meshParams);
        }
        
        if (!bundle.mesh || !bundle.mesh->isValid()) {
            bundle.isValid = false;
            bundle.errorMessage = "Failed to generate mesh";
            return bundle;
        }
        
        // Optimize mesh if requested
        if (params.optimizeMesh) {
            bundle.mesh->optimize();
        }
        
        // Generate UVs if requested
        if (params.uvParams.atlasSize.x > 0 && params.uvParams.atlasSize.y > 0) {
            bundle.uvPacking = UVGen::generateUVs(*bundle.mesh, params.uvParams);
        }
        
        // Generate material if requested
        if (!params.materialParams.id.empty()) {
            bundle.materialHandle = MaterialGen::createMaterial(params.materialParams);
        }
        
        // Generate LODs if requested
        if (!params.lodParams.baseMeshId.empty()) {
            for (size_t i = 0; i < params.lodParams.targetRatios.size(); ++i) {
                auto lodMesh = bundle.mesh->createLOD(params.lodParams.targetRatios[i], params.lodParams.preserveBorders);
                bundle.lods.push_back(lodMesh);
            }
        }
        
        // Calculate memory usage
        bundle.memoryUsage = bundle.mesh->getMemoryUsage();
        
        bundle.isValid = true;
        
    } catch (const std::exception& e) {
        bundle.isValid = false;
        bundle.errorMessage = std::string("Exception during generation: ") + e.what();
    }
    
    return bundle;
}

void MeshAssetGenerator::cleanupAsyncJobs() {
    std::lock_guard<std::mutex> lock(m_jobsMutex);
    m_asyncJobs.erase(
        std::remove_if(m_asyncJobs.begin(), m_asyncJobs.end(),
            [](const std::future<MeshAssetBundle>& future) {
                return future.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
            }),
        m_asyncJobs.end()
    );
}

void MeshAssetGenerator::updateStats(const MeshAssetBundle& bundle, double generationTime) {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    
    m_stats.totalAssets++;
    if (bundle.isValid) {
        m_stats.generatedAssets++;
        m_stats.averageGenerationTime = 
            (m_stats.averageGenerationTime * (m_stats.generatedAssets - 1) + generationTime) / m_stats.generatedAssets;
        m_stats.totalMemoryUsage += bundle.memoryUsage;
    } else {
        m_stats.failedAssets++;
    }
}

void MeshAssetGenerator::emitAssetGeneratedEvent(const MeshAssetBundle& bundle) {
    for (const auto& callback : m_assetGeneratedCallbacks) {
        try {
            callback(bundle);
        } catch (...) {
            // Ignore callback exceptions
        }
    }
}

void MeshAssetGenerator::emitAssetFailedEvent(const std::string& assetId, const std::string& error) {
    for (const auto& callback : m_assetFailedCallbacks) {
        try {
            callback(assetId, error);
        } catch (...) {
            // Ignore callback exceptions
        }
    }
}

void MeshAssetGenerator::emitCacheHitEvent(const std::string& assetId) {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    m_stats.cacheHits++;
    
    for (const auto& callback : m_cacheHitCallbacks) {
        try {
            callback(assetId);
        } catch (...) {
            // Ignore callback exceptions
        }
    }
}

void MeshAssetGenerator::emitCacheMissEvent(const std::string& assetId) {
    std::lock_guard<std::mutex> lock(m_statsMutex);
    m_stats.cacheMisses++;
    
    for (const auto& callback : m_cacheMissCallbacks) {
        try {
            callback(assetId);
        } catch (...) {
            // Ignore callback exceptions
        }
    }
}

void MeshAssetGenerator::cleanupCache() {
    if (m_assetCache.size() <= m_maxCacheSize) return;
    
    // Remove least recently used assets
    std::vector<std::pair<std::string, size_t>> accessCounts;
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
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(1000, 9999);
    
    std::stringstream ss;
    ss << "mesh_" << dis(gen);
    return ss.str();
}

} // namespace MagiTech::GeneratorAgent 
