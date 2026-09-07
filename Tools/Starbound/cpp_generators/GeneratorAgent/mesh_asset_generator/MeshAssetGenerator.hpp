#pragma once

#include "../../../core/mesh/Mesh.hpp"
#include "../../../core/mesh/MeshGenerator.hpp"
#include "../../../core/mesh/UVGen.hpp"
#include "../../../core/mesh/MaterialGen.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <sol/sol.hpp>
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <future>

namespace MagiTech::GeneratorAgent {

// Forward declarations
class MeshAssetBundle;
class MeshAssetPresets;

/**
 * @brief Mesh asset generation parameters
 */
struct MeshAssetParams {
    std::string id;                    // Unique asset ID
    std::string type;                  // Asset type (primitive, terrain, procedural, etc.)
    MeshParams meshParams;             // Mesh generation parameters
    LODParams lodParams;               // LOD generation parameters (optional)
    MaterialParams materialParams;      // Material generation parameters (optional)
    MorphParams morphParams;           // Morph target parameters (optional)
    UVGenParams uvParams;              // UV generation parameters (optional)
    
    // Generation options
    bool generateAsync;                // Generate asynchronously
    bool cacheResult;                  // Cache the generated asset
    bool validateResult;               // Validate the generated asset
    bool optimizeMesh;                 // Optimize the mesh after generation
    
    // Performance settings
    float maxGenerationTime;           // Maximum generation time in seconds
    size_t maxMemoryUsage;            // Maximum memory usage in bytes
    
    MeshAssetParams() : generateAsync(false), cacheResult(true), validateResult(true),
                       optimizeMesh(true), maxGenerationTime(5.0f), maxMemoryUsage(100 * 1024 * 1024) {}
};

/**
 * @brief Mesh asset bundle containing generated assets
 */
struct MeshAssetBundle {
    bool isValid;                      // Whether the bundle is valid
    std::string errorMessage;          // Error message if invalid
    
    // Generated assets
    std::shared_ptr<Mesh> mesh;        // Generated mesh
    MeshHandle meshHandle;             // Mesh handle for GPU management
    MaterialHandle materialHandle;     // Material handle (if generated)
    
    // Asset metadata
    std::string assetId;               // Asset ID
    std::string assetType;             // Asset type
    size_t memoryUsage;                // Memory usage in bytes
    double generationTime;             // Generation time in seconds
    
    // LOD data
    std::vector<std::shared_ptr<Mesh>> lods; // LOD meshes
    std::vector<MeshHandle> lodHandles;      // LOD handles
    
    // UV and material data
    AtlasPacking uvPacking;            // UV atlas packing
    std::vector<std::shared_ptr<TextureHandle>> textures; // Generated textures
    
    MeshAssetBundle() : isValid(false), memoryUsage(0), generationTime(0) {}
};

/**
 * @brief Mesh asset generation statistics
 */
struct MeshAssetStats {
    uint64_t totalAssets = 0;
    uint64_t generatedAssets = 0;
    uint64_t cachedAssets = 0;
    uint64_t failedAssets = 0;
    uint64_t totalAsyncJobs = 0;
    uint64_t completedJobs = 0;
    uint64_t failedJobs = 0;
    
    double averageGenerationTime = 0.0;
    double averageLoadTime = 0.0;
    double totalMemoryUsage = 0.0;
    
    void reset() {
        totalAssets = 0;
        generatedAssets = 0;
        cachedAssets = 0;
        failedAssets = 0;
        totalAsyncJobs = 0;
        completedJobs = 0;
        failedJobs = 0;
        averageGenerationTime = 0.0;
        averageLoadTime = 0.0;
        totalMemoryUsage = 0.0;
    }
};

/**
 * @brief Mesh asset generator class
 */
class MeshAssetGenerator {
public:
    MeshAssetGenerator();
    ~MeshAssetGenerator();
    
    // Initialization and configuration
    void initialize(uint32_t threadCount = 4);
    void shutdown();
    void setConfig(const nlohmann::json& config);
    nlohmann::json getConfig() const;
    
    // Asset generation
    MeshAssetBundle generateSync(const MeshAssetParams& params);
    std::future<MeshAssetBundle> generateAsync(const MeshAssetParams& params);
    std::vector<std::future<MeshAssetBundle>> generateBatch(const std::vector<MeshAssetParams>& params);
    
    // Asset management
    bool isAssetLoaded(const std::string& assetId) const;
    MeshAssetBundle getAsset(const std::string& assetId) const;
    void unloadAsset(const std::string& assetId);
    void unloadAllAssets();
    
    // Cache management
    void enableCaching(bool enable = true);
    void clearCache();
    void setCacheSize(size_t maxSize);
    size_t getCacheSize() const;
    size_t getMaxCacheSize() const;
    double getCacheHitRate() const;
    
    // Performance monitoring
    void enablePerformanceMonitoring(bool enable = true);
    void setPerformanceThresholds(float maxGenerationTime, float maxLoadTime);
    MeshAssetStats getStats() const;
    void resetStats();
    void logPerformanceMetrics();
    
    // Validation and error handling
    bool validateParams(const MeshAssetParams& params) const;
    std::vector<std::string> validateAsset(const MeshAssetBundle& bundle) const;
    void setValidationLevel(int level); // 0=none, 1=basic, 2=strict
    
    // Utility functions
    std::vector<std::string> getAvailableAssetTypes() const;
    std::vector<std::string> getLoadedAssetIds() const;
    size_t getTotalMemoryUsage() const;
    
    // Event callbacks
    void onAssetGenerated(std::function<void(const MeshAssetBundle&)> callback);
    void onAssetFailed(std::function<void(const std::string&, const std::string&)> callback);
    void onCacheHit(std::function<void(const std::string&)> callback);
    void onCacheMiss(std::function<void(const std::string&)> callback);

private:
    // Internal state
    bool m_initialized;
    bool m_cachingEnabled;
    bool m_performanceMonitoringEnabled;
    int m_validationLevel;
    
    // Configuration
    float m_maxGenerationTime;
    float m_maxLoadTime;
    size_t m_maxCacheSize;
    size_t m_maxMemoryUsage;
    
    // Statistics
    mutable MeshAssetStats m_stats;
    mutable std::mutex m_statsMutex;
    
    // Cache
    mutable std::shared_mutex m_cacheMutex;
    std::unordered_map<std::string, MeshAssetBundle> m_assetCache;
    std::unordered_map<std::string, size_t> m_assetAccessCount;
    
    // Async job management
    std::vector<std::future<MeshAssetBundle>> m_asyncJobs;
    std::mutex m_jobsMutex;
    
    // Event callbacks
    std::vector<std::function<void(const MeshAssetBundle&)>> m_assetGeneratedCallbacks;
    std::vector<std::function<void(const std::string&, const std::string&)>> m_assetFailedCallbacks;
    std::vector<std::function<void(const std::string&)>> m_cacheHitCallbacks;
    std::vector<std::function<void(const std::string&)>> m_cacheMissCallbacks;
    
    // Internal methods
    MeshAssetBundle generateAssetInternal(const MeshAssetParams& params);
    void cleanupAsyncJobs();
    void updateStats(const MeshAssetBundle& bundle, double generationTime);
    void emitAssetGeneratedEvent(const MeshAssetBundle& bundle);
    void emitAssetFailedEvent(const std::string& assetId, const std::string& error);
    void emitCacheHitEvent(const std::string& assetId);
    void emitCacheMissEvent(const std::string& assetId);
    void cleanupCache();
    std::string generateUniqueAssetId() const;
};

/**
 * @brief Mesh asset presets for common asset types
 */
class MeshAssetPresets {
public:
    // Primitive presets
    static MeshAssetParams cube(const glm::vec3& dimensions = glm::vec3(1.0f));
    static MeshAssetParams sphere(float radius = 0.5f, uint32_t subdivisions = 16);
    static MeshAssetParams cylinder(float radius = 0.5f, float height = 1.0f, uint32_t subdivisions = 16);
    static MeshAssetParams torus(float majorRadius = 1.0f, float minorRadius = 0.3f);
    static MeshAssetParams plane(const glm::vec2& size = glm::vec2(1.0f));
    
    // Terrain presets
    static MeshAssetParams terrain(const glm::vec2& size = glm::vec2(100.0f), uint32_t resolution = 256);
    static MeshAssetParams mountain(const glm::vec2& size = glm::vec2(200.0f), uint32_t resolution = 512);
    static MeshAssetParams valley(const glm::vec2& size = glm::vec2(150.0f), uint32_t resolution = 384);
    
    // Procedural presets
    static MeshAssetParams proceduralSphere(float radius = 0.5f, uint32_t subdivisions = 16);
    static MeshAssetParams proceduralCube(const glm::vec3& dimensions = glm::vec3(1.0f));
    static MeshAssetParams proceduralCylinder(float radius = 0.5f, float height = 1.0f);
    
    // Material presets
    static MaterialParams pbrMetal();
    static MaterialParams pbrPlastic();
    static MaterialParams pbrWood();
    static MaterialParams pbrStone();
    static MaterialParams emissive();
    static MaterialParams transparent();
    
    // LOD presets
    static LODParams standardLOD();
    static LODParams aggressiveLOD();
    static LODParams conservativeLOD();
    
    // UV presets
    static UVGenParams standardUV();
    static UVGenParams optimizedUV();
    static UVGenParams seamlessUV();
};

/**
 * @brief Mesh asset utilities for parameter creation and validation
 */
class MeshAssetUtils {
public:
    // Parameter creation
    static MeshAssetParams createMeshParams(const nlohmann::json& data);
    static MeshAssetParams createMeshParams(const std::string& id, const std::string& type);
    
    // Validation
    static bool validateMeshParams(const MeshAssetParams& params);
    static bool validateLODParams(const LODParams& params);
    static bool validateMaterialParams(const MaterialParams& params);
    static bool validateUVParams(const UVGenParams& params);
    
    // Conversion utilities
    static nlohmann::json paramsToJson(const MeshAssetParams& params);
    static MeshAssetParams jsonToParams(const nlohmann::json& data);
    
    // Utility functions
    static std::string generateAssetId(const std::string& prefix = "mesh");
    static size_t estimateMemoryUsage(const MeshAssetParams& params);
    static double estimateGenerationTime(const MeshAssetParams& params);
    
    // Asset comparison
    static bool compareAssets(const MeshAssetBundle& a, const MeshAssetBundle& b);
    static float calculateSimilarity(const MeshAssetBundle& a, const MeshAssetBundle& b);
};

} // namespace MagiTech::GeneratorAgent 
