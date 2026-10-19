#include "MeshAssetGenerator.hpp"
#include "core/LuaJson.hpp"
#include "core/Log.hpp"
#include <sol/sol.hpp>
#include <deque>
#include <memory>
#include <mutex>

namespace MagiTech::GeneratorAgent {

namespace {

// ---------------------------------------------------------------------------
// Generator instance used by the bindings (injectable, created lazily otherwise)
// ---------------------------------------------------------------------------
std::mutex& generatorMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<MeshAssetGenerator>& generatorSlot() {
    static std::shared_ptr<MeshAssetGenerator> g;
    return g;
}

// ---------------------------------------------------------------------------
// Async job handle exposed to Lua
// ---------------------------------------------------------------------------
struct MeshAssetJob {
    std::shared_future<MeshAssetBundle> future;

    bool isReady() const {
        return future.valid() && future.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
    }
    // Blocks until the asset is generated.
    MeshAssetBundle get() const {
        if (!future.valid()) {
            MeshAssetBundle bundle;
            bundle.errorMessage = "Invalid mesh asset job";
            return bundle;
        }
        return future.get();
    }
};

// ---------------------------------------------------------------------------
// Event bridge: generator callbacks may fire on worker threads, so they only
// queue events; pollMeshAssetEvents() delivers them to Lua on the Lua thread.
// ---------------------------------------------------------------------------
struct QueuedEvent {
    enum class Kind { Generated, Failed, CacheHit, CacheMiss } kind;
    MeshAssetBundle bundle;   // Generated
    std::string assetId;      // all kinds
    std::string error;        // Failed
};

struct EventBridge {
    std::mutex mutex;
    std::deque<QueuedEvent> queue;
    std::vector<sol::protected_function> generated;
    std::vector<sol::protected_function> failed;
    std::vector<sol::protected_function> cacheHit;
    std::vector<sol::protected_function> cacheMiss;
    const MeshAssetGenerator* bridgedGenerator = nullptr;
};

EventBridge& eventBridge() {
    static EventBridge bridge;
    return bridge;
}

void push(QueuedEvent event) {
    auto& bridge = eventBridge();
    std::lock_guard<std::mutex> lock(bridge.mutex);
    bridge.queue.push_back(std::move(event));
}

// Installs the queueing callbacks on the generator once per generator instance.
void ensureBridge(MeshAssetGenerator& generator) {
    auto& bridge = eventBridge();
    {
        std::lock_guard<std::mutex> lock(bridge.mutex);
        if (bridge.bridgedGenerator == &generator) return;
        bridge.bridgedGenerator = &generator;
    }
    generator.onAssetGenerated([](const MeshAssetBundle& bundle) {
        push({QueuedEvent::Kind::Generated, bundle, bundle.assetId, {}});
    });
    generator.onAssetFailed([](const std::string& id, const std::string& error) {
        push({QueuedEvent::Kind::Failed, {}, id, error});
    });
    generator.onCacheHit([](const std::string& id) {
        push({QueuedEvent::Kind::CacheHit, {}, id, {}});
    });
    generator.onCacheMiss([](const std::string& id) {
        push({QueuedEvent::Kind::CacheMiss, {}, id, {}});
    });
}

void addLuaCallback(std::vector<sol::protected_function> EventBridge::*list, sol::protected_function fn) {
    auto& bridge = eventBridge();
    std::lock_guard<std::mutex> lock(bridge.mutex);
    (bridge.*list).push_back(std::move(fn));
}

template <typename... Args>
void invokeAll(const std::vector<sol::protected_function>& callbacks, const char* what, Args&&... args) {
    for (const auto& fn : callbacks) {
        sol::protected_function_result result = fn(args...);
        if (!result.valid()) {
            sol::error err = result;
            Log::warn("MeshAsset", "Lua {} callback failed: {}", what, err.what());
        }
    }
}

nlohmann::json toJson(const sol::object& value) {
    return MagiTech::LuaJson::fromLua(value);
}

template <typename T>
T valueOr(const sol::optional<T>& v, T fallback) {
    return v ? *v : fallback;
}

} // namespace

void setMeshAssetGenerator(std::shared_ptr<MeshAssetGenerator> generator) {
    std::lock_guard<std::mutex> lock(generatorMutex());
    generatorSlot() = std::move(generator);
}

std::shared_ptr<MeshAssetGenerator> meshAssetGenerator() {
    std::lock_guard<std::mutex> lock(generatorMutex());
    auto& slot = generatorSlot();
    if (!slot) {
        // No generator injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<MeshAssetGenerator>();
        slot->initialize(4);
    }
    return slot;
}

void pollMeshAssetEvents() {
    auto& bridge = eventBridge();
    std::deque<QueuedEvent> events;
    std::vector<sol::protected_function> generated, failed, cacheHit, cacheMiss;
    {
        std::lock_guard<std::mutex> lock(bridge.mutex);
        events.swap(bridge.queue);
        generated = bridge.generated;
        failed = bridge.failed;
        cacheHit = bridge.cacheHit;
        cacheMiss = bridge.cacheMiss;
    }
    for (const auto& event : events) {
        switch (event.kind) {
            case QueuedEvent::Kind::Generated: invokeAll(generated, "onAssetGenerated", event.bundle); break;
            case QueuedEvent::Kind::Failed:    invokeAll(failed, "onAssetFailed", event.assetId, event.error); break;
            case QueuedEvent::Kind::CacheHit:  invokeAll(cacheHit, "onCacheHit", event.assetId); break;
            case QueuedEvent::Kind::CacheMiss: invokeAll(cacheMiss, "onCacheMiss", event.assetId); break;
        }
    }
}

void registerMeshAssetBindings(sol::state& lua) {
    // Callbacks from a previous Lua state must not be called with this one.
    {
        auto& bridge = eventBridge();
        std::lock_guard<std::mutex> lock(bridge.mutex);
        bridge.generated.clear();
        bridge.failed.clear();
        bridge.cacheHit.clear();
        bridge.cacheMiss.clear();
        bridge.queue.clear();
    }

    // Create mesh asset module
    sol::table meshAsset = lua.create_named_table("MeshAsset");

    // mt pipeline parameter structs. MeshParams, LODParams, MaterialParams and
    // MeshAssetBundle live in the MeshAsset table because other families register
    // global usertypes with the same names.
    meshAsset.new_usertype<mt::MeshParams>("MeshParams",
        sol::constructors<mt::MeshParams()>(),
        "id", &mt::MeshParams::id,
        "type", &mt::MeshParams::type,
        "dimensions", &mt::MeshParams::dimensions,
        "subdivisions", &mt::MeshParams::subdivisions,
        "noiseFrequency", &mt::MeshParams::noiseFrequency,
        "isoThreshold", &mt::MeshParams::isoThreshold,
        "sculptHeightMap", &mt::MeshParams::sculptHeightMap,
        "generateNormals", &mt::MeshParams::generateNormals,
        "generateTangents", &mt::MeshParams::generateTangents,
        "generateUVs", &mt::MeshParams::generateUVs,
        "weldVertices", &mt::MeshParams::weldVertices,
        "seed", &mt::MeshParams::seed
    );

    meshAsset.new_usertype<mt::LODParams>("LODParams",
        sol::constructors<mt::LODParams()>(),
        "baseMeshId", &mt::LODParams::baseMeshId,
        "screenSizes", &mt::LODParams::screenSizes,
        "targetRatios", &mt::LODParams::targetRatios,
        "preserveBorders", &mt::LODParams::preserveBorders,
        "preserveUVSeams", &mt::LODParams::preserveUVSeams,
        "maxTriangles", &mt::LODParams::maxTriangles,
        "errorThreshold", &mt::LODParams::errorThreshold
    );

    meshAsset.new_usertype<mt::MaterialParams>("MaterialParams",
        sol::constructors<mt::MaterialParams()>(),
        "id", &mt::MaterialParams::id,
        "name", &mt::MaterialParams::name,
        "shaderType", &mt::MaterialParams::shaderType,
        "albedo", &mt::MaterialParams::albedo,
        "emissive", &mt::MaterialParams::emissive,
        "metallic", &mt::MaterialParams::metallic,
        "roughness", &mt::MaterialParams::roughness,
        "ao", &mt::MaterialParams::ao,
        "normalScale", &mt::MaterialParams::normalScale,
        "emissiveIntensity", &mt::MaterialParams::emissiveIntensity,
        "usePBR", &mt::MaterialParams::usePBR,
        "generateProcedural", &mt::MaterialParams::generateProcedural
    );

    lua.new_usertype<mt::UVGenParams>("UVGenParams",
        sol::constructors<mt::UVGenParams()>(),
        "atlasSize", &mt::UVGenParams::atlasSize,
        "padding", &mt::UVGenParams::padding,
        "texelDensity", &mt::UVGenParams::texelDensity,
        "preserveSeams", &mt::UVGenParams::preserveSeams,
        "optimizeCharts", &mt::UVGenParams::optimizeCharts,
        "generateUDIM", &mt::UVGenParams::generateUDIM,
        "maxCharts", &mt::UVGenParams::maxCharts
    );

    // MeshAssetParams
    lua.new_usertype<MeshAssetParams>("MeshAssetParams",
        sol::constructors<MeshAssetParams()>(),
        "id", &MeshAssetParams::id,
        "type", &MeshAssetParams::type,
        "meshParams", &MeshAssetParams::meshParams,
        "lodParams", &MeshAssetParams::lodParams,
        "materialParams", &MeshAssetParams::materialParams,
        "uvParams", &MeshAssetParams::uvParams,
        "generateAsync", &MeshAssetParams::generateAsync,
        "cacheResult", &MeshAssetParams::cacheResult,
        "validateResult", &MeshAssetParams::validateResult,
        "optimizeMesh", &MeshAssetParams::optimizeMesh,
        "maxGenerationTime", &MeshAssetParams::maxGenerationTime,
        "maxMemoryUsage", &MeshAssetParams::maxMemoryUsage
    );

    // MeshAssetBundle
    meshAsset.new_usertype<MeshAssetBundle>("MeshAssetBundle",
        sol::constructors<MeshAssetBundle()>(),
        "isValid", &MeshAssetBundle::isValid,
        "errorMessage", &MeshAssetBundle::errorMessage,
        "assetId", &MeshAssetBundle::assetId,
        "assetType", &MeshAssetBundle::assetType,
        "memoryUsage", &MeshAssetBundle::memoryUsage,
        "generationTime", &MeshAssetBundle::generationTime,
        "vertexCount", sol::readonly_property([](const MeshAssetBundle& b) -> uint32_t {
            return b.mesh ? b.mesh->vertexCount : 0u;
        }),
        "triangleCount", sol::readonly_property([](const MeshAssetBundle& b) -> uint32_t {
            return b.mesh ? b.mesh->triangleCount : 0u;
        }),
        "lodCount", sol::readonly_property([](const MeshAssetBundle& b) -> size_t { return b.lods.size(); }),
        "textureCount", sol::readonly_property([](const MeshAssetBundle& b) -> size_t { return b.textures.size(); }),
        "hasMaterial", sol::readonly_property([](const MeshAssetBundle& b) { return b.materialHandle.valid(); }),
        "uvPackingEfficiency", sol::readonly_property([](const MeshAssetBundle& b) { return b.uvPacking.packingEfficiency; })
    );

    // MeshAssetStats
    lua.new_usertype<MeshAssetStats>("MeshAssetStats",
        sol::constructors<MeshAssetStats()>(),
        "totalAssets", &MeshAssetStats::totalAssets,
        "generatedAssets", &MeshAssetStats::generatedAssets,
        "cachedAssets", &MeshAssetStats::cachedAssets,
        "failedAssets", &MeshAssetStats::failedAssets,
        "totalAsyncJobs", &MeshAssetStats::totalAsyncJobs,
        "completedJobs", &MeshAssetStats::completedJobs,
        "failedJobs", &MeshAssetStats::failedJobs,
        "cacheHits", &MeshAssetStats::cacheHits,
        "cacheMisses", &MeshAssetStats::cacheMisses,
        "averageGenerationTime", &MeshAssetStats::averageGenerationTime,
        "averageLoadTime", &MeshAssetStats::averageLoadTime,
        "totalMemoryUsage", &MeshAssetStats::totalMemoryUsage,
        "reset", &MeshAssetStats::reset
    );

    // Async job handle
    lua.new_usertype<MeshAssetJob>("MeshAssetJob",
        sol::no_constructor,
        "isReady", &MeshAssetJob::isReady,
        "get", &MeshAssetJob::get
    );

    // Initialize function
    meshAsset["initialize"] = [](sol::optional<uint32_t> threadCount) {
        auto generator = meshAssetGenerator();
        generator->initialize(valueOr(threadCount, 4u));
    };

    // Shutdown function
    meshAsset["shutdown"] = []() {
        meshAssetGenerator()->shutdown();
    };

    // Configuration functions (Lua tables <-> JSON)
    meshAsset["setConfig"] = [](const sol::object& config) {
        meshAssetGenerator()->setConfig(toJson(config));
    };

    meshAsset["getConfig"] = [](sol::this_state s) -> sol::object {
        return MagiTech::LuaJson::toLua(sol::state_view(s), meshAssetGenerator()->getConfig());
    };

    // Asset generation functions
    meshAsset["generateSync"] = [](const MeshAssetParams& params) -> MeshAssetBundle {
        return meshAssetGenerator()->generateSync(params);
    };

    meshAsset["generateAsync"] = [](const MeshAssetParams& params) -> MeshAssetJob {
        return MeshAssetJob{meshAssetGenerator()->generateAsync(params).share()};
    };

    meshAsset["generateBatch"] = [](const std::vector<MeshAssetParams>& params) {
        std::vector<MeshAssetJob> jobs;
        for (auto& future : meshAssetGenerator()->generateBatch(params)) {
            jobs.push_back(MeshAssetJob{future.share()});
        }
        return sol::as_table(std::move(jobs));
    };

    // Asset management functions
    meshAsset["isAssetLoaded"] = [](const std::string& assetId) -> bool {
        return meshAssetGenerator()->isAssetLoaded(assetId);
    };

    meshAsset["getAsset"] = [](const std::string& assetId) -> MeshAssetBundle {
        return meshAssetGenerator()->getAsset(assetId);
    };

    meshAsset["unloadAsset"] = [](const std::string& assetId) {
        meshAssetGenerator()->unloadAsset(assetId);
    };

    meshAsset["unloadAllAssets"] = []() {
        meshAssetGenerator()->unloadAllAssets();
    };

    // Cache management functions
    meshAsset["enableCaching"] = [](sol::optional<bool> enable) {
        meshAssetGenerator()->enableCaching(valueOr(enable, true));
    };

    meshAsset["clearCache"] = []() {
        meshAssetGenerator()->clearCache();
    };

    meshAsset["setCacheSize"] = [](size_t maxSize) {
        meshAssetGenerator()->setCacheSize(maxSize);
    };

    meshAsset["getCacheSize"] = []() -> size_t {
        return meshAssetGenerator()->getCacheSize();
    };

    meshAsset["getMaxCacheSize"] = []() -> size_t {
        return meshAssetGenerator()->getMaxCacheSize();
    };

    meshAsset["getCacheHitRate"] = []() -> double {
        return meshAssetGenerator()->getCacheHitRate();
    };

    // Performance monitoring functions
    meshAsset["enablePerformanceMonitoring"] = [](sol::optional<bool> enable) {
        meshAssetGenerator()->enablePerformanceMonitoring(valueOr(enable, true));
    };

    meshAsset["setPerformanceThresholds"] = [](float maxGenerationTime, float maxLoadTime) {
        meshAssetGenerator()->setPerformanceThresholds(maxGenerationTime, maxLoadTime);
    };

    meshAsset["getStats"] = []() -> MeshAssetStats {
        return meshAssetGenerator()->getStats();
    };

    meshAsset["resetStats"] = []() {
        meshAssetGenerator()->resetStats();
    };

    meshAsset["logPerformanceMetrics"] = []() {
        meshAssetGenerator()->logPerformanceMetrics();
    };

    // Validation functions
    meshAsset["validateParams"] = [](const MeshAssetParams& params) -> bool {
        return meshAssetGenerator()->validateParams(params);
    };

    meshAsset["validateAsset"] = [](const MeshAssetBundle& bundle) {
        return sol::as_table(meshAssetGenerator()->validateAsset(bundle));
    };

    meshAsset["setValidationLevel"] = [](int level) {
        meshAssetGenerator()->setValidationLevel(level);
    };

    // Utility functions
    meshAsset["getAvailableAssetTypes"] = []() {
        return sol::as_table(meshAssetGenerator()->getAvailableAssetTypes());
    };

    meshAsset["getLoadedAssetIds"] = []() {
        return sol::as_table(meshAssetGenerator()->getLoadedAssetIds());
    };

    meshAsset["getTotalMemoryUsage"] = []() -> size_t {
        return meshAssetGenerator()->getTotalMemoryUsage();
    };

    // Event callback functions (delivered by MeshAsset.pollEvents / pollMeshAssetEvents)
    meshAsset["onAssetGenerated"] = [](sol::protected_function callback) {
        ensureBridge(*meshAssetGenerator());
        addLuaCallback(&EventBridge::generated, std::move(callback));
    };

    meshAsset["onAssetFailed"] = [](sol::protected_function callback) {
        ensureBridge(*meshAssetGenerator());
        addLuaCallback(&EventBridge::failed, std::move(callback));
    };

    meshAsset["onCacheHit"] = [](sol::protected_function callback) {
        ensureBridge(*meshAssetGenerator());
        addLuaCallback(&EventBridge::cacheHit, std::move(callback));
    };

    meshAsset["onCacheMiss"] = [](sol::protected_function callback) {
        ensureBridge(*meshAssetGenerator());
        addLuaCallback(&EventBridge::cacheMiss, std::move(callback));
    };

    meshAsset["pollEvents"] = []() {
        pollMeshAssetEvents();
    };

    // Create MeshAssetUtils module
    sol::table meshAssetUtils = lua.create_named_table("MeshAssetUtils");

    // Parameter creation functions: createMeshParams(table) or createMeshParams(id, type)
    meshAssetUtils["createMeshParams"] = sol::overload(
        [](const std::string& id, const std::string& type) -> MeshAssetParams {
            return MeshAssetUtils::createMeshParams(id, type);
        },
        [](const sol::table& data) -> MeshAssetParams {
            return MeshAssetUtils::createMeshParams(toJson(data));
        }
    );

    // Validation functions
    meshAssetUtils["validateMeshParams"] = [](const MeshAssetParams& params) -> bool {
        return MeshAssetUtils::validateMeshParams(params);
    };

    meshAssetUtils["validateLODParams"] = [](const mt::LODParams& params) -> bool {
        return MeshAssetUtils::validateLODParams(params);
    };

    meshAssetUtils["validateMaterialParams"] = [](const mt::MaterialParams& params) -> bool {
        return MeshAssetUtils::validateMaterialParams(params);
    };

    meshAssetUtils["validateUVParams"] = [](const mt::UVGenParams& params) -> bool {
        return MeshAssetUtils::validateUVParams(params);
    };

    // Conversion functions
    meshAssetUtils["paramsToJson"] = [](const MeshAssetParams& params, sol::this_state s) -> sol::object {
        return MagiTech::LuaJson::toLua(sol::state_view(s), MeshAssetUtils::paramsToJson(params));
    };

    meshAssetUtils["jsonToParams"] = [](const sol::table& data) -> MeshAssetParams {
        return MeshAssetUtils::jsonToParams(toJson(data));
    };

    // Utility functions
    meshAssetUtils["generateAssetId"] = [](sol::optional<std::string> prefix) -> std::string {
        return MeshAssetUtils::generateAssetId(valueOr(prefix, std::string("mesh")));
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

    // Create MeshAssetPresets module (arguments are optional, as in C++)
    sol::table meshAssetPresets = lua.create_named_table("MeshAssetPresets");

    // Primitive presets
    // Vector arguments (when glm types are bound) or plain numbers are accepted.
    meshAssetPresets["cube"] = sol::overload(
        [](const glm::vec3& dimensions) { return MeshAssetPresets::cube(dimensions); },
        [](sol::optional<float> x, sol::optional<float> y, sol::optional<float> z) {
            const float sx = valueOr(x, 1.0f);
            return MeshAssetPresets::cube(glm::vec3(sx, valueOr(y, sx), valueOr(z, sx)));
        });

    meshAssetPresets["sphere"] = [](sol::optional<float> radius, sol::optional<uint32_t> subdivisions) {
        return MeshAssetPresets::sphere(valueOr(radius, 0.5f), valueOr(subdivisions, 16u));
    };

    meshAssetPresets["cylinder"] = [](sol::optional<float> radius, sol::optional<float> height,
                                      sol::optional<uint32_t> subdivisions) {
        return MeshAssetPresets::cylinder(valueOr(radius, 0.5f), valueOr(height, 1.0f), valueOr(subdivisions, 16u));
    };

    meshAssetPresets["torus"] = [](sol::optional<float> majorRadius, sol::optional<float> minorRadius) {
        return MeshAssetPresets::torus(valueOr(majorRadius, 1.0f), valueOr(minorRadius, 0.3f));
    };

    meshAssetPresets["plane"] = sol::overload(
        [](const glm::vec2& size) { return MeshAssetPresets::plane(size); },
        [](sol::optional<float> width, sol::optional<float> depth) {
            const float w = valueOr(width, 1.0f);
            return MeshAssetPresets::plane(glm::vec2(w, valueOr(depth, w)));
        });

    // Terrain presets
    meshAssetPresets["terrain"] = sol::overload(
        [](const glm::vec2& size, sol::optional<uint32_t> resolution) {
            return MeshAssetPresets::terrain(size, valueOr(resolution, 256u));
        },
        [](sol::optional<float> width, sol::optional<float> depth, sol::optional<uint32_t> resolution) {
            const float w = valueOr(width, 100.0f);
            return MeshAssetPresets::terrain(glm::vec2(w, valueOr(depth, w)), valueOr(resolution, 256u));
        });

    meshAssetPresets["mountain"] = sol::overload(
        [](const glm::vec2& size, sol::optional<uint32_t> resolution) {
            return MeshAssetPresets::mountain(size, valueOr(resolution, 512u));
        },
        [](sol::optional<float> width, sol::optional<float> depth, sol::optional<uint32_t> resolution) {
            const float w = valueOr(width, 200.0f);
            return MeshAssetPresets::mountain(glm::vec2(w, valueOr(depth, w)), valueOr(resolution, 512u));
        });

    meshAssetPresets["valley"] = sol::overload(
        [](const glm::vec2& size, sol::optional<uint32_t> resolution) {
            return MeshAssetPresets::valley(size, valueOr(resolution, 384u));
        },
        [](sol::optional<float> width, sol::optional<float> depth, sol::optional<uint32_t> resolution) {
            const float w = valueOr(width, 150.0f);
            return MeshAssetPresets::valley(glm::vec2(w, valueOr(depth, w)), valueOr(resolution, 384u));
        });

    // Procedural presets
    meshAssetPresets["proceduralSphere"] = [](sol::optional<float> radius, sol::optional<uint32_t> subdivisions) {
        return MeshAssetPresets::proceduralSphere(valueOr(radius, 0.5f), valueOr(subdivisions, 16u));
    };

    meshAssetPresets["proceduralCube"] = sol::overload(
        [](const glm::vec3& dimensions) { return MeshAssetPresets::proceduralCube(dimensions); },
        [](sol::optional<float> x, sol::optional<float> y, sol::optional<float> z) {
            const float sx = valueOr(x, 1.0f);
            return MeshAssetPresets::proceduralCube(glm::vec3(sx, valueOr(y, sx), valueOr(z, sx)));
        });

    meshAssetPresets["proceduralCylinder"] = [](sol::optional<float> radius, sol::optional<float> height) {
        return MeshAssetPresets::proceduralCylinder(valueOr(radius, 0.5f), valueOr(height, 1.0f));
    };

    // Material presets
    meshAssetPresets["pbrMetal"] = &MeshAssetPresets::pbrMetal;
    meshAssetPresets["pbrPlastic"] = &MeshAssetPresets::pbrPlastic;
    meshAssetPresets["pbrWood"] = &MeshAssetPresets::pbrWood;
    meshAssetPresets["pbrStone"] = &MeshAssetPresets::pbrStone;
    meshAssetPresets["emissive"] = &MeshAssetPresets::emissive;
    meshAssetPresets["transparent"] = &MeshAssetPresets::transparent;

    // LOD presets
    meshAssetPresets["standardLOD"] = &MeshAssetPresets::standardLOD;
    meshAssetPresets["aggressiveLOD"] = &MeshAssetPresets::aggressiveLOD;
    meshAssetPresets["conservativeLOD"] = &MeshAssetPresets::conservativeLOD;

    // UV presets
    meshAssetPresets["standardUV"] = &MeshAssetPresets::standardUV;
    meshAssetPresets["optimizedUV"] = &MeshAssetPresets::optimizedUV;
    meshAssetPresets["seamlessUV"] = &MeshAssetPresets::seamlessUV;
}

} // namespace MagiTech::GeneratorAgent
