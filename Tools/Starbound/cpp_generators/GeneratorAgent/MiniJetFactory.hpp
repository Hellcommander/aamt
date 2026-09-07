#pragma once

#include "MiniJetTypes.hpp"
#include <future>
#include <memory>
#include <unordered_map>
#include <filesystem>

namespace MiniJetGen {

// Forward declarations for generator modules
namespace DefinitionParser {
    MiniJetDefinition parseFromYAML(const std::string& filePath);
    bool validateDefinition(const MiniJetDefinition& def);
}

namespace ModuleAssembler {
    struct AssemblyResult {
        std::unordered_map<std::string, MeshHandle> meshes;
        std::unordered_map<std::string, MaterialHandle> materials;
        Skeleton skeleton;
    };
    
    AssemblyResult assembleModules(const MiniJetDefinition& def);
    void weldModuleSeams(AssemblyResult& result, const MiniJetDefinition& def);
    void bakeSkinWeights(AssemblyResult& result, const MiniJetDefinition& def);
}

namespace MaterialSynthesizer {
    struct MaterialResult {
        std::unordered_map<std::string, MaterialHandle> materials;
        std::unordered_map<std::string, std::string> shaderGraphs;
    };
    
    MaterialResult synthesizeMagitechMaterials(const MiniJetDefinition& def);
    MaterialHandle createRuneGlowMaterial(const MagitechMaterials::RuneGlow& params);
    MaterialHandle createEngineHeatMaterial(const MagitechMaterials::EngineHeat& params);
    MaterialHandle createEnergyTrailMaterial(const MagitechMaterials::EnergyTrail& params);
}

namespace AnimationProcessor {
    struct AnimationResult {
        std::unordered_map<std::string, Animation> animations;
        std::unordered_map<std::string, float> blendTimes;
    };
    
    AnimationResult processAnimations(const MiniJetDefinition& def, const Skeleton& skeleton);
    Animation retargetAnimation(const Animation& source, const Skeleton& target);
    void optimizeAnimation(Animation& anim, Quality quality);
}

namespace PhysicsRigBuilder {
    struct PhysicsResult {
        std::unordered_map<std::string, PhysicsBody> bodies;
        std::unordered_map<std::string, ThrusterNode> thrusters;
        std::vector<std::pair<std::string, std::string>> joints;
    };
    
    PhysicsResult buildPhysicsRig(const MiniJetDefinition& def);
    PhysicsBody createModuleCollider(const ModuleDefinition& module, const PhysicsDefinition::CollisionShape& shape);
    ThrusterNode createThrusterNode(const ModuleDefinition& module);
}

namespace LODGenerator {
    struct LODResult {
        std::unordered_map<std::string, std::array<MeshHandle, static_cast<size_t>(Quality::COUNT)>> lodMeshes;
        std::unordered_map<std::string, std::array<MaterialHandle, static_cast<size_t>(Quality::COUNT)>> lodMaterials;
    };
    
    LODResult generateLODs(const MiniJetDefinition& def, const ModuleAssembler::AssemblyResult& assembly);
    MeshHandle decimateMesh(const MeshHandle& mesh, float decimateFactor);
    MaterialHandle simplifyMaterial(const MaterialHandle& material, float detailLevel);
}

namespace PackageWriter {
    bool writePackage(const std::string& name, const MiniJetAsset& asset);
    bool writeMesh(const std::string& path, const MeshHandle& mesh);
    bool writeMaterial(const std::string& path, const MaterialHandle& material);
    bool writeAnimation(const std::string& path, const Animation& animation);
    bool writePhysics(const std::string& path, const PhysicsRigBuilder::PhysicsResult& physics);
    bool writeMetadata(const std::string& path, const MiniJetDefinition& def);
}

namespace PackageReader {
    MiniJetAsset readPackage(const std::string& name);
    MeshHandle readMesh(const std::string& path);
    MaterialHandle readMaterial(const std::string& path);
    Animation readAnimation(const std::string& path);
    PhysicsBody readPhysics(const std::string& path);
    MiniJetDefinition readMetadata(const std::string& path);
}

// Cache for runtime assets
class MiniJetCache {
    static constexpr size_t MAX_CACHE_SIZE = 50;
    
    struct CacheEntry {
        std::shared_ptr<MiniJetAsset> asset;
        size_t hash;
        std::chrono::steady_clock::time_point lastAccess;
    };
    
    std::unordered_map<std::string, CacheEntry> m_cache;
    std::mutex m_mutex;
    
public:
    std::shared_ptr<MiniJetAsset> get(const std::string& name, size_t hash);
    void put(const std::string& name, std::shared_ptr<MiniJetAsset> asset, size_t hash);
    void clear();
    void evictOldest();
    size_t size() const;
};

// Main factory class
class MiniJetFactory {
    std::unique_ptr<MultithreadBusPlugin> m_pool;
    std::unique_ptr<MiniJetCache> m_cache;
    bool m_initialized = false;
    
    // File watching for hot-reload
    std::unordered_map<std::string, std::filesystem::file_time_type> m_fileTimestamps;
    std::unordered_map<std::string, size_t> m_fileHashes;
    
    // Performance metrics
    struct Metrics {
        size_t totalAssetsGenerated = 0;
        size_t cacheHits = 0;
        size_t cacheMisses = 0;
        double averageGenerationTime = 0.0;
        double averageLoadTime = 0.0;
    } m_metrics;
    
public:
    MiniJetFactory();
    ~MiniJetFactory();
    
    // Initialization and shutdown
    void initialize(size_t num_threads = 4);
    void shutdown();
    bool isInitialized() const { return m_initialized; }
    
    // Synchronous operations
    std::shared_ptr<MiniJetAsset> load(const std::string& name, Quality quality = Quality::High);
    std::shared_ptr<MiniJetAsset> generate(const std::string& definitionPath, Quality quality = Quality::High);
    bool generatePackage(const std::string& name, const std::string& definitionPath);
    
    // Asynchronous operations
    std::future<std::shared_ptr<MiniJetAsset>> loadAsync(const std::string& name, Quality quality = Quality::High);
    std::future<std::shared_ptr<MiniJetAsset>> generateAsync(const std::string& definitionPath, Quality quality = Quality::High);
    std::future<bool> generatePackageAsync(const std::string& name, const std::string& definitionPath);
    
    // Cache management
    void clearCache();
    void preload(const std::vector<std::string>& names);
    size_t getCacheSize() const;
    
    // Hot-reload functionality
    void watchForChanges(const std::string& definitionPath);
    void checkForUpdates();
    void reloadAsset(const std::string& name);
    
    // Performance monitoring
    const Metrics& getMetrics() const { return m_metrics; }
    void resetMetrics();
    
    // Utility functions
    bool validateDefinition(const std::string& definitionPath);
    std::vector<std::string> getAvailableAssets() const;
    size_t getAssetHash(const std::string& name) const;
    
private:
    std::shared_ptr<MiniJetAsset> generateAsset(const MiniJetDefinition& def, Quality quality);
    void updateFileTimestamps(const std::string& definitionPath);
    bool hasFileChanged(const std::string& path);
    void updateMetrics(double generationTime, double loadTime, bool cacheHit);
};

// Runtime loader for instantiated mini-jets
class MiniJetLoader {
    std::shared_ptr<MiniJetFactory> m_factory;
    
public:
    explicit MiniJetLoader(std::shared_ptr<MiniJetFactory> factory);
    
    MiniJetInstance createInstance(const std::string& name, Quality quality = Quality::High);
    MiniJetInstance createInstance(std::shared_ptr<MiniJetAsset> asset);
    
    void updateInstance(MiniJetInstance& instance, float deltaTime);
    void setAnimation(MiniJetInstance& instance, const std::string& animationName);
    void setLOD(MiniJetInstance& instance, Quality quality);
    
    // Flight control functions
    void setThrottle(MiniJetInstance& instance, float throttle);
    void setControlInput(MiniJetInstance& instance, const glm::vec3& input);
    void updateFlightPhysics(MiniJetInstance& instance, float deltaTime);
    
    // Magitech effect control
    void setRuneGlowIntensity(MiniJetInstance& instance, float intensity);
    void setEngineHeatLevel(MiniJetInstance& instance, float heat);
    void setEnergyTrailLength(MiniJetInstance& instance, float length);
};

// Editor integration
class MiniJetEditor {
    std::shared_ptr<MiniJetFactory> m_factory;
    std::shared_ptr<MiniJetLoader> m_loader;
    std::unordered_map<std::string, MiniJetEditorState> m_editorStates;
    
public:
    explicit MiniJetEditor(std::shared_ptr<MiniJetFactory> factory);
    
    // Editor UI functions
    void showEditorPanel(const std::string& assetName);
    void showModulePanel(const std::string& assetName);
    void showMaterialPanel(const std::string& assetName);
    void showAnimationPanel(const std::string& assetName);
    void showPhysicsPanel(const std::string& assetName);
    void showFlightPanel(const std::string& assetName);
    
    // Live preview
    MiniJetInstance& getPreviewInstance(const std::string& assetName);
    void updatePreview(const std::string& assetName, float deltaTime);
    
    // Asset management
    void rebuildAsset(const std::string& assetName);
    void exportAsset(const std::string& assetName, const std::string& outputPath);
    void importAsset(const std::string& inputPath);
    
    // Editor state management
    MiniJetEditorState& getEditorState(const std::string& assetName);
    void saveEditorState(const std::string& assetName);
    void loadEditorState(const std::string& assetName);
    
private:
    void renderModuleHierarchy(const std::string& assetName);
    void renderMaterialProperties(const std::string& assetName);
    void renderAnimationTimeline(const std::string& assetName);
    void renderPhysicsDebug(const std::string& assetName);
    void renderFlightControls(const std::string& assetName);
};

} // namespace MiniJetGen 
