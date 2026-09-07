#include "MiniJetFactory.hpp"
#include "core/Log.hpp"
#include "core/plugins/AdaptiveBusPlugin.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>

namespace MiniJetGen {

// MiniJetCache implementation
std::shared_ptr<MiniJetAsset> MiniJetCache::get(const std::string& name, size_t hash) {
    std::lock_guard<std::mutex> lock(m_mutex);
    
    auto it = m_cache.find(name);
    if (it != m_cache.end() && it->second.hash == hash) {
        it->second.lastAccess = std::chrono::steady_clock::now();
        return it->second.asset;
    }
    
    return nullptr;
}

void MiniJetCache::put(const std::string& name, std::shared_ptr<MiniJetAsset> asset, size_t hash) {
    std::lock_guard<std::mutex> lock(m_mutex);
    
    // Evict oldest if cache is full
    if (m_cache.size() >= MAX_CACHE_SIZE) {
        evictOldest();
    }
    
    CacheEntry entry;
    entry.asset = asset;
    entry.hash = hash;
    entry.lastAccess = std::chrono::steady_clock::now();
    
    m_cache[name] = entry;
}

void MiniJetCache::clear() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_cache.clear();
}

void MiniJetCache::evictOldest() {
    auto oldest = m_cache.begin();
    for (auto it = m_cache.begin(); it != m_cache.end(); ++it) {
        if (it->second.lastAccess < oldest->second.lastAccess) {
            oldest = it;
        }
    }
    
    if (oldest != m_cache.end()) {
        m_cache.erase(oldest);
    }
}

size_t MiniJetCache::size() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_cache.size();
}

// MiniJetFactory implementation
MiniJetFactory::MiniJetFactory() {
    m_cache = std::make_unique<MiniJetCache>();
}

MiniJetFactory::~MiniJetFactory() {
    shutdown();
}

void MiniJetFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    
    m_pool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized = true;
    
    Log::info("MiniJetFactory initialized with {} threads", num_threads);
}

void MiniJetFactory::shutdown() {
    if (!m_initialized) return;
    
    m_pool.reset();
    m_initialized = false;
    
    Log::info("MiniJetFactory shutdown complete");
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::load(const std::string& name, Quality quality) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    // Check cache first
    size_t hash = getAssetHash(name);
    if (auto cached = m_cache->get(name, hash)) {
        updateMetrics(0.0, std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), true);
        return cached;
    }
    
    // Load from package
    auto asset = PackageReader::readPackage(name);
    if (asset.definition.name.empty()) {
        Log::error("Failed to load MiniJet asset: {}", name);
        updateMetrics(0.0, std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), false);
        return nullptr;
    }
    
    // Cache the asset
    auto sharedAsset = std::make_shared<MiniJetAsset>(asset);
    m_cache->put(name, sharedAsset, hash);
    
    updateMetrics(0.0, std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), false);
    return sharedAsset;
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::generate(const std::string& definitionPath, Quality quality) {
    auto startTime = std::chrono::high_resolution_clock::now();
    
    // Parse definition
    auto definition = DefinitionParser::parseFromYAML(definitionPath);
    if (!DefinitionParser::validateDefinition(definition)) {
        Log::error("Failed to validate MiniJet definition: {}", definitionPath);
        updateMetrics(std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), 0.0, false);
        return nullptr;
    }
    
    // Generate asset
    auto asset = generateAsset(definition, quality);
    if (!asset) {
        Log::error("Failed to generate MiniJet asset from definition: {}", definitionPath);
        updateMetrics(std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), 0.0, false);
        return nullptr;
    }
    
    updateMetrics(std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(), 0.0, false);
    return asset;
}

bool MiniJetFactory::generatePackage(const std::string& name, const std::string& definitionPath) {
    auto asset = generate(definitionPath);
    if (!asset) {
        return false;
    }
    
    return PackageWriter::writePackage(name, *asset);
}

std::future<std::shared_ptr<MiniJetAsset>> MiniJetFactory::loadAsync(const std::string& name, Quality quality) {
    return m_pool->enqueue([this, name, quality]() {
        return load(name, quality);
    });
}

std::future<std::shared_ptr<MiniJetAsset>> MiniJetFactory::generateAsync(const std::string& definitionPath, Quality quality) {
    return m_pool->enqueue([this, definitionPath, quality]() {
        return generate(definitionPath, quality);
    });
}

std::future<bool> MiniJetFactory::generatePackageAsync(const std::string& name, const std::string& definitionPath) {
    return m_pool->enqueue([this, name, definitionPath]() {
        return generatePackage(name, definitionPath);
    });
}

void MiniJetFactory::clearCache() {
    m_cache->clear();
    Log::info("MiniJet cache cleared");
}

void MiniJetFactory::preload(const std::vector<std::string>& names) {
    for (const auto& name : names) {
        m_pool->enqueue([this, name]() {
            load(name);
        });
    }
    
    Log::info("Preloading {} MiniJet assets", names.size());
}

size_t MiniJetFactory::getCacheSize() const {
    return m_cache->size();
}

void MiniJetFactory::watchForChanges(const std::string& definitionPath) {
    updateFileTimestamps(definitionPath);
    Log::info("Watching for changes in: {}", definitionPath);
}

void MiniJetFactory::checkForUpdates() {
    for (const auto& [path, timestamp] : m_fileTimestamps) {
        if (hasFileChanged(path)) {
            Log::info("File changed detected: {}", path);
            
            // Extract asset name from path
            std::filesystem::path fsPath(path);
            std::string name = fsPath.stem().string();
            
            // Reload the asset
            reloadAsset(name);
            
            // Update timestamp
            updateFileTimestamps(path);
        }
    }
}

void MiniJetFactory::reloadAsset(const std::string& name) {
    // Remove from cache
    m_cache->clear(); // Simple approach - clear entire cache
    
    // Regenerate if we have the definition path
    for (const auto& [path, timestamp] : m_fileTimestamps) {
        std::filesystem::path fsPath(path);
        if (fsPath.stem().string() == name) {
            generatePackage(name, path);
            Log::info("Reloaded MiniJet asset: {}", name);
            break;
        }
    }
}

void MiniJetFactory::resetMetrics() {
    m_metrics = {};
    Log::info("MiniJetFactory metrics reset");
}

bool MiniJetFactory::validateDefinition(const std::string& definitionPath) {
    auto definition = DefinitionParser::parseFromYAML(definitionPath);
    return DefinitionParser::validateDefinition(definition);
}

std::vector<std::string> MiniJetFactory::getAvailableAssets() const {
    std::vector<std::string> assets;
    
    // Scan for .mjpack files
    std::filesystem::path assetsPath = "assets/minijets";
    if (std::filesystem::exists(assetsPath)) {
        for (const auto& entry : std::filesystem::directory_iterator(assetsPath)) {
            if (entry.path().extension() == ".mjpack") {
                assets.push_back(entry.path().stem().string());
            }
        }
    }
    
    return assets;
}

size_t MiniJetFactory::getAssetHash(const std::string& name) const {
    // Simple hash based on name and file timestamp
    std::string packagePath = "assets/minijets/" + name + ".mjpack/metadata.json";
    
    if (std::filesystem::exists(packagePath)) {
        auto timestamp = std::filesystem::last_write_time(packagePath);
        auto time_t = std::chrono::duration_cast<std::chrono::seconds>(timestamp.time_since_epoch()).count();
        return std::hash<std::string>{}(name) ^ std::hash<time_t>{}(time_t);
    }
    
    return std::hash<std::string>{}(name);
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::generateAsset(const MiniJetDefinition& def, Quality quality) {
    Log::info("Generating MiniJet asset: {}", def.name);
    
    auto asset = std::make_shared<MiniJetAsset>();
    asset->definition = def;
    
    // Step 1: Assemble modules
    auto assembly = ModuleAssembler::assembleModules(def);
    
    // Step 2: Weld module seams
    ModuleAssembler::weldModuleSeams(assembly, def);
    
    // Step 3: Bake skin weights
    ModuleAssembler::bakeSkinWeights(assembly, def);
    
    // Step 4: Synthesize Magitech materials
    auto materials = MaterialSynthesizer::synthesizeMagitechMaterials(def);
    
    // Step 5: Process animations
    auto animations = AnimationProcessor::processAnimations(def, assembly.skeleton);
    
    // Step 6: Build physics rig
    auto physics = PhysicsRigBuilder::buildPhysicsRig(def);
    
    // Step 7: Generate LODs
    auto lods = LODGenerator::generateLODs(def, assembly);
    
    // Step 8: Assemble final asset
    asset->skeleton = assembly.skeleton;
    asset->animations = animations.animations;
    
    // Combine module assets with LODs
    for (const auto& moduleDef : def.modules) {
        ModuleAssets moduleAssets;
        
        // Copy LOD meshes and materials
        moduleAssets.lodMeshes = lods.lodMeshes[moduleDef.id];
        moduleAssets.lodMaterials = lods.lodMaterials[moduleDef.id];
        
        // Add thruster if this module has one
        auto thrusterIt = physics.thrusters.find(moduleDef.id);
        if (thrusterIt != physics.thrusters.end()) {
            moduleAssets.thruster = thrusterIt->second;
        }
        
        // Add physics body if this module has one
        auto bodyIt = physics.bodies.find(moduleDef.id);
        if (bodyIt != physics.bodies.end()) {
            moduleAssets.physicsBody = bodyIt->second;
        }
        
        asset->modules[moduleDef.id] = moduleAssets;
    }
    
    Log::info("MiniJet asset generation completed: {}", def.name);
    return asset;
}

void MiniJetFactory::updateFileTimestamps(const std::string& definitionPath) {
    if (std::filesystem::exists(definitionPath)) {
        auto timestamp = std::filesystem::last_write_time(definitionPath);
        m_fileTimestamps[definitionPath] = timestamp;
        
        // Also watch module files
        auto definition = DefinitionParser::parseFromYAML(definitionPath);
        for (const auto& module : definition.modules) {
            if (std::filesystem::exists(module.meshPath)) {
                auto moduleTimestamp = std::filesystem::last_write_time(module.meshPath);
                m_fileTimestamps[module.meshPath] = moduleTimestamp;
            }
        }
    }
}

bool MiniJetFactory::hasFileChanged(const std::string& path) {
    if (!std::filesystem::exists(path)) {
        return false;
    }
    
    auto currentTimestamp = std::filesystem::last_write_time(path);
    auto it = m_fileTimestamps.find(path);
    
    if (it == m_fileTimestamps.end()) {
        m_fileTimestamps[path] = currentTimestamp;
        return false;
    }
    
    if (currentTimestamp != it->second) {
        it->second = currentTimestamp;
        return true;
    }
    
    return false;
}

void MiniJetFactory::updateMetrics(double generationTime, double loadTime, bool cacheHit) {
    if (cacheHit) {
        m_metrics.cacheHits++;
    } else {
        m_metrics.cacheMisses++;
        m_metrics.totalAssetsGenerated++;
    }
    
    if (generationTime > 0) {
        m_metrics.averageGenerationTime = (m_metrics.averageGenerationTime + generationTime) / 2.0;
    }
    
    if (loadTime > 0) {
        m_metrics.averageLoadTime = (m_metrics.averageLoadTime + loadTime) / 2.0;
    }
}

// MiniJetLoader implementation
MiniJetLoader::MiniJetLoader(std::shared_ptr<MiniJetFactory> factory) : m_factory(factory) {
}

MiniJetInstance MiniJetLoader::createInstance(const std::string& name, Quality quality) {
    auto asset = m_factory->load(name, quality);
    if (!asset) {
        Log::error("Failed to create MiniJet instance: {}", name);
        return MiniJetInstance{};
    }
    
    return createInstance(asset);
}

MiniJetInstance MiniJetLoader::createInstance(std::shared_ptr<MiniJetAsset> asset) {
    MiniJetInstance instance;
    instance.asset = asset;
    instance.currentLOD = Quality::High;
    instance.currentAnimation = "hover"; // Default animation
    
    // Initialize flight state
    instance.throttle = 0.0f;
    instance.altitude = 0.0f;
    instance.speed = 0.0f;
    instance.isFlying = false;
    instance.isLanding = false;
    instance.isTakingOff = false;
    instance.flightTime = 0.0f;
    
    // Initialize Magitech effects
    instance.runeGlowIntensity = 1.0f;
    instance.engineHeatLevel = 0.0f;
    instance.energyTrailLength = 0.0f;
    
    return instance;
}

void MiniJetLoader::updateInstance(MiniJetInstance& instance, float deltaTime) {
    if (!instance.asset) return;
    
    // Update animation time
    instance.animationTime += deltaTime;
    
    // Update flight time
    instance.flightTime += deltaTime;
    
    // Update Magitech effects
    instance.runeGlowIntensity = 1.0f + 0.2f * std::sin(instance.flightTime * 2.0f);
    instance.engineHeatLevel = std::min(instance.engineHeatLevel + deltaTime * 0.1f, 1.0f);
    instance.energyTrailLength = std::min(instance.energyTrailLength + deltaTime * 5.0f, 50.0f);
}

void MiniJetLoader::setAnimation(MiniJetInstance& instance, const std::string& animationName) {
    if (!instance.asset) return;
    
    if (instance.asset->animations.find(animationName) != instance.asset->animations.end()) {
        instance.currentAnimation = animationName;
        instance.animationTime = 0.0f;
    }
}

void MiniJetLoader::setLOD(MiniJetInstance& instance, Quality quality) {
    instance.currentLOD = quality;
}

void MiniJetLoader::setThrottle(MiniJetInstance& instance, float throttle) {
    instance.throttle = std::clamp(throttle, 0.0f, 1.0f);
}

void MiniJetLoader::setControlInput(MiniJetInstance& instance, const glm::vec3& input) {
    // Apply control input to flight physics
    // This would integrate with the actual flight simulation
}

void MiniJetLoader::updateFlightPhysics(MiniJetInstance& instance, float deltaTime) {
    if (!instance.asset) return;
    
    const auto& flightParams = instance.asset->definition.flightParameters;
    
    // Update speed based on throttle
    float targetSpeed = instance.throttle * flightParams.maxSpeed;
    instance.speed = glm::mix(instance.speed, targetSpeed, deltaTime * 2.0f);
    
    // Update altitude based on speed and lift
    if (instance.speed > 50.0f) {
        instance.altitude += instance.speed * deltaTime * 0.1f;
    }
    
    // Update flight state
    if (instance.speed > 100.0f && !instance.isFlying) {
        instance.isFlying = true;
        instance.isTakingOff = false;
    }
    
    if (instance.speed < 50.0f && instance.isFlying) {
        instance.isFlying = false;
        instance.isLanding = true;
    }
}

void MiniJetLoader::setRuneGlowIntensity(MiniJetInstance& instance, float intensity) {
    instance.runeGlowIntensity = std::clamp(intensity, 0.0f, 2.0f);
}

void MiniJetLoader::setEngineHeatLevel(MiniJetInstance& instance, float heat) {
    instance.engineHeatLevel = std::clamp(heat, 0.0f, 1.0f);
}

void MiniJetLoader::setEnergyTrailLength(MiniJetInstance& instance, float length) {
    instance.energyTrailLength = std::clamp(length, 0.0f, 100.0f);
}

// MiniJetEditor implementation
MiniJetEditor::MiniJetEditor(std::shared_ptr<MiniJetFactory> factory) 
    : m_factory(factory), m_loader(std::make_shared<MiniJetLoader>(factory)) {
}

void MiniJetEditor::showEditorPanel(const std::string& assetName) {
    // This would integrate with ImGui to show the main editor panel
    // Implementation would depend on the specific UI framework being used
}

void MiniJetEditor::showModulePanel(const std::string& assetName) {
    // Show module hierarchy and properties
}

void MiniJetEditor::showMaterialPanel(const std::string& assetName) {
    // Show material properties and Magitech effect controls
}

void MiniJetEditor::showAnimationPanel(const std::string& assetName) {
    // Show animation timeline and controls
}

void MiniJetEditor::showPhysicsPanel(const std::string& assetName) {
    // Show physics debug information
}

void MiniJetEditor::showFlightPanel(const std::string& assetName) {
    // Show flight controls and parameters
}

MiniJetInstance& MiniJetEditor::getPreviewInstance(const std::string& assetName) {
    // Get or create preview instance
    static std::unordered_map<std::string, MiniJetInstance> previewInstances;
    
    auto it = previewInstances.find(assetName);
    if (it == previewInstances.end()) {
        previewInstances[assetName] = m_loader->createInstance(assetName);
    }
    
    return previewInstances[assetName];
}

void MiniJetEditor::updatePreview(const std::string& assetName, float deltaTime) {
    auto& instance = getPreviewInstance(assetName);
    m_loader->updateInstance(instance, deltaTime);
}

void MiniJetEditor::rebuildAsset(const std::string& assetName) {
    m_factory->reloadAsset(assetName);
}

void MiniJetEditor::exportAsset(const std::string& assetName, const std::string& outputPath) {
    // Export asset to the specified path
}

void MiniJetEditor::importAsset(const std::string& inputPath) {
    // Import asset from the specified path
}

MiniJetEditorState& MiniJetEditor::getEditorState(const std::string& assetName) {
    auto it = m_editorStates.find(assetName);
    if (it == m_editorStates.end()) {
        m_editorStates[assetName] = MiniJetEditorState{};
    }
    return m_editorStates[assetName];
}

void MiniJetEditor::saveEditorState(const std::string& assetName) {
    // Save editor state to file
}

void MiniJetEditor::loadEditorState(const std::string& assetName) {
    // Load editor state from file
}

void MiniJetEditor::renderModuleHierarchy(const std::string& assetName) {
    // Render module hierarchy tree
}

void MiniJetEditor::renderMaterialProperties(const std::string& assetName) {
    // Render material property controls
}

void MiniJetEditor::renderAnimationTimeline(const std::string& assetName) {
    // Render animation timeline
}

void MiniJetEditor::renderPhysicsDebug(const std::string& assetName) {
    // Render physics debug visualization
}

void MiniJetEditor::renderFlightControls(const std::string& assetName) {
    // Render flight control interface
}

} // namespace MiniJetGen 
