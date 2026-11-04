#include "ParticleAssetFactory.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <deque>
#include <numbers>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace MagiTech {
namespace Particles {

namespace {
    constexpr float kPi = std::numbers::pi_v<float>;

    float elapsedMs(std::chrono::steady_clock::time_point since) {
        return std::chrono::duration<float, std::milli>(std::chrono::steady_clock::now() - since).count();
    }
}

// ============================================================================
// ParticleAssetFactory
// ============================================================================

struct ParticleAssetFactory::InstanceRuntime {
    ParticleEmitter emitter;
    ParticleBehavior behavior;
    ParticleRenderer renderer;
    ParticleLOD lod;
    std::vector<ParticleSubEmitterManager> subEmitters;
    std::vector<Particle> particles;
    struct PendingSpawn {
        std::string effectName;
        glm::vec3 position;
    };
    std::vector<PendingSpawn> pendingSpawns;
    int maxParticles = 1000;
};

ParticleAssetFactory::ParticleAssetFactory() {
    initializeComponents();
}

ParticleAssetFactory::~ParticleAssetFactory() {
    shutdown();
}

void ParticleAssetFactory::initializeComponents() {
    // The pool is created stopped: tasks run inline until initialize() starts it.
    m_pool = std::make_unique<GeneratorTaskPool>();

    m_renderer = std::make_unique<ParticleRenderer>();
    m_lod = std::make_unique<ParticleLOD>();
    m_shader = std::make_unique<ParticleShader>();
    m_compute = std::make_unique<ParticleCompute>();

    m_forceFieldManager = std::make_unique<ParticleForceFieldManager>();
    m_collisionManager = std::make_unique<ParticleCollisionManager>();
}

void ParticleAssetFactory::initialize(size_t cacheSize, size_t numThreads) {
    if (m_initialized.exchange(true)) return;
    m_cache.set_capacity(cacheSize);
    m_maxThreads = static_cast<int>(numThreads);
    m_pool->start(numThreads);
}

void ParticleAssetFactory::shutdown() {
    if (!m_initialized.exchange(false)) return;
    m_pool->stop();
}

std::future<ParticleEffectResult> ParticleAssetFactory::generateAsync(const ParticleEffectDefinition& definition) {
    return m_pool->enqueue([this, definition]() {
        return generateInternal(definition);
    });
}

ParticleEffectResult ParticleAssetFactory::generate(const ParticleEffectDefinition& definition) {
    return generateInternal(definition);
}

ParticleEffectResult ParticleAssetFactory::generateInternal(const ParticleEffectDefinition& definition) {
    ++m_activeGenerations;
    struct GenerationGuard {
        ParticleAssetFactory& self;
        ~GenerationGuard() {
            if (--self.m_activeGenerations == 0) self.m_generationProgress = 0.0f;
        }
    } guard{*this};

    try {
        m_generationProgress = 0.0f;

        // Check cache first
        const uint64_t hash = hashCombine(definition);
        if (definition.enableCaching) {
            if (auto cached = m_cache.find(hash)) {
                m_cacheHits++;
                return *cached;
            }
            m_cacheMisses++;
        }

        // Validate definition
        if (!validateDefinition(definition)) {
            throw std::runtime_error("Invalid particle effect definition");
        }

        if (m_totalMemoryUsage.load() + calculateMemoryUsage(definition) > m_maxMemoryUsage.load()) {
            throw std::runtime_error("Particle memory budget exceeded");
        }

        m_generationProgress = 0.1f;

        // Generate particle system
        ParticleBundle bundle;
        bundle.system = static_cast<ParticleSystemHandle>(hash ^ (hash >> 32));
        bundle.gpuAccelerated = m_gpuAccelerationEnabled.load();
        bundle.creationTime = std::chrono::system_clock::now();
        bundle.metadata = definition.metadata;
        bundle.metadata["name"] = definition.name;
        bundle.metadata["category"] = definition.category;

        m_generationProgress = 0.3f;

        // Calculate LOD data
        const float quality = qualityScale();
        bundle.lodData.screenSizes = definition.lod.screenSizes;
        bundle.lodData.rateScales = definition.lod.rateScales;
        bundle.lodData.qualityScales = definition.lod.qualityScales;

        // Generate LOD variants (missing per-level scales default to 1)
        for (size_t i = 0; i < definition.lod.screenSizes.size(); ++i) {
            const float rateScale = i < definition.lod.rateScales.size() ? definition.lod.rateScales[i] : 1.0f;
            const float qualityScaleLevel = i < definition.lod.qualityScales.size() ? definition.lod.qualityScales[i] : 1.0f;
            bundle.lodData.maxParticles.push_back(static_cast<int>(1000.0f * rateScale * quality));
            bundle.lodData.cullDistances.push_back(50.0f * qualityScaleLevel);
        }

        m_generationProgress = 0.6f;

        // Generate shaders if GPU acceleration is enabled
        std::vector<std::string> warnings;
        if (bundle.gpuAccelerated) {
            std::lock_guard<std::mutex> lock(m_componentMutex);
            bundle.shader = m_shader->compileShader(definition.render, false);
            m_shader->setShaderParameters(bundle.shader, definition.render);
            if (m_shader->hasCompilationErrors()) {
                warnings.push_back(m_shader->getCompilationErrors());
            }
            bundle.computeShader = m_compute->compileComputeShader(
                m_compute->generateUpdateShader(definition.behavior));
        }

        m_generationProgress = 0.8f;

        // Calculate memory usage
        bundle.memoryUsage = calculateMemoryUsage(definition);
        m_totalMemoryUsage += bundle.memoryUsage;

        // Create result
        ParticleEffectResult result;
        result.bundle = bundle;
        result.definition = definition;
        result.processingTime = std::chrono::system_clock::now();
        result.success = true;
        result.warnings = std::move(warnings);

        m_generationProgress = 1.0f;

        // Cache the result
        if (definition.enableCaching) {
            m_cache.insert(hash, result);
        }

        return result;

    } catch (const std::exception& e) {
        setLastError(e.what());
        ParticleEffectResult result;
        result.definition = definition;
        result.processingTime = std::chrono::system_clock::now();
        result.success = false;
        result.errorMessage = e.what();
        return result;
    }
}

std::future<ParticleEffectResult> ParticleAssetFactory::generateFromTemplate(
    const std::string& templateName, const std::map<std::string, float>& parameters) {
    ParticleEffectDefinition definition;
    {
        std::lock_guard<std::mutex> lock(m_stateMutex);
        auto it = m_manager.templates.find(templateName);
        if (it == m_manager.templates.end()) {
            std::promise<ParticleEffectResult> failed;
            ParticleEffectResult result;
            result.success = false;
            result.errorMessage = "Unknown particle template: " + templateName;
            setLastError(result.errorMessage);
            failed.set_value(std::move(result));
            return failed.get_future();
        }
        definition = it->second.baseDefinition;
    }

    // Known parameter names override definition fields; everything else is
    // forwarded to the emitter's custom parameters.
    for (const auto& [key, value] : parameters) {
        if (key == "rate") definition.emitter.rate = value;
        else if (key == "duration") definition.emitter.duration = value;
        else if (key == "burstCount") definition.emitter.burstCount = static_cast<int>(value);
        else if (key == "gravity") definition.behavior.gravity = value;
        else if (key == "drag") definition.behavior.drag = value;
        else if (key == "turbulenceStrength") definition.behavior.turbulenceStrength = value;
        else if (key == "radius") definition.shape.radius = value;
        else if (key == "minLife") definition.lifetime.minLife = value;
        else if (key == "maxLife") definition.lifetime.maxLife = value;
        else if (key == "glowIntensity") definition.render.glowIntensity = value;
        else definition.emitter.customParameters[key] = value;
    }
    return generateAsync(definition);
}

ParticleEffectInstance ParticleAssetFactory::createInstance(const std::string& templateName,
                                                            const glm::vec3& position,
                                                            const glm::vec3& rotation,
                                                            const glm::vec3& scale) {
    ParticleEffectTemplate effectTemplate;
    {
        std::lock_guard<std::mutex> lock(m_stateMutex);
        auto it = m_manager.templates.find(templateName);
        if (it == m_manager.templates.end()) {
            setLastError("Unknown particle template: " + templateName);
            return ParticleEffectInstance{};
        }
        if (static_cast<int>(m_manager.instances.size()) >= m_manager.maxInstances) {
            setLastError("Particle instance limit reached");
            return ParticleEffectInstance{};
        }
        effectTemplate = it->second;
    }

    ParticleEffectInstance instance;
    instance.templateName = templateName;
    instance.definition = effectTemplate.baseDefinition;
    instance.definition.emitter.position = position;
    instance.definition.emitter.rotation = rotation;
    instance.definition.emitter.scale = scale;
    instance.position = position;
    instance.rotation = rotation;
    instance.scale = scale;
    instance.active = true;
    instance.duration = instance.definition.emitter.duration;
    instance.state.isActive = true;

    // Generate (or fetch) the GPU-side assets for this definition
    ParticleEffectResult generated = generateInternal(instance.definition);
    if (!generated.success) {
        return ParticleEffectInstance{};
    }

    auto runtime = std::make_unique<InstanceRuntime>();
    runtime->emitter.initialize(instance.definition.emitter);
    runtime->emitter.setShape(instance.definition.shape);
    runtime->emitter.setBehavior(instance.definition.behavior);
    runtime->emitter.setLifetime(instance.definition.lifetime);
    runtime->behavior.initialize(instance.definition.behavior);
    runtime->renderer.initialize(instance.definition.render);
    runtime->lod.initialize(instance.definition.lod);
    runtime->maxParticles = std::min(effectTemplate.advanced.maxParticles,
                                     generated.bundle.lodData.maxParticles.empty()
                                         ? effectTemplate.advanced.maxParticles
                                         : generated.bundle.lodData.maxParticles.front());
    InstanceRuntime* raw = runtime.get();
    for (const auto& sub : effectTemplate.subEmitters) {
        ParticleSubEmitterManager manager;
        manager.initialize(sub);
        manager.setSpawnCallback([raw](const std::string& effectName, const glm::vec3& pos,
                                       const glm::vec3&, float, const glm::vec4&, float) {
            raw->pendingSpawns.push_back({effectName, pos});
        });
        raw->subEmitters.push_back(std::move(manager));
    }

    std::lock_guard<std::mutex> lock(m_stateMutex);
    instance.id = templateName + "#" + std::to_string(m_nextInstanceId++);
    raw->behavior.setExternalForce([this](const glm::vec3& p) {
        return m_manager.enableGlobalForces ? m_forceFieldManager->computeForce(p) : glm::vec3(0.0f);
    });
    raw->behavior.setCollisionResolver([this](Particle& particle) {
        if (m_manager.enableGlobalCollisions) m_collisionManager->resolveAll(particle);
    });
    instance.startTime = m_manager.globalTime;
    m_manager.instances[instance.id] = instance;
    m_runtimes[instance.id] = std::move(runtime);
    m_manager.totalMemoryUsage += generated.bundle.memoryUsage;
    return instance;
}

void ParticleAssetFactory::destroyInstance(const std::string& instanceId) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_manager.instances.erase(instanceId);
    m_runtimes.erase(instanceId);
}

void ParticleAssetFactory::updateInstance(const std::string& instanceId, float deltaTime) {
    const auto start = std::chrono::steady_clock::now();
    std::vector<std::pair<std::string, glm::vec3>> spawns;
    {
        std::lock_guard<std::mutex> lock(m_stateMutex);
        auto instIt = m_manager.instances.find(instanceId);
        auto rtIt = m_runtimes.find(instanceId);
        if (instIt == m_manager.instances.end() || rtIt == m_runtimes.end()) return;

        ParticleEffectInstance& instance = instIt->second;
        InstanceRuntime& rt = *rtIt->second;
        if (!instance.active || instance.state.isPaused) return;

        m_manager.globalTime += deltaTime;
        instance.state.currentTime += deltaTime;

        // Emission
        rt.emitter.update(deltaTime);
        int toEmit = rt.emitter.consumeEmissionCount(deltaTime);
        const int capacity = std::max(0, rt.maxParticles - static_cast<int>(rt.particles.size()));
        toEmit = std::min(toEmit, capacity);
        if (toEmit > 0) rt.emitter.emitParticles(rt.particles, toEmit);

        // Simulation
        rt.behavior.updateParticles(rt.particles, deltaTime);
        for (auto& sub : rt.subEmitters) {
            for (auto& particle : rt.particles) {
                if (particle.active) sub.updateSubEmitter(particle, deltaTime);
            }
        }
        rt.particles.erase(std::remove_if(rt.particles.begin(), rt.particles.end(),
                                          [](const Particle& p) { return !p.active; }),
                           rt.particles.end());
        const float updateMs = elapsedMs(start);

        // Rendering preparation
        const auto renderStart = std::chrono::steady_clock::now();
        rt.renderer.prepareParticles(rt.particles);
        rt.renderer.renderParticles(rt.particles);
        const float renderMs = elapsedMs(renderStart);

        // Loop or finish
        if (rt.emitter.isFinished() && rt.particles.empty()) {
            if (instance.definition.emitter.loop) {
                instance.loopCount++;
                rt.emitter.initialize(instance.definition.emitter);
            } else {
                instance.active = false;
            }
        }

        instance.state.activeParticles = static_cast<uint32_t>(rt.particles.size());
        instance.state.totalParticles = static_cast<uint32_t>(rt.emitter.getEmittedCount());
        instance.state.updateTime = updateMs;
        instance.state.renderTime = renderMs;
        instance.state.memoryUsage = static_cast<float>(rt.particles.capacity() * sizeof(Particle));
        instance.state.isActive = instance.active;
        instance.state.currentLOD = 0;

        m_performanceMetrics.updateTime = updateMs;
        m_performanceMetrics.renderTime = renderMs;
        m_performanceMetrics.cpuTime = updateMs + renderMs;
        m_performanceMetrics.frameTime = elapsedMs(start);
        m_performanceMetrics.drawCalls = rt.renderer.getDrawCalls();
        m_performanceMetrics.activeParticles = static_cast<int>(rt.particles.size());
        m_performanceMetrics.totalParticles = rt.emitter.getEmittedCount();
        m_performanceMetrics.memoryUsage = m_totalMemoryUsage.load();
        m_performanceMetrics.gpuAccelerated = m_gpuAccelerationEnabled.load();
        m_performanceMetrics.lodLevel = instance.state.currentLOD;

        for (auto& spawn : rt.pendingSpawns) spawns.emplace_back(std::move(spawn.effectName), spawn.position);
        rt.pendingSpawns.clear();
    }

    // Sub-emitter spawns create new instances outside the state lock
    for (const auto& [effectName, position] : spawns) {
        createInstance(effectName, position);
    }
}

void ParticleAssetFactory::registerTemplate(const ParticleEffectTemplate& effectTemplate) {
    if (effectTemplate.name.empty()) {
        setLastError("Particle template needs a name");
        return;
    }
    if (!validateAdvancedParams(effectTemplate.advanced)) {
        setLastError("Invalid advanced parameters for template " + effectTemplate.name);
        return;
    }
    std::lock_guard<std::mutex> lock(m_stateMutex);
    removeTemplateFieldsLocked(effectTemplate.name);
    // Template force fields and colliders join the global sets while the template is registered
    for (size_t i = 0; i < effectTemplate.forceFields.size(); ++i) {
        ParticleForceField field = effectTemplate.forceFields[i];
        field.id = effectTemplate.name + ".field." + std::to_string(i);
        m_forceFieldManager->addForceField(field);
    }
    for (size_t i = 0; i < effectTemplate.collisions.size(); ++i) {
        ParticleCollision collision = effectTemplate.collisions[i];
        collision.id = effectTemplate.name + ".collision." + std::to_string(i);
        m_collisionManager->addCollision(collision);
    }
    m_manager.globalForceFields = m_forceFieldManager->fields();
    m_manager.globalCollisions = m_collisionManager->collisions();
    m_manager.templates[effectTemplate.name] = effectTemplate;
}

void ParticleAssetFactory::unregisterTemplate(const std::string& templateName) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    removeTemplateFieldsLocked(templateName);
    m_manager.globalForceFields = m_forceFieldManager->fields();
    m_manager.globalCollisions = m_collisionManager->collisions();
    m_manager.templates.erase(templateName);
}

void ParticleAssetFactory::removeTemplateFieldsLocked(const std::string& templateName) {
    auto it = m_manager.templates.find(templateName);
    if (it == m_manager.templates.end()) return;
    for (size_t i = 0; i < it->second.forceFields.size(); ++i) {
        m_forceFieldManager->removeForceField(templateName + ".field." + std::to_string(i));
    }
    for (size_t i = 0; i < it->second.collisions.size(); ++i) {
        m_collisionManager->removeCollision(templateName + ".collision." + std::to_string(i));
    }
}

ParticleEffectTemplate ParticleAssetFactory::getTemplate(const std::string& templateName) const {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    auto it = m_manager.templates.find(templateName);
    return it != m_manager.templates.end() ? it->second : ParticleEffectTemplate{};
}

void ParticleAssetFactory::addGlobalForceField(const ParticleForceField& forceField) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_forceFieldManager->addForceField(forceField);
    m_manager.globalForceFields = m_forceFieldManager->fields();
}

void ParticleAssetFactory::removeGlobalForceField(const std::string& forceFieldId) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_forceFieldManager->removeForceField(forceFieldId);
    m_manager.globalForceFields = m_forceFieldManager->fields();
}

void ParticleAssetFactory::updateGlobalForceFields(float deltaTime) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_forceFieldManager->updateForceFields(deltaTime);
}

void ParticleAssetFactory::addGlobalCollision(const ParticleCollision& collision) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_collisionManager->addCollision(collision);
    m_manager.globalCollisions = m_collisionManager->collisions();
}

void ParticleAssetFactory::removeGlobalCollision(const std::string& collisionId) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_collisionManager->removeCollision(collisionId);
    m_manager.globalCollisions = m_collisionManager->collisions();
}

void ParticleAssetFactory::updateGlobalCollisions(float deltaTime) {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_collisionManager->updateCollisions(deltaTime);
    m_manager.globalCollisions = m_collisionManager->collisions();
}

// Utility functions
uint64_t ParticleAssetFactory::hashCombine(const ParticleEffectDefinition& definition) const {
    uint64_t hash = definition.hashKey();
    // Quality and GPU mode change the generated bundle, so they are part of the key.
    hash ^= static_cast<uint64_t>(m_particleQuality.load()) + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
    hash ^= static_cast<uint64_t>(m_gpuAccelerationEnabled.load()) + 0x9e3779b97f4a7c15ULL + (hash << 6) + (hash >> 2);
    return hash;
}

bool ParticleAssetFactory::validateDefinition(const ParticleEffectDefinition& definition) const {
    return validateEmitterParams(definition.emitter) &&
           validateBehaviorParams(definition.behavior) &&
           validateShapeParams(definition.shape) &&
           validateLifetimeParams(definition.lifetime) &&
           validateRenderParams(definition.render) &&
           validateLODParams(definition.lod);
}

bool ParticleAssetFactory::validateEmitterParams(const EmitterParams& params) const {
    // Negative duration means "infinite" (looping effects such as fire).
    return params.rate >= 0.0f && params.burstCount >= 0 && params.burstInterval >= 0.0f;
}

bool ParticleAssetFactory::validateBehaviorParams(const BehaviorParams& params) const {
    return params.gravity >= -100.0f && params.gravity <= 100.0f && params.drag >= 0.0f;
}

bool ParticleAssetFactory::validateShapeParams(const ShapeParams& params) const {
    return params.dimensions.x >= 0.0f && params.dimensions.y >= 0.0f && params.dimensions.z >= 0.0f &&
           params.radius >= 0.0f && params.innerRadius >= 0.0f &&
           (params.type != ShapeParams::CustomMesh || !params.meshPath.empty());
}

bool ParticleAssetFactory::validateLifetimeParams(const LifetimeParams& params) const {
    return params.minLife >= 0.0f && params.maxLife >= params.minLife;
}

bool ParticleAssetFactory::validateRenderParams(const RenderParams& params) const {
    return !params.texturePath.empty() && params.frameCount >= 1;
}

bool ParticleAssetFactory::validateLODParams(const LODParams& params) const {
    // An empty LOD table means a single LOD level; otherwise the per-level scale
    // tables may not have more entries than there are levels.
    if (params.screenSizes.empty()) {
        return params.rateScales.empty() && params.qualityScales.empty();
    }
    return params.rateScales.size() <= params.screenSizes.size() &&
           params.qualityScales.size() <= params.screenSizes.size();
}

bool ParticleAssetFactory::validateAdvancedParams(const AdvancedParticleParams& params) const {
    return params.maxParticles > 0 && params.batchSize > 0 && params.cullDistance >= 0.0f;
}

size_t ParticleAssetFactory::calculateMemoryUsage(const ParticleEffectDefinition& definition) const {
    size_t memory = 0;

    // Estimate particle data memory from the highest-detail LOD
    int maxParticles = 1000;
    if (!definition.lod.rateScales.empty()) {
        const float maxScale = *std::max_element(definition.lod.rateScales.begin(), definition.lod.rateScales.end());
        maxParticles = static_cast<int>(1000.0f * std::max(maxScale, 0.0f) * qualityScale());
    }
    memory += static_cast<size_t>(maxParticles) * sizeof(Particle);

    // Estimate texture memory
    memory += 1024 * 1024; // 1MB texture estimate

    // Estimate shader memory
    if (m_gpuAccelerationEnabled.load()) {
        memory += 64 * 1024; // 64KB shader estimate
    }

    return memory;
}

float ParticleAssetFactory::qualityScale() const {
    switch (m_particleQuality.load()) {
        case ParticleQuality::Low: return 0.25f;
        case ParticleQuality::Medium: return 0.5f;
        case ParticleQuality::High: return 1.0f;
        case ParticleQuality::Ultra: return 2.0f;
    }
    return 1.0f;
}

void ParticleAssetFactory::setLastError(const std::string& message) {
    Log::error("ParticleAsset", "{}", message);
    std::lock_guard<std::mutex> lock(m_errorMutex);
    m_lastError = message;
}

// Cache management
void ParticleAssetFactory::clearCache() {
    m_cache.clear();
    m_cacheHits = 0;
    m_cacheMisses = 0;
}

void ParticleAssetFactory::setCacheSize(size_t maxEntries) {
    m_cache.set_capacity(maxEntries);
}

size_t ParticleAssetFactory::getCacheSize() const {
    return m_cache.size();
}

size_t ParticleAssetFactory::getCacheHits() const {
    return m_cacheHits;
}

size_t ParticleAssetFactory::getCacheMisses() const {
    return m_cacheMisses;
}

// Thread pool management
void ParticleAssetFactory::setMaxThreads(int threads) {
    if (threads <= 0) return;
    m_maxThreads = threads;
    if (m_initialized.load()) {
        // Drain the current pool, then restart with the new size
        m_pool->stop();
        m_pool->start(static_cast<size_t>(threads));
    }
}

int ParticleAssetFactory::getMaxThreads() const {
    return m_maxThreads;
}

// GPU acceleration
void ParticleAssetFactory::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

bool ParticleAssetFactory::isGPUAccelerationEnabled() const {
    return m_gpuAccelerationEnabled;
}

// Quality settings
void ParticleAssetFactory::setParticleQuality(ParticleQuality quality) {
    m_particleQuality = quality;
}

ParticleQuality ParticleAssetFactory::getParticleQuality() const {
    return m_particleQuality;
}

// Performance monitoring
ParticlePerformanceMetrics ParticleAssetFactory::getPerformanceMetrics() const {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    ParticlePerformanceMetrics metrics = m_performanceMetrics;
    metrics.memoryUsage = m_totalMemoryUsage.load();
    metrics.gpuAccelerated = m_gpuAccelerationEnabled.load();
    return metrics;
}

void ParticleAssetFactory::resetPerformanceMetrics() {
    std::lock_guard<std::mutex> lock(m_stateMutex);
    m_performanceMetrics = ParticlePerformanceMetrics{};
}

// Error handling
std::string ParticleAssetFactory::getLastError() const {
    std::lock_guard<std::mutex> lock(m_errorMutex);
    return m_lastError;
}

void ParticleAssetFactory::clearLastError() {
    std::lock_guard<std::mutex> lock(m_errorMutex);
    m_lastError.clear();
}

// Generation status
bool ParticleAssetFactory::isGenerating() const {
    return m_activeGenerations.load() > 0;
}

float ParticleAssetFactory::getGenerationProgress() const {
    return m_generationProgress;
}

// Memory management
size_t ParticleAssetFactory::getTotalMemoryUsage() const {
    return m_totalMemoryUsage;
}

void ParticleAssetFactory::setMaxMemoryUsage(size_t maxBytes) {
    m_maxMemoryUsage = maxBytes;
}

size_t ParticleAssetFactory::getMaxMemoryUsage() const {
    return m_maxMemoryUsage;
}

// ============================================================================
// ParticleEmitter
// ============================================================================

ParticleEmitter::ParticleEmitter()
    : m_currentTime(0.0f)
    , m_lastEmitTime(0.0f)
    , m_emitAccumulator(0.0f)
    , m_emittedCount(0)
    , m_pendingBurst(0)
    , m_active(true)
    , m_gpuEnabled(false)
    , m_rng(std::random_device{}())
    , m_burstMode(false)
    , m_burstCount(0)
    , m_burstInterval(0.0f)
    , m_lastBurstTime(0.0f) {
}

ParticleEmitter::~ParticleEmitter() = default;

void ParticleEmitter::initialize(const EmitterParams& params) {
    m_params = params;
    m_gpuEnabled = params.gpuDriven;
    m_burstMode = params.burstMode;
    m_burstCount = params.burstCount;
    m_burstInterval = params.burstInterval;
    m_currentTime = 0.0f;
    m_lastEmitTime = 0.0f;
    m_lastBurstTime = 0.0f;
    m_emitAccumulator = 0.0f;
    m_active = true;
    // Burst emitters fire their first burst immediately
    m_pendingBurst = m_burstMode ? m_burstCount : 0;
}

void ParticleEmitter::setShape(const ShapeParams& shape) { m_shape = shape; }
void ParticleEmitter::setBehavior(const BehaviorParams& behavior) { m_behavior = behavior; }
void ParticleEmitter::setLifetime(const LifetimeParams& lifetime) { m_lifetime = lifetime; }

void ParticleEmitter::update(float deltaTime) {
    m_currentTime += deltaTime;

    const bool infinite = m_params.duration < 0.0f;
    if (!m_active || (!infinite && m_currentTime >= m_params.duration)) {
        m_active = false;
        return;
    }

    if (m_burstMode && m_burstInterval > 0.0f) {
        if (m_currentTime - m_lastBurstTime >= m_burstInterval) {
            triggerBurst();
        }
    }
}

int ParticleEmitter::consumeEmissionCount(float deltaTime) {
    int count = m_pendingBurst;
    m_pendingBurst = 0;
    if (m_active) {
        m_emitAccumulator += calculateEmitRate() * deltaTime;
        const int continuous = static_cast<int>(m_emitAccumulator);
        m_emitAccumulator -= static_cast<float>(continuous);
        count += continuous;
    }
    if (count > 0) m_lastEmitTime = m_currentTime;
    return count;
}

void ParticleEmitter::emitParticles(std::vector<Particle>& particles, int count) {
    std::uniform_real_distribution<float> lifeDist(m_lifetime.minLife, std::max(m_lifetime.minLife, m_lifetime.maxLife));
    for (int i = 0; i < count; ++i) {
        Particle particle;
        particle.position = calculateEmitPosition();
        particle.velocity = calculateEmitVelocity();
        particle.acceleration = m_behavior.acceleration;
        particle.lifetime = std::max(lifeDist(m_rng), 0.001f);
        particle.size = m_lifetime.sizeRange.x;
        particle.color = m_lifetime.startColor;
        particle.rotation = m_shape.randomRotation ? random01() * 2.0f * kPi : 0.0f;
        particle.active = true;

        particles.push_back(particle);
        m_emittedCount++;
    }
}

float ParticleEmitter::random01() {
    return std::uniform_real_distribution<float>(0.0f, 1.0f)(m_rng);
}

glm::vec3 ParticleEmitter::calculateEmitPosition() {
    glm::vec3 offset(0.0f);

    // Add shape-based variation
    switch (m_shape.type) {
        case ShapeParams::Sphere: {
            const float theta = random01() * 2.0f * kPi;
            const float phi = std::acos(1.0f - 2.0f * random01());
            const float r = m_shape.radius * std::cbrt(random01());
            offset = glm::vec3(r * std::sin(phi) * std::cos(theta),
                               r * std::sin(phi) * std::sin(theta),
                               r * std::cos(phi));
            break;
        }
        case ShapeParams::Box:
            offset = glm::vec3((random01() - 0.5f) * m_shape.dimensions.x,
                               (random01() - 0.5f) * m_shape.dimensions.y,
                               (random01() - 0.5f) * m_shape.dimensions.z);
            break;
        case ShapeParams::Circle: {
            const float theta = random01() * 2.0f * kPi;
            const float r = m_shape.radius * std::sqrt(random01());
            offset = glm::vec3(r * std::cos(theta), 0.0f, r * std::sin(theta));
            break;
        }
        case ShapeParams::Cone: {
            // Base disc of the cone; direction is handled in calculateEmitVelocity
            const float theta = random01() * 2.0f * kPi;
            const float r = m_shape.radius * std::sqrt(random01());
            offset = glm::vec3(r * std::cos(theta), 0.0f, r * std::sin(theta));
            break;
        }
        case ShapeParams::Cylinder: {
            const float theta = random01() * 2.0f * kPi;
            const float r = m_shape.radius * std::sqrt(random01());
            offset = glm::vec3(r * std::cos(theta), (random01() - 0.5f) * m_shape.dimensions.y, r * std::sin(theta));
            break;
        }
        case ShapeParams::Torus: {
            const float u = random01() * 2.0f * kPi;
            const float v = random01() * 2.0f * kPi;
            const float tube = m_shape.innerRadius * std::sqrt(random01());
            offset = glm::vec3((m_shape.radius + tube * std::cos(v)) * std::cos(u),
                               tube * std::sin(v),
                               (m_shape.radius + tube * std::cos(v)) * std::sin(u));
            break;
        }
        case ShapeParams::CustomMesh:
            // Mesh surface sampling needs the loaded mesh; emit from its bounding box
            offset = glm::vec3((random01() - 0.5f) * m_shape.dimensions.x,
                               (random01() - 0.5f) * m_shape.dimensions.y,
                               (random01() - 0.5f) * m_shape.dimensions.z);
            break;
        case ShapeParams::Point:
        default:
            break;
    }

    return m_params.position + offset * m_params.scale;
}

glm::vec3 ParticleEmitter::calculateEmitVelocity() {
    glm::vec3 velocity = m_behavior.initialVelocity;

    if (m_shape.type == ShapeParams::Cone && m_shape.angle > 0.0f) {
        // Spread the initial velocity inside the cone around its direction
        const float speed = glm::length(velocity);
        if (speed > 0.0f) {
            const float halfAngle = m_shape.angle * kPi / 180.0f;
            const float theta = random01() * 2.0f * kPi;
            const float tilt = random01() * halfAngle;
            const glm::vec3 axis = velocity / speed;
            const glm::vec3 helper = std::abs(axis.y) < 0.99f ? glm::vec3(0, 1, 0) : glm::vec3(1, 0, 0);
            const glm::vec3 u = glm::normalize(glm::cross(axis, helper));
            const glm::vec3 w = glm::cross(axis, u);
            velocity = speed * (std::cos(tilt) * axis + std::sin(tilt) * (std::cos(theta) * u + std::sin(theta) * w));
        }
    }

    // Add variance
    velocity.x += (random01() - 0.5f) * m_behavior.velocityVariance.x;
    velocity.y += (random01() - 0.5f) * m_behavior.velocityVariance.y;
    velocity.z += (random01() - 0.5f) * m_behavior.velocityVariance.z;

    return velocity;
}

float ParticleEmitter::calculateEmitRate() {
    return m_burstMode ? 0.0f : std::max(m_params.rate, 0.0f);
}

bool ParticleEmitter::isActive() const { return m_active; }
bool ParticleEmitter::isFinished() const { return !m_active && m_pendingBurst == 0; }
float ParticleEmitter::getCurrentTime() const { return m_currentTime; }
int ParticleEmitter::getEmittedCount() const { return m_emittedCount; }

void ParticleEmitter::triggerBurst() {
    m_pendingBurst += m_burstCount;
    m_lastBurstTime = m_currentTime;
}

void ParticleEmitter::setBurstCount(int count) { m_burstCount = std::max(count, 0); }
void ParticleEmitter::setBurstInterval(float interval) { m_burstInterval = std::max(interval, 0.0f); }
void ParticleEmitter::enableGPU(bool enable) { m_gpuEnabled = enable; }
bool ParticleEmitter::isGPUEnabled() const { return m_gpuEnabled; }

// ============================================================================
// ParticleBehavior
// ============================================================================

ParticleBehavior::ParticleBehavior()
    : m_gpuEnabled(false) {
}

ParticleBehavior::~ParticleBehavior() = default;

void ParticleBehavior::initialize(const BehaviorParams& params) {
    m_params = params;
}

void ParticleBehavior::setExternalForce(std::function<glm::vec3(const glm::vec3&)> force) {
    m_externalForce = std::move(force);
}

void ParticleBehavior::setCollisionResolver(std::function<void(Particle&)> resolver) {
    m_collisionResolver = std::move(resolver);
}

void ParticleBehavior::updateParticle(Particle& particle, float deltaTime) {
    if (!particle.active) return;

    // Update age
    particle.age += deltaTime;
    if (particle.age >= particle.lifetime) {
        particle.active = false;
        return;
    }

    // Calculate forces
    glm::vec3 forces = calculateForces(particle);

    // Apply physics
    particle.acceleration = m_params.acceleration + forces;
    particle.velocity += particle.acceleration * deltaTime;
    particle.position += particle.velocity * deltaTime;

    // Apply drag
    particle.velocity *= std::max(0.0f, 1.0f - m_params.drag * deltaTime);

    // Update rotation
    particle.rotation += particle.rotationSpeed * deltaTime;

    if (m_params.collision) {
        applyCollision(particle);
    }
}

void ParticleBehavior::updateParticles(std::vector<Particle>& particles, float deltaTime) {
    for (auto& particle : particles) {
        updateParticle(particle, deltaTime);
    }
}

glm::vec3 ParticleBehavior::calculateForces(const Particle& particle) {
    glm::vec3 forces(0);

    // Gravity
    forces.y += m_params.gravity;

    // Wind
    forces += m_params.wind;

    // Turbulence
    if (m_params.turbulence) {
        forces += calculateTurbulenceForce(particle);
    }

    // Attractor
    if (m_params.attractorMode) {
        forces += calculateAttractorForce(particle);
    }

    // Global force fields
    if (m_externalForce) {
        forces += m_externalForce(particle.position);
    }

    return forces;
}

glm::vec3 ParticleBehavior::calculateAttractorForce(const Particle& particle) {
    glm::vec3 toAttractor = m_params.attractorPosition - particle.position;
    float distance = glm::length(toAttractor);

    if (distance > m_params.attractorRadius || distance <= 1e-6f) return glm::vec3(0);

    float force = m_params.attractorStrength / (distance * distance + 1.0f);
    return (toAttractor / distance) * force;
}

glm::vec3 ParticleBehavior::calculateTurbulenceForce(const Particle& particle) {
    // Simple turbulence using noise
    float time = particle.age;
    glm::vec3 turbulence(
        std::sin(time * 2.0f + particle.position.x * 0.1f) * m_params.turbulenceStrength,
        std::cos(time * 1.5f + particle.position.y * 0.1f) * m_params.turbulenceStrength,
        std::sin(time * 1.8f + particle.position.z * 0.1f) * m_params.turbulenceStrength
    );

    return turbulence;
}

void ParticleBehavior::applyCollision(Particle& particle) {
    if (m_collisionResolver) {
        m_collisionResolver(particle);
    }
}

void ParticleBehavior::setGravity(float gravity) { m_params.gravity = gravity; }
void ParticleBehavior::setDrag(float drag) { m_params.drag = std::max(drag, 0.0f); }
void ParticleBehavior::setWind(const glm::vec3& wind) { m_params.wind = wind; }

void ParticleBehavior::setTurbulence(float strength) {
    m_params.turbulence = strength > 0.0f;
    m_params.turbulenceStrength = strength;
}

void ParticleBehavior::setAttractor(const glm::vec3& position, float strength, float radius) {
    m_params.attractorMode = true;
    m_params.attractorPosition = position;
    m_params.attractorStrength = strength;
    m_params.attractorRadius = radius;
}

void ParticleBehavior::clearAttractor() {
    m_params.attractorMode = false;
    m_params.attractorStrength = 0.0f;
}

void ParticleBehavior::enableGPU(bool enable) { m_gpuEnabled = enable; }
bool ParticleBehavior::isGPUEnabled() const { return m_gpuEnabled; }

// ============================================================================
// ParticleRenderer
// ============================================================================

ParticleRenderer::ParticleRenderer()
    : m_gpuEnabled(false), m_renderTime(0.0f), m_drawCalls(0) {
}

ParticleRenderer::~ParticleRenderer() = default;

void ParticleRenderer::initialize(const RenderParams& params) {
    m_params = params;
}

void ParticleRenderer::prepareParticles(std::vector<Particle>& particles) {
    for (auto& particle : particles) {
        if (!particle.active) continue;
        updateParticleColor(particle);
        updateParticleSize(particle);
        updateParticleUV(particle);
        if (m_params.softParticles) applySoftParticles(particle);
        if (m_params.distortion) applyDistortion(particle);
        if (m_params.glow) applyGlow(particle);
    }
}

void ParticleRenderer::renderParticles(const std::vector<Particle>& particles) {
    const auto start = std::chrono::steady_clock::now();
    const auto visible = std::count_if(particles.begin(), particles.end(),
                                       [](const Particle& p) { return p.active && p.color.a > 0.0f; });
    // One instanced draw per 1024 particles (or per particle without GPU instancing)
    constexpr long long kBatch = 1024;
    m_drawCalls = visible == 0 ? 0 : static_cast<int>(m_gpuEnabled ? (visible + kBatch - 1) / kBatch : visible);
    m_renderTime = elapsedMs(start);
}

void ParticleRenderer::updateParticleColor(Particle& particle) {
    if (!m_params.alphaOverLife) return;
    // Interpolate start -> middle -> end tint over the particle's life
    const float t = particle.lifetime > 0.0f ? std::clamp(particle.age / particle.lifetime, 0.0f, 1.0f) : 1.0f;
    const glm::vec4 tint = t < 0.5f ? glm::mix(m_params.colorOverLife[0], m_params.colorOverLife[1], t * 2.0f)
                                    : glm::mix(m_params.colorOverLife[1], m_params.colorOverLife[2], (t - 0.5f) * 2.0f);
    particle.color *= tint * m_params.colorOverLife[3];
}

void ParticleRenderer::updateParticleSize(Particle& particle) {
    if (m_params.frameSize.x > 0.0f && m_params.frameSize.y > 0.0f) {
        // Keep the sprite aspect from the frame size
        particle.size = std::max(particle.size, 0.0f);
    }
}

void ParticleRenderer::updateParticleUV(Particle& particle) {
    if (!m_params.animated || m_params.frameCount <= 1) {
        particle.uvOffset = glm::vec2(0.0f);
        return;
    }
    const int frame = static_cast<int>(particle.age * m_params.frameRate) % m_params.frameCount;
    particle.uvOffset = glm::vec2(static_cast<float>(frame) / static_cast<float>(m_params.frameCount), 0.0f);
}

void ParticleRenderer::applySoftParticles(Particle& particle) {
    // Soft particles fade near intersecting geometry; without depth data the edge alpha is softened.
    particle.color.a *= 0.9f;
}

void ParticleRenderer::applyDistortion(Particle& particle) {
    particle.uvOffset += glm::vec2(std::sin(particle.age * 10.0f), std::cos(particle.age * 10.0f)) * (m_params.distortionStrength * 0.01f);
}

void ParticleRenderer::applyGlow(Particle& particle) {
    const float boost = 1.0f + m_params.glowIntensity;
    particle.color = glm::vec4(glm::vec3(particle.color) * boost, particle.color.a);
}

void ParticleRenderer::setTexture(const std::string& path) { m_params.texturePath = path; }
void ParticleRenderer::setNormalMap(const std::string& path) { m_params.normalMapPath = path; }
void ParticleRenderer::setEmissionMap(const std::string& path) { m_params.emissionMapPath = path; }
void ParticleRenderer::setBillboard(bool enabled) { m_params.billboard = enabled; }
void ParticleRenderer::setAlignToCamera(bool enabled) { m_params.alignToCamera = enabled; }
void ParticleRenderer::setSoftParticles(bool enabled) { m_params.softParticles = enabled; }
void ParticleRenderer::setAdditive(bool enabled) { m_params.additive = enabled; if (enabled) m_params.multiply = false; }
void ParticleRenderer::setMultiply(bool enabled) { m_params.multiply = enabled; if (enabled) m_params.additive = false; }

void ParticleRenderer::setDistortion(bool enabled, float strength) {
    m_params.distortion = enabled;
    m_params.distortionStrength = strength;
}

void ParticleRenderer::setGlow(bool enabled, float intensity) {
    m_params.glow = enabled;
    m_params.glowIntensity = intensity;
}

void ParticleRenderer::enableGPU(bool enable) { m_gpuEnabled = enable; }
bool ParticleRenderer::isGPUEnabled() const { return m_gpuEnabled; }
float ParticleRenderer::getRenderTime() const { return m_renderTime; }
int ParticleRenderer::getDrawCalls() const { return m_drawCalls; }

// ============================================================================
// ParticleLOD
// ============================================================================

ParticleLOD::ParticleLOD() : m_adaptiveEnabled(false), m_adaptiveThreshold(0.0f) {}
ParticleLOD::~ParticleLOD() = default;

void ParticleLOD::initialize(const LODParams& params) {
    m_params = params;
    m_adaptiveEnabled = params.adaptiveLOD;
    m_adaptiveThreshold = params.adaptiveThreshold;
}

int ParticleLOD::selectLOD(float screenSize) const {
    // screenSizes are thresholds from most to least detailed
    for (size_t i = 0; i < m_params.screenSizes.size(); ++i) {
        float threshold = m_params.screenSizes[i];
        if (m_adaptiveEnabled) threshold += m_adaptiveThreshold;
        if (screenSize >= threshold) return static_cast<int>(i);
    }
    return m_params.screenSizes.empty() ? 0 : static_cast<int>(m_params.screenSizes.size()) - 1;
}

float ParticleLOD::getRateScale(int lodLevel) const {
    return lodLevel >= 0 && lodLevel < static_cast<int>(m_params.rateScales.size()) ? m_params.rateScales[lodLevel] : 1.0f;
}

float ParticleLOD::getQualityScale(int lodLevel) const {
    return lodLevel >= 0 && lodLevel < static_cast<int>(m_params.qualityScales.size()) ? m_params.qualityScales[lodLevel] : 1.0f;
}

int ParticleLOD::getMaxParticles(int lodLevel) const {
    return static_cast<int>(1000.0f * getRateScale(lodLevel));
}

float ParticleLOD::getCullDistance(int lodLevel) const {
    return 50.0f * getQualityScale(lodLevel);
}

void ParticleLOD::enableAdaptive(bool enabled) { m_adaptiveEnabled = enabled; }
void ParticleLOD::setAdaptiveThreshold(float threshold) { m_adaptiveThreshold = threshold; }
bool ParticleLOD::isAdaptiveEnabled() const { return m_adaptiveEnabled; }
int ParticleLOD::getLODCount() const { return static_cast<int>(m_params.screenSizes.size()); }

float ParticleLOD::getScreenThreshold(int lodLevel) const {
    return lodLevel >= 0 && lodLevel < static_cast<int>(m_params.screenSizes.size()) ? m_params.screenSizes[lodLevel] : 0.0f;
}

// ============================================================================
// ParticleShader
// ============================================================================

ParticleShader::ParticleShader() : m_optimizationLevel(2), m_debugInfoEnabled(false), m_nextHandle(1) {}
ParticleShader::~ParticleShader() = default;

ShaderHandle ParticleShader::compileShader(const RenderParams& params, bool isVertex) {
    m_compilationErrors.clear();
    if (params.animated && params.frameCount <= 0) {
        m_compilationErrors = "Animated particle shader needs frameCount >= 1";
    }
    if (params.additive && params.multiply) {
        m_compilationErrors += (m_compilationErrors.empty() ? "" : "; ");
        m_compilationErrors += "Additive and multiply blending are exclusive; using additive";
    }

    std::string source = isVertex ? generateVertexShader(params) : generateFragmentShader(params);
    if (!isVertex && params.billboard && !params.alignToCamera) {
        // Billboards without camera alignment expand quads in a geometry stage
        source += "\n// --- geometry stage ---\n" + generateGeometryShader(params);
    }
    if (m_debugInfoEnabled) {
        source = "// optimization level " + std::to_string(m_optimizationLevel) + "\n" + source;
    }

    const ShaderHandle handle = m_nextHandle++;
    m_sources[handle] = std::move(source);
    return handle;
}

void ParticleShader::setShaderParameters(ShaderHandle shader, const RenderParams& params) {
    auto& uniforms = m_parameters[shader];
    uniforms["uFrameCount"] = static_cast<float>(params.frameCount);
    uniforms["uFrameRate"] = params.frameRate;
    uniforms["uDistortionStrength"] = params.distortion ? params.distortionStrength : 0.0f;
    uniforms["uGlowIntensity"] = params.glow ? params.glowIntensity : 0.0f;
    for (const auto& [name, value] : params.customParameters) {
        uniforms[name] = value;
    }
}

std::string ParticleShader::getShaderSource(ShaderHandle shader) const {
    auto it = m_sources.find(shader);
    return it != m_sources.end() ? it->second : std::string();
}

void ParticleShader::setOptimizationLevel(int level) { m_optimizationLevel = std::clamp(level, 0, 3); }
void ParticleShader::enableDebugInfo(bool enable) { m_debugInfoEnabled = enable; }
std::string ParticleShader::getCompilationErrors() const { return m_compilationErrors; }
bool ParticleShader::hasCompilationErrors() const { return !m_compilationErrors.empty(); }

std::string ParticleShader::generateVertexShader(const RenderParams& params) {
    std::ostringstream src;
    src << "#version 450\n"
        << "layout(location = 0) in vec3 inPosition;\n"
        << "layout(location = 1) in vec4 inColor;\n"
        << "layout(location = 2) in float inSize;\n"
        << "layout(location = 3) in vec2 inUVOffset;\n"
        << "layout(location = 0) out vec4 vColor;\n"
        << "layout(location = 1) out vec2 vUVOffset;\n"
        << "uniform mat4 uViewProj;\n"
        << "void main() {\n"
        << "    vColor = inColor;\n"
        << "    vUVOffset = inUVOffset;\n"
        << "    gl_Position = uViewProj * vec4(inPosition, 1.0);\n"
        << "    gl_PointSize = inSize" << (params.billboard ? " * 64.0" : "") << ";\n"
        << "}\n";
    return src.str();
}

std::string ParticleShader::generateFragmentShader(const RenderParams& params) {
    std::ostringstream src;
    src << "#version 450\n"
        << "layout(location = 0) in vec4 vColor;\n"
        << "layout(location = 1) in vec2 vUVOffset;\n"
        << "layout(location = 0) out vec4 outColor;\n"
        << "uniform sampler2D uTexture;\n"
        << "uniform float uFrameCount;\n"
        << "uniform float uGlowIntensity;\n"
        << "uniform float uDistortionStrength;\n";
    if (!params.normalMapPath.empty()) src << "uniform sampler2D uNormalMap;\n";
    if (!params.emissionMapPath.empty()) src << "uniform sampler2D uEmissionMap;\n";
    src << "void main() {\n"
        << "    vec2 uv = gl_PointCoord;\n";
    if (params.animated && params.frameCount > 1) {
        src << "    uv = vec2(uv.x / uFrameCount, uv.y) + vUVOffset;\n";
    }
    if (params.distortion) {
        src << "    uv += (texture(uTexture, uv).rg - 0.5) * uDistortionStrength * 0.01;\n";
    }
    src << "    vec4 color = texture(uTexture, uv) * vColor;\n";
    if (!params.emissionMapPath.empty()) {
        src << "    color.rgb += texture(uEmissionMap, uv).rgb;\n";
    }
    if (params.glow) {
        src << "    color.rgb *= 1.0 + uGlowIntensity;\n";
    }
    if (params.multiply && !params.additive) {
        src << "    color.rgb = mix(vec3(1.0), color.rgb, color.a);\n";
    }
    src << "    outColor = color;\n"
        << "}\n";
    return src.str();
}

std::string ParticleShader::generateGeometryShader(const RenderParams& params) {
    std::ostringstream src;
    src << "#version 450\n"
        << "layout(points) in;\n"
        << "layout(triangle_strip, max_vertices = 4) out;\n"
        << "uniform vec2 uFrameSize = vec2(" << params.frameSize.x << ", " << params.frameSize.y << ");\n"
        << "void main() {\n"
        << "    for (int i = 0; i < 4; ++i) {\n"
        << "        vec2 corner = vec2(i & 1, i >> 1) - 0.5;\n"
        << "        gl_Position = gl_in[0].gl_Position + vec4(corner * uFrameSize, 0.0, 0.0);\n"
        << "        EmitVertex();\n"
        << "    }\n"
        << "    EndPrimitive();\n"
        << "}\n";
    return src.str();
}

// ============================================================================
// ParticleCompute
// ============================================================================

ParticleCompute::ParticleCompute()
    : m_workGroupSize(256), m_computeTime(0.0f), m_computeAvailable(false), m_nextHandle(1) {}
ParticleCompute::~ParticleCompute() = default;

ComputeShaderHandle ParticleCompute::compileComputeShader(const std::string& source) {
    if (source.empty()) return 0;
    const ComputeShaderHandle handle = m_nextHandle++;
    m_sources[handle] = source;
    return handle;
}

void ParticleCompute::dispatchCompute(const ComputeShaderHandle& shader, int particleCount) {
    const auto start = std::chrono::steady_clock::now();
    if (m_sources.find(shader) == m_sources.end() || particleCount <= 0) {
        m_computeTime = 0.0f;
        return;
    }
    if (!m_computeAvailable) {
        // No GPU compute device is attached; the CPU path (ParticleBehavior) simulates instead.
        Log::debug("ParticleAsset", "Compute dispatch of {} particles skipped (no compute device)", particleCount);
    }
    m_computeTime = elapsedMs(start);
}

void ParticleCompute::setWorkGroupSize(int size) { m_workGroupSize = std::max(1, size); }
int ParticleCompute::getWorkGroupSize() const { return m_workGroupSize; }
float ParticleCompute::getComputeTime() const { return m_computeTime; }
bool ParticleCompute::isComputeAvailable() const { return m_computeAvailable; }

std::string ParticleCompute::generateUpdateShader(const BehaviorParams& params) {
    std::ostringstream src;
    src << "#version 450\n"
        << "layout(local_size_x = " << m_workGroupSize << ") in;\n"
        << "struct Particle { vec4 position; vec4 velocity; vec4 color; vec4 misc; };\n"
        << "layout(std430, binding = 0) buffer Particles { Particle particles[]; };\n"
        << "uniform float uDeltaTime;\n"
        << "void main() {\n"
        << "    uint i = gl_GlobalInvocationID.x;\n"
        << "    if (i >= particles.length()) return;\n"
        << "    Particle p = particles[i];\n"
        << "    vec3 force = vec3(0.0, " << params.gravity << ", 0.0) + vec3("
        << params.wind.x << ", " << params.wind.y << ", " << params.wind.z << ");\n";
    if (params.turbulence) {
        src << "    force += vec3(sin(p.misc.x * 2.0 + p.position.x * 0.1), cos(p.misc.x * 1.5 + p.position.y * 0.1), "
            << "sin(p.misc.x * 1.8 + p.position.z * 0.1)) * " << params.turbulenceStrength << ";\n";
    }
    if (params.attractorMode) {
        src << "    vec3 toA = vec3(" << params.attractorPosition.x << ", " << params.attractorPosition.y << ", "
            << params.attractorPosition.z << ") - p.position.xyz;\n"
            << "    float d = length(toA);\n"
            << "    if (d > 1e-6 && d <= " << params.attractorRadius << ") force += toA / d * ("
            << params.attractorStrength << " / (d * d + 1.0));\n";
    }
    src << "    p.velocity.xyz += force * uDeltaTime;\n"
        << "    p.velocity.xyz *= max(0.0, 1.0 - " << params.drag << " * uDeltaTime);\n"
        << "    p.position.xyz += p.velocity.xyz * uDeltaTime;\n"
        << "    p.misc.x += uDeltaTime;\n"
        << "    particles[i] = p;\n"
        << "}\n";
    return src.str();
}

std::string ParticleCompute::generateEmitShader(const EmitterParams& params) {
    std::ostringstream src;
    src << "#version 450\n"
        << "layout(local_size_x = " << m_workGroupSize << ") in;\n"
        << "struct Particle { vec4 position; vec4 velocity; vec4 color; vec4 misc; };\n"
        << "layout(std430, binding = 0) buffer Particles { Particle particles[]; };\n"
        << "uniform uint uEmitOffset;\n"
        << "uniform uint uEmitCount;\n"
        << "void main() {\n"
        << "    uint i = gl_GlobalInvocationID.x;\n"
        << "    if (i >= uEmitCount) return;\n"
        << "    Particle p;\n"
        << "    p.position = vec4(" << params.position.x << ", " << params.position.y << ", " << params.position.z << ", 1.0);\n"
        << "    p.velocity = vec4(0.0);\n"
        << "    p.color = vec4(1.0);\n"
        << "    p.misc = vec4(0.0);\n"
        << "    particles[uEmitOffset + i] = p;\n"
        << "}\n";
    return src.str();
}

// ============================================================================
// ParticleForceFieldManager
// ============================================================================

ParticleForceFieldManager::ParticleForceFieldManager() : m_time(0.0f), m_nextAutoId(1) {}
ParticleForceFieldManager::~ParticleForceFieldManager() = default;

std::string ParticleForceFieldManager::makeId(const char* prefix) {
    return std::string(prefix) + "_" + std::to_string(m_nextAutoId++);
}

void ParticleForceFieldManager::addForceField(const ParticleForceField& forceField) {
    ParticleForceField field = forceField;
    if (field.id.empty()) field.id = makeId("field");
    m_forceFields.push_back(std::move(field));
}

void ParticleForceFieldManager::removeForceField(const std::string& id) {
    m_forceFields.erase(std::remove_if(m_forceFields.begin(), m_forceFields.end(),
                                       [&](const ParticleForceField& f) { return f.id == id; }),
                        m_forceFields.end());
}

void ParticleForceFieldManager::updateForceFields(float deltaTime) {
    m_time += deltaTime;
}

glm::vec3 ParticleForceFieldManager::computeForce(const glm::vec3& position) const {
    glm::vec3 total(0.0f);
    for (const auto& field : m_forceFields) {
        if (!field.active) continue;
        switch (field.type) {
            case ParticleForceField::Gravity: total += calculateGravityForce(position, field); break;
            case ParticleForceField::Wind: total += calculateWindForce(position, field); break;
            case ParticleForceField::Turbulence: total += calculateTurbulenceForce(position, field); break;
            case ParticleForceField::Attractor: total += calculateAttractorForce(position, field); break;
            case ParticleForceField::Repulsor: total += calculateRepulsorForce(position, field); break;
            case ParticleForceField::Vortex: total += calculateVortexForce(position, field); break;
            case ParticleForceField::Custom:
                if (field.customForce) total += field.customForce(position, m_time) * attenuation(position, field);
                break;
        }
    }
    return total;
}

float ParticleForceFieldManager::attenuation(const glm::vec3& position, const ParticleForceField& field) const {
    if (field.radius <= 0.0f) return 1.0f;
    const float distance = glm::length(position - field.position);
    if (distance >= field.radius) return 0.0f;
    return std::pow(1.0f - distance / field.radius, std::max(field.falloff, 0.0f));
}

void ParticleForceFieldManager::addGravityField(const glm::vec3& position, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Gravity;
    f.id = makeId("gravity");
    f.position = position;
    f.direction = glm::vec3(0.0f, -1.0f, 0.0f);
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addWindField(const glm::vec3& position, const glm::vec3& direction, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Wind;
    f.id = makeId("wind");
    f.position = position;
    f.direction = direction;
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addTurbulenceField(const glm::vec3& position, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Turbulence;
    f.id = makeId("turbulence");
    f.position = position;
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addAttractorField(const glm::vec3& position, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Attractor;
    f.id = makeId("attractor");
    f.position = position;
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addRepulsorField(const glm::vec3& position, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Repulsor;
    f.id = makeId("repulsor");
    f.position = position;
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addVortexField(const glm::vec3& position, const glm::vec3& axis, float strength, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Vortex;
    f.id = makeId("vortex");
    f.position = position;
    f.direction = axis;
    f.strength = strength;
    f.radius = radius;
    m_forceFields.push_back(std::move(f));
}

void ParticleForceFieldManager::addCustomField(const std::string& id,
                                               std::function<glm::vec3(const glm::vec3&, float)> forceFunc,
                                               const glm::vec3& position, float radius) {
    ParticleForceField f;
    f.type = ParticleForceField::Custom;
    f.id = id.empty() ? makeId("custom") : id;
    f.position = position;
    f.radius = radius;
    f.strength = 1.0f;
    f.customForce = std::move(forceFunc);
    m_forceFields.push_back(std::move(f));
}

glm::vec3 ParticleForceFieldManager::calculateGravityForce(const glm::vec3& position, const ParticleForceField& field) const {
    const float len = glm::length(field.direction);
    const glm::vec3 dir = len > 0.0f ? field.direction / len : glm::vec3(0.0f, -1.0f, 0.0f);
    return dir * field.strength * attenuation(position, field);
}

glm::vec3 ParticleForceFieldManager::calculateWindForce(const glm::vec3& position, const ParticleForceField& field) const {
    const float len = glm::length(field.direction);
    if (len <= 0.0f) return glm::vec3(0.0f);
    return field.direction / len * field.strength * attenuation(position, field);
}

glm::vec3 ParticleForceFieldManager::calculateTurbulenceForce(const glm::vec3& position, const ParticleForceField& field) const {
    const glm::vec3 noise(std::sin(m_time * 2.0f + position.y * 0.37f + position.z * 0.11f),
                          std::cos(m_time * 1.7f + position.z * 0.29f + position.x * 0.13f),
                          std::sin(m_time * 1.3f + position.x * 0.31f + position.y * 0.17f));
    return noise * field.strength * attenuation(position, field);
}

glm::vec3 ParticleForceFieldManager::calculateAttractorForce(const glm::vec3& position, const ParticleForceField& field) const {
    const glm::vec3 toCenter = field.position - position;
    const float distance = glm::length(toCenter);
    if (distance <= 1e-6f) return glm::vec3(0.0f);
    return toCenter / distance * field.strength * attenuation(position, field);
}

glm::vec3 ParticleForceFieldManager::calculateRepulsorForce(const glm::vec3& position, const ParticleForceField& field) const {
    return -calculateAttractorForce(position, field);
}

glm::vec3 ParticleForceFieldManager::calculateVortexForce(const glm::vec3& position, const ParticleForceField& field) const {
    const float axisLen = glm::length(field.direction);
    const glm::vec3 axis = axisLen > 0.0f ? field.direction / axisLen : glm::vec3(0.0f, 1.0f, 0.0f);
    const glm::vec3 radial = position - field.position;
    const glm::vec3 tangent = glm::cross(axis, radial);
    const float len = glm::length(tangent);
    if (len <= 1e-6f) return glm::vec3(0.0f);
    return tangent / len * field.strength * attenuation(position, field);
}

// ============================================================================
// ParticleCollisionManager
// ============================================================================

ParticleCollisionManager::ParticleCollisionManager() : m_nextAutoId(1) {}
ParticleCollisionManager::~ParticleCollisionManager() = default;

std::string ParticleCollisionManager::makeId(const char* prefix) {
    return std::string(prefix) + "_" + std::to_string(m_nextAutoId++);
}

void ParticleCollisionManager::addCollision(const ParticleCollision& collision) {
    ParticleCollision c = collision;
    if (c.id.empty()) c.id = makeId("collision");
    m_collisions.push_back(std::move(c));
}

void ParticleCollisionManager::removeCollision(const std::string& id) {
    m_collisions.erase(std::remove_if(m_collisions.begin(), m_collisions.end(),
                                      [&](const ParticleCollision& c) { return c.id == id; }),
                       m_collisions.end());
}

void ParticleCollisionManager::updateCollisions(float) {
    // Drop colliders that were deactivated
    m_collisions.erase(std::remove_if(m_collisions.begin(), m_collisions.end(),
                                      [](const ParticleCollision& c) { return !c.active || c.type == ParticleCollision::None; }),
                       m_collisions.end());
}

void ParticleCollisionManager::resolveAll(Particle& particle) {
    for (const auto& collision : m_collisions) {
        if (collision.active) resolveCollision(particle, collision);
    }
}

void ParticleCollisionManager::addSphereCollision(const glm::vec3& position, float radius, float restitution) {
    ParticleCollision c;
    c.type = ParticleCollision::Sphere;
    c.id = makeId("sphere");
    c.position = position;
    c.dimensions = glm::vec3(radius);
    c.restitution = restitution;
    m_collisions.push_back(std::move(c));
}

void ParticleCollisionManager::addBoxCollision(const glm::vec3& position, const glm::vec3& dimensions, float restitution) {
    ParticleCollision c;
    c.type = ParticleCollision::Box;
    c.id = makeId("box");
    c.position = position;
    c.dimensions = dimensions;
    c.restitution = restitution;
    m_collisions.push_back(std::move(c));
}

void ParticleCollisionManager::addPlaneCollision(const glm::vec3& position, const glm::vec3& normal, float restitution) {
    ParticleCollision c;
    c.type = ParticleCollision::Plane;
    c.id = makeId("plane");
    c.position = position;
    const float len = glm::length(normal);
    c.normal = len > 0.0f ? normal / len : glm::vec3(0.0f, 1.0f, 0.0f);
    c.restitution = restitution;
    m_collisions.push_back(std::move(c));
}

void ParticleCollisionManager::addMeshCollision(const std::string& meshPath, const glm::vec3& position, float restitution) {
    ParticleCollision c;
    c.type = ParticleCollision::Mesh;
    c.id = makeId("mesh");
    c.meshPath = meshPath;
    c.position = position;
    c.restitution = restitution;
    m_collisions.push_back(std::move(c));
}

void ParticleCollisionManager::resolveCollision(Particle& particle, const ParticleCollision& collision) {
    bool hit = false;
    switch (collision.type) {
        case ParticleCollision::Sphere: hit = checkSphereCollision(particle, collision); break;
        case ParticleCollision::Box: hit = checkBoxCollision(particle, collision); break;
        case ParticleCollision::Plane: hit = checkPlaneCollision(particle, collision); break;
        case ParticleCollision::Mesh: hit = checkMeshCollision(particle, collision); break;
        case ParticleCollision::None: break;
    }
    if (!hit) return;

    particle.velocity = calculateCollisionResponse(particle, collision);

    // Push the particle back to the collider surface
    switch (collision.type) {
        case ParticleCollision::Sphere: {
            const glm::vec3 d = particle.position - collision.position;
            const float len = glm::length(d);
            const glm::vec3 n = len > 1e-6f ? d / len : glm::vec3(0.0f, 1.0f, 0.0f);
            particle.position = collision.position + n * collision.dimensions.x;
            break;
        }
        case ParticleCollision::Plane: {
            const float dist = glm::dot(particle.position - collision.position, collision.normal);
            particle.position -= collision.normal * dist;
            break;
        }
        default:
            break;
    }
}

bool ParticleCollisionManager::checkSphereCollision(const Particle& particle, const ParticleCollision& collision) {
    return glm::length(particle.position - collision.position) < collision.dimensions.x;
}

bool ParticleCollisionManager::checkBoxCollision(const Particle& particle, const ParticleCollision& collision) {
    const glm::vec3 half = collision.dimensions * 0.5f;
    const glm::vec3 d = glm::abs(particle.position - collision.position);
    return d.x < half.x && d.y < half.y && d.z < half.z;
}

bool ParticleCollisionManager::checkPlaneCollision(const Particle& particle, const ParticleCollision& collision) {
    return glm::dot(particle.position - collision.position, collision.normal) < 0.0f;
}

bool ParticleCollisionManager::checkMeshCollision(const Particle& particle, const ParticleCollision& collision) {
    // Mesh geometry is not loaded here; use its bounding box when one is given.
    if (collision.dimensions == glm::vec3(0.0f)) return false;
    return checkBoxCollision(particle, collision);
}

glm::vec3 ParticleCollisionManager::calculateCollisionResponse(const Particle& particle, const ParticleCollision& collision) {
    glm::vec3 normal(0.0f, 1.0f, 0.0f);
    switch (collision.type) {
        case ParticleCollision::Sphere: {
            const glm::vec3 d = particle.position - collision.position;
            const float len = glm::length(d);
            if (len > 1e-6f) normal = d / len;
            break;
        }
        case ParticleCollision::Plane:
            normal = collision.normal;
            break;
        case ParticleCollision::Box:
        case ParticleCollision::Mesh: {
            // Exit through the face with the smallest penetration
            const glm::vec3 half = collision.dimensions * 0.5f;
            const glm::vec3 d = particle.position - collision.position;
            const glm::vec3 pen = half - glm::abs(d);
            if (pen.x <= pen.y && pen.x <= pen.z) normal = glm::vec3(d.x >= 0 ? 1.0f : -1.0f, 0, 0);
            else if (pen.y <= pen.z) normal = glm::vec3(0, d.y >= 0 ? 1.0f : -1.0f, 0);
            else normal = glm::vec3(0, 0, d.z >= 0 ? 1.0f : -1.0f);
            break;
        }
        case ParticleCollision::None:
            return particle.velocity;
    }

    const float vn = glm::dot(particle.velocity, normal);
    if (vn >= 0.0f) return particle.velocity;   // already separating
    const glm::vec3 normalPart = normal * vn;
    const glm::vec3 tangentPart = particle.velocity - normalPart;
    return tangentPart * (1.0f - std::clamp(collision.friction, 0.0f, 1.0f)) - normalPart * collision.restitution;
}

// ============================================================================
// ParticleTrailManager
// ============================================================================

ParticleTrailManager::ParticleTrailManager() : m_renderedSegments(0) {}
ParticleTrailManager::~ParticleTrailManager() = default;

void ParticleTrailManager::initialize(const ParticleTrail& trail) {
    m_trail = trail;
    m_trailPoints.clear();
    m_trailAges.clear();
}

void ParticleTrailManager::updateTrail(Particle& particle, float deltaTime) {
    if (!m_trail.enabled) return;
    updateTrailAges(deltaTime);
    if (particle.active) addTrailPoint(particle.position);
    removeOldPoints();
}

void ParticleTrailManager::renderTrail(const Particle& particle) {
    if (!m_trail.enabled || m_trailPoints.size() < 2 || !particle.active) {
        m_renderedSegments = 0;
        return;
    }
    renderTrailMesh();
}

void ParticleTrailManager::setMaxPoints(int maxPoints) { m_trail.maxPoints = std::max(maxPoints, 2); removeOldPoints(); }
void ParticleTrailManager::setFadeTime(float fadeTime) { m_trail.fadeTime = std::max(fadeTime, 0.0f); }
void ParticleTrailManager::setWidth(float width) { m_trail.width = std::max(width, 0.0f); }
void ParticleTrailManager::setColor(const glm::vec4& color) { m_trail.color = color; }
void ParticleTrailManager::setTexture(const std::string& path) { m_trail.texturePath = path; m_trail.useTexture = !path.empty(); }
void ParticleTrailManager::enableTexture(bool enabled) { m_trail.useTexture = enabled && !m_trail.texturePath.empty(); }

void ParticleTrailManager::addTrailPoint(const glm::vec3& position) {
    m_trailPoints.push_back(position);
    m_trailAges.push_back(0.0f);
}

void ParticleTrailManager::updateTrailAges(float deltaTime) {
    for (auto& age : m_trailAges) age += deltaTime;
}

void ParticleTrailManager::removeOldPoints() {
    // Expired points are at the front (oldest first)
    size_t expired = 0;
    while (expired < m_trailAges.size() && m_trail.fadeTime > 0.0f && m_trailAges[expired] > m_trail.fadeTime) ++expired;
    const size_t maxPoints = static_cast<size_t>(std::max(m_trail.maxPoints, 2));
    if (m_trailPoints.size() - expired > maxPoints) expired = m_trailPoints.size() - maxPoints;
    m_trailPoints.erase(m_trailPoints.begin(), m_trailPoints.begin() + static_cast<std::ptrdiff_t>(expired));
    m_trailAges.erase(m_trailAges.begin(), m_trailAges.begin() + static_cast<std::ptrdiff_t>(expired));
}

void ParticleTrailManager::renderTrailMesh() {
    // A ribbon of (points - 1) quads; the GPU backend consumes points() + width/color.
    m_renderedSegments = static_cast<int>(m_trailPoints.size()) - 1;
}

// ============================================================================
// ParticleSubEmitterManager
// ============================================================================

ParticleSubEmitterManager::ParticleSubEmitterManager() : m_lastEmitTime(0.0f), m_rng(std::random_device{}()) {}
ParticleSubEmitterManager::~ParticleSubEmitterManager() = default;

void ParticleSubEmitterManager::initialize(const ParticleSubEmitter& subEmitter) {
    m_subEmitter = subEmitter;
    m_lastEmitTime = 0.0f;
}

void ParticleSubEmitterManager::setSpawnCallback(SpawnCallback callback) { m_spawnCallback = std::move(callback); }

void ParticleSubEmitterManager::updateSubEmitter(Particle& parentParticle, float deltaTime) {
    m_lastEmitTime += deltaTime;
    if (m_subEmitter.effectName.empty() || !m_spawnCallback || !shouldEmit(deltaTime)) return;
    m_spawnCallback(m_subEmitter.effectName,
                    calculateInheritedPosition(parentParticle),
                    calculateInheritedVelocity(parentParticle),
                    calculateInheritedRotation(parentParticle),
                    calculateInheritedColor(parentParticle),
                    calculateInheritedSize(parentParticle));
    m_lastEmitTime = 0.0f;
}

void ParticleSubEmitterManager::setEffectName(const std::string& effectName) { m_subEmitter.effectName = effectName; }
void ParticleSubEmitterManager::setProbability(float probability) { m_subEmitter.probability = std::max(probability, 0.0f); }
void ParticleSubEmitterManager::setOffset(const glm::vec3& offset) { m_subEmitter.offset = offset; }
void ParticleSubEmitterManager::setInheritVelocity(bool inherit) { m_subEmitter.inheritVelocity = inherit; }
void ParticleSubEmitterManager::setInheritRotation(bool inherit) { m_subEmitter.inheritRotation = inherit; }
void ParticleSubEmitterManager::setInheritColor(bool inherit) { m_subEmitter.inheritColor = inherit; }
void ParticleSubEmitterManager::setInheritSize(bool inherit) { m_subEmitter.inheritSize = inherit; }

bool ParticleSubEmitterManager::shouldEmit(float deltaTime) {
    // probability is a rate per second of parent life
    const float chance = std::clamp(m_subEmitter.probability * deltaTime, 0.0f, 1.0f);
    return std::uniform_real_distribution<float>(0.0f, 1.0f)(m_rng) < chance;
}

glm::vec3 ParticleSubEmitterManager::calculateInheritedPosition(const Particle& parentParticle) {
    return parentParticle.position + m_subEmitter.offset;
}

glm::vec3 ParticleSubEmitterManager::calculateInheritedVelocity(const Particle& parentParticle) {
    return m_subEmitter.inheritVelocity ? parentParticle.velocity : glm::vec3(0.0f);
}

float ParticleSubEmitterManager::calculateInheritedRotation(const Particle& parentParticle) {
    return m_subEmitter.inheritRotation ? parentParticle.rotation : 0.0f;
}

glm::vec4 ParticleSubEmitterManager::calculateInheritedColor(const Particle& parentParticle) {
    return m_subEmitter.inheritColor ? parentParticle.color : glm::vec4(1.0f);
}

float ParticleSubEmitterManager::calculateInheritedSize(const Particle& parentParticle) {
    return m_subEmitter.inheritSize ? parentParticle.size : 1.0f;
}

} // namespace Particles
} // namespace MagiTech
