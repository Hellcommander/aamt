#pragma once

#include "MechTypes.hpp"
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include <future>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <mutex>
#include <atomic>

namespace MagiTech {
namespace Mechs {

class MechFactory {
public:
    MechFactory();
    ~MechFactory();

    void initialize(size_t cache_size, size_t num_threads);
    void shutdown();

    // Enhanced async generation with hybrid features
    std::future<MechBundle> generateAsync(MechParams p);
    
    // Synchronous generation for immediate use
    MechBundle generateSync(MechParams p);
    
    // Instance management
    MechInstanceState createInstance(const MechParams& params);
    bool destroyInstance(const MechInstanceState& instance);
    bool updateInstance(MechInstanceState& instance, float deltaTime);
    
    // Form morphing
    bool startMorph(MechInstanceState& instance, const std::string& formName);
    bool setMorphProgress(MechInstanceState& instance, float progress);
    bool pauseMorph(MechInstanceState& instance);
    bool resumeMorph(MechInstanceState& instance);
    
    // Batch operations
    std::vector<std::future<MechBundle>> generateBatch(const std::vector<MechParams>& params);
    void generateBatchSync(const std::vector<MechParams>& params, std::vector<MechBundle>& results);
    
    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    bool isCached(const MechParams& params) const;
    void setCacheSize(size_t size);
    
    // Performance monitoring
    const MechPerformanceMetrics& getPerformanceMetrics() const { return metrics_; }
    void resetPerformanceMetrics() { metrics_.reset(); }
    
    // GPU acceleration
    void setGPUAcceleration(bool enabled) { gpuAccelerationEnabled_ = enabled; }
    bool isGPUAccelerationEnabled() const { return gpuAccelerationEnabled_; }
    
    // Hot reload support
    void watchDefinition(const std::string& mechId);
    void unwatchDefinition(const std::string& mechId);
    void processHotReloads();
    
    // Procedural generation
    void setProceduralParams(const ProceduralParams& params) { proceduralParams_ = params; }
    const ProceduralParams& getProceduralParams() const { return proceduralParams_; }
    
    // Template-based generation
    MechParams createFromTemplate(const std::string& templateName);
    void registerTemplate(const std::string& name, const MechParams& template_);
    std::vector<std::string> getAvailableTemplates() const;
    
    // Validation
    bool validateParams(const MechParams& params);
    std::vector<std::string> getValidationErrors() const;

    // === SEGMENTED MECH GENERATION ===
    
    // Segmented mech generation (snake/worm)
    std::future<SegmentedMechBundle> generateSegmentedAsync(const SegmentedMechParams& params, 
                                                            const CockpitParams& cockpitParams = CockpitParams{},
                                                            const UIParams& uiParams = UIParams{});
    
    SegmentedMechBundle generateSegmentedSync(const SegmentedMechParams& params,
                                             const CockpitParams& cockpitParams = CockpitParams{},
                                             const UIParams& uiParams = UIParams{});
    
    // Segmented mech instance management
    SegmentedMechInstanceState createSegmentedInstance(const SegmentedMechParams& params,
                                                      const CockpitParams& cockpitParams = CockpitParams{});
    bool destroySegmentedInstance(const SegmentedMechInstanceState& instance);
    bool updateSegmentedInstance(SegmentedMechInstanceState& instance, float deltaTime);
    
    // Dynamic segment management
    bool addSegment(SegmentedMechInstanceState& instance, int index);
    bool removeSegment(SegmentedMechInstanceState& instance, int index);
    bool setSegmentCount(SegmentedMechInstanceState& instance, int count);
    bool updateSegmentProperties(SegmentedMechInstanceState& instance, int segmentIndex, 
                               const std::unordered_map<std::string, float>& properties);
    
    // Segmented mech animation control
    bool startSegmentedAnimation(SegmentedMechInstanceState& instance, const std::string& animationName);
    bool setSegmentedAnimationProgress(SegmentedMechInstanceState& instance, float progress);
    bool pauseSegmentedAnimation(SegmentedMechInstanceState& instance);
    bool resumeSegmentedAnimation(SegmentedMechInstanceState& instance);
    
    // Cockpit integration
    bool attachCockpit(SegmentedMechInstanceState& instance, const CockpitParams& cockpitParams);
    bool detachCockpit(SegmentedMechInstanceState& instance);
    bool updateCockpitParams(SegmentedMechInstanceState& instance, const CockpitParams& cockpitParams);
    
    // Segmented mech batch operations
    std::vector<std::future<SegmentedMechBundle>> generateSegmentedBatch(
        const std::vector<std::pair<SegmentedMechParams, CockpitParams>>& params);
    
    // Segmented mech cache management
    void clearSegmentedCache();
    size_t getSegmentedCacheSize() const;
    bool isSegmentedCached(const SegmentedMechParams& params) const;
    
    // Segmented mech validation
    bool validateSegmentedParams(const SegmentedMechParams& params);
    bool validateCockpitParams(const CockpitParams& params);
    std::vector<std::string> getSegmentedValidationErrors() const;
    
    // Segmented mech templates
    SegmentedMechParams createSegmentedFromTemplate(const std::string& templateName);
    void registerSegmentedTemplate(const std::string& name, const SegmentedMechParams& template_);
    std::vector<std::string> getAvailableSegmentedTemplates() const;
    
    // Cockpit templates
    CockpitParams createCockpitFromTemplate(const std::string& templateName);
    void registerCockpitTemplate(const std::string& name, const CockpitParams& template_);
    std::vector<std::string> getAvailableCockpitTemplates() const;

    // === CENTIPEDE MECH GENERATION ===
    
    // Centipede mech generation
    std::future<CentipedeMechBundle> generateCentipedeAsync(const CentipedeMechParams& params);
    CentipedeMechBundle generateCentipedeSync(const CentipedeMechParams& params);
    
    // Centipede mech instance management
    CentipedeMechInstanceState createCentipedeInstance(const CentipedeMechParams& params);
    bool destroyCentipedeInstance(const CentipedeMechInstanceState& instance);
    bool updateCentipedeInstance(CentipedeMechInstanceState& instance, float deltaTime);
    
    // Dynamic segment management for centipede
    bool addCentipedeSegment(CentipedeMechInstanceState& instance, int index);
    bool removeCentipedeSegment(CentipedeMechInstanceState& instance, int index);
    bool setCentipedeSegmentCount(CentipedeMechInstanceState& instance, int count);
    bool updateCentipedeSegmentProperties(CentipedeMechInstanceState& instance, int segmentIndex, 
                                        const std::unordered_map<std::string, float>& properties);
    
    // Leg management for centipede
    bool addCentipedeLeg(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex);
    bool removeCentipedeLeg(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex);
    bool updateCentipedeLegProperties(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex,
                                     const std::unordered_map<std::string, float>& properties);
    
    // Centipede animation control
    bool startCentipedeAnimation(CentipedeMechInstanceState& instance, const std::string& animationName);
    bool setCentipedeAnimationProgress(CentipedeMechInstanceState& instance, float progress);
    bool pauseCentipedeAnimation(CentipedeMechInstanceState& instance);
    bool resumeCentipedeAnimation(CentipedeMechInstanceState& instance);
    
    // Centipede cockpit integration
    bool attachCentipedeCockpit(CentipedeMechInstanceState& instance, const CockpitParams& cockpitParams);
    bool detachCentipedeCockpit(CentipedeMechInstanceState& instance);
    bool updateCentipedeCockpitParams(CentipedeMechInstanceState& instance, const CockpitParams& cockpitParams);
    
    // Centipede weapon and sensor management
    bool addCentipedeWeapon(CentipedeMechInstanceState& instance, const std::string& weaponType, int hardpointIndex);
    bool removeCentipedeWeapon(CentipedeMechInstanceState& instance, int hardpointIndex);
    bool updateCentipedeSensorArray(CentipedeMechInstanceState& instance, const std::string& sensorType);
    
    // Centipede batch operations
    std::vector<std::future<CentipedeMechBundle>> generateCentipedeBatch(const std::vector<CentipedeMechParams>& params);
    
    // Centipede cache management
    void clearCentipedeCache();
    size_t getCentipedeCacheSize() const;
    bool isCentipedeCached(const CentipedeMechParams& params) const;
    
    // Centipede validation
    bool validateCentipedeParams(const CentipedeMechParams& params);
    std::vector<std::string> getCentipedeValidationErrors() const;
    
    // Centipede templates
    CentipedeMechParams createCentipedeFromTemplate(const std::string& templateName);
    void registerCentipedeTemplate(const std::string& name, const CentipedeMechParams& template_);
    std::vector<std::string> getAvailableCentipedeTemplates() const;
    
    // Centipede utility functions
    bool spawnCentipedeMech(const CentipedeMechParams& params);
    CentipedeMechParams createCentipedeMechParams();
    std::string getCentipedeMechInfo(const CentipedeMechInstanceState& instance);
    bool setCentipedeMechProperty(CentipedeMechInstanceState& instance, const std::string& property, float value);
    float getCentipedeMechProperty(const CentipedeMechInstanceState& instance, const std::string& property);

private:
    ConcurrentLRUCache<uint64_t, MechBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized = false;
    
    // Enhanced features
    MechPerformanceMetrics metrics_;
    ProceduralParams proceduralParams_;
    bool gpuAccelerationEnabled_ = true;
    
    // Instance tracking
    std::unordered_map<std::string, MechInstanceState> activeInstances_;
    mutable std::mutex instanceMutex_;
    
    // Template system
    std::unordered_map<std::string, MechParams> mechTemplates_;
    mutable std::mutex templateMutex_;
    
    // Hot reload
    struct FileWatcher {
        std::string mechId;
        std::string filePath;
        std::chrono::system_clock::time_point lastModified;
        uint64_t lastHash;
    };
    std::vector<FileWatcher> fileWatchers_;
    mutable std::mutex watcherMutex_;
    
    // Validation
    mutable std::vector<std::string> validationErrors_;
    
    // === SEGMENTED MECH COMPONENTS ===
    
    // Segmented mech cache
    ConcurrentLRUCache<uint64_t, SegmentedMechBundle> m_segmentedCache;
    
    // Segmented mech instances
    std::unordered_map<std::string, SegmentedMechInstanceState> activeSegmentedInstances_;
    mutable std::mutex segmentedInstanceMutex_;
    
    // Segmented mech templates
    std::unordered_map<std::string, SegmentedMechParams> segmentedMechTemplates_;
    std::unordered_map<std::string, CockpitParams> cockpitTemplates_;
    mutable std::mutex segmentedTemplateMutex_;
    
    // Segmented mech validation
    mutable std::vector<std::string> segmentedValidationErrors_;
    
    // === CENTIPEDE MECH COMPONENTS ===
    
    // Centipede mech cache
    ConcurrentLRUCache<uint64_t, CentipedeMechBundle> m_centipedeCache;
    
    // Centipede mech instances
    std::unordered_map<std::string, CentipedeMechInstanceState> activeCentipedeInstances_;
    mutable std::mutex centipedeInstanceMutex_;
    
    // Centipede mech templates
    std::unordered_map<std::string, CentipedeMechParams> centipedeMechTemplates_;
    mutable std::mutex centipedeTemplateMutex_;
    
    // Centipede mech validation
    mutable std::vector<std::string> centipedeValidationErrors_;
    
    // Internal methods
    MechBundle generateMechBundle(const MechParams& params);
    SegmentedMechBundle generateSegmentedBundle(const SegmentedMechParams& params,
                                               const CockpitParams& cockpitParams,
                                               const UIParams& uiParams);
    uint64_t computeFileHash(const std::string& filePath) const;
    void checkFileChanges();
    bool rebuildFromFile(const std::string& mechId);
    
    // Segmented mech internal methods
    SegmentHandle createSegment(const SegmentedMechParams& params, int index);
    bool destroySegment(SegmentHandle handle);
    bool updateSegmentSkeleton(SegmentedMechInstanceState& instance);
    bool generateSegmentMesh(const SegmentedMechParams& params, int index, MeshHandle& mesh);
    bool generateSegmentPhysics(const SegmentedMechParams& params, int index, PhysicsHandle& physics);
    bool generateCockpitMesh(const CockpitParams& params, MeshHandle& mesh);
    bool generateCockpitTexture(const CockpitParams& params, TextureHandle& texture);
    bool generateUIIcon(const SegmentedMechParams& params, const UIParams& uiParams, TextureHandle& icon);
    
    // Performance tracking
    void updateMetrics(uint64_t generationTime, uint64_t memoryUsage);
    void trackInstanceCount();

    // Centipede internal methods
    CentipedeMechBundle generateCentipedeBundle(const CentipedeMechParams& params);
    MeshHandle createCentipedeSegment(const CentipedeMechParams& params, int segmentIndex);
    MeshHandle createCentipedeJoint(const CentipedeMechParams& params, int jointIndex);
    MeshHandle createCentipedeLeg(const CentipedeMechParams& params, int segmentIndex, int legIndex);
    MeshHandle createCentipedeCockpit(const CentipedeMechParams& params);
    std::vector<MeshHandle> createCentipedeWeapons(const CentipedeMechParams& params);
    MeshHandle createCentipedeSensorArray(const CentipedeMechParams& params);
    PhysicsHandle createCentipedeCollider(const CentipedeMechParams& params);
    std::vector<MaterialHandle> createCentipedeMaterials(const CentipedeMechParams& params);
    std::vector<ParticleHandle> createCentipedeVFX(const CentipedeMechParams& params);
    std::vector<AudioHandle> createCentipedeAudio(const CentipedeMechParams& params);
    
    // Centipede simulation helpers
    bool updateCentipedeSegmentPositions(CentipedeMechInstanceState& instance);
    bool updateCentipedeLegIK(CentipedeMechInstanceState& instance);
    bool updateCentipedePhysics(CentipedeMechInstanceState& instance, float deltaTime);
    bool updateCentipedeAnimation(CentipedeMechInstanceState& instance, float deltaTime);
};

} // namespace Mechs
} // namespace MagiTech
