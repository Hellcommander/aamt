#include "ParticleAssetFactory.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>

namespace MagiTech {
namespace Particles {

// Global factory instance
ParticleAssetFactory particleFactory;

// ParticleAssetFactory Implementation
ParticleAssetFactory::ParticleAssetFactory()
    : m_gpuAccelerationEnabled(true)
    , m_maxThreads(4)
    , m_particleQuality(ParticleQuality::HIGH)
    , m_isGenerating(false)
    , m_generationProgress(0.0f)
    , m_cacheHits(0)
    , m_cacheMisses(0)
    , m_totalMemoryUsage(0)
    , m_maxMemoryUsage(1024 * 1024 * 1024) { // 1GB default
    
    initializeComponents();
}

ParticleAssetFactory::~ParticleAssetFactory() = default;

void ParticleAssetFactory::initializeComponents() {
    // Initialize cache with default size
    m_cache = std::make_unique<ConcurrentLRU<uint64_t, ParticleEffectResult>>(100);
    
    // Initialize thread pool
    m_pool = std::make_unique<ThreadPool>(m_maxThreads);
    
    // Initialize generator components
    m_emitter = std::make_unique<ParticleEmitter>();
    m_behavior = std::make_unique<ParticleBehavior>();
    m_renderer = std::make_unique<ParticleRenderer>();
    m_lod = std::make_unique<ParticleLOD>();
    m_shader = std::make_unique<ParticleShader>();
    m_compute = std::make_unique<ParticleCompute>();
    
    // Initialize manager components
    m_forceFieldManager = std::make_unique<ParticleForceField>();
    m_collisionManager = std::make_unique<ParticleCollision>();
    m_trailManager = std::make_unique<ParticleTrail>();
    m_subEmitterManager = std::make_unique<ParticleSubEmitter>();
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
    try {
        m_isGenerating = true;
        m_generationProgress = 0.0f;
        
        // Check cache first
        uint64_t hash = hashCombine(definition);
        auto cached = m_cache->get(hash);
        if (cached) {
            m_cacheHits++;
            return *cached;
        }
        
        m_cacheMisses++;
        
        // Validate definition
        if (!validateDefinition(definition)) {
            throw std::runtime_error("Invalid particle effect definition");
        }
        
        m_generationProgress = 0.1f;
        
        // Initialize components
        m_emitter->initialize(definition.emitter);
        m_behavior->initialize(definition.behavior);
        m_renderer->initialize(definition.render);
        m_lod->initialize(definition.lod);
        
        m_generationProgress = 0.3f;
        
        // Generate particle system
        ParticleBundle bundle;
        bundle.system = static_cast<ParticleSystemHandle>(hash);
        bundle.gpuAccelerated = m_gpuAccelerationEnabled;
        bundle.creationTime = std::chrono::system_clock::now();
        
        // Calculate LOD data
        bundle.lodData.screenSizes = definition.lod.screenSizes;
        bundle.lodData.rateScales = definition.lod.rateScales;
        bundle.lodData.qualityScales = definition.lod.qualityScales;
        
        // Generate LOD variants
        for (size_t i = 0; i < definition.lod.screenSizes.size(); ++i) {
            bundle.lodData.maxParticles.push_back(static_cast<int>(1000 * definition.lod.rateScales[i]));
            bundle.lodData.cullDistances.push_back(50.0f * definition.lod.qualityScales[i]);
        }
        
        m_generationProgress = 0.6f;
        
        // Generate shaders if GPU acceleration is enabled
        if (m_gpuAccelerationEnabled) {
            bundle.shader = m_shader->compileShader(definition.render, false);
            bundle.computeShader = m_compute->compileComputeShader(
                m_compute->generateUpdateShader(definition.behavior)
            );
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
        
        m_generationProgress = 1.0f;
        
        // Cache the result
        m_cache->put(hash, result);
        
        return result;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        ParticleEffectResult result;
        result.success = false;
        result.errorMessage = e.what();
        return result;
    } finally {
        m_isGenerating = false;
        m_generationProgress = 0.0f;
    }
}

// ParticleEmitter Implementation
ParticleEmitter::ParticleEmitter()
    : m_currentTime(0.0f)
    , m_lastEmitTime(0.0f)
    , m_emittedCount(0)
    , m_active(true)
    , m_gpuEnabled(false)
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
}

void ParticleEmitter::update(float deltaTime) {
    m_currentTime += deltaTime;
    
    if (!m_active || m_currentTime >= m_params.duration) {
        m_active = false;
        return;
    }
    
    if (m_burstMode) {
        if (m_currentTime - m_lastBurstTime >= m_burstInterval) {
            triggerBurst();
        }
    }
}

void ParticleEmitter::emitParticles(std::vector<Particle>& particles, int count) {
    for (int i = 0; i < count; ++i) {
        Particle particle;
        particle.position = calculateEmitPosition();
        particle.velocity = calculateEmitVelocity();
        particle.lifetime = m_params.rate > 0 ? 1.0f / m_params.rate : 1.0f;
        particle.active = true;
        
        particles.push_back(particle);
        m_emittedCount++;
    }
}

glm::vec3 ParticleEmitter::calculateEmitPosition() {
    glm::vec3 basePos = m_params.position;
    
    // Add shape-based variation
    switch (m_params.shape.type) {
        case ShapeType::SPHERE:
            {
                float theta = static_cast<float>(rand()) / RAND_MAX * 2.0f * M_PI;
                float phi = static_cast<float>(rand()) / RAND_MAX * M_PI;
                float r = m_params.shape.radius * std::sqrt(static_cast<float>(rand()) / RAND_MAX);
                
                basePos.x += r * std::sin(phi) * std::cos(theta);
                basePos.y += r * std::sin(phi) * std::sin(theta);
                basePos.z += r * std::cos(phi);
            }
            break;
        case ShapeType::BOX:
            {
                basePos.x += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.shape.dimensions.x;
                basePos.y += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.shape.dimensions.y;
                basePos.z += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.shape.dimensions.z;
            }
            break;
        default:
            break;
    }
    
    return basePos;
}

glm::vec3 ParticleEmitter::calculateEmitVelocity() {
    glm::vec3 velocity = m_params.behavior.initialVelocity;
    
    // Add variance
    velocity.x += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.behavior.velocityVariance.x;
    velocity.y += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.behavior.velocityVariance.y;
    velocity.z += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * m_params.behavior.velocityVariance.z;
    
    return velocity;
}

float ParticleEmitter::calculateEmitRate() {
    return m_params.rate;
}

// ParticleBehavior Implementation
ParticleBehavior::ParticleBehavior()
    : m_gpuEnabled(false) {
}

ParticleBehavior::~ParticleBehavior() = default;

void ParticleBehavior::initialize(const BehaviorParams& params) {
    m_params = params;
    m_gpuEnabled = params.gpuDriven;
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
    particle.acceleration = forces;
    particle.velocity += particle.acceleration * deltaTime;
    particle.position += particle.velocity * deltaTime;
    
    // Apply drag
    particle.velocity *= (1.0f - m_params.drag * deltaTime);
    
    // Update rotation
    particle.rotation += particle.rotationSpeed * deltaTime;
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
    
    return forces;
}

glm::vec3 ParticleBehavior::calculateAttractorForce(const Particle& particle) {
    glm::vec3 toAttractor = m_params.attractorPosition - particle.position;
    float distance = glm::length(toAttractor);
    
    if (distance > m_params.attractorRadius) return glm::vec3(0);
    
    float force = m_params.attractorStrength / (distance * distance + 1.0f);
    return glm::normalize(toAttractor) * force;
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

// Utility functions
uint64_t ParticleAssetFactory::hashCombine(const ParticleEffectDefinition& definition) const {
    uint64_t hash = 0;
    
    // Combine all parameter hashes
    hash ^= definition.emitter.hashKey();
    hash ^= definition.behavior.hashKey();
    hash ^= definition.shape.hashKey();
    hash ^= definition.lifetime.hashKey();
    hash ^= definition.render.hashKey();
    hash ^= definition.lod.hashKey();
    
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
    return !params.id.empty() && params.rate >= 0.0f && params.duration >= 0.0f;
}

bool ParticleAssetFactory::validateBehaviorParams(const BehaviorParams& params) const {
    return params.gravity >= -100.0f && params.gravity <= 100.0f && params.drag >= 0.0f;
}

bool ParticleAssetFactory::validateShapeParams(const ShapeParams& params) const {
    return params.dimensions.x >= 0.0f && params.dimensions.y >= 0.0f && params.dimensions.z >= 0.0f;
}

bool ParticleAssetFactory::validateLifetimeParams(const LifetimeParams& params) const {
    return params.minLife >= 0.0f && params.maxLife >= params.minLife;
}

bool ParticleAssetFactory::validateRenderParams(const RenderParams& params) const {
    return !params.texturePath.empty();
}

bool ParticleAssetFactory::validateLODParams(const LODParams& params) const {
    return !params.screenSizes.empty() && !params.rateScales.empty();
}

size_t ParticleAssetFactory::calculateMemoryUsage(const ParticleEffectDefinition& definition) const {
    size_t memory = 0;
    
    // Estimate particle data memory
    int maxParticles = 1000; // Default estimate
    memory += maxParticles * sizeof(Particle);
    
    // Estimate texture memory
    memory += 1024 * 1024; // 1MB texture estimate
    
    // Estimate shader memory
    if (m_gpuAccelerationEnabled) {
        memory += 64 * 1024; // 64KB shader estimate
    }
    
    return memory;
}

// Cache management
void ParticleAssetFactory::clearCache() {
    m_cache->clear();
}

void ParticleAssetFactory::setCacheSize(size_t maxEntries) {
    m_cache = std::make_unique<ConcurrentLRU<uint64_t, ParticleEffectResult>>(maxEntries);
}

size_t ParticleAssetFactory::getCacheSize() const {
    return m_cache->size();
}

size_t ParticleAssetFactory::getCacheHits() const {
    return m_cacheHits;
}

size_t ParticleAssetFactory::getCacheMisses() const {
    return m_cacheMisses;
}

// Thread pool management
void ParticleAssetFactory::setMaxThreads(int threads) {
    m_maxThreads = threads;
    m_pool = std::make_unique<ThreadPool>(threads);
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

// Error handling
std::string ParticleAssetFactory::getLastError() const {
    return m_lastError;
}

void ParticleAssetFactory::clearLastError() {
    m_lastError.clear();
}

// Generation status
bool ParticleAssetFactory::isGenerating() const {
    return m_isGenerating;
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

} // namespace Particles
} // namespace MagiTech
