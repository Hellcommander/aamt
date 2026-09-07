#pragma once

#include "ParticleAssetTypes.hpp"
#include <memory>
#include <future>
#include <unordered_map>
#include <string>
#include <functional>

namespace MagiTech {
namespace Particles {

// Forward declarations
class ConcurrentLRU;
class ThreadPool;
class ParticleEmitter;
class ParticleBehavior;
class ParticleRenderer;
class ParticleLOD;
class ParticleShader;
class ParticleCompute;
class ParticleForceField;
class ParticleCollision;
class ParticleTrail;
class ParticleSubEmitter;

// Particle Asset Factory
class ParticleAssetFactory {
public:
    ParticleAssetFactory();
    ~ParticleAssetFactory();
    
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
    void registerTemplate(const ParticleEffectTemplate& template);
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
    // Core components
    std::unique_ptr<ConcurrentLRU<uint64_t, ParticleEffectResult>> m_cache;
    std::unique_ptr<ThreadPool> m_pool;
    
    // Generator components
    std::unique_ptr<ParticleEmitter> m_emitter;
    std::unique_ptr<ParticleBehavior> m_behavior;
    std::unique_ptr<ParticleRenderer> m_renderer;
    std::unique_ptr<ParticleLOD> m_lod;
    std::unique_ptr<ParticleShader> m_shader;
    std::unique_ptr<ParticleCompute> m_compute;
    
    // Manager components
    std::unique_ptr<ParticleForceField> m_forceFieldManager;
    std::unique_ptr<ParticleCollision> m_collisionManager;
    std::unique_ptr<ParticleTrail> m_trailManager;
    std::unique_ptr<ParticleSubEmitter> m_subEmitterManager;
    
    // Settings
    bool m_gpuAccelerationEnabled;
    int m_maxThreads;
    ParticleQuality m_particleQuality;
    std::string m_lastError;
    
    // Generation tracking
    bool m_isGenerating;
    float m_generationProgress;
    
    // Statistics
    size_t m_cacheHits;
    size_t m_cacheMisses;
    ParticlePerformanceMetrics m_performanceMetrics;
    
    // Memory management
    size_t m_totalMemoryUsage;
    size_t m_maxMemoryUsage;
    
    // Internal methods
    void initializeComponents();
    ParticleEffectResult generateInternal(const ParticleEffectDefinition& definition);
    
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
    void update(float deltaTime);
    void emitParticles(std::vector<Particle>& particles, int count);
    
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
    float m_currentTime;
    float m_lastEmitTime;
    int m_emittedCount;
    bool m_active;
    bool m_gpuEnabled;
    
    // Burst mode
    bool m_burstMode;
    int m_burstCount;
    float m_burstInterval;
    float m_lastBurstTime;
    
    // Internal methods
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
    
    // Internal methods
    glm::vec3 calculateForces(const Particle& particle);
    glm::vec3 calculateAttractorForce(const Particle& particle);
    glm::vec3 calculateTurbulenceForce(const Particle& particle);
    void applyCollision(Particle& particle);
};

// Particle Renderer
class ParticleRenderer {
public:
    ParticleRenderer();
    ~ParticleRenderer();
    
    void initialize(const RenderParams& params);
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

// Particle Shader
class ParticleShader {
public:
    ParticleShader();
    ~ParticleShader();
    
    ShaderHandle compileShader(const RenderParams& params, bool isVertex = false);
    void setShaderParameters(ShaderHandle shader, const RenderParams& params);
    
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
    
    // Internal methods
    std::string generateVertexShader(const RenderParams& params);
    std::string generateFragmentShader(const RenderParams& params);
    std::string generateGeometryShader(const RenderParams& params);
};

// Particle Compute
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
    
private:
    int m_workGroupSize;
    float m_computeTime;
    bool m_computeAvailable;
    
    // Internal methods
    std::string generateUpdateShader(const BehaviorParams& params);
    std::string generateEmitShader(const EmitterParams& params);
};

// Particle Force Field
class ParticleForceField {
public:
    ParticleForceField();
    ~ParticleForceField();
    
    void addForceField(const ParticleForceField& forceField);
    void removeForceField(const std::string& id);
    void updateForceFields(float deltaTime);
    
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
    
    // Internal methods
    glm::vec3 calculateGravityForce(const glm::vec3& position, const ParticleForceField& field);
    glm::vec3 calculateWindForce(const glm::vec3& position, const ParticleForceField& field);
    glm::vec3 calculateTurbulenceForce(const glm::vec3& position, const ParticleForceField& field);
    glm::vec3 calculateAttractorForce(const glm::vec3& position, const ParticleForceField& field);
    glm::vec3 calculateRepulsorForce(const glm::vec3& position, const ParticleForceField& field);
    glm::vec3 calculateVortexForce(const glm::vec3& position, const ParticleForceField& field);
};

// Particle Collision
class ParticleCollision {
public:
    ParticleCollision();
    ~ParticleCollision();
    
    void addCollision(const ParticleCollision& collision);
    void removeCollision(const std::string& id);
    void updateCollisions(float deltaTime);
    
    // Collision types
    void addSphereCollision(const glm::vec3& position, float radius, float restitution = 0.5f);
    void addBoxCollision(const glm::vec3& position, const glm::vec3& dimensions, float restitution = 0.5f);
    void addPlaneCollision(const glm::vec3& position, const glm::vec3& normal, float restitution = 0.5f);
    void addMeshCollision(const std::string& meshPath, const glm::vec3& position, float restitution = 0.5f);
    
    // Collision response
    void resolveCollision(Particle& particle, const ParticleCollision& collision);
    
private:
    std::vector<ParticleCollision> m_collisions;
    
    // Internal methods
    bool checkSphereCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkBoxCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkPlaneCollision(const Particle& particle, const ParticleCollision& collision);
    bool checkMeshCollision(const Particle& particle, const ParticleCollision& collision);
    glm::vec3 calculateCollisionResponse(const Particle& particle, const ParticleCollision& collision);
};

// Particle Trail
class ParticleTrail {
public:
    ParticleTrail();
    ~ParticleTrail();
    
    void initialize(const ParticleTrail& trail);
    void updateTrail(Particle& particle, float deltaTime);
    void renderTrail(const Particle& particle);
    
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
    
    // Internal methods
    void addTrailPoint(const glm::vec3& position);
    void updateTrailAges(float deltaTime);
    void removeOldPoints();
    void renderTrailMesh();
};

// Particle Sub-Emitter
class ParticleSubEmitter {
public:
    ParticleSubEmitter();
    ~ParticleSubEmitter();
    
    void initialize(const ParticleSubEmitter& subEmitter);
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
    float m_lastEmitTime;
    
    // Internal methods
    bool shouldEmit(float deltaTime);
    glm::vec3 calculateInheritedPosition(const Particle& parentParticle);
    glm::vec3 calculateInheritedVelocity(const Particle& parentParticle);
    float calculateInheritedRotation(const Particle& parentParticle);
    glm::vec4 calculateInheritedColor(const Particle& parentParticle);
    float calculateInheritedSize(const Particle& parentParticle);
};

// Global factory instance
extern ParticleAssetFactory particleFactory;

} // namespace Particles
} // namespace MagiTech
