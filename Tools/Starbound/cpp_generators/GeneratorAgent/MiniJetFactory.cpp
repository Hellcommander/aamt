#include "MiniJetFactory.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/Log.hpp"
#include <imgui.h>
#include <glm/gtc/quaternion.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>

namespace MiniJetGen {

using MagiTech::Log;

namespace {

constexpr const char* kQualityLabels[] = {"Ultra", "High", "Medium", "Low"};

std::string editorStatePath(const std::string& assetName) {
    return "assets/minijets/editor/" + assetName + ".json";
}

nlohmann::json vec3Json(const glm::vec3& v) { return nlohmann::json::array({v.x, v.y, v.z}); }

glm::vec3 vec3From(const nlohmann::json& j, const glm::vec3& fallback) {
    if (!j.is_array() || j.size() < 3) return fallback;
    return {j[0].get<float>(), j[1].get<float>(), j[2].get<float>()};
}

// ImGui calls are only valid while the host application has an ImGui context
bool imguiReady() { return ImGui::GetCurrentContext() != nullptr; }

} // namespace

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
    if (m_cache.size() >= MAX_CACHE_SIZE && m_cache.find(name) == m_cache.end()) {
        evictOldest();
    }

    CacheEntry entry;
    entry.asset = std::move(asset);
    entry.hash = hash;
    entry.lastAccess = std::chrono::steady_clock::now();

    m_cache[name] = entry;
}

void MiniJetCache::clear() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_cache.clear();
}

void MiniJetCache::erase(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_cache.erase(name);
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
    m_pool = std::make_unique<GeneratorTaskPool>();   // not started: runs tasks inline until initialize()
}

MiniJetFactory::~MiniJetFactory() {
    shutdown();
}

void MiniJetFactory::initialize(size_t num_threads) {
    if (m_initialized) return;

    m_pool->start(num_threads);
    m_initialized = true;

    Log::info("MiniJet", "MiniJetFactory initialized with {} threads", num_threads);
}

void MiniJetFactory::shutdown() {
    if (!m_initialized) return;

    m_pool->stop();   // finishes queued work; later tasks run inline
    m_initialized = false;

    Log::info("MiniJetFactory shutdown complete");
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::load(const std::string& name, Quality quality) {
    auto startTime = std::chrono::high_resolution_clock::now();
    auto elapsed = [&] { return std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(); };

    // Check cache first
    size_t hash = getAssetHash(name);
    if (auto cached = m_cache->get(name, hash)) {
        updateMetrics(0.0, elapsed(), true);
        return cached;
    }

    // Load from package
    auto asset = PackageReader::readPackage(name);
    if (asset.definition.name.empty()) {
        Log::error("MiniJet", "Failed to load MiniJet asset: {}", name);
        updateMetrics(0.0, elapsed(), false);
        return nullptr;
    }
    Log::debug("MiniJet", "Loaded {} (requested LOD {}); all LOD levels are resident", name,
               kQualityLabels[std::clamp(static_cast<int>(quality), 0, 3)]);

    // Cache the asset
    auto sharedAsset = std::make_shared<MiniJetAsset>(std::move(asset));
    m_cache->put(name, sharedAsset, hash);

    updateMetrics(0.0, elapsed(), false);
    return sharedAsset;
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::generate(const std::string& definitionPath, Quality quality) {
    auto startTime = std::chrono::high_resolution_clock::now();
    auto elapsed = [&] { return std::chrono::duration<double>(std::chrono::high_resolution_clock::now() - startTime).count(); };

    // Parse definition
    auto definition = DefinitionParser::parseFromFile(definitionPath);
    if (!DefinitionParser::validateDefinition(definition)) {
        Log::error("MiniJet", "Failed to validate MiniJet definition: {}", definitionPath);
        updateMetrics(elapsed(), 0.0, false);
        return nullptr;
    }

    // Generate asset
    auto asset = generateAsset(definition, quality);
    if (!asset) {
        Log::error("MiniJet", "Failed to generate MiniJet asset from definition: {}", definitionPath);
        updateMetrics(elapsed(), 0.0, false);
        return nullptr;
    }

    {
        std::lock_guard<std::mutex> lock(m_watchMutex);
        m_definitionPaths[definition.name] = definitionPath;
    }
    updateMetrics(elapsed(), 0.0, false);
    return asset;
}

bool MiniJetFactory::generatePackage(const std::string& name, const std::string& definitionPath) {
    auto asset = generate(definitionPath);
    if (!asset) {
        return false;
    }

    {
        std::lock_guard<std::mutex> lock(m_watchMutex);
        m_definitionPaths[name] = definitionPath;
    }
    const bool ok = PackageWriter::writePackage(name, *asset);
    if (ok) m_cache->erase(name);   // the package changed: next load re-reads it
    return ok;
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
        // fire-and-forget: the loaded asset lands in the cache
        (void)m_pool->enqueue([this, name]() {
            load(name);
        });
    }

    Log::info("MiniJet", "Preloading {} MiniJet assets", names.size());
}

size_t MiniJetFactory::getCacheSize() const {
    return m_cache->size();
}

void MiniJetFactory::watchForChanges(const std::string& definitionPath) {
    updateFileTimestamps(definitionPath);
    {
        std::lock_guard<std::mutex> lock(m_watchMutex);
        m_definitionPaths[std::filesystem::path(definitionPath).stem().string()] = definitionPath;
    }
    Log::info("MiniJet", "Watching for changes in: {}", definitionPath);
}

void MiniJetFactory::checkForUpdates() {
    // Collect changed definitions first (reloading touches the watch tables)
    std::vector<std::string> paths;
    std::unordered_map<std::string, std::string> definitionPaths;
    {
        std::lock_guard<std::mutex> lock(m_watchMutex);
        for (const auto& [path, timestamp] : m_fileTimestamps) paths.push_back(path);
        definitionPaths = m_definitionPaths;
    }

    std::vector<std::string> changedAssets;
    for (const auto& path : paths) {
        if (!hasFileChanged(path)) continue;
        Log::info("MiniJet", "File changed detected: {}", path);
        for (const auto& [name, defPath] : definitionPaths) {
            bool affected = defPath == path;
            if (!affected) {
                // module meshes belong to the definition that references them
                const auto def = DefinitionParser::parseFromFile(defPath);
                for (const auto& module : def.modules) affected = affected || module.meshPath == path;
            }
            if (affected && std::find(changedAssets.begin(), changedAssets.end(), name) == changedAssets.end()) {
                changedAssets.push_back(name);
            }
        }
    }

    for (const auto& name : changedAssets) {
        reloadAsset(name);
    }
}

void MiniJetFactory::reloadAsset(const std::string& name) {
    // Remove from cache
    m_cache->erase(name);

    // Regenerate from the definition this asset was built from
    std::string definitionPath;
    {
        std::lock_guard<std::mutex> lock(m_watchMutex);
        auto it = m_definitionPaths.find(name);
        if (it != m_definitionPaths.end()) definitionPath = it->second;
    }
    if (definitionPath.empty()) {
        Log::warn("MiniJet", "No definition known for MiniJet asset: {}", name);
        return;
    }
    if (generatePackage(name, definitionPath)) {
        updateFileTimestamps(definitionPath);
        Log::info("MiniJet", "Reloaded MiniJet asset: {}", name);
    }
}

MiniJetFactory::Metrics MiniJetFactory::getMetrics() const {
    std::lock_guard<std::mutex> lock(m_metricsMutex);
    return m_metrics;
}

void MiniJetFactory::resetMetrics() {
    {
        std::lock_guard<std::mutex> lock(m_metricsMutex);
        m_metrics = {};
    }
    Log::info("MiniJetFactory metrics reset");
}

bool MiniJetFactory::validateDefinition(const std::string& definitionPath) {
    auto definition = DefinitionParser::parseFromFile(definitionPath);
    return DefinitionParser::validateDefinition(definition);
}

std::vector<std::string> MiniJetFactory::getAvailableAssets() const {
    std::vector<std::string> assets;

    // Scan for .mjpack package directories
    std::error_code ec;
    std::filesystem::path assetsPath = "assets/minijets";
    if (std::filesystem::exists(assetsPath, ec)) {
        for (const auto& entry : std::filesystem::directory_iterator(assetsPath, ec)) {
            if (entry.path().extension() == ".mjpack") {
                assets.push_back(entry.path().stem().string());
            }
        }
    }

    return assets;
}

size_t MiniJetFactory::getAssetHash(const std::string& name) const {
    // Name combined with the package's metadata timestamp: a rewritten package gets a new hash
    std::string packagePath = "assets/minijets/" + name + ".mjpack/metadata.json";

    std::error_code ec;
    if (std::filesystem::exists(packagePath, ec)) {
        auto timestamp = std::filesystem::last_write_time(packagePath, ec);
        const long long ticks = static_cast<long long>(timestamp.time_since_epoch().count());
        size_t seed = std::hash<std::string>{}(name);
        seed ^= std::hash<long long>{}(ticks) + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
        return seed;
    }

    return std::hash<std::string>{}(name);
}

std::shared_ptr<MiniJetAsset> MiniJetFactory::generateAsset(const MiniJetDefinition& def, Quality quality) {
    Log::info("MiniJet", "Generating MiniJet asset: {}", def.name);

    auto asset = std::make_shared<MiniJetAsset>();
    asset->definition = def;

    // Step 1: Assemble modules
    auto assembly = ModuleAssembler::assembleModules(def);
    if (assembly.meshes.empty()) {
        Log::error("MiniJet", "No module meshes could be loaded for {}", def.name);
        return nullptr;
    }

    // Step 2: Weld module seams
    ModuleAssembler::weldModuleSeams(assembly, def);

    // Step 3: Bake skin weights
    ModuleAssembler::bakeSkinWeights(assembly, def);

    // Step 4: Synthesize Magitech materials and assign them by module role
    auto materials = MaterialSynthesizer::synthesizeMagitechMaterials(def);
    for (const auto& moduleDef : def.modules) {
        const char* role = nullptr;
        switch (moduleDef.type) {
            case ModuleType::Thruster_Main:
            case ModuleType::Thruster_Aux: role = "engineHeat"; break;
            case ModuleType::Cockpit: role = "canopy"; break;
            case ModuleType::Energy_Core: role = "runeGlow"; break;
            default: break;
        }
        if (role && assembly.materials.count(moduleDef.id)) {
            assembly.materials[moduleDef.id] = materials.materials[role];
        }
    }

    // Step 5: Process animations (lower requested qualities get stronger clip optimization)
    auto animations = AnimationProcessor::processAnimations(def, assembly.skeleton);
    if (quality == Quality::Medium || quality == Quality::Low) {
        for (auto& [id, anim] : animations.animations) AnimationProcessor::optimizeAnimation(anim, quality);
    }

    // Step 6: Build physics rig
    auto physics = PhysicsRigBuilder::buildPhysicsRig(def);

    // Step 7: Generate LODs
    auto lods = LODGenerator::generateLODs(def, assembly);

    // Step 8: Assemble final asset
    asset->skeleton = assembly.skeleton;
    asset->animations = animations.animations;
    asset->physicsBodies = physics.bodies;

    // Combine module assets with LODs
    for (const auto& moduleDef : def.modules) {
        ModuleAssets moduleAssets;

        // Copy LOD meshes and materials
        auto meshIt = lods.lodMeshes.find(moduleDef.id);
        if (meshIt != lods.lodMeshes.end()) moduleAssets.lodMeshes = meshIt->second;
        auto matIt = lods.lodMaterials.find(moduleDef.id);
        if (matIt != lods.lodMaterials.end()) moduleAssets.lodMaterials = matIt->second;

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

    Log::info("MiniJet", "MiniJet asset generation completed: {}", def.name);
    return asset;
}

void MiniJetFactory::updateFileTimestamps(const std::string& definitionPath) {
    std::error_code ec;
    if (!std::filesystem::exists(definitionPath, ec)) return;

    auto timestamp = std::filesystem::last_write_time(definitionPath, ec);
    // Also watch module files
    auto definition = DefinitionParser::parseFromFile(definitionPath);

    std::lock_guard<std::mutex> lock(m_watchMutex);
    m_fileTimestamps[definitionPath] = timestamp;
    for (const auto& module : definition.modules) {
        if (std::filesystem::exists(module.meshPath, ec)) {
            m_fileTimestamps[module.meshPath] = std::filesystem::last_write_time(module.meshPath, ec);
        }
    }
}

bool MiniJetFactory::hasFileChanged(const std::string& path) {
    std::error_code ec;
    if (!std::filesystem::exists(path, ec)) {
        return false;
    }

    auto currentTimestamp = std::filesystem::last_write_time(path, ec);
    std::lock_guard<std::mutex> lock(m_watchMutex);
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
    std::lock_guard<std::mutex> lock(m_metricsMutex);
    if (cacheHit) {
        m_metrics.cacheHits++;
    } else {
        m_metrics.cacheMisses++;
        if (generationTime > 0) m_metrics.totalAssetsGenerated++;
    }

    // Running means
    if (generationTime > 0) {
        m_metrics.generationSamples++;
        m_metrics.averageGenerationTime += (generationTime - m_metrics.averageGenerationTime) / static_cast<double>(m_metrics.generationSamples);
    }

    if (loadTime > 0) {
        m_metrics.loadSamples++;
        m_metrics.averageLoadTime += (loadTime - m_metrics.averageLoadTime) / static_cast<double>(m_metrics.loadSamples);
    }
}

// MiniJetLoader implementation
MiniJetLoader::MiniJetLoader(std::shared_ptr<MiniJetFactory> factory) : m_factory(std::move(factory)) {
}

MiniJetInstance MiniJetLoader::createInstance(const std::string& name, Quality quality) {
    auto asset = m_factory->load(name, quality);
    if (!asset) {
        Log::error("MiniJet", "Failed to create MiniJet instance: {}", name);
        return MiniJetInstance{};
    }

    MiniJetInstance instance = createInstance(asset);
    instance.currentLOD = quality;
    return instance;
}

MiniJetInstance MiniJetLoader::createInstance(std::shared_ptr<MiniJetAsset> asset) {
    MiniJetInstance instance;
    instance.asset = asset;
    instance.currentLOD = Quality::High;
    // Default animation: "hover" when the asset has it, else its first clip
    instance.currentAnimation = "hover";
    if (asset && !asset->animations.empty() && !asset->animations.count("hover")) {
        instance.currentAnimation = asset->animations.begin()->first;
    }

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

    // Update animation time (looping clips wrap, others clamp)
    instance.animationTime += deltaTime;
    auto animIt = instance.asset->animations.find(instance.currentAnimation);
    if (animIt != instance.asset->animations.end() && animIt->second.duration > 0.0f) {
        bool loop = true;
        for (const auto& def : instance.asset->definition.animations)
            if (def.id == instance.currentAnimation) loop = def.loop;
        instance.animationTime = loop ? std::fmod(instance.animationTime, animIt->second.duration)
                                      : std::min(instance.animationTime, animIt->second.duration);
    }

    // Update flight time
    instance.flightTime += deltaTime;

    // Update Magitech effects: rune pulse at the material's rate, heat/trail follow throttle and speed
    const auto& materials = instance.asset->definition.magitechMaterials;
    instance.runeGlowIntensity = materials.runeGlow.glowIntensity *
                                 (1.0f + 0.2f * std::sin(instance.flightTime * 6.2831853f * materials.runeGlow.pulseRate));
    const float targetHeat = instance.throttle;
    instance.engineHeatLevel += (targetHeat - instance.engineHeatLevel) * std::min(1.0f, deltaTime * 0.5f);
    const float speedRatio = std::clamp(instance.speed / std::max(1.0f, instance.asset->definition.flightParameters.maxSpeed), 0.0f, 1.0f);
    const float targetTrail = materials.energyTrail.trailLength * speedRatio;
    instance.energyTrailLength += (targetTrail - instance.energyTrailLength) * std::min(1.0f, deltaTime * 2.0f);
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
    // pitch / yaw / roll stick input, consumed by updateFlightPhysics
    instance.controlInput = glm::clamp(input, glm::vec3(-1.0f), glm::vec3(1.0f));
}

void MiniJetLoader::updateFlightPhysics(MiniJetInstance& instance, float deltaTime) {
    if (!instance.asset || deltaTime <= 0.0f) return;

    const auto& flightParams = instance.asset->definition.flightParameters;

    // Speed follows throttle, reduced by drag
    float targetSpeed = instance.throttle * flightParams.maxSpeed;
    instance.speed = glm::mix(instance.speed, targetSpeed, std::min(1.0f, deltaTime * 2.0f));
    instance.speed = std::max(0.0f, instance.speed - flightParams.dragCoefficient * 0.01f * instance.speed * deltaTime);

    // Control surfaces are only effective with airflow
    const float authority = std::clamp(instance.speed / std::max(1.0f, flightParams.maxSpeed * 0.3f), 0.0f, 1.0f);
    const glm::vec3 rates = instance.controlInput * glm::radians(flightParams.turnRate) * authority * deltaTime;
    const glm::quat pitch = glm::angleAxis(rates.x, glm::vec3(1, 0, 0));
    const glm::quat yaw = glm::angleAxis(rates.y, glm::vec3(0, 1, 0));
    const glm::quat roll = glm::angleAxis(rates.z, glm::vec3(0, 0, 1));
    instance.rotation = glm::normalize(instance.rotation * yaw * pitch * roll);

    // Move along the nose; lift above take-off speed, limited climb rate and ceiling
    const glm::vec3 forward = instance.rotation * glm::vec3(0, 0, -1);
    instance.velocity = forward * instance.speed;
    if (instance.speed > 50.0f) {
        const float lift = flightParams.liftCoefficient * (instance.speed - 50.0f) * 0.1f;
        instance.velocity.y += std::min(lift, flightParams.climbRate);
    } else if (instance.position.y > 0.0f) {
        instance.velocity.y -= 9.81f;   // not enough airspeed: sink
    }
    instance.position += instance.velocity * deltaTime;
    instance.position.y = std::clamp(instance.position.y, 0.0f, flightParams.maxAltitude);
    instance.altitude = instance.position.y;

    // Update flight state
    if (instance.speed > 100.0f && !instance.isFlying) {
        instance.isFlying = true;
        instance.isTakingOff = false;
        instance.isLanding = false;
    } else if (instance.throttle > 0.0f && !instance.isFlying) {
        instance.isTakingOff = true;
    }

    if (instance.speed < 50.0f && instance.isFlying) {
        instance.isFlying = false;
        instance.isLanding = true;
    }
    if (instance.isLanding && instance.altitude <= 0.0f) {
        instance.isLanding = false;
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

// MiniJetEditor implementation (ImGui panels; no-ops when no ImGui context is active)
MiniJetEditor::MiniJetEditor(std::shared_ptr<MiniJetFactory> factory)
    : m_factory(factory), m_loader(std::make_shared<MiniJetLoader>(factory)) {
}

void MiniJetEditor::showEditorPanel(const std::string& assetName) {
    if (!imguiReady()) return;
    const std::string title = "MiniJet Editor - " + assetName;
    if (ImGui::Begin(title.c_str())) {
        auto& state = getEditorState(assetName);
        int lod = static_cast<int>(state.previewLOD);
        if (ImGui::Combo("Preview LOD", &lod, kQualityLabels, 4)) {
            state.previewLOD = static_cast<Quality>(lod);
            m_loader->setLOD(getPreviewInstance(assetName), state.previewLOD);
        }
        ImGui::Checkbox("Show physics", &state.showPhysics);
        ImGui::SameLine();
        ImGui::Checkbox("Show thrusters", &state.showThrusters);
        ImGui::SameLine();
        ImGui::Checkbox("Show Magitech effects", &state.showMagitechEffects);
        if (ImGui::Button("Rebuild")) rebuildAsset(assetName);
        ImGui::SameLine();
        if (ImGui::Button("Save state")) saveEditorState(assetName);
        ImGui::SameLine();
        if (ImGui::Button("Load state")) loadEditorState(assetName);
        ImGui::Separator();
        renderModuleHierarchy(assetName);
        renderMaterialProperties(assetName);
        renderAnimationTimeline(assetName);
        if (state.showPhysics) renderPhysicsDebug(assetName);
        renderFlightControls(assetName);
    }
    ImGui::End();
}

void MiniJetEditor::showModulePanel(const std::string& assetName) {
    if (!imguiReady()) return;
    if (ImGui::Begin(("Modules - " + assetName).c_str())) renderModuleHierarchy(assetName);
    ImGui::End();
}

void MiniJetEditor::showMaterialPanel(const std::string& assetName) {
    if (!imguiReady()) return;
    if (ImGui::Begin(("Materials - " + assetName).c_str())) renderMaterialProperties(assetName);
    ImGui::End();
}

void MiniJetEditor::showAnimationPanel(const std::string& assetName) {
    if (!imguiReady()) return;
    if (ImGui::Begin(("Animation - " + assetName).c_str())) renderAnimationTimeline(assetName);
    ImGui::End();
}

void MiniJetEditor::showPhysicsPanel(const std::string& assetName) {
    if (!imguiReady()) return;
    if (ImGui::Begin(("Physics - " + assetName).c_str())) renderPhysicsDebug(assetName);
    ImGui::End();
}

void MiniJetEditor::showFlightPanel(const std::string& assetName) {
    if (!imguiReady()) return;
    if (ImGui::Begin(("Flight - " + assetName).c_str())) renderFlightControls(assetName);
    ImGui::End();
}

MiniJetInstance& MiniJetEditor::getPreviewInstance(const std::string& assetName) {
    // Get or create preview instance
    static std::unordered_map<std::string, MiniJetInstance> previewInstances;

    auto it = previewInstances.find(assetName);
    if (it == previewInstances.end()) {
        it = previewInstances.emplace(assetName, m_loader->createInstance(assetName)).first;
    }

    return it->second;
}

void MiniJetEditor::updatePreview(const std::string& assetName, float deltaTime) {
    auto& instance = getPreviewInstance(assetName);
    auto& state = getEditorState(assetName);
    state.previewTime += deltaTime;
    m_loader->updateFlightPhysics(instance, deltaTime);
    m_loader->updateInstance(instance, deltaTime);
    if (state.showMagitechEffects) {
        instance.runeGlowIntensity *= state.runeGlowIntensity;
    }
}

void MiniJetEditor::rebuildAsset(const std::string& assetName) {
    m_factory->reloadAsset(assetName);
    // refresh the preview with the rebuilt asset
    getPreviewInstance(assetName) = m_loader->createInstance(assetName, getEditorState(assetName).previewLOD);
}

void MiniJetEditor::exportAsset(const std::string& assetName, const std::string& outputPath) {
    auto asset = m_factory->load(assetName);
    if (!asset) {
        Log::error("MiniJet", "Cannot export unknown MiniJet asset: {}", assetName);
        return;
    }
    if (PackageWriter::writePackageTo(outputPath, *asset)) {
        Log::info("MiniJet", "Exported {} to {}", assetName, outputPath);
    }
}

void MiniJetEditor::importAsset(const std::string& inputPath) {
    MiniJetAsset asset = PackageReader::readPackageFrom(inputPath);
    if (asset.definition.name.empty()) {
        Log::error("MiniJet", "Cannot import MiniJet package: {}", inputPath);
        return;
    }
    const std::string name = std::filesystem::path(inputPath).stem().string();
    if (PackageWriter::writePackage(name, asset)) {
        m_factory->load(name);   // refresh cache with the imported package
        Log::info("MiniJet", "Imported MiniJet package {} as {}", inputPath, name);
    }
}

MiniJetEditorState& MiniJetEditor::getEditorState(const std::string& assetName) {
    auto it = m_editorStates.find(assetName);
    if (it == m_editorStates.end()) {
        it = m_editorStates.emplace(assetName, MiniJetEditorState{}).first;
    }
    return it->second;
}

void MiniJetEditor::saveEditorState(const std::string& assetName) {
    const auto& s = getEditorState(assetName);
    nlohmann::json j = {
        {"selectedModule", s.selectedModule}, {"selectedAnimation", s.selectedAnimation},
        {"previewLOD", static_cast<int>(s.previewLOD)}, {"previewTime", s.previewTime},
        {"showPhysics", s.showPhysics}, {"showThrusters", s.showThrusters},
        {"showMagitechEffects", s.showMagitechEffects}, {"runeGlowColor", vec3Json(s.runeGlowColor)},
        {"runeGlowIntensity", s.runeGlowIntensity}, {"engineHeatDistortion", s.engineHeatDistortion},
        {"energyTrailOpacity", s.energyTrailOpacity}, {"maxSpeed", s.maxSpeed}, {"maxAltitude", s.maxAltitude},
        {"thrustForce", s.thrustForce}, {"moduleOffset", vec3Json(s.moduleOffset)},
        {"moduleScale", vec3Json(s.moduleScale)},
        {"moduleRotation", {s.moduleRotation.w, s.moduleRotation.x, s.moduleRotation.y, s.moduleRotation.z}}};
    const std::string path = editorStatePath(assetName);
    std::error_code ec;
    std::filesystem::create_directories(std::filesystem::path(path).parent_path(), ec);
    std::ofstream file(path);
    if (!file.is_open()) {
        Log::error("MiniJet", "Cannot save editor state: {}", path);
        return;
    }
    file << j.dump(2);
}

void MiniJetEditor::loadEditorState(const std::string& assetName) {
    const std::string path = editorStatePath(assetName);
    std::ifstream file(path);
    if (!file.is_open()) return;
    nlohmann::json j = nlohmann::json::parse(file, nullptr, false);
    if (j.is_discarded() || !j.is_object()) {
        Log::error("MiniJet", "Invalid editor state file: {}", path);
        return;
    }
    auto& s = getEditorState(assetName);
    s.selectedModule = j.value("selectedModule", s.selectedModule);
    s.selectedAnimation = j.value("selectedAnimation", s.selectedAnimation);
    s.previewLOD = static_cast<Quality>(std::clamp(j.value("previewLOD", static_cast<int>(s.previewLOD)), 0, 3));
    s.previewTime = j.value("previewTime", s.previewTime);
    s.showPhysics = j.value("showPhysics", s.showPhysics);
    s.showThrusters = j.value("showThrusters", s.showThrusters);
    s.showMagitechEffects = j.value("showMagitechEffects", s.showMagitechEffects);
    s.runeGlowColor = vec3From(j.value("runeGlowColor", nlohmann::json()), s.runeGlowColor);
    s.runeGlowIntensity = j.value("runeGlowIntensity", s.runeGlowIntensity);
    s.engineHeatDistortion = j.value("engineHeatDistortion", s.engineHeatDistortion);
    s.energyTrailOpacity = j.value("energyTrailOpacity", s.energyTrailOpacity);
    s.maxSpeed = j.value("maxSpeed", s.maxSpeed);
    s.maxAltitude = j.value("maxAltitude", s.maxAltitude);
    s.thrustForce = j.value("thrustForce", s.thrustForce);
    s.moduleOffset = vec3From(j.value("moduleOffset", nlohmann::json()), s.moduleOffset);
    s.moduleScale = vec3From(j.value("moduleScale", nlohmann::json()), s.moduleScale);
    if (j.contains("moduleRotation") && j.at("moduleRotation").size() == 4) {
        const auto& r = j.at("moduleRotation");
        s.moduleRotation = glm::normalize(glm::quat(r[0].get<float>(), r[1].get<float>(), r[2].get<float>(), r[3].get<float>()));
    }
}

void MiniJetEditor::renderModuleHierarchy(const std::string& assetName) {
    auto& instance = getPreviewInstance(assetName);
    auto& state = getEditorState(assetName);
    if (!instance.asset || !ImGui::CollapsingHeader("Modules", ImGuiTreeNodeFlags_DefaultOpen)) return;
    for (const auto& module : instance.asset->definition.modules) {
        const bool selected = state.selectedModule == module.id;
        if (ImGui::Selectable((module.id + "  [" + module.attachBone + "]").c_str(), selected)) {
            state.selectedModule = module.id;
            state.moduleOffset = module.offset;
            state.moduleScale = module.scale;
            state.moduleRotation = module.rotation;
        }
    }
    if (!state.selectedModule.empty()) {
        ImGui::DragFloat3("Offset", &state.moduleOffset.x, 0.01f);
        ImGui::DragFloat3("Scale", &state.moduleScale.x, 0.01f, 0.01f, 10.0f);
        auto moduleIt = instance.asset->modules.find(state.selectedModule);
        if (moduleIt != instance.asset->modules.end()) {
            const auto& mesh = moduleIt->second.lodMeshes[static_cast<size_t>(state.previewLOD)];
            ImGui::Text("LOD mesh: %zu vertices, %zu triangles", mesh.vertexCount(), mesh.triangleCount());
        }
    }
}

void MiniJetEditor::renderMaterialProperties(const std::string& assetName) {
    auto& state = getEditorState(assetName);
    if (!ImGui::CollapsingHeader("Magitech materials")) return;
    ImGui::ColorEdit3("Rune glow color", &state.runeGlowColor.x);
    ImGui::SliderFloat("Rune glow intensity", &state.runeGlowIntensity, 0.0f, 2.0f);
    ImGui::SliderFloat("Engine heat distortion", &state.engineHeatDistortion, 0.0f, 1.0f);
    ImGui::SliderFloat("Energy trail opacity", &state.energyTrailOpacity, 0.0f, 1.0f);
}

void MiniJetEditor::renderAnimationTimeline(const std::string& assetName) {
    auto& instance = getPreviewInstance(assetName);
    auto& state = getEditorState(assetName);
    if (!instance.asset || !ImGui::CollapsingHeader("Animation")) return;
    for (const auto& [id, anim] : instance.asset->animations) {
        if (ImGui::Selectable(id.c_str(), instance.currentAnimation == id)) {
            state.selectedAnimation = id;
            m_loader->setAnimation(instance, id);
        }
    }
    auto it = instance.asset->animations.find(instance.currentAnimation);
    if (it != instance.asset->animations.end() && it->second.duration > 0.0f) {
        ImGui::SliderFloat("Time", &instance.animationTime, 0.0f, it->second.duration);
        ImGui::Text("%zu tracks", it->second.tracks.size());
    }
}

void MiniJetEditor::renderPhysicsDebug(const std::string& assetName) {
    auto& instance = getPreviewInstance(assetName);
    if (!instance.asset || !ImGui::CollapsingHeader("Physics")) return;
    static const char* shapeNames[] = {"None", "Box", "Capsule", "Convex hull"};
    const bool showThrusters = getEditorState(assetName).showThrusters;
    for (const auto& [id, module] : instance.asset->modules) {
        const auto& body = module.physicsBody;
        ImGui::Text("%s: %s, mass %.1f kg", id.c_str(), shapeNames[static_cast<int>(body.shape)], body.mass);
        if (module.thruster.isValid() && showThrusters) {
            ImGui::Text("  thruster %.0f N, heat %.2f", module.thruster.force, module.thruster.heatDistortion);
        }
    }
    ImGui::Text("Total mass (definition): %.1f kg", instance.asset->definition.physics.totalMass);
}

void MiniJetEditor::renderFlightControls(const std::string& assetName) {
    auto& instance = getPreviewInstance(assetName);
    auto& state = getEditorState(assetName);
    if (!instance.asset || !ImGui::CollapsingHeader("Flight")) return;
    float throttle = instance.throttle;
    if (ImGui::SliderFloat("Throttle", &throttle, 0.0f, 1.0f)) m_loader->setThrottle(instance, throttle);
    glm::vec3 input = instance.controlInput;
    if (ImGui::SliderFloat3("Pitch/Yaw/Roll", &input.x, -1.0f, 1.0f)) m_loader->setControlInput(instance, input);
    ImGui::DragFloat("Max speed", &state.maxSpeed, 1.0f, 1.0f, 2000.0f);
    ImGui::DragFloat("Max altitude", &state.maxAltitude, 10.0f, 1.0f, 50000.0f);
    ImGui::DragFloat("Thrust", &state.thrustForce, 10.0f, 0.0f, 100000.0f);
    ImGui::Text("Speed %.1f  Altitude %.1f  %s", instance.speed, instance.altitude,
                instance.isFlying ? "flying" : (instance.isLanding ? "landing" : (instance.isTakingOff ? "taking off" : "grounded")));
}

} // namespace MiniJetGen
