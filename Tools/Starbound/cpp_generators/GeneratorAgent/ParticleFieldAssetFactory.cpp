#include "ParticleFieldAssetFactory.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>

namespace MagiTech {
namespace ParticleFields {

// Global factory instance
ParticleFieldAssetFactory fieldFactory;

// Static members for VolumeNoise
std::random_device NoiseGen::VolumeNoise::m_randomDevice;
std::mt19937 NoiseGen::VolumeNoise::m_generator(m_randomDevice());
std::uniform_real_distribution<float> NoiseGen::VolumeNoise::m_distribution(0.0f, 1.0f);

// Static members for CompileGen
int ShaderGen::CompileGen::m_optimizationLevel = 2;
bool ShaderGen::CompileGen::m_debugInfoEnabled = false;
std::string ShaderGen::CompileGen::m_compilationErrors;

// ParticleFieldAssetFactory Implementation
ParticleFieldAssetFactory::ParticleFieldAssetFactory()
    : m_gpuAccelerationEnabled(true)
    , m_maxThreads(4)
    , m_isGenerating(false)
    , m_generationProgress(0.0f)
    , m_cacheHits(0)
    , m_cacheMisses(0) {
    
    initializeComponents();
}

ParticleFieldAssetFactory::~ParticleFieldAssetFactory() = default;

void ParticleFieldAssetFactory::initializeComponents() {
    // Initialize cache with default size
    m_cache = std::make_unique<ConcurrentLRU<uint64_t, ParticleFieldBundle>>(100);
    
    // Initialize thread pool
    m_pool = std::make_unique<ThreadPool>(m_maxThreads);
    
    // Initialize generator components
    m_fieldGen = std::make_unique<FieldGen>();
    m_noiseGen = std::make_unique<NoiseGen>();
    m_colorGen = std::make_unique<ColorGen>();
    m_simGen = std::make_unique<SimGen>();
    m_lodGen = std::make_unique<LODGen>();
    m_shaderGen = std::make_unique<ShaderGen>();
}

std::future<ParticleFieldBundle> ParticleFieldAssetFactory::generateAsync(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) {
    
    // Validate parameters
    if (!validateParams(fp, np, cr, pp)) {
        throw std::invalid_argument("Invalid particle field parameters: " + m_lastError);
    }
    
    // Generate hash key for caching
    uint64_t key = hashCombine(fp, np, cr, pp);
    
    // Check cache first
    if (auto hit = m_cache->find(key)) {
        m_cacheHits++;
        return std::async(std::launch::deferred, [hit]() { return *hit; });
    }
    
    m_cacheMisses++;
    m_isGenerating = true;
    m_generationProgress = 0.0f;
    
    // Enqueue generation task
    return m_pool->enqueue([this, fp, np, cr, pp, key]() {
        try {
            ParticleFieldBundle bundle = generateInternal(fp, np, cr, pp);
            m_cache->insert(key, bundle);
            m_isGenerating = false;
            m_generationProgress = 1.0f;
            return bundle;
        } catch (const std::exception& e) {
            m_lastError = e.what();
            m_isGenerating = false;
            m_generationProgress = 0.0f;
            throw;
        }
    });
}

ParticleFieldBundle ParticleFieldAssetFactory::generate(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) {
    
    // Validate parameters
    if (!validateParams(fp, np, cr, pp)) {
        throw std::invalid_argument("Invalid particle field parameters: " + m_lastError);
    }
    
    // Generate hash key for caching
    uint64_t key = hashCombine(fp, np, cr, pp);
    
    // Check cache first
    if (auto hit = m_cache->find(key)) {
        m_cacheHits++;
        return *hit;
    }
    
    m_cacheMisses++;
    
    // Generate synchronously
    ParticleFieldBundle bundle = generateInternal(fp, np, cr, pp);
    m_cache->insert(key, bundle);
    return bundle;
}

ParticleFieldBundle ParticleFieldAssetFactory::generateInternal(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) {
    
    ParticleFieldBundle bundle;
    
    // Step 1: Generate noise volume (if using volume mode)
    if (fp.useVolume) {
        bundle.noiseVolume = NoiseGen::buildVolume(np, fp.boundsMin, fp.boundsMax);
        m_generationProgress = 0.2f;
    }
    
    // Step 2: Generate color ramp texture
    bundle.colorRampTex = ColorGen::buildRamp(cr);
    m_generationProgress = 0.4f;
    
    // Step 3: Compute LOD data
    bundle.lodData = LODGen::compute(fp.lod);
    m_generationProgress = 0.6f;
    
    // Step 4: Build field shader
    bundle.fieldShader = ShaderGen::buildFieldShader(fp, np, cr, pp);
    m_generationProgress = 0.8f;
    
    // Step 5: Spawn particle field
    bundle.particles = FieldGen::spawnField(fp, np, pp, bundle.colorRampTex);
    m_generationProgress = 1.0f;
    
    return bundle;
}

// Cache Management
void ParticleFieldAssetFactory::clearCache() {
    m_cache->clear();
}

void ParticleFieldAssetFactory::setCacheSize(size_t maxEntries) {
    m_cache = std::make_unique<ConcurrentLRU<uint64_t, ParticleFieldBundle>>(maxEntries);
}

size_t ParticleFieldAssetFactory::getCacheSize() const {
    return m_cache->size();
}

size_t ParticleFieldAssetFactory::getCacheHits() const {
    return m_cacheHits;
}

size_t ParticleFieldAssetFactory::getCacheMisses() const {
    return m_cacheMisses;
}

// Thread Pool Management
void ParticleFieldAssetFactory::setMaxThreads(int threads) {
    m_maxThreads = std::max(1, threads);
    m_pool = std::make_unique<ThreadPool>(m_maxThreads);
}

int ParticleFieldAssetFactory::getMaxThreads() const {
    return m_maxThreads;
}

// GPU Acceleration
void ParticleFieldAssetFactory::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

bool ParticleFieldAssetFactory::isGPUAccelerationEnabled() const {
    return m_gpuAccelerationEnabled;
}

// Error Handling
std::string ParticleFieldAssetFactory::getLastError() const {
    return m_lastError;
}

void ParticleFieldAssetFactory::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
uint64_t ParticleFieldAssetFactory::hashCombine(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) const {
    
    // Combine all parameter hashes
    uint64_t hash = fp.hashKey();
    hash = hash * 31 + np.hashKey();
    hash = hash * 31 + cr.hashKey();
    hash = hash * 31 + pp.hashKey();
    
    // Include GPU acceleration setting
    hash = hash * 31 + (m_gpuAccelerationEnabled ? 1 : 0);
    
    return hash;
}

// Field Generation Status
bool ParticleFieldAssetFactory::isGenerating() const {
    return m_isGenerating;
}

float ParticleFieldAssetFactory::getGenerationProgress() const {
    return m_generationProgress;
}

// Asset Validation
bool ParticleFieldAssetFactory::validateParams(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) const {
    
    return validateFieldParams(fp) &&
           validateNoiseParams(np) &&
           validateColorRampParams(cr) &&
           validateParticleParams(pp);
}

bool ParticleFieldAssetFactory::validateFieldParams(const ParticleFieldParams& fp) const {
    if (fp.id.empty()) {
        m_lastError = "Field ID cannot be empty";
        return false;
    }
    
    if (fp.density <= 0.0f) {
        m_lastError = "Density must be positive";
        return false;
    }
    
    if (fp.boundsMin.x >= fp.boundsMax.x ||
        fp.boundsMin.y >= fp.boundsMax.y ||
        fp.boundsMin.z >= fp.boundsMax.z) {
        m_lastError = "Invalid bounds: min must be less than max";
        return false;
    }
    
    return true;
}

bool ParticleFieldAssetFactory::validateNoiseParams(const NoiseParams& np) const {
    if (np.octaves < 1 || np.octaves > 16) {
        m_lastError = "Octaves must be between 1 and 16";
        return false;
    }
    
    if (np.frequency <= 0.0f) {
        m_lastError = "Frequency must be positive";
        return false;
    }
    
    if (np.lacunarity <= 0.0f) {
        m_lastError = "Lacunarity must be positive";
        return false;
    }
    
    if (np.gain <= 0.0f || np.gain >= 1.0f) {
        m_lastError = "Gain must be between 0 and 1";
        return false;
    }
    
    return true;
}

bool ParticleFieldAssetFactory::validateColorRampParams(const ColorRampParams& cr) const {
    if (cr.stops.empty()) {
        m_lastError = "Color ramp must have at least one stop";
        return false;
    }
    
    if (cr.resolution < 16 || cr.resolution > 4096) {
        m_lastError = "Resolution must be between 16 and 4096";
        return false;
    }
    
    // Validate stop order
    for (size_t i = 1; i < cr.stops.size(); ++i) {
        if (cr.stops[i].first <= cr.stops[i-1].first) {
            m_lastError = "Color stops must be in ascending order";
            return false;
        }
    }
    
    return true;
}

bool ParticleFieldAssetFactory::validateParticleParams(const ParticleParams& pp) const {
    if (pp.sizeRange.x <= 0.0f || pp.sizeRange.y <= 0.0f) {
        m_lastError = "Size range must be positive";
        return false;
    }
    
    if (pp.sizeRange.x > pp.sizeRange.y) {
        m_lastError = "Size range min must be less than max";
        return false;
    }
    
    if (pp.lifeTimeRange.x <= 0.0f || pp.lifeTimeRange.y <= 0.0f) {
        m_lastError = "Lifetime range must be positive";
        return false;
    }
    
    if (pp.lifeTimeRange.x > pp.lifeTimeRange.y) {
        m_lastError = "Lifetime range min must be less than max";
        return false;
    }
    
    if (pp.speedRange.x < 0.0f || pp.speedRange.y < 0.0f) {
        m_lastError = "Speed range must be non-negative";
        return false;
    }
    
    if (pp.speedRange.x > pp.speedRange.y) {
        m_lastError = "Speed range min must be less than max";
        return false;
    }
    
    return true;
}

// FieldGen Implementation
namespace FieldGen {

ParticleSystemHandle spawnField(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ParticleParams& pp,
    const TextureHandle& ramp) {
    
    ParticleSystem ps(fp.gpuDriven);
    ps.configure(pp.lifeTimeRange, pp.sizeRange, pp.alignToCamera);
    
    if (fp.useVolume) {
        ps.emitVolume(fp.boundsMin, fp.boundsMax, fp.density, fp.seed, np);
    } else {
        ps.emitSurface(fp.boundsMin, fp.boundsMax, fp.density);
    }
    
    ps.setColorRamp(ramp);
    return ps.create();
}

// ParticleSystem Implementation
ParticleSystem::ParticleSystem(bool gpuDriven)
    : m_gpuDriven(gpuDriven)
    , m_updateTime(0.0f)
    , m_renderTime(0.0f) {
    
    if (m_gpuDriven) {
        initializeGPU();
    } else {
        initializeCPU();
    }
}

ParticleSystem::~ParticleSystem() = default;

void ParticleSystem::configure(const glm::vec2& lifeTimeRange,
                              const glm::vec2& sizeRange,
                              bool alignToCamera) {
    m_lifeTimeRange = lifeTimeRange;
    m_sizeRange = sizeRange;
    m_alignToCamera = alignToCamera;
}

void ParticleSystem::emitVolume(const glm::vec3& boundsMin,
                               const glm::vec3& boundsMax,
                               float density,
                               float seed,
                               const NoiseParams& noiseParams) {
    
    // Calculate volume and particle count
    glm::vec3 size = boundsMax - boundsMin;
    float volume = size.x * size.y * size.z;
    size_t particleCount = static_cast<size_t>(volume * density);
    
    // Initialize random generator
    std::mt19937 gen(static_cast<uint32_t>(seed));
    std::uniform_real_distribution<float> posDist(0.0f, 1.0f);
    std::uniform_real_distribution<float> lifeDist(m_lifeTimeRange.x, m_lifeTimeRange.y);
    std::uniform_real_distribution<float> sizeDist(m_sizeRange.x, m_sizeRange.y);
    std::uniform_real_distribution<float> speedDist(m_speedRange.x, m_speedRange.y);
    
    // Generate particles
    m_particles.resize(particleCount);
    for (auto& particle : m_particles) {
        // Generate position within bounds
        glm::vec3 pos = boundsMin + glm::vec3(
            posDist(gen) * size.x,
            posDist(gen) * size.y,
            posDist(gen) * size.z
        );
        
        // Apply noise-based density weighting
        float noiseValue = NoiseGen::VolumeNoise::fbm3D(pos, 
                                                       noiseParams.octaves,
                                                       noiseParams.frequency,
                                                       noiseParams.lacunarity,
                                                       noiseParams.gain);
        
        // Skip particles in low-density areas
        if (noiseValue < 0.3f) {
            particle.active = false;
            continue;
        }
        
        // Set particle properties
        particle.position = pos;
        particle.velocity = glm::vec3(speedDist(gen), speedDist(gen), speedDist(gen));
        particle.lifetime = lifeDist(gen);
        particle.size = sizeDist(gen);
        particle.age = 0.0f;
        particle.color = glm::vec4(1.0f);
        particle.active = true;
    }
}

void ParticleSystem::emitSurface(const glm::vec3& boundsMin,
                                const glm::vec3& boundsMax,
                                float density) {
    
    // Calculate surface area and particle count
    glm::vec3 size = boundsMax - boundsMin;
    float surfaceArea = 2.0f * (size.x * size.y + size.y * size.z + size.z * size.x);
    size_t particleCount = static_cast<size_t>(surfaceArea * density);
    
    // Initialize random generator
    std::mt19937 gen;
    std::uniform_real_distribution<float> posDist(0.0f, 1.0f);
    std::uniform_real_distribution<float> lifeDist(m_lifeTimeRange.x, m_lifeTimeRange.y);
    std::uniform_real_distribution<float> sizeDist(m_sizeRange.x, m_sizeRange.y);
    
    // Generate particles on surfaces
    m_particles.resize(particleCount);
    for (auto& particle : m_particles) {
        // Randomly select a face
        int face = gen() % 6;
        glm::vec3 pos;
        
        switch (face) {
            case 0: // -X face
                pos = glm::vec3(boundsMin.x, 
                               boundsMin.y + posDist(gen) * size.y,
                               boundsMin.z + posDist(gen) * size.z);
                break;
            case 1: // +X face
                pos = glm::vec3(boundsMax.x,
                               boundsMin.y + posDist(gen) * size.y,
                               boundsMin.z + posDist(gen) * size.z);
                break;
            case 2: // -Y face
                pos = glm::vec3(boundsMin.x + posDist(gen) * size.x,
                               boundsMin.y,
                               boundsMin.z + posDist(gen) * size.z);
                break;
            case 3: // +Y face
                pos = glm::vec3(boundsMin.x + posDist(gen) * size.x,
                               boundsMax.y,
                               boundsMin.z + posDist(gen) * size.z);
                break;
            case 4: // -Z face
                pos = glm::vec3(boundsMin.x + posDist(gen) * size.x,
                               boundsMin.y + posDist(gen) * size.y,
                               boundsMin.z);
                break;
            case 5: // +Z face
                pos = glm::vec3(boundsMin.x + posDist(gen) * size.x,
                               boundsMin.y + posDist(gen) * size.y,
                               boundsMax.z);
                break;
        }
        
        // Set particle properties
        particle.position = pos;
        particle.velocity = glm::vec3(0.0f);
        particle.lifetime = lifeDist(gen);
        particle.size = sizeDist(gen);
        particle.age = 0.0f;
        particle.color = glm::vec4(1.0f);
        particle.active = true;
    }
}

void ParticleSystem::setColorRamp(const TextureHandle& ramp) {
    m_colorRamp = ramp;
}

ParticleSystemHandle ParticleSystem::create() {
    // Return a unique handle
    static uint32_t nextHandle = 1;
    return nextHandle++;
}

void ParticleSystem::enableComputeUpdate(const std::string& shaderPath) {
    m_computeShaderPath = shaderPath;
    if (m_gpuDriven) {
        // TODO: Load and compile compute shader
    }
}

void ParticleSystem::enableCPUUpdate(std::function<void(Particle&, float)> updateFunc) {
    m_cpuUpdateFunc = updateFunc;
}

size_t ParticleSystem::getParticleCount() const {
    return m_particles.size();
}

const std::vector<Particle>& ParticleSystem::getParticles() const {
    return m_particles;
}

float ParticleSystem::getUpdateTime() const {
    return m_updateTime;
}

float ParticleSystem::getRenderTime() const {
    return m_renderTime;
}

void ParticleSystem::initializeGPU() {
    // TODO: Initialize GPU resources
}

void ParticleSystem::initializeCPU() {
    // TODO: Initialize CPU resources
}

void ParticleSystem::updateParticles(float deltaTime) {
    auto start = std::chrono::high_resolution_clock::now();
    
    if (m_gpuDriven) {
        // TODO: GPU update
    } else if (m_cpuUpdateFunc) {
        for (auto& particle : m_particles) {
            if (particle.active) {
                m_cpuUpdateFunc(particle, deltaTime);
            }
        }
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    m_updateTime = std::chrono::duration<float>(end - start).count();
}

} // namespace FieldGen

// NoiseGen Implementation
namespace NoiseGen {

TextureHandle buildVolume(const NoiseParams& np,
                         const glm::vec3& min,
                         const glm::vec3& max) {
    
    return VolumeNoise::generate3D(np.noiseType,
                                  np.octaves,
                                  np.frequency,
                                  np.lacunarity,
                                  np.gain,
                                  min,
                                  max,
                                  np.warp);
}

// VolumeNoise Implementation
TextureHandle VolumeNoise::generate3D(const std::string& noiseType,
                                     int octaves,
                                     float frequency,
                                     float lacunarity,
                                     float gain,
                                     const glm::vec3& min,
                                     const glm::vec3& max,
                                     const glm::vec3& warp) {
    
    // TODO: Implement actual 3D texture generation
    // For now, return a placeholder handle
    static uint32_t nextHandle = 1;
    return nextHandle++;
}

float VolumeNoise::perlin3D(const glm::vec3& pos, float frequency) {
    // TODO: Implement Perlin noise
    return 0.5f + 0.5f * std::sin(pos.x * frequency) * 
                    std::sin(pos.y * frequency) * 
                    std::sin(pos.z * frequency);
}

float VolumeNoise::simplex3D(const glm::vec3& pos, float frequency) {
    // TODO: Implement Simplex noise
    return 0.5f + 0.5f * std::sin(pos.x * frequency) * 
                    std::sin(pos.y * frequency) * 
                    std::sin(pos.z * frequency);
}

float VolumeNoise::worley3D(const glm::vec3& pos, float frequency) {
    // TODO: Implement Worley noise
    return 0.5f + 0.5f * std::sin(pos.x * frequency) * 
                    std::sin(pos.y * frequency) * 
                    std::sin(pos.z * frequency);
}

float VolumeNoise::fbm3D(const glm::vec3& pos,
                         int octaves,
                         float frequency,
                         float lacunarity,
                         float gain) {
    float value = 0.0f;
    float amplitude = 1.0f;
    float freq = frequency;
    
    for (int i = 0; i < octaves; ++i) {
        value += amplitude * perlin3D(pos, freq);
        amplitude *= gain;
        freq *= lacunarity;
    }
    
    return value;
}

glm::vec3 VolumeNoise::domainWarp(const glm::vec3& pos,
                                  const glm::vec3& warp,
                                  const std::string& noiseType) {
    // TODO: Implement domain warping
    return pos + warp * perlin3D(pos, 1.0f);
}

} // namespace NoiseGen

// ColorGen Implementation
namespace ColorGen {

TextureHandle buildRamp(const ColorRampParams& cr) {
    return RampBuilder::create1DRamp(cr.stops, cr.resolution, cr.cyclic);
}

// RampBuilder Implementation
TextureHandle RampBuilder::create1DRamp(const std::vector<std::pair<float, glm::vec4>>& stops,
                                       int resolution,
                                       bool cyclic) {
    
    if (!validateStops(stops)) {
        throw std::invalid_argument("Invalid color ramp stops");
    }
    
    // TODO: Implement actual texture creation
    // For now, return a placeholder handle
    static uint32_t nextHandle = 1;
    return nextHandle++;
}

glm::vec4 RampBuilder::interpolateColors(const glm::vec4& color1,
                                         const glm::vec4& color2,
                                         float t) {
    return glm::mix(color1, color2, t);
}

bool RampBuilder::validateStops(const std::vector<std::pair<float, glm::vec4>>& stops) {
    if (stops.empty()) return false;
    
    // Check for ascending order
    for (size_t i = 1; i < stops.size(); ++i) {
        if (stops[i].first <= stops[i-1].first) {
            return false;
        }
    }
    
    return true;
}

std::vector<uint8_t> RampBuilder::generateRampTexture(const std::vector<std::pair<float, glm::vec4>>& stops,
                                                     int resolution,
                                                     bool cyclic) {
    std::vector<uint8_t> texture(resolution * 4); // RGBA
    
    for (int i = 0; i < resolution; ++i) {
        float t = static_cast<float>(i) / (resolution - 1);
        
        // Find the appropriate color stops
        glm::vec4 color = stops[0].second;
        for (size_t j = 1; j < stops.size(); ++j) {
            if (t <= stops[j].first) {
                float localT = (t - stops[j-1].first) / (stops[j].first - stops[j-1].first);
                color = interpolateColors(stops[j-1].second, stops[j].second, localT);
                break;
            }
        }
        
        // Convert to RGBA8
        texture[i*4 + 0] = static_cast<uint8_t>(color.r * 255.0f);
        texture[i*4 + 1] = static_cast<uint8_t>(color.g * 255.0f);
        texture[i*4 + 2] = static_cast<uint8_t>(color.b * 255.0f);
        texture[i*4 + 3] = static_cast<uint8_t>(color.a * 255.0f);
    }
    
    return texture;
}

} // namespace ColorGen

// SimGen Implementation
namespace SimGen {

void attachSim(ParticleSystemHandle ps, bool gpu) {
    // TODO: Implement simulation attachment
}

// SimulationModule Implementation
SimulationModule::SimulationModule(bool gpuDriven)
    : m_gpuDriven(gpuDriven)
    , m_gravity(0.0f, -9.81f, 0.0f)
    , m_wind(0.0f)
    , m_turbulence(0.0f)
    , m_updateTime(0.0f)
    , m_activeParticles(0) {
}

SimulationModule::~SimulationModule() = default;

void SimulationModule::enableComputeUpdate(const std::string& shaderPath) {
    m_computeShaderPath = shaderPath;
}

void SimulationModule::enableCPUUpdate(std::function<void(Particle&, float)> updateFunc) {
    m_cpuUpdateFunc = updateFunc;
}

void SimulationModule::update(float deltaTime) {
    auto start = std::chrono::high_resolution_clock::now();
    
    if (m_gpuDriven) {
        // TODO: GPU simulation update
    } else if (m_cpuUpdateFunc) {
        // TODO: CPU simulation update
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    m_updateTime = std::chrono::duration<float>(end - start).count();
}

void SimulationModule::setGravity(const glm::vec3& gravity) {
    m_gravity = gravity;
}

void SimulationModule::setWind(const glm::vec3& wind) {
    m_wind = wind;
}

void SimulationModule::setTurbulence(float intensity) {
    m_turbulence = intensity;
}

float SimulationModule::getUpdateTime() const {
    return m_updateTime;
}

int SimulationModule::getActiveParticles() const {
    return m_activeParticles;
}

} // namespace SimGen

// LODGen Implementation
namespace LODGen {

LODData compute(const LODParams& lp) {
    LODData data;
    data.thresholds = lp.screenSizes;
    data.scales = lp.densityScales;
    return data;
}

// LODManager Implementation
LODManager::LODManager(const LODParams& params) {
    m_thresholds = params.screenSizes;
    m_scales = params.densityScales;
}

int LODManager::selectLOD(float screenSize) const {
    for (int i = 0; i < static_cast<int>(m_thresholds.size()); ++i) {
        if (screenSize >= m_thresholds[i]) {
            return i;
        }
    }
    return static_cast<int>(m_thresholds.size()) - 1;
}

float LODManager::getDensityScale(int lodLevel) const {
    if (lodLevel >= 0 && lodLevel < static_cast<int>(m_scales.size())) {
        return m_scales[lodLevel];
    }
    return 1.0f;
}

int LODManager::getLODCount() const {
    return static_cast<int>(m_thresholds.size());
}

float LODManager::getScreenThreshold(int lodLevel) const {
    if (lodLevel >= 0 && lodLevel < static_cast<int>(m_thresholds.size())) {
        return m_thresholds[lodLevel];
    }
    return 0.0f;
}

} // namespace LODGen

// ShaderGen Implementation
namespace ShaderGen {

ShaderHandle buildFieldShader(const ParticleFieldParams& fp,
                             const NoiseParams& np,
                             const ColorRampParams& cr,
                             const ParticleParams& pp) {
    
    auto src = TemplateGen::expand(
        "shaders/field_render.frag",
        {
            {"USE_VOLUME", TemplateGen::toString(fp.useVolume)},
            {"SOFT_PARTICLES", TemplateGen::toString(pp.alignToCamera)},
            {"NOISE_TYPE", np.noiseType}
        },
        {}
    );
    
    return CompileGen::compile(src, ShaderStage::Fragment);
}

// TemplateGen Implementation
std::string TemplateGen::expand(const std::string& templatePath,
                               const std::map<std::string, std::string>& defines,
                               const std::map<std::string, std::string>& includes) {
    
    // TODO: Implement template expansion
    // For now, return a basic shader template
    std::stringstream ss;
    ss << "#version 450\n";
    ss << "precision highp float;\n\n";
    
    // Add defines
    for (const auto& [key, value] : defines) {
        ss << "#define " << key << " " << value << "\n";
    }
    
    ss << "\n";
    ss << "void main() {\n";
    ss << "    // TODO: Implement field rendering\n";
    ss << "}\n";
    
    return ss.str();
}

std::string TemplateGen::toString(bool value) {
    return value ? "true" : "false";
}

std::string TemplateGen::toString(int value) {
    return std::to_string(value);
}

std::string TemplateGen::toString(float value) {
    return std::to_string(value);
}

std::string TemplateGen::toString(const std::string& value) {
    return value;
}

std::string TemplateGen::replaceVariables(const std::string& templateStr,
                                        const std::map<std::string, std::string>& variables) {
    std::string result = templateStr;
    
    for (const auto& [key, value] : variables) {
        std::string placeholder = "{{" + key + "}}";
        size_t pos = result.find(placeholder);
        while (pos != std::string::npos) {
            result.replace(pos, placeholder.length(), value);
            pos = result.find(placeholder);
        }
    }
    
    return result;
}

// CompileGen Implementation
ShaderHandle CompileGen::compile(const std::string& source, ShaderStage stage) {
    // TODO: Implement actual shader compilation
    // For now, return a placeholder handle
    static uint32_t nextHandle = 1;
    return nextHandle++;
}

void CompileGen::setOptimizationLevel(int level) {
    m_optimizationLevel = level;
}

void CompileGen::enableDebugInfo(bool enable) {
    m_debugInfoEnabled = enable;
}

std::string CompileGen::getCompilationErrors() {
    return m_compilationErrors;
}

bool CompileGen::hasCompilationErrors() {
    return !m_compilationErrors.empty();
}

} // namespace ShaderGen

} // namespace ParticleFields
} // namespace MagiTech
