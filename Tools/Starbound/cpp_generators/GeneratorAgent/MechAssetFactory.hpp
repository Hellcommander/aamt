#pragma once
#include "MechAssetTypes.hpp"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <thread>
#include <future>
#include <filesystem>

namespace MagiTech {
namespace MechAssets {

// Forward declarations
class MechGenerator;
class ModuleAssembler;
class MorphGenerator;
class PhysicsRigBuilder;
class LODBuilder;
class PackageWriter;
class MechLoader;

// Mech Asset Factory - Main entry point for mech asset generation and management
class MechAssetFactory {
public:
    MechAssetFactory();
    ~MechAssetFactory();

    // Core factory methods
    MechHandle createMech(const MechDefinitionParams& params);
    MechHandle loadMech(const std::string& name, LODQuality quality = LODQuality::HIGH);
    bool unloadMech(MechHandle handle);
    
    // Instance management
    MechInstanceState createInstance(MechHandle mechHandle);
    bool destroyInstance(const MechInstanceState& instance);
    bool updateInstance(MechInstanceState& instance, float deltaTime);
    
    // Morph control
    bool startMorph(MechInstanceState& instance, const std::string& profileName);
    bool setMorphProgress(MechInstanceState& instance, float progress);
    bool pauseMorph(MechInstanceState& instance);
    bool resumeMorph(MechInstanceState& instance);
    
    // Hot reload support
    bool watchDefinition(const std::string& mechName);
    bool unwatchDefinition(const std::string& mechName);
    void processHotReloads();
    
    // Performance and debugging
    const MechPerformanceMetrics& getPerformanceMetrics() const { return metrics_; }
    void resetPerformanceMetrics() { metrics_.reset(); }
    
    // GPU acceleration
    void setGPUAcceleration(bool enabled) { gpuAccelerationEnabled_ = enabled; }
    bool isGPUAccelerationEnabled() const { return gpuAccelerationEnabled_; }
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    bool isCached(const std::string& name) const;

private:
    // Core components
    std::unique_ptr<MechGenerator> generator_;
    std::unique_ptr<ModuleAssembler> assembler_;
    std::unique_ptr<MorphGenerator> morphGen_;
    std::unique_ptr<PhysicsRigBuilder> physicsBuilder_;
    std::unique_ptr<LODBuilder> lodBuilder_;
    std::unique_ptr<PackageWriter> packWriter_;
    std::unique_ptr<MechLoader> loader_;
    
    // Asset cache with thread safety
    mutable std::mutex cacheMutex_;
    std::unordered_map<uint64_t, std::shared_ptr<MechAsset>> assetCache_;
    std::unordered_map<MechHandle, std::shared_ptr<MechAsset>> handleToAsset_;
    
    // Instance tracking
    mutable std::mutex instanceMutex_;
    std::unordered_map<uint64_t, MechInstanceState> activeInstances_;
    
    // Hot reload file watchers
    struct FileWatcher {
        std::string mechName;
        std::filesystem::path definitionPath;
        std::chrono::system_clock::time_point lastModified;
        uint64_t lastHash;
    };
    std::vector<FileWatcher> fileWatchers_;
    std::mutex watcherMutex_;
    
    // Performance tracking
    MechPerformanceMetrics metrics_;
    std::chrono::system_clock::time_point lastMetricsUpdate_;
    
    // Configuration
    bool gpuAccelerationEnabled_ = true;
    bool hotReloadEnabled_ = true;
    size_t maxCacheSize_ = 100;
    
    // Internal methods
    uint64_t generateCacheKey(const std::string& name, LODQuality quality) const;
    std::shared_ptr<MechAsset> buildAsset(const MechDefinitionParams& params);
    std::shared_ptr<MechAsset> loadFromPack(const std::string& name, LODQuality quality);
    bool saveToPack(const MechAsset& asset, const std::string& name);
    void updateMetrics();
    
    // Hot reload helpers
    void checkFileChanges();
    bool rebuildAsset(const std::string& mechName);
    uint64_t computeFileHash(const std::filesystem::path& path) const;
    
    // Threading
    std::thread hotReloadThread_;
    std::atomic<bool> hotReloadRunning_{false};
    void hotReloadWorker();
};

// Mech Generator - Handles parsing and validation of mech definitions
class MechGenerator {
public:
    MechGenerator();
    ~MechGenerator();
    
    MechDefinitionParams parseDefinition(const std::string& filePath);
    bool validateDefinition(const MechDefinitionParams& params);
    std::vector<std::string> getValidationErrors() const;
    
private:
    std::vector<std::string> validationErrors_;
    
    bool validateModule(const ModuleDefinition& module);
    bool validateMorphProfile(const MorphProfile& profile);
    bool validatePhysicsRig(const PhysicsRigDefinition& rig);
    bool validateLODs(const std::vector<LODDefinition>& lods);
};

// Module Assembler - Handles mesh assembly and skeleton integration
class ModuleAssembler {
public:
    ModuleAssembler();
    ~ModuleAssembler();
    
    bool assembleModules(const std::vector<ModuleDefinition>& modules, 
                        const std::string& skeletonTemplate,
                        MechAsset& asset);
    
private:
    bool weldModuleSeams(const std::vector<ModuleData>& modules);
    bool bakeSkinnedMesh(const ModuleData& module);
    bool remapBoneIndices(const std::vector<ModuleData>& modules);
};

// Morph Generator - Handles morph target generation and interpolation
class MorphGenerator {
public:
    MorphGenerator();
    ~MorphGenerator();
    
    bool generateMorphTargets(const std::vector<MorphProfile>& profiles,
                             const std::vector<ModuleData>& modules,
                             MechAsset& asset);
    
private:
    bool computeVertexDeltas(const MorphProfile& profile, 
                            const ModuleData& fromModule,
                            const ModuleData& toModule);
    float evaluateMorphCurve(MorphCurveType curveType, float t, 
                            const std::vector<float>& customCurve = {});
};

// Physics Rig Builder - Handles physics body and joint creation
class PhysicsRigBuilder {
public:
    PhysicsRigBuilder();
    ~PhysicsRigBuilder();
    
    bool buildPhysicsRig(const PhysicsRigDefinition& rigDef,
                        const std::vector<ModuleData>& modules,
                        MechAsset& asset);
    
private:
    bool createRigidBody(const ModuleData& module, const PhysicsRigDefinition& rigDef);
    bool createJointConstraints(const std::vector<JointConstraint>& joints);
    bool generateColliders(const ModuleData& module, ColliderType type, const glm::vec3& size);
};

// LOD Builder - Handles LOD generation and optimization
class LODBuilder {
public:
    LODBuilder();
    ~LODBuilder();
    
    bool generateLODs(const std::vector<LODDefinition>& lods,
                     const std::vector<ModuleData>& modules,
                     MechAsset& asset);
    
private:
    bool decimateMesh(const ModuleData& module, float ratio);
    bool downsampleMorphTargets(const ModuleData& module, float detailRatio);
    bool preserveMeshFeatures(const ModuleData& module, bool preserveBorders, bool preserveUVSeams);
};

// Package Writer - Handles .mechpack file creation
class PackageWriter {
public:
    PackageWriter();
    ~PackageWriter();
    
    bool writePackage(const MechAsset& asset, const std::string& filePath);
    bool readPackage(const std::string& filePath, MechAsset& asset);
    
private:
    bool writeHeader(const MechPackHeader& header, std::ofstream& file);
    bool writeModuleTable(const std::vector<ModuleData>& modules, std::ofstream& file);
    bool writeMorphTable(const std::vector<MorphProfile>& profiles, std::ofstream& file);
    bool writePhysicsRig(const PhysicsRigHandle& rig, std::ofstream& file);
    bool writeMetadata(const MechAsset& asset, std::ofstream& file);
    
    bool readHeader(MechPackHeader& header, std::ifstream& file);
    bool readModuleTable(std::vector<ModuleData>& modules, std::ifstream& file);
    bool readMorphTable(std::vector<MorphProfile>& profiles, std::ifstream& file);
    bool readPhysicsRig(PhysicsRigHandle& rig, std::ifstream& file);
    bool readMetadata(MechAsset& asset, std::ifstream& file);
};

// Mech Loader - Handles runtime loading and instantiation
class MechLoader {
public:
    MechLoader();
    ~MechLoader();
    
    MechHandle loadMech(const std::string& name, LODQuality quality);
    bool unloadMech(MechHandle handle);
    
private:
    std::unordered_map<MechHandle, std::shared_ptr<MechAsset>> loadedMechs_;
    std::mutex loaderMutex_;
    
    MechHandle nextHandle_ = 1;
    MechHandle allocateHandle();
};

} // namespace MechAssets
} // namespace MagiTech 
