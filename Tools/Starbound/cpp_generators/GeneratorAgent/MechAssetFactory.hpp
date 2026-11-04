#pragma once
#include "MechAssetTypes.hpp"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <thread>
#include <future>
#include <filesystem>
#include <fstream>
#include <string>
#include <utility>
#include <vector>

namespace MagiTech {
namespace Mechs {
struct MechColliderShape;   // MechFamilyAssetStore.hpp
}
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
        std::filesystem::file_time_type lastModified;
        uint64_t lastHash = 0;
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
    /** Releases the asset's store resources unless a cache map still holds it (cacheMutex_ held). */
    void releaseIfUnreferenced(const std::shared_ptr<MechAsset>& asset);
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

// ---------------------------------------------------------------------------
// FormShiftMechGen pipeline stages (implemented in MechAssetPipeline.cpp).
// Geometry is built with the `mt` mesh pipeline; meshes, skeletons and physics
// rigs are stored in Mechs::MechFamilyAssetStore and referenced by handle from
// MechAsset / ModuleData (lodMeshes[0] is the full-detail module mesh).
// ---------------------------------------------------------------------------

// Mech Generator - Handles parsing and validation of mech definitions
class MechGenerator {
public:
    MechGenerator();
    ~MechGenerator();

    /** Parses a .mechdef (JSON) file; throws std::runtime_error on I/O or format errors. */
    MechDefinitionParams parseDefinition(const std::string& filePath);
    bool validateDefinition(const MechDefinitionParams& params);
    std::vector<std::string> getValidationErrors() const;

private:
    std::vector<std::string> validationErrors_;

    bool validateModule(const ModuleDefinition& module);
    bool validateMorphProfile(const MorphProfile& profile, const MechDefinitionParams& params);
    bool validatePhysicsRig(const PhysicsRigDefinition& rig);
    bool validateLODs(const std::vector<LODDefinition>& lods);
};

// Module Assembler - Handles mesh assembly and skeleton integration
class ModuleAssembler {
public:
    ModuleAssembler();
    ~ModuleAssembler();

    /** Builds every module mesh, the module hierarchy transforms and the mech skeleton. */
    bool assembleModules(const std::vector<ModuleDefinition>& modules,
                        const std::string& skeletonTemplate,
                        MechAsset& asset);

private:
    /** Welds duplicate vertices of modules that are welded to their parent. */
    bool weldModuleSeams(const std::vector<ModuleData>& modules, const std::vector<ModuleDefinition>& definitions);
    /** Rigidly skins the module mesh to its bone. */
    bool bakeSkinnedMesh(const ModuleData& module, int boneIndex);
    /** Verifies every vertex references a bone of the skeleton. */
    bool remapBoneIndices(const std::vector<ModuleData>& modules, size_t boneCount);
};

// Morph Generator - Handles morph target generation and interpolation
class MorphGenerator {
public:
    MorphGenerator();
    ~MorphGenerator();

    /** Adds one morph target per (profile, module) to the module meshes. */
    bool generateMorphTargets(const std::vector<MorphProfile>& profiles,
                             const std::vector<ModuleData>& modules,
                             MechAsset& asset);

    /** Morph weight for normalized time t under the given curve. */
    static float evaluateMorphCurve(MorphCurveType curveType, float t,
                                    const std::vector<float>& customCurve = {});

private:
    /** Appends the vertex deltas of `profile` for `module` to its mesh; returns the morph target index or -1. */
    int computeVertexDeltas(const MorphProfile& profile, const ModuleData& module);
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
    /** Mass assigned to a module body (explicit per-module mass or an even share). */
    float moduleMass(const ModuleData& module, const PhysicsRigDefinition& rigDef, size_t moduleCount) const;
    /** Collider fitted to the module mesh bounds (capsule for limbs, sphere for pods, box otherwise). */
    bool generateCollider(const ModuleData& module, float mass, Mechs::MechColliderShape& out) const;
};

// LOD Builder - Handles LOD generation and optimization
class LODBuilder {
public:
    LODBuilder();
    ~LODBuilder();

    /** Appends one simplified mesh per LOD definition to every module's lodMeshes. */
    bool generateLODs(const std::vector<LODDefinition>& lods,
                     const std::vector<ModuleData>& modules,
                     MechAsset& asset);

private:
    MeshHandle decimateMesh(MeshHandle baseMesh, const LODDefinition& lod);
    /** Transfers the base mesh morph targets onto the LOD mesh (nearest vertex), scaled by detailRatio. */
    bool downsampleMorphTargets(MeshHandle baseMesh, MeshHandle lodMesh, float detailRatio);
};

// Package Writer - Handles .mechpack file creation
class PackageWriter {
public:
    PackageWriter();
    ~PackageWriter();

    bool writePackage(const MechAsset& asset, const std::string& filePath);
    /** Reads a package and registers its meshes / skeleton / physics rig in the asset store. */
    bool readPackage(const std::string& filePath, MechAsset& asset);

private:
    bool writeHeader(const MechPackHeader& header, std::ofstream& file);
    bool writeModuleTable(const std::vector<ModuleData>& modules, std::ofstream& file);
    bool writeMorphTable(const std::vector<MorphProfile>& profiles, std::ofstream& file);
    bool writePhysicsRig(const PhysicsRigHandle& rig, std::ofstream& file);
    bool writeMetadata(const MechAsset& asset, std::ofstream& file);

    bool readHeader(MechPackHeader& header, std::ifstream& file);
    bool readModuleTable(std::vector<ModuleData>& modules, uint32_t count, std::ifstream& file);
    bool readMorphTable(std::vector<MorphProfile>& profiles, uint32_t count, std::ifstream& file);
    bool readPhysicsRig(PhysicsRigHandle& rig, std::ifstream& file);
    bool readMetadata(MechAsset& asset, uint32_t lodCount, std::ifstream& file);
};

// Mech Loader - Handles runtime loading and instantiation
class MechLoader {
public:
    MechLoader();
    ~MechLoader();

    /** Loads assets/mechs/<name>.mechpack keeping only the LODs of `quality`. */
    MechHandle loadMech(const std::string& name, LODQuality quality);
    bool unloadMech(MechHandle handle);
    std::shared_ptr<const MechAsset> getMech(MechHandle handle);

private:
    std::unordered_map<MechHandle, std::shared_ptr<MechAsset>> loadedMechs_;
    std::mutex loaderMutex_;

    MechHandle nextHandle_ = 1;
    MechHandle allocateHandle();
};

/** Releases every mesh, skeleton and physics rig referenced by the asset from the asset store. */
void releaseMechAssetResources(const MechAsset& asset);

/** Keeps only the LODs (and their module LOD meshes) of quality; lodMeshes[0] is always kept. */
void filterMechAssetLODs(MechAsset& asset, LODQuality quality);

/** Unique handle for a new mech asset (shared by the factory and the loader). */
MechHandle allocateMechAssetHandle();

} // namespace MechAssets
} // namespace MagiTech 
