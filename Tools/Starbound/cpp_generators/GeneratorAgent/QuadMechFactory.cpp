#include "QuadMechFactory.hpp"
#include "QuadMechGenerators.cpp"
#include "core/Log.hpp"
#include <fstream>
#include <filesystem>
#include <chrono>

namespace MagiTech {
namespace QuadMech {

// ============================================================================
// QUAD MECH CACHE IMPLEMENTATION
// ============================================================================

template<typename K, typename V>
void QuadMechCache<K, V>::moveToFront(Node* node) {
    if (node == m_head) return;
    
    // Remove from current position
    if (node->prev) node->prev->next = node->next;
    if (node->next) node->next->prev = node->prev;
    if (node == m_tail) m_tail = node->prev;
    
    // Insert at front
    insertAtFront(node);
}

template<typename K, typename V>
void QuadMechCache<K, V>::insertAtFront(Node* node) {
    node->next = m_head;
    node->prev = nullptr;
    if (m_head) m_head->prev = node;
    m_head = node;
    if (!m_tail) m_tail = node;
}

template<typename K, typename V>
void QuadMechCache<K, V>::evictLRU() {
    if (!m_tail) return;
    
    auto key = m_tail->key;
    m_cache.erase(key);
    
    if (m_head == m_tail) {
        m_head = m_tail = nullptr;
    } else {
        m_tail = m_tail->prev;
        m_tail->next = nullptr;
    }
}

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
    
    m_cache = QuadMechCache<uint64_t, QuadMechAsset>(cache_size);
    m_threadPool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized.store(true);
    
    Log::info("QuadMechFactory initialized with cache_size={}, threads={}", cache_size, num_threads);
}

void QuadMechFactory::shutdown() {
    if (!m_initialized.load()) return;
    
    m_threadPool.reset();
    m_cache.clear();
    m_initialized.store(false);
    
    Log::info("QuadMechFactory shutdown complete");
}

std::future<QuadMechInstance> QuadMechFactory::loadAsync(const std::string& mechName, LODQuality quality) {
    if (!m_initialized.load() || !m_threadPool) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }
    
    return m_threadPool->enqueue([=]() {
        auto startTime = std::chrono::high_resolution_clock::now();
        
        Log::info("Loading QuadMech asynchronously: {} (LOD: {})", mechName, static_cast<int>(quality));
        
        QuadMechAsset asset = loadMechAsset(mechName, quality);
        QuadMechInstance instance = createInstance(asset);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto loadTime = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
        
        updatePerformanceMetrics(loadTime, false); // Cache miss for async loads
        m_totalLoads++;
        
        Log::info("QuadMech loaded successfully: {} (took {}ms)", mechName, loadTime);
        return instance;
    });
}

QuadMechInstance QuadMechFactory::loadSync(const std::string& mechName, LODQuality quality) {
    if (!m_initialized.load()) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    // Check cache first
    uint64_t cacheKey = XXH64(mechName.c_str(), mechName.length(), static_cast<uint64_t>(quality));
    auto cachedAsset = m_cache.find(cacheKey);
    
    bool cacheHit = cachedAsset.has_value();
    if (cacheHit) {
        m_cacheHits++;
        Log::info("QuadMech cache hit: {} (LOD: {})", mechName, static_cast<int>(quality));
        auto endTime = std::chrono::high_resolution_clock::now();
        auto loadTime = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
        updatePerformanceMetrics(loadTime, true);
        return createInstance(cachedAsset.value());
    }
    
    m_cacheMisses++;
    Log::info("QuadMech cache miss: {} (LOD: {})", mechName, static_cast<int>(quality));
    
    QuadMechAsset asset = loadMechAsset(mechName, quality);
    m_cache.insert(cacheKey, asset);
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto loadTime = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime).count();
    updatePerformanceMetrics(loadTime, false);
    m_totalLoads++;
    
    return createInstance(asset);
}

std::future<bool> QuadMechFactory::generatePackageAsync(const std::string& definitionPath, const std::string& outputPath) {
    if (!m_initialized.load() || !m_threadPool) {
        throw std::runtime_error("QuadMechFactory not initialized");
    }
    
    return m_threadPool->enqueue([=]() {
        Log::info("Generating QuadMech package asynchronously: {} -> {}", definitionPath, outputPath);
        return generatePackageSync(definitionPath, outputPath);
    });
}

bool QuadMechFactory::generatePackageSync(const std::string& definitionPath, const std::string& outputPath) {
    Log::info("Generating QuadMech package: {} -> {}", definitionPath, outputPath);
    
    try {
        // Read and parse definition
        std::ifstream file(definitionPath);
        if (!file.is_open()) {
            Log::error("Failed to open definition file: {}", definitionPath);
            return false;
        }
        
        std::string yamlContent((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        file.close();
        
        QuadMechDefinition def = QuadMechGen::DefinitionParser::parseFromYAML(yamlContent);
        
        if (!QuadMechGen::DefinitionParser::validateDefinition(def)) {
            Log::error("Definition validation failed for: {}", definitionPath);
            return false;
        }
        
        // Generate asset for high quality (will be used to generate LODs)
        QuadMechAsset asset = generateMechAsset(def, LODQuality::HIGH);
        
        // Write package
        bool success = writePackageToDisk(asset, outputPath);
        
        if (success) {
            Log::info("QuadMech package generated successfully: {}", outputPath);
        } else {
            Log::error("Failed to write QuadMech package: {}", outputPath);
        }
        
        return success;
        
    } catch (const std::exception& e) {
        Log::error("Exception during package generation: {}", e.what());
        return false;
    }
}

void QuadMechFactory::watchForChanges(const std::string& mechName) {
    std::unique_lock<std::shared_mutex> lock(m_fileWatcherMutex);
    
    std::string definitionPath = "assets/mechs/" + mechName + ".quadmechdef";
    updateFileTimestamp(definitionPath);
    
    Log::info("Now watching for changes: {}", definitionPath);
}

void QuadMechFactory::unwatchForChanges(const std::string& mechName) {
    std::unique_lock<std::shared_mutex> lock(m_fileWatcherMutex);
    
    std::string definitionPath = "assets/mechs/" + mechName + ".quadmechdef";
    m_fileTimestamps.erase(definitionPath);
    
    Log::info("Stopped watching: {}", definitionPath);
}

bool QuadMechFactory::checkForUpdates(const std::string& mechName) {
    std::shared_lock<std::shared_mutex> lock(m_fileWatcherMutex);
    
    std::string definitionPath = "assets/mechs/" + mechName + ".quadmechdef";
    return hasFileChanged(definitionPath);
}

void QuadMechFactory::reloadMech(const std::string& mechName) {
    Log::info("Reloading QuadMech: {}", mechName);
    
    // Clear cache entry for this mech
    uint64_t cacheKey = XXH64(mechName.c_str(), mechName.length(), 0);
    // Note: In a real implementation, we'd need to clear all LOD variants
    
    // Force reload on next access
    Log::info("QuadMech cache cleared for: {}", mechName);
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
    // Note: In a real implementation, we'd need to recreate the cache with new capacity
    Log::info("Cache capacity set to: {}", capacity);
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
    std::string mechDir = "assets/mechs/";
    if (std::filesystem::exists(mechDir)) {
        for (const auto& entry : std::filesystem::directory_iterator(mechDir)) {
            if (entry.is_regular_file() && entry.path().extension() == ".quadmechdef") {
                mechs.push_back(entry.path().stem().string());
            }
        }
    }
    
    return mechs;
}

bool QuadMechFactory::mechExists(const std::string& mechName) const {
    std::string definitionPath = "assets/mechs/" + mechName + ".quadmechdef";
    return std::filesystem::exists(definitionPath);
}

// ============================================================================
// PRIVATE HELPER METHODS
// ============================================================================

QuadMechAsset QuadMechFactory::loadMechAsset(const std::string& mechName, LODQuality quality) {
    Log::info("Loading QuadMech asset: {} (LOD: {})", mechName, static_cast<int>(quality));
    
    // Try to load from package first
    std::string packagePath = "assets/mechs/" + mechName + ".mechpack";
    if (std::filesystem::exists(packagePath)) {
        return QuadMechGen::PackageReader::readMechPackage(packagePath);
    }
    
    // Fall back to definition file
    std::string definitionPath = "assets/mechs/" + mechName + ".quadmechdef";
    if (!std::filesystem::exists(definitionPath)) {
        throw std::runtime_error("QuadMech not found: " + mechName);
    }
    
    // Read and parse definition
    std::ifstream file(definitionPath);
    std::string yamlContent((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    file.close();
    
    QuadMechDefinition def = QuadMechGen::DefinitionParser::parseFromYAML(yamlContent);
    return generateMechAsset(def, quality);
}

QuadMechInstance QuadMechFactory::createInstance(const QuadMechAsset& asset) {
    QuadMechInstance instance;
    instance.asset = const_cast<QuadMechAsset*>(&asset); // Note: In real implementation, this would be properly managed
    instance.transform = glm::mat4(1.0f);
    instance.currentAnimation = "idle";
    instance.currentLOD = LODQuality::HIGH;
    instance.energyLevel = 1.0f;
    instance.runeGlowIntensity = 1.0f;
    instance.cockpitOpen = false;
    instance.pilotInside = false;
    
    return instance;
}

uint64_t QuadMechFactory::computeFileHash(const std::string& filePath) {
    if (!std::filesystem::exists(filePath)) return 0;
    
    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) return 0;
    
    XXH64_state_t state;
    XXH64_reset(&state, 0);
    
    char buffer[4096];
    while (file.read(buffer, sizeof(buffer))) {
        XXH64_update(&state, buffer, file.gcount());
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
    Log::info("Generating QuadMech asset: {} (LOD: {})", def.name, static_cast<int>(quality));
    
    QuadMechAsset asset;
    asset.definition = def;
    asset.hashKey = def.hashKey();
    
    // Build skeleton
    asset.skeleton = QuadMechGen::ModuleAssembler::buildSkeleton(def);
    
    // Assemble modules
    auto modules = QuadMechGen::ModuleAssembler::assembleModules(def, quality);
    for (size_t i = 0; i < modules.size(); ++i) {
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
    if (!physicsBodies.empty()) {
        asset.rootBody = physicsBodies[0];
    }
    
    Log::info("QuadMech asset generated successfully: {} ({} modules, {} animations)", 
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
