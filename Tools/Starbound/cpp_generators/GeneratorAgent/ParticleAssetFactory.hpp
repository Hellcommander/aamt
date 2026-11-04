#pragma once

#include "ParticleAssetTypes.hpp"
#include "GeneratorConcurrency.hpp"
#include <atomic>
#include <functional>
#include <future>
#include <map>
#include <memory>
#include <mutex>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

namespace MagiTech {
namespace Particles {

class ParticleEmitter;
class ParticleBehavior;
class ParticleRenderer;
class ParticleLOD;
class ParticleShader;
class ParticleCompute;
class ParticleForceFieldManager;
class ParticleCollisionManager;
class ParticleTrailManager;
class ParticleSubEmitterManager;

// Particle Asset Factory
class ParticleAssetFactory {
public:
    ParticleAssetFactory();
    ~ParticleAssetFactory();

    ParticleAssetFactory(const ParticleAssetFactory&) = delete;
    ParticleAssetFactory& operator=(const ParticleAssetFactory&) = delete;

    // Lifecycle: sizes the cache and starts the worker pool. Until initialize()
    // is called, async generation runs inline on the calling thread.
    void initialize(size_t cacheSize, size_t numThreads);
    void shutdown();
    bool isInitialized() const { return m_initialized.load(); }

    // Main async generation function
    std::future<ParticleEffectResult> generateAsync(const ParticleEffectDefinition& definition);

    // Synchronous generation for immediate use
    ParticleEffectResult generate(const ParticleEffectDefinition& definition);

    // Template-based generation
    std::future<ParticleEffectResult> generateFromTemplate(const std::string& templateName,
                                                         const std::map<std::string, float>& parameters);

    // Instance management
    ParticleEffectInstance createInstance(const std::string& templateName,
                                       const glm::vec3& position,
                                       const glm::vec3& rotation = glm::vec3(0),
                                       const glm::vec3& scale = glm::vec3(1));

    void destroyInstance(const std::string& instanceId);
    void updateInstance(const std::string& instanceId, float deltaTime);

    // Template management
    void registerTemplate(const ParticleEffectTemplate& effectTemplate);
    void unregisterTemplate(const std::string& templateName);
    ParticleEffectTemplate getTemplate(const std::string& templateName) const;

    // Force field management
    void addGlobalForceField(const ParticleForceField& forceField);
    void removeGlobalForceField(const std::string& forceFieldId);
    void updateGlobalForceFields(float deltaTime);

    // Collision management
    void addGlobalCollision(const ParticleCollision& collision);
    void removeGlobalCollision(const std::string& collisionId);
    void updateGlobalCollisions(float deltaTime);

    // Cache management
    void clearCache();
    void setCacheSize(size_t maxEntries);
    size_t getCacheSize() const;
    size_t getCacheHits() const;
    size_t getCacheMisses() const;

    // Thread pool management
    void setMaxThreads(int threads);
    int getMaxThreads() const;

    // GPU acceleration
    void enableGPUAcceleration(bool enable);
    bool isGPUAccelerationEnabled() const;

    // Quality settings
    void setParticleQuality(ParticleQuality quality);
    ParticleQuality getParticleQuality() const;

    // Performance monitoring
    ParticlePerformanceMetrics getPerformanceMetrics() const;
    void resetPerformanceMetrics();

    // Error handling
    std::string getLastError() const;
    void clearLastError();

    // Utility functions
    uint64_t hashCombine(const ParticleEffectDefinition& definition) const;

    // Generation status
    bool isGenerating() const;
    float getGenerationProgress() const;

    // Asset validation
    bool validateDefinition(const ParticleEffectDefinition& definition) const;

    // Memory management
    size_t getTotalMemoryUsage() const;
    void setMaxMemoryUsage(size_t maxBytes);
    size_t getMaxMemoryUsage() const;

private:
    // Per-instance simulation state
    struct InstanceRuntime;

    // Core components
    ConcurrentLRUCache<uint64_t, ParticleEffectResult> m_cache{100};
    std::unique_ptr<GeneratorTaskPool> m_pool;

    // Generator components (shader/compute generation is serialized by m_componentMutex)
    std::unique_ptr<ParticleRenderer> m_renderer;
    std::unique_ptr<ParticleLOD> m_lod;
    std::unique_ptr<ParticleShader> m_shader;
    std::unique_ptr<ParticleCompute> m_compute;
    mutable std::mutex m_componentMutex;

    // Manager components (guarded by m_stateMutex)
    std::unique_ptr<ParticleForceFieldManager> m_forceFieldManager;
    std::unique_ptr<ParticleCollisionManager> m_collisionManager;
    ParticleManager m_manager;
    std::unordered_map<std::string, std::unique_ptr<InstanceRuntime>> m_runtimes;
    uint64_t m_nextInstanceId = 1;
    mutable std::mutex m_stateMutex;

    // Settings
    std::atomic<bool> m_initialized{false};
    std::atomic<bool> m_gpuAccelerationEnabled{true};
    std::atomic<int> m_maxThreads{4};
    std::atomic<ParticleQuality> m_particleQuality{ParticleQuality::High};
    std::string m_lastError;
    mutable std::mutex m_errorMutex;

    // Generation tracking
    std::atomic<int> m_activeGenerations{0};
    std::atomic<float> m_generationProgress{0.0f};

    // Statistics
    std::atomic<size_t> m_cacheHits{0};
    std::atomic<size_t> m_cacheMisses{0};
    ParticlePerformanceMetrics m_performanceMetrics;   // guarded by m_stateMutex

    // Memory management
    std::atomic<size_t> m_totalMemoryUsage{0};
    std::atomic<size_t> m_maxMemoryUsage{1024ull * 1024ull * 1024ull};  // 1GB default

    // Internal methods
    void initializeComponents();
    ParticleEffectResult generateInternal(const ParticleEffectDefinition& definition);
    size_t calculateMemoryUsage(const ParticleEffectDefinition& definition) const;
    void setLastError(const std::string& message);
    void removeTemplateFieldsLocked(const std::string& templateName);
    float qualityScale() const;

    // Validation helpers
    bool validateEmitterParams(const EmitterParams& params) const;
    bool validateBehaviorParams(const BehaviorParams& params) const;
    bool validateShapeParams(const ShapeParams& params) const;
    bool validateLifetimeParams(const LifetimeParams& params) const;
    bool validateRenderParams(const RenderParams& params) const;
    bool validateLODParams(const LODParams& params) const;
    bool validateAdvancedParams(const AdvancedParticleParams& params) const;
};

// Particle Emitter
class ParticleEmitter {
public:
    ParticleEmitter();
    ~ParticleEmitter();

    void initialize(const EmitterParams& params);
    void setShape(const ShapeParams& shape);
    void setBehavior(const BehaviorParams& behavior);
    void setLifetime(const LifetimeParams& lifetime);
    void update(float deltaTime);
    void emitParticles(std::vector<Particle>& particles, int count);

    /** Particles to emit this frame (continuous rate plus pending bursts). */
    int consumeEmissionCount(float deltaTime);

    // Emitter state
    bool isActive() const;
    bool isFinished() const;
    float getCurrentTime() const;
    int getEmittedCount() const;

    // Burst mode
    void triggerBurst();
    void setBurstCount(int count);
    void setBurstInterval(float interval);

    // GPU acceleration
    void enableGPU(bool enable);
    bool isGPUEnabled() const;

private:
    EmitterParams m_params;
    ShapeParams m_shape;
    BehaviorParams m_behavior;
    LifetimeParams m_lifetime;
    float m_currentTime;
    float m_lastEmitTime;
    float m_emitAccumulator;
    int m_emittedCount;
    int m_pendingBurst;
    bool m_active;
    bool m_gpuEnabled;
    std::mt19937 m_rng;

    // Burst mode
    bool m_burstMode;
    int m_burstCount;
    float m_burstInterval;
    float m_lastBurstTime;

    // Internal methods
    float random01();
    glm::vec3 calculateEmitPosition();
    glm::vec3 calculateEmitVelocity();
    float calculateEmitRate();
};

// Particle Behavior
class ParticleBehavior {
public:
    ParticleBehavior();
    ~ParticleBehavior();

    void initialize(const BehaviorParams& params);
    void updateParticle(Particle& particle, float deltaTime);
    void updateParticles(std::vector<Particle>& particles, float deltaTime);

    /** Optional external force (e.g. global force fields), evaluated per particle. */
    void setExternalForce(std::function<glm::vec3(const glm::vec3&)> force);
    /** Optional collision resolver, applied when BehaviorParams::collision is set. */
    void setCollisionResolver(std::function<void(Particle&)> resolver);

    // Physics parameters
    void setGravity(float gravity);
    void setDrag(float drag);
    void setWind(const glm::vec3& wind);
    void setTurbulence(float strength);

    // Attractor system
    void setAttractor(const glm::vec3& position, float strength, float radius);
    void clearAttractor();

    // GPU acceleration
    void enableGPU(bool enable);
    bool isGPUEnabled() const;

private:
    BehaviorParams m_params;
    bool m_gpuEnabled;
    std::function<glm::vec3(const glm::vec3&)> m_externalForce;
    std::function<void(Particle&)> m_collisionResolver;

    // Internal methods
    glm::vec3 calculateForces(const Particle& particle);
    glm::vec3 calculateAttractorForce(const Particle& particle);
    glm::vec3 calculateTurbulenceForce(const Particle& particle);
    void applyCollision(Particle& particle);
};

// Particle Renderer (CPU side: prepares per-particle render state and tracks stats)
class ParticleRenderer {
public:
    ParticleRenderer();
    ~ParticleRenderer();

    void initialize(const RenderParams& params);
    void prepareParticles(std::vector<Particle>& particles);
    void renderParticles(const std::vector<Particle>& particles);

    // Texture management
    void setTexture(const std::string& path);
    void setNormalMap(const std::string& path);
    void setEmissionMap(const std::string& path);

    // Rendering options
    void setBillboard(bool enabled);
    void setAlignToCamera(bool enabled);
    void setSoftParticles(bool enabled);
    void setAdditive(bool enabled);
    void setMultiply(bool enabled);

    // Effects
    void setDistortion(bool enabled, float strength);
    void setGlow(bool enabled, float intensity);

    // GPU acceleration
    void enableGPU(bool enable);
    bool isGPUEnabled() const;

    // Performance
    float getRenderTime() const;
    int getDrawCalls() const;

private:
    RenderParams m_params;
    bool m_gpuEnabled;
    float m_renderTime;
    int m_drawCalls;

    // Internal methods
    void updateParticleColor(Particle& particle);
    void updateParticleSize(Particle& particle);
    void updateParticleUV(Particle& particle);
    void applySoftParticles(Particle& particle);
    void applyDistortion(Particle& particle);
    void applyGlow(Particle& particle);
};

// Particle LOD
class ParticleLOD {
public:
    ParticleLOD();
    ~ParticleLOD();

    void initialize(const LODParams& params);
    int selectLOD(float screenSize) const;
    float getRateScale(int lodLevel) const;
    float getQualityScale(int lodLevel) const;
    int getMaxParticles(int lodLevel) const;
    float getCullDistance(int lodLevel) const;

    // Adaptive LOD
    void enableAdaptive(bool enabled);
    void setAdaptiveThreshold(float threshold);
    bool isAdaptiveEnabled() const;

    // LOD statistics
    int getLODCount() const;
    float getScreenThreshold(int lodLevel) const;

private:
    LODParams m_params;
    bool m_adaptiveEnabled;
    float m_adaptiveThreshold;
};

// Particle Shader (generates GLSL sources and tracks them by handle)
class ParticleShader {
public:
    ParticleShader();
    ~ParticleShader();

    ShaderHandle compileShader(const RenderParams& params, bool isVertex = false);
    void setShaderParameters(ShaderHandle shader, const RenderParams& params);
    std::string getShaderSource(ShaderHandle shader) const;

    // Shader management
    void setOptimizationLevel(int level);
    void enableDebugInfo(bool enable);

    // Error handling
    std::string getCompilationErrors() const;
    bool hasCompilationErrors() const;

private:
    int m_optimizationLevel;
    bool m_debugInfoEnabled;
    std::string m_compilationErrors;
    ShaderHandle m_nextHandle;
    std::unordered_map<ShaderHandle, std::string> m_sources;
    std::unordered_map<ShaderHandle, std::map<std::string, float>> m_parameters;

    // Internal methods
    std::string generateVertexShader(const RenderParams& params);
    std::string generateFragmentShader(const RenderParams& params);
    std::string generateGeometryShader(const RenderParams& params);
};

// Particle Compute (generates compute sources; dispatch needs a GPU backend)
class ParticleCompute {
public:
    ParticleCompute();
    ~ParticleCompute();

    ComputeShaderHandle compileComputeShader(const std::string& source);
    void dispatchCompute(const ComputeShaderHandle& shader, int particleCount);

    // Compute shader management
    void setWorkGroupSize(int size);
    int getWorkGroupSize() const;

    // Performance
    float getComputeTime() const;
    bool isComputeAvailable() const;

    // Source generation
    std::string generateUpdateShader(const BehaviorParams& params);
    std::string generateEmitShader(const EmitterParams& params);

private:
    int m_workGroupSize;
    float m_computeTime;
    bool m_computeAvailable;
    ComputeShaderHandle m_nextHandle;
    std::unordered_map<ComputeShaderHandle, std::string> m_sources;
};

// Global force field set (data in ParticleForceField)
class ParticleForceFieldManager {
public:
    ParticleForceFieldManager();
    ~ParticleForceFieldManager();

    void addForceField(const ParticleForceField& forceField);
    void removeForceField(const std::string& id);
    void updateForceFields(float deltaTime);
    glm::vec3 computeForce(const glm::vec3& position) const;
    const std::vector<ParticleForceField>& fields() const { return m_forceFields; }

    // Force field types
    void addGravityField(const glm::vec3& position, float strength, float radius);
    void addWindField(const glm::vec3& position, const glm::vec3& direction, float strength, float radius);
    void addTurbulenceField(const glm::vec3& position, float strength, float radius);
    void addAttractorField(const glm::vec3& position, float strength, float radius);
    void addRepulsorField(const glm::vec3& position, float strength, float radius);
    void addVortexField(const glm::vec3& position, const glm::vec3& axis, float strength, float radius);

    // Custom force fields
    void addCustomField(const std::string& id,
                       std::function<glm::vec3(const glm::vec3&, float)> forceFunc,
                       const glm::vec3& position, float radius);

private:
    std::vector<ParticleForceField> m_forceFields;
    float m_time;
    uint64_t m_nextAutoId;

    std::string makeId(const char* prefix);
    float attenuation(const glm::vec3& position, const ParticleForceField& field) const;

    // Internal methods
    glm::vec3 calculateGravityForce(const glm::vec3& position, const ParticleForceField& field) const;
    glm::vec3 calculateWindForce(const glm::vec3& position, const ParticleForceField& field) const;
    glm::vec3 calculateTurbulenceForce(const glm::vec3& position, const ParticleForceField& field) const;
    glm::vec3 calculateAttractorForce(const glm::vec3& position, const ParticleForceField& field) const;
    glm::vec3 calculateRepulsorForce(const glm::vec3& position, const ParticleForceField& field) const;
    glm::vec3 calculateVortexForce(const glm::vec3& position, const ParticleForceField& field) const;
};

// Global collider set (data in ParticleCollision)
class ParticleCollisionManager {
public:
    ParticleCollisionManager();
    ~ParticleCollisionManager();

    void addCollision(const ParticleCollision& collision);
    void removeCollision(const std::string& id);
    void updateCollisions(float deltaTime);
    void resolveAll(Particle& particle);
    const std::vector<ParticleCollision>& collisions() const { return m_collisions; }

    // Collision types
    void addSphereCollision(const glm::vec3& position, float radius, float restitution = 0.5f);
    void addBoxCollision(const glm::vec3& position, const glm::vec3& dimensions, float restitution = 0.5f);
    void addPlaneCollision(const glm::vec3& position, const glm::vec3& normal, float restitution = 0.5f);
    void addMeshCollision(const std::string& meshPath, const glm::vec3& position, float restitution = 0.5f);

    // Collision response
    void resolveCollision(Particle& particle, const ParticleCollision& collision);

private:
    std::vector<ParticleCollision> m_collisions;
    uint64_t m_nextAutoId;

    std::string makeId(const char* prefix);

    // Internal methods
    bool checkSphereCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkBoxCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkPlaneCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkMeshCollision(const Particle& particle, const ParticleCollision& collision);
    glm::vec3 calculateCollisionResponse(const Particle& particle, const ParticleCollision& collision);
};

// Trail history for one particle
class ParticleTrailManager {
public:
    ParticleTrailManager();
    ~ParticleTrailManager();

    void initialize(const ParticleTrail& trail);
    void updateTrail(Particle& particle, float deltaTime);
    void renderTrail(const Particle& particle);
    const std::vector<glm::vec3>& points() const { return m_trailPoints; }

    // Trail properties
    void setMaxPoints(int maxPoints);
    void setFadeTime(float fadeTime);
    void setWidth(float width);
    void setColor(const glm::vec4& color);

    // Texture support
    void setTexture(const std::string& path);
    void enableTexture(bool enabled);

private:
    ParticleTrail m_trail;
    std::vector<glm::vec3> m_trailPoints;
    std::vector<float> m_trailAges;
    int m_renderedSegments;

    // Internal methods
    void addTrailPoint(const glm::vec3& position);
    void updateTrailAges(float deltaTime);
    void removeOldPoints();
    void renderTrailMesh();
};

// Spawns secondary effects from a parent particle
class ParticleSubEmitterManager {
public:
    using SpawnCallback = std::function<void(const std::string& effectName, const glm::vec3& position,
                                             const glm::vec3& velocity, float rotation,
                                             const glm::vec4& color, float size)>;

    ParticleSubEmitterManager();
    ~ParticleSubEmitterManager();

    void initialize(const ParticleSubEmitter& subEmitter);
    void setSpawnCallback(SpawnCallback callback);
    void updateSubEmitter(Particle& parentParticle, float deltaTime);

    // Sub-emitter properties
    void setEffectName(const std::string& effectName);
    void setProbability(float probability);
    void setOffset(const glm::vec3& offset);

    // Inheritance
    void setInheritVelocity(bool inherit);
    void setInheritRotation(bool inherit);
    void setInheritColor(bool inherit);
    void setInheritSize(bool inherit);

private:
    ParticleSubEmitter m_subEmitter;
    SpawnCallback m_spawnCallback;
    float m_lastEmitTime;
    std::mt19937 m_rng;

    // Internal methods
    bool shouldEmit(float deltaTime);
    glm::vec3 calculateInheritedPosition(const Particle& parentParticle);
    glm::vec3 calculateInheritedVelocity(const Particle& parentParticle);
    float calculateInheritedRotation(const Particle& parentParticle);
    glm::vec4 calculateInheritedColor(const Particle& parentParticle);
    float calculateInheritedSize(const Particle& parentParticle);
};

} // namespace Particles
} // namespace MagiTech
