#include "QuadMechFactory.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/Log.hpp"
#include <fstream>
#include <filesystem>
#include <chrono>
#include <iterator>
#include <stdexcept>

namespace MagiTech {
namespace QuadMech {

namespace {
constexpr const char* kLogCategory = "QuadMech";
constexpr const char* kMechDirectory = "assets/mechs/";

std::string readTextFile(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file: " + path);
    }
    return std::string((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
}

uint64_t elapsedMs(std::chrono::high_resolution_clock::time_point start) {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::high_resolution_clock::now() - start).count());
}
} // namespace

// ============================================================================
// QUAD MECH FACTORY IMPLEMENTATION
// ============================================================================

QuadMechFactory::QuadMechFactory() {
    Log::info("QuadMechFactory created");
}

QuadMechFactory::~QuadMechFactory() {
    shutdown();
}

void QuadMechFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized.load()) return;

    m_cache.setCapacity(cache_size);
    m_threadPool = std::make_unique<GeneratorTaskPool>(num_threads);
    m_initialized.store(true);

    Log::info(kLogCategory, "QuadMechFactory initialized with cache_size={}, threads={}", cache_size, num_threads);
}

void QuadMechFactory::shutdown() {
    if (!m_initialized.load()) return;

    m_threadPool.reset();
    m_cache.clear();
    m_initialized.store(false);

    Log::info("QuadMechFactory shutdown complete");
}

std::string QuadMechFactory::definitionPathFor(const std::string& mechName) {
    return std::string(kMechDirectory) + mechName + ".quadmechdef";
}

std::string QuadMechFactory::packagePathFor(const std::string& mechName) {
    return std::string(kMechDirectory) + mechName + ".mechpack";
}

uint64_t QuadMechFactory::cacheKeyFor(const std::string& mechName, LODQuality quality) {
    return XXH64(mechName.c_str(), mechName.length(), static_cast<uint64_t>(quality));
}

std::future<QuadMechInstance> QuadMechFactory::loadAsync(const std::string& mechName, LODQuality quality) {
    if (!m_initialized.load() || !m_threadPool) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }

    return m_threadPool->enqueue([this, mechName, quality]() {
        auto startTime = std::chrono::high_resolution_clock::now();

        Log::info(kLogCategory, "Loading QuadMech asynchronously: {} (LOD: {})", mechName, static_cast<int>(quality));

        bool cacheHit = false;
        AssetPtr asset = loadMechAssetCached(mechName, quality, cacheHit);
        QuadMechInstance instance = createInstance(asset, quality);

        uint64_t loadTime = elapsedMs(startTime);
        updatePerformanceMetrics(loadTime, cacheHit);
        m_totalLoads++;

        Log::info(kLogCategory, "QuadMech loaded successfully: {} (took {}ms)", mechName, loadTime);
        return instance;
    });
}

QuadMechInstance QuadMechFactory::loadSync(const std::string& mechName, LODQuality quality) {
    if (!m_initialized.load()) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }

    auto startTime = std::chrono::high_resolution_clock::now();

    bool cacheHit = false;
    AssetPtr asset = loadMechAssetCached(mechName, quality, cacheHit);

    updatePerformanceMetrics(elapsedMs(startTime), cacheHit);
    m_totalLoads++;

    return createInstance(asset, quality);
}

QuadMechFactory::AssetPtr QuadMechFactory::loadMechAssetCached(const std::string& mechName, LODQuality quality, bool& cacheHit) {
    const uint64_t cacheKey = cacheKeyFor(mechName, quality);
    if (auto cached = m_cache.find(cacheKey)) {
        cacheHit = true;
        Log::info(kLogCategory, "QuadMech cache hit: {} (LOD: {})", mechName, static_cast<int>(quality));
        return *cached;
    }

    cacheHit = false;
    Log::info(kLogCategory, "QuadMech cache miss: {} (LOD: {})", mechName, static_cast<int>(quality));
    AssetPtr asset = loadMechAsset(mechName, quality);
    m_cache.insert(cacheKey, asset);
    return asset;
}

std::future<bool> QuadMechFactory::generatePackageAsync(const std::string& definitionPath, const std::string& outputPath) {
    if (!m_initialized.load() || !m_threadPool) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }

    return m_threadPool->enqueue([this, definitionPath, outputPath]() {
        Log::info(kLogCategory, "Generating QuadMech package asynchronously: {} -> {}", definitionPath, outputPath);
        return generatePackageSync(definitionPath, outputPath);
    });
}

bool QuadMechFactory::generatePackageSync(const std::string& definitionPath, const std::string& outputPath) {
    Log::info(kLogCategory, "Generating QuadMech package: {} -> {}", definitionPath, outputPath);

    try {
        if (!std::filesystem::exists(definitionPath)) {
            Log::error(kLogCategory, "Failed to open definition file: {}", definitionPath);
            return false;
        }

        QuadMechDefinition def = QuadMechGen::DefinitionParser::parseFromYAML(readTextFile(definitionPath));

        if (!QuadMechGen::DefinitionParser::validateDefinition(def)) {
            Log::error(kLogCategory, "Definition validation failed for: {}", definitionPath);
            return false;
        }

        // Generate asset for high quality (will be used to generate LODs)
        QuadMechAsset asset = generateMechAsset(def, LODQuality::HIGH);

        // Write package
        bool success = writePackageToDisk(asset, outputPath);

        if (success) {
            Log::info(kLogCategory, "QuadMech package generated successfully: {}", outputPath);
        } else {
            Log::error(kLogCategory, "Failed to write QuadMech package: {}", outputPath);
        }

        return success;

    } catch (const std::exception& e) {
        Log::error(kLogCategory, "Exception during package generation: {}", e.what());
        return false;
    }
}

void QuadMechFactory::watchForChanges(const std::string& mechName) {
    std::unique_lock<std::shared_mutex> lock(m_fileWatcherMutex);

    std::string definitionPath = definitionPathFor(mechName);
    updateFileTimestamp(definitionPath);

    Log::info(kLogCategory, "Now watching for changes: {}", definitionPath);
}

void QuadMechFactory::unwatchForChanges(const std::string& mechName) {
    std::unique_lock<std::shared_mutex> lock(m_fileWatcherMutex);

    std::string definitionPath = definitionPathFor(mechName);
    m_fileTimestamps.erase(definitionPath);

    Log::info(kLogCategory, "Stopped watching: {}", definitionPath);
}

bool QuadMechFactory::checkForUpdates(const std::string& mechName) {
    std::shared_lock<std::shared_mutex> lock(m_fileWatcherMutex);
    return hasFileChanged(definitionPathFor(mechName));
}

void QuadMechFactory::reloadMech(const std::string& mechName) {
    Log::info(kLogCategory, "Reloading QuadMech: {}", mechName);

    // Drop every LOD variant so the next access regenerates from disk.
    size_t evicted = 0;
    for (int q = static_cast<int>(LODQuality::HIGH); q <= static_cast<int>(LODQuality::ULTRA_LOW); ++q) {
        if (m_cache.erase(cacheKeyFor(mechName, static_cast<LODQuality>(q)))) ++evicted;
    }

    // Re-arm the watcher so the same change is not reported again.
    {
        std::unique_lock<std::shared_mutex> lock(m_fileWatcherMutex);
        const std::string definitionPath = definitionPathFor(mechName);
        if (m_fileTimestamps.count(definitionPath)) {
            updateFileTimestamp(definitionPath);
        }
    }

    Log::info(kLogCategory, "QuadMech cache cleared for: {} ({} LOD variants evicted)", mechName, evicted);
}

void QuadMechFactory::clearCache() {
    m_cache.clear();
    Log::info("QuadMech cache cleared");
}

size_t QuadMechFactory::getCacheSize() const {
    return m_cache.size();
}

double QuadMechFactory::getCacheHitRate() const {
    return m_cache.getHitRate();
}

void QuadMechFactory::setCacheCapacity(size_t capacity) {
    m_cache.setCapacity(capacity);
    Log::info(kLogCategory, "Cache capacity set to: {}", m_cache.capacity());
}

QuadMechFactory::PerformanceMetrics QuadMechFactory::getPerformanceMetrics() const {
    PerformanceMetrics metrics;
    metrics.totalLoads = m_totalLoads.load();
    metrics.cacheHits = m_cacheHits.load();
    metrics.cacheMisses = m_cacheMisses.load();
    metrics.totalLoadTime = m_totalLoadTime.load();
    metrics.cacheHitRate = getCacheHitRate();

    if (metrics.totalLoads > 0) {
        metrics.averageLoadTime = static_cast<double>(metrics.totalLoadTime) / metrics.totalLoads;
    }

    return metrics;
}

void QuadMechFactory::resetPerformanceMetrics() {
    m_totalLoads = 0;
    m_cacheHits = 0;
    m_cacheMisses = 0;
    m_totalLoadTime = 0;
    Log::info("QuadMech performance metrics reset");
}

bool QuadMechFactory::validateMechDefinition(const QuadMechDefinition& def) {
    return QuadMechGen::DefinitionParser::validateDefinition(def);
}

std::vector<std::string> QuadMechFactory::getAvailableMechs() const {
    std::vector<std::string> mechs;

    // Scan for .quadmechdef files
    std::error_code ec;
    if (std::filesystem::exists(kMechDirectory, ec)) {
        for (const auto& entry : std::filesystem::directory_iterator(kMechDirectory, ec)) {
            if (entry.is_regular_file() && entry.path().extension() == ".quadmechdef") {
                mechs.push_back(entry.path().stem().string());
            }
        }
    }

    return mechs;
}

bool QuadMechFactory::mechExists(const std::string& mechName) const {
    return std::filesystem::exists(definitionPathFor(mechName)) ||
           std::filesystem::exists(packagePathFor(mechName));
}

QuadMechInstance QuadMechFactory::instantiateDefinition(const QuadMechDefinition& def, LODQuality quality) {
    auto asset = std::make_shared<QuadMechAsset>(generateMechAsset(def, quality));
    return createInstance(asset, quality);
}

// ============================================================================
// PRIVATE HELPER METHODS
// ============================================================================

QuadMechFactory::AssetPtr QuadMechFactory::loadMechAsset(const std::string& mechName, LODQuality quality) {
    Log::info(kLogCategory, "Loading QuadMech asset: {} (LOD: {})", mechName, static_cast<int>(quality));

    // Try to load from package first
    std::string packagePath = packagePathFor(mechName);
    if (std::filesystem::exists(packagePath)) {
        return std::make_shared<QuadMechAsset>(QuadMechGen::PackageReader::readMechPackage(packagePath));
    }

    // Fall back to definition file
    std::string definitionPath = definitionPathFor(mechName);
    if (!std::filesystem::exists(definitionPath)) {
        throw std::runtime_error("QuadMech not found: " + mechName);
    }

    QuadMechDefinition def = QuadMechGen::DefinitionParser::parseFromYAML(readTextFile(definitionPath));
    return std::make_shared<QuadMechAsset>(generateMechAsset(def, quality));
}

QuadMechInstance QuadMechFactory::createInstance(const AssetPtr& asset, LODQuality quality) {
    QuadMechInstance instance;
    instance.asset = asset;
    instance.transform = glm::mat4(1.0f);
    instance.currentAnimation = "idle";
    instance.currentLOD = quality;
    instance.energyLevel = 1.0f;
    instance.runeGlowIntensity = 1.0f;
    instance.cockpitOpen = false;
    instance.pilotInside = false;
    if (asset) {
        if (asset->rootBody) instance.physicsBodies.push_back(asset->rootBody);
        for (const auto& [moduleId, module] : asset->modules) {
            if (module.physicsBody && module.physicsBody != asset->rootBody) {
                instance.physicsBodies.push_back(module.physicsBody);
            }
        }
    }

    return instance;
}

uint64_t QuadMechFactory::computeFileHash(const std::string& filePath) {
    if (!std::filesystem::exists(filePath)) return 0;

    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) return 0;

    XXH64_state_t state;
    XXH64_reset(&state, 0);

    char buffer[4096];
    while (file.read(buffer, sizeof(buffer)) || file.gcount() > 0) {
        XXH64_update(&state, buffer, static_cast<size_t>(file.gcount()));
    }

    return XXH64_digest(&state);
}

void QuadMechFactory::updateFileTimestamp(const std::string& filePath) {
    if (std::filesystem::exists(filePath)) {
        auto lastWriteTime = std::filesystem::last_write_time(filePath);
        auto timePoint = std::chrono::clock_cast<std::chrono::system_clock>(lastWriteTime);
        m_fileTimestamps[filePath] = timePoint;
    }
}

bool QuadMechFactory::hasFileChanged(const std::string& filePath) {
    if (!std::filesystem::exists(filePath)) return false;

    auto it = m_fileTimestamps.find(filePath);
    if (it == m_fileTimestamps.end()) return false;

    auto lastWriteTime = std::filesystem::last_write_time(filePath);
    auto timePoint = std::chrono::clock_cast<std::chrono::system_clock>(lastWriteTime);

    return timePoint > it->second;
}

QuadMechAsset QuadMechFactory::generateMechAsset(const QuadMechDefinition& def, LODQuality quality) {
    Log::info(kLogCategory, "Generating QuadMech asset: {} (LOD: {})", def.name, static_cast<int>(quality));

    QuadMechAsset asset;
    asset.definition = def;

    // Build skeleton
    asset.skeleton = QuadMechGen::ModuleAssembler::buildSkeleton(def);

    // Assemble modules
    auto modules = QuadMechGen::ModuleAssembler::assembleModules(def, quality);
    for (size_t i = 0; i < modules.size() && i < def.modules.size(); ++i) {
        asset.modules[def.modules[i].id] = modules[i];
    }

    // Create Magitech materials
    asset.energyRunesMaterial = QuadMechGen::MaterialSynthesizer::createEnergyRunesMaterial(def.magitechMaterials.energyRunes);
    asset.energyCoreMaterial = QuadMechGen::MaterialSynthesizer::createEnergyCoreMaterial(def.magitechMaterials.energyCore);
    asset.canopyMaterial = QuadMechGen::MaterialSynthesizer::createCanopyMaterial(def.magitechMaterials.canopy);

    // Process animations
    asset.animations = QuadMechGen::AnimationProcessor::processAllAnimations(def, asset.skeleton);

    // Build physics rig
    auto physicsBodies = QuadMechGen::PhysicsRigBuilder::buildPhysicsRig(def);
    QuadMechGen::PhysicsRigBuilder::setupJointConstraints(def, physicsBodies);
    // The rig has one body per module, in definition order; the first is the root.
    for (size_t i = 0; i < physicsBodies.size() && i < def.modules.size(); ++i) {
        auto it = asset.modules.find(def.modules[i].id);
        if (it != asset.modules.end()) it->second.physicsBody = physicsBodies[i];
    }
    if (!physicsBodies.empty()) {
        asset.rootBody = physicsBodies[0];
    }

    Log::info(kLogCategory, "QuadMech asset generated successfully: {} ({} modules, {} animations)",
              def.name, asset.modules.size(), asset.animations.size());

    return asset;
}

bool QuadMechFactory::writePackageToDisk(const QuadMechAsset& asset, const std::string& outputPath) {
    return QuadMechGen::PackageWriter::writeMechPackage(asset, outputPath);
}

void QuadMechFactory::updatePerformanceMetrics(uint64_t loadTime, bool cacheHit) {
    m_totalLoadTime += loadTime;
    if (cacheHit) {
        m_cacheHits++;
    } else {
        m_cacheMisses++;
    }
}

} // namespace QuadMech
} // namespace MagiTech
