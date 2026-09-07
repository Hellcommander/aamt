#include "MeshAssetGenerator.hpp"
#include <sol/sol.hpp>
#include <memory>

namespace MagiTech::GeneratorAgent {

void registerMeshAssetBindings(sol::state& lua) {
    // Create mesh asset module
    sol::table meshAsset = lua.create_named_table("MeshAsset");
    
    // MeshAssetParams
    auto meshAssetParams = lua.new_usertype<MeshAssetParams>("MeshAssetParams",
        sol::constructors<MeshAssetParams()>(),
        "id", &MeshAssetParams::id,
        "type", &MeshAssetParams::type,
        "generateAsync", &MeshAssetParams::generateAsync,
        "cacheResult", &MeshAssetParams::cacheResult,
        "validateResult", &MeshAssetParams::validateResult,
        "optimizeMesh", &MeshAssetParams::optimizeMesh,
        "maxGenerationTime", &MeshAssetParams::maxGenerationTime,
        "maxMemoryUsage", &MeshAssetParams::maxMemoryUsage
    );
    
    // MeshAssetBundle
    auto meshAssetBundle = lua.new_usertype<MeshAssetBundle>("MeshAssetBundle",
        sol::constructors<MeshAssetBundle()>(),
        "isValid", &MeshAssetBundle::isValid,
        "errorMessage", &MeshAssetBundle::errorMessage,
        "assetId", &MeshAssetBundle::assetId,
        "assetType", &MeshAssetBundle::assetType,
        "memoryUsage", &MeshAssetBundle::memoryUsage,
        "generationTime", &MeshAssetBundle::generationTime
    );
    
    // MeshAssetStats
    auto meshAssetStats = lua.new_usertype<MeshAssetStats>("MeshAssetStats",
        sol::constructors<MeshAssetStats()>(),
        "totalAssets", &MeshAssetStats::totalAssets,
        "generatedAssets", &MeshAssetStats::generatedAssets,
        "cachedAssets", &MeshAssetStats::cachedAssets,
        "failedAssets", &MeshAssetStats::failedAssets,
        "totalAsyncJobs", &MeshAssetStats::totalAsyncJobs,
        "completedJobs", &MeshAssetStats::completedJobs,
        "failedJobs", &MeshAssetStats::failedJobs,
        "averageGenerationTime", &MeshAssetStats::averageGenerationTime,
        "averageLoadTime", &MeshAssetStats::averageLoadTime,
        "totalMemoryUsage", &MeshAssetStats::totalMemoryUsage,
        "reset", &MeshAssetStats::reset
    );
    
    // MeshAssetGenerator singleton
    static std::unique_ptr<MeshAssetGenerator> g_meshAssetGenerator = std::make_unique<MeshAssetGenerator>();
    
    // Initialize function
    meshAsset["initialize"] = [](uint32_t threadCount) {
        g_meshAssetGenerator->initialize(threadCount);
    };
    
    // Shutdown function
    meshAsset["shutdown"] = []() {
        g_meshAssetGenerator->shutdown();
    };
    
    // Configuration functions
    meshAsset["setConfig"] = [](const nlohmann::json& config) {
        g_meshAssetGenerator->setConfig(config);
    };
    
    meshAsset["getConfig"] = []() -> nlohmann::json {
        return g_meshAssetGenerator->getConfig();
    };
    
    // Asset generation functions
    meshAsset["generateSync"] = [](const MeshAssetParams& params) -> MeshAssetBundle {
        return g_meshAssetGenerator->generateSync(params);
    };
    
    meshAsset["generateAsync"] = [](const MeshAssetParams& params) -> std::future<MeshAssetBundle> {
        return g_meshAssetGenerator->generateAsync(params);
    };
    
    meshAsset["generateBatch"] = [](const std::vector<MeshAssetParams>& params) -> std::vector<std::future<MeshAssetBundle>> {
        return g_meshAssetGenerator->generateBatch(params);
    };
    
    // Asset management functions
    meshAsset["isAssetLoaded"] = [](const std::string& assetId) -> bool {
        return g_meshAssetGenerator->isAssetLoaded(assetId);
    };
    
    meshAsset["getAsset"] = [](const std::string& assetId) -> MeshAssetBundle {
        return g_meshAssetGenerator->getAsset(assetId);
    };
    
    meshAsset["unloadAsset"] = [](const std::string& assetId) {
        g_meshAssetGenerator->unloadAsset(assetId);
    };
    
    meshAsset["unloadAllAssets"] = []() {
        g_meshAssetGenerator->unloadAllAssets();
    };
    
    // Cache management functions
    meshAsset["enableCaching"] = [](bool enable) {
        g_meshAssetGenerator->enableCaching(enable);
    };
    
    meshAsset["clearCache"] = []() {
        g_meshAssetGenerator->clearCache();
    };
    
    meshAsset["setCacheSize"] = [](size_t maxSize) {
        g_meshAssetGenerator->setCacheSize(maxSize);
    };
    
    meshAsset["getCacheSize"] = []() -> size_t {
        return g_meshAssetGenerator->getCacheSize();
    };
    
    meshAsset["getMaxCacheSize"] = []() -> size_t {
        return g_meshAssetGenerator->getMaxCacheSize();
    };
    
    meshAsset["getCacheHitRate"] = []() -> double {
        return g_meshAssetGenerator->getCacheHitRate();
    };
    
    // Performance monitoring functions
    meshAsset["enablePerformanceMonitoring"] = [](bool enable) {
        g_meshAssetGenerator->enablePerformanceMonitoring(enable);
    };
    
    meshAsset["setPerformanceThresholds"] = [](float maxGenerationTime, float maxLoadTime) {
        g_meshAssetGenerator->setPerformanceThresholds(maxGenerationTime, maxLoadTime);
    };
    
    meshAsset["getStats"] = []() -> MeshAssetStats {
        return g_meshAssetGenerator->getStats();
    };
    
    meshAsset["resetStats"] = []() {
        g_meshAssetGenerator->resetStats();
    };
    
    meshAsset["logPerformanceMetrics"] = []() {
        g_meshAssetGenerator->logPerformanceMetrics();
    };
    
    // Validation functions
    meshAsset["validateParams"] = [](const MeshAssetParams& params) -> bool {
        return g_meshAssetGenerator->validateParams(params);
    };
    
    meshAsset["validateAsset"] = [](const MeshAssetBundle& bundle) -> std::vector<std::string> {
        return g_meshAssetGenerator->validateAsset(bundle);
    };
    
    meshAsset["setValidationLevel"] = [](int level) {
        g_meshAssetGenerator->setValidationLevel(level);
    };
    
    // Utility functions
    meshAsset["getAvailableAssetTypes"] = []() -> std::vector<std::string> {
        return g_meshAssetGenerator->getAvailableAssetTypes();
    };
    
    meshAsset["getLoadedAssetIds"] = []() -> std::vector<std::string> {
        return g_meshAssetGenerator->getLoadedAssetIds();
    };
    
    meshAsset["getTotalMemoryUsage"] = []() -> size_t {
        return g_meshAssetGenerator->getTotalMemoryUsage();
    };
    
    // Event callback functions
    meshAsset["onAssetGenerated"] = [](std::function<void(const MeshAssetBundle&)> callback) {
        g_meshAssetGenerator->onAssetGenerated(callback);
    };
    
    meshAsset["onAssetFailed"] = [](std::function<void(const std::string&, const std::string&)> callback) {
        g_meshAssetGenerator->onAssetFailed(callback);
    };
    
    meshAsset["onCacheHit"] = [](std::function<void(const std::string&)> callback) {
        g_meshAssetGenerator->onCacheHit(callback);
    };
    
    meshAsset["onCacheMiss"] = [](std::function<void(const std::string&)> callback) {
        g_meshAssetGenerator->onCacheMiss(callback);
    };
    
    // Create MeshAssetUtils module
    sol::table meshAssetUtils = lua.create_named_table("MeshAssetUtils");
    
    // Parameter creation functions
    meshAssetUtils["createMeshParams"] = sol::overload(
        [](const nlohmann::json& data) -> MeshAssetParams {
            return MeshAssetUtils::createMeshParams(data);
        },
        [](const std::string& id, const std::string& type) -> MeshAssetParams {
            return MeshAssetUtils::createMeshParams(id, type);
        }
    );
    
    // Validation functions
    meshAssetUtils["validateMeshParams"] = [](const MeshAssetParams& params) -> bool {
        return MeshAssetUtils::validateMeshParams(params);
    };
    
    meshAssetUtils["validateLODParams"] = [](const LODParams& params) -> bool {
        return MeshAssetUtils::validateLODParams(params);
    };
    
    meshAssetUtils["validateMaterialParams"] = [](const MaterialParams& params) -> bool {
        return MeshAssetUtils::validateMaterialParams(params);
    };
    
    meshAssetUtils["validateUVParams"] = [](const UVGenParams& params) -> bool {
        return MeshAssetUtils::validateUVParams(params);
    };
    
    // Conversion functions
    meshAssetUtils["paramsToJson"] = [](const MeshAssetParams& params) -> nlohmann::json {
        return MeshAssetUtils::paramsToJson(params);
    };
    
    meshAssetUtils["jsonToParams"] = [](const nlohmann::json& data) -> MeshAssetParams {
        return MeshAssetUtils::jsonToParams(data);
    };
    
    // Utility functions
    meshAssetUtils["generateAssetId"] = [](const std::string& prefix) -> std::string {
        return MeshAssetUtils::generateAssetId(prefix);
    };
    
    meshAssetUtils["estimateMemoryUsage"] = [](const MeshAssetParams& params) -> size_t {
        return MeshAssetUtils::estimateMemoryUsage(params);
    };
    
    meshAssetUtils["estimateGenerationTime"] = [](const MeshAssetParams& params) -> double {
        return MeshAssetUtils::estimateGenerationTime(params);
    };
    
    // Asset comparison functions
    meshAssetUtils["compareAssets"] = [](const MeshAssetBundle& a, const MeshAssetBundle& b) -> bool {
        return MeshAssetUtils::compareAssets(a, b);
    };
    
    meshAssetUtils["calculateSimilarity"] = [](const MeshAssetBundle& a, const MeshAssetBundle& b) -> float {
        return MeshAssetUtils::calculateSimilarity(a, b);
    };
    
    // Create MeshAssetPresets module
    sol::table meshAssetPresets = lua.create_named_table("MeshAssetPresets");
    
    // Primitive presets
    meshAssetPresets["cube"] = [](const glm::vec3& dimensions) -> MeshAssetParams {
        return MeshAssetPresets::cube(dimensions);
    };
    
    meshAssetPresets["sphere"] = [](float radius, uint32_t subdivisions) -> MeshAssetParams {
        return MeshAssetPresets::sphere(radius, subdivisions);
    };
    
    meshAssetPresets["cylinder"] = [](float radius, float height, uint32_t subdivisions) -> MeshAssetParams {
        return MeshAssetPresets::cylinder(radius, height, subdivisions);
    };
    
    meshAssetPresets["torus"] = [](float majorRadius, float minorRadius) -> MeshAssetParams {
        return MeshAssetPresets::torus(majorRadius, minorRadius);
    };
    
    meshAssetPresets["plane"] = [](const glm::vec2& size) -> MeshAssetParams {
        return MeshAssetPresets::plane(size);
    };
    
    // Terrain presets
    meshAssetPresets["terrain"] = [](const glm::vec2& size, uint32_t resolution) -> MeshAssetParams {
        return MeshAssetPresets::terrain(size, resolution);
    };
    
    meshAssetPresets["mountain"] = [](const glm::vec2& size, uint32_t resolution) -> MeshAssetParams {
        return MeshAssetPresets::mountain(size, resolution);
    };
    
    meshAssetPresets["valley"] = [](const glm::vec2& size, uint32_t resolution) -> MeshAssetParams {
        return MeshAssetPresets::valley(size, resolution);
    };
    
    // Procedural presets
    meshAssetPresets["proceduralSphere"] = [](float radius, uint32_t subdivisions) -> MeshAssetParams {
        return MeshAssetPresets::proceduralSphere(radius, subdivisions);
    };
    
    meshAssetPresets["proceduralCube"] = [](const glm::vec3& dimensions) -> MeshAssetParams {
        return MeshAssetPresets::proceduralCube(dimensions);
    };
    
    meshAssetPresets["proceduralCylinder"] = [](float radius, float height) -> MeshAssetParams {
        return MeshAssetPresets::proceduralCylinder(radius, height);
    };
    
    // Material presets
    meshAssetPresets["pbrMetal"] = []() -> MaterialParams {
        return MeshAssetPresets::pbrMetal();
    };
    
    meshAssetPresets["pbrPlastic"] = []() -> MaterialParams {
        return MeshAssetPresets::pbrPlastic();
    };
    
    meshAssetPresets["pbrWood"] = []() -> MaterialParams {
        return MeshAssetPresets::pbrWood();
    };
    
    meshAssetPresets["pbrStone"] = []() -> MaterialParams {
        return MeshAssetPresets::pbrStone();
    };
    
    meshAssetPresets["emissive"] = []() -> MaterialParams {
        return MeshAssetPresets::emissive();
    };
    
    meshAssetPresets["transparent"] = []() -> MaterialParams {
        return MeshAssetPresets::transparent();
    };
    
    // LOD presets
    meshAssetPresets["standardLOD"] = []() -> LODParams {
        return MeshAssetPresets::standardLOD();
    };
    
    meshAssetPresets["aggressiveLOD"] = []() -> LODParams {
        return MeshAssetPresets::aggressiveLOD();
    };
    
    meshAssetPresets["conservativeLOD"] = []() -> LODParams {
        return MeshAssetPresets::conservativeLOD();
    };
    
    // UV presets
    meshAssetPresets["standardUV"] = []() -> UVGenParams {
        return MeshAssetPresets::standardUV();
    };
    
    meshAssetPresets["optimizedUV"] = []() -> UVGenParams {
        return MeshAssetPresets::optimizedUV();
    };
    
    meshAssetPresets["seamlessUV"] = []() -> UVGenParams {
        return MeshAssetPresets::seamlessUV();
    };
}

} // namespace MagiTech::GeneratorAgent 
