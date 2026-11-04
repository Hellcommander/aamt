#include "ParticleFieldAssetFactory.hpp"
#include "GeneratorConcurrency.hpp"
#include "core/Log.hpp"
#include "core/rendering/AssetHandle.hpp"
#include "vendor/FastNoiseLite/Cpp/FastNoiseLite.h"
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
std::mutex NoiseGen::VolumeNoise::m_randomMutex;
std::mt19937 NoiseGen::VolumeNoise::m_generator(std::random_device{}());
std::uniform_real_distribution<float> NoiseGen::VolumeNoise::m_distribution(0.0f, 1.0f);

// Static members for CompileGen
std::mutex ShaderGen::CompileGen::m_mutex;
int ShaderGen::CompileGen::m_optimizationLevel = 2;
bool ShaderGen::CompileGen::m_debugInfoEnabled = false;
std::string ShaderGen::CompileGen::m_compilationErrors;

// ---------------------------------------------------------------------------
// Field texture store
// ---------------------------------------------------------------------------
namespace {

struct TextureStore {
    std::mutex mutex;
    std::unordered_map<TextureHandle, FieldTextureData> textures;
};

TextureStore& textureStore() {
    static TextureStore store;
    return store;
}

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
}

} // namespace

TextureHandle storeFieldTexture(FieldTextureData data) {
    const TextureHandle handle = nextAssetHandle();
    std::lock_guard<std::mutex> lock(textureStore().mutex);
    textureStore().textures[handle] = std::move(data);
    return handle;
}

std::optional<FieldTextureData> getFieldTexture(TextureHandle handle) {
    std::lock_guard<std::mutex> lock(textureStore().mutex);
    auto it = textureStore().textures.find(handle);
    if (it == textureStore().textures.end()) return std::nullopt;
    return it->second;
}

// ParticleFieldAssetFactory Implementation
ParticleFieldAssetFactory::ParticleFieldAssetFactory()
    : m_gpuAccelerationEnabled(true)
    , m_maxThreads(4)
    , m_activeGenerations(0)
    , m_generationProgress(0.0f)
    , m_cacheHits(0)
    , m_cacheMisses(0) {

    initializeComponents();
}

ParticleFieldAssetFactory::~ParticleFieldAssetFactory() = default;

void ParticleFieldAssetFactory::initializeComponents() {
    // Initialize cache with default size
    m_cache = std::make_unique<ConcurrentLRUCache<uint64_t, ParticleFieldBundle>>(100);

    // Initialize thread pool
    m_pool = std::make_unique<GeneratorTaskPool>(static_cast<size_t>(m_maxThreads));
}

void ParticleFieldAssetFactory::setLastError(const std::string& error) const {
    std::lock_guard<std::mutex> lock(m_errorMutex);
    m_lastError = error;
}

std::future<ParticleFieldBundle> ParticleFieldAssetFactory::generateAsync(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ColorRampParams& cr,
    const ParticleParams& pp) {

    // Validate parameters
    if (!validateParams(fp, np, cr, pp)) {
        throw std::invalid_argument("Invalid particle field parameters: " + getLastError());
    }

    // Generate hash key for caching
    uint64_t key = hashCombine(fp, np, cr, pp);

    // Check cache first
    if (auto hit = m_cache->find(key)) {
        m_cacheHits++;
        return std::async(std::launch::deferred, [hit]() { return *hit; });
    }

    m_cacheMisses++;
    m_activeGenerations++;
    m_generationProgress = 0.0f;

    // Enqueue generation task
    return m_pool->enqueue([this, fp, np, cr, pp, key]() {
        try {
            ParticleFieldBundle bundle = generateInternal(fp, np, cr, pp);
            m_cache->insert(key, bundle);
            m_activeGenerations--;
            return bundle;
        } catch (const std::exception& e) {
            setLastError(e.what());
            m_activeGenerations--;
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
        throw std::invalid_argument("Invalid particle field parameters: " + getLastError());
    }

    // Generate hash key for caching
    uint64_t key = hashCombine(fp, np, cr, pp);

    // Check cache first
    if (auto hit = m_cache->find(key)) {
        m_cacheHits++;
        return *hit;
    }

    m_cacheMisses++;
    m_activeGenerations++;

    // Generate synchronously
    try {
        ParticleFieldBundle bundle = generateInternal(fp, np, cr, pp);
        m_cache->insert(key, bundle);
        m_activeGenerations--;
        return bundle;
    } catch (const std::exception& e) {
        setLastError(e.what());
        m_activeGenerations--;
        throw;
    }
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

    // Step 5: Spawn particle field and attach its simulation
    bundle.particles = FieldGen::spawnField(fp, np, pp, bundle.colorRampTex);
    SimGen::attachSim(bundle.particles, fp.gpuDriven && m_gpuAccelerationEnabled);
    m_generationProgress = 1.0f;

    return bundle;
}

// Cache Management
void ParticleFieldAssetFactory::clearCache() {
    m_cache->clear();
}

void ParticleFieldAssetFactory::setCacheSize(size_t maxEntries) {
    m_cache->set_capacity(maxEntries);
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
    // The old pool finishes its queued tasks when it is destroyed.
    m_pool = std::make_unique<GeneratorTaskPool>(static_cast<size_t>(m_maxThreads));
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
    std::lock_guard<std::mutex> lock(m_errorMutex);
    return m_lastError;
}

void ParticleFieldAssetFactory::clearLastError() {
    std::lock_guard<std::mutex> lock(m_errorMutex);
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
    return m_activeGenerations.load() > 0;
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
        setLastError("Field ID cannot be empty");
        return false;
    }

    if (fp.density <= 0.0f) {
        setLastError("Density must be positive");
        return false;
    }

    if (fp.boundsMin.x >= fp.boundsMax.x ||
        fp.boundsMin.y >= fp.boundsMax.y ||
        fp.boundsMin.z >= fp.boundsMax.z) {
        setLastError("Invalid bounds: min must be less than max");
        return false;
    }

    if (fp.lod.screenSizes.size() != fp.lod.densityScales.size()) {
        setLastError("LOD screen sizes and density scales must have the same length");
        return false;
    }

    return true;
}

bool ParticleFieldAssetFactory::validateNoiseParams(const NoiseParams& np) const {
    if (np.octaves < 1 || np.octaves > 16) {
        setLastError("Octaves must be between 1 and 16");
        return false;
    }

    if (np.frequency <= 0.0f) {
        setLastError("Frequency must be positive");
        return false;
    }

    if (np.lacunarity <= 0.0f) {
        setLastError("Lacunarity must be positive");
        return false;
    }

    if (np.gain <= 0.0f || np.gain >= 1.0f) {
        setLastError("Gain must be between 0 and 1");
        return false;
    }

    return true;
}

bool ParticleFieldAssetFactory::validateColorRampParams(const ColorRampParams& cr) const {
    if (cr.stops.empty()) {
        setLastError("Color ramp must have at least one stop");
        return false;
    }

    if (cr.resolution < 16 || cr.resolution > 4096) {
        setLastError("Resolution must be between 16 and 4096");
        return false;
    }

    // Validate stop order
    for (size_t i = 1; i < cr.stops.size(); ++i) {
        if (cr.stops[i].first <= cr.stops[i-1].first) {
            setLastError("Color stops must be in ascending order");
            return false;
        }
    }

    return true;
}

bool ParticleFieldAssetFactory::validateParticleParams(const ParticleParams& pp) const {
    if (pp.sizeRange.x <= 0.0f || pp.sizeRange.y <= 0.0f) {
        setLastError("Size range must be positive");
        return false;
    }

    if (pp.sizeRange.x > pp.sizeRange.y) {
        setLastError("Size range min must be less than max");
        return false;
    }

    if (pp.lifeTimeRange.x <= 0.0f || pp.lifeTimeRange.y <= 0.0f) {
        setLastError("Lifetime range must be positive");
        return false;
    }

    if (pp.lifeTimeRange.x > pp.lifeTimeRange.y) {
        setLastError("Lifetime range min must be less than max");
        return false;
    }

    if (pp.speedRange.x < 0.0f || pp.speedRange.y < 0.0f) {
        setLastError("Speed range must be non-negative");
        return false;
    }

    if (pp.speedRange.x > pp.speedRange.y) {
        setLastError("Speed range min must be less than max");
        return false;
    }

    return true;
}

// FieldGen Implementation
namespace FieldGen {

namespace {
struct SystemRegistry {
    std::mutex mutex;
    std::unordered_map<ParticleSystemHandle, std::shared_ptr<ParticleSystem>> systems;
};
SystemRegistry& systemRegistry() {
    static SystemRegistry registry;
    return registry;
}
} // namespace

std::shared_ptr<ParticleSystem> getSystem(ParticleSystemHandle handle) {
    std::lock_guard<std::mutex> lock(systemRegistry().mutex);
    auto it = systemRegistry().systems.find(handle);
    return it == systemRegistry().systems.end() ? nullptr : it->second;
}

void destroySystem(ParticleSystemHandle handle) {
    std::lock_guard<std::mutex> lock(systemRegistry().mutex);
    systemRegistry().systems.erase(handle);
}

ParticleSystemHandle spawnField(
    const ParticleFieldParams& fp,
    const NoiseParams& np,
    const ParticleParams& pp,
    const TextureHandle& ramp) {

    ParticleSystem ps(fp.gpuDriven);
    ps.configure(pp.lifeTimeRange, pp.sizeRange, pp.alignToCamera);
    ps.setSpeedRange(pp.speedRange);
    ps.setColorRamp(ramp);

    if (fp.useVolume) {
        ps.emitVolume(fp.boundsMin, fp.boundsMax, fp.density, fp.seed, np);
    } else {
        ps.emitSurface(fp.boundsMin, fp.boundsMax, fp.density, fp.seed);
    }

    const ParticleSystemHandle handle = ps.create();
    Log::info("ParticleField", "Spawned field '{}' as system {} ({} particles)", fp.id, handle, ps.getActiveParticleCount());
    return handle;
}

// ParticleSystem Implementation
ParticleSystem::ParticleSystem(bool gpuDriven)
    : m_gpuDriven(gpuDriven)
    , m_lifeTimeRange(1.0f, 1.0f)
    , m_sizeRange(1.0f, 1.0f)
    , m_speedRange(0.0f, 0.0f)
    , m_alignToCamera(true)
    , m_colorRamp(0)
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

void ParticleSystem::setSpeedRange(const glm::vec2& speedRange) {
    m_speedRange = speedRange;
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
    std::uniform_real_distribution<float> dirDist(-1.0f, 1.0f);

    // Generate particles; the noise field decides where the cloud is dense.
    m_particles.clear();
    m_particles.reserve(particleCount);
    for (size_t i = 0; i < particleCount; ++i) {
        // Generate position within bounds
        glm::vec3 pos = boundsMin + glm::vec3(
            posDist(gen) * size.x,
            posDist(gen) * size.y,
            posDist(gen) * size.z
        );

        // Apply noise-based density weighting (domain-warped)
        const glm::vec3 warped = NoiseGen::VolumeNoise::domainWarp(pos, noiseParams.warp, noiseParams.noiseType);
        float noiseValue = NoiseGen::VolumeNoise::sample(noiseParams.noiseType, warped,
                                                         noiseParams.octaves,
                                                         noiseParams.frequency,
                                                         noiseParams.lacunarity,
                                                         noiseParams.gain);

        // Skip particles in low-density areas
        if (noiseValue < 0.3f) {
            continue;
        }

        Particle particle;
        particle.position = pos;
        glm::vec3 dir(dirDist(gen), dirDist(gen), dirDist(gen));
        if (glm::length(dir) < 1e-4f) dir = glm::vec3(0.0f, 1.0f, 0.0f);
        particle.velocity = glm::normalize(dir) * speedDist(gen);
        particle.lifetime = lifeDist(gen);
        particle.size = sizeDist(gen);
        particle.age = 0.0f;
        particle.color = glm::vec4(1.0f);
        particle.active = true;
        m_particles.push_back(particle);
    }
    applyColorRamp();
}

void ParticleSystem::emitSurface(const glm::vec3& boundsMin,
                                const glm::vec3& boundsMax,
                                float density,
                                float seed) {

    // Calculate surface area and particle count
    glm::vec3 size = boundsMax - boundsMin;
    float surfaceArea = 2.0f * (size.x * size.y + size.y * size.z + size.z * size.x);
    size_t particleCount = static_cast<size_t>(surfaceArea * density);

    // Initialize random generator
    std::mt19937 gen(static_cast<uint32_t>(seed));
    std::uniform_real_distribution<float> posDist(0.0f, 1.0f);
    std::uniform_real_distribution<float> lifeDist(m_lifeTimeRange.x, m_lifeTimeRange.y);
    std::uniform_real_distribution<float> sizeDist(m_sizeRange.x, m_sizeRange.y);
    std::uniform_int_distribution<int> faceDist(0, 5);

    // Generate particles on surfaces
    m_particles.resize(particleCount);
    for (auto& particle : m_particles) {
        // Randomly select a face
        int face = faceDist(gen);
        glm::vec3 pos(0.0f);

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
            default: // +Z face
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
    applyColorRamp();
}

void ParticleSystem::setColorRamp(const TextureHandle& ramp) {
    m_colorRamp = ramp;
    applyColorRamp();
}

void ParticleSystem::applyColorRamp() {
    // Colour each particle from the ramp by its normalized lifetime.
    if (m_colorRamp == 0 || m_particles.empty()) return;
    auto ramp = getFieldTexture(m_colorRamp);
    if (!ramp || ramp->width <= 0 || ramp->rgba.empty()) return;
    const float span = std::max(m_lifeTimeRange.y - m_lifeTimeRange.x, 1e-6f);
    for (auto& particle : m_particles) {
        const float t = std::clamp((particle.lifetime - m_lifeTimeRange.x) / span, 0.0f, 1.0f);
        const int x = std::clamp(static_cast<int>(t * (ramp->width - 1) + 0.5f), 0, ramp->width - 1);
        const size_t i = static_cast<size_t>(x) * 4;
        particle.color = glm::vec4(ramp->rgba[i] / 255.0f, ramp->rgba[i + 1] / 255.0f,
                                   ramp->rgba[i + 2] / 255.0f, ramp->rgba[i + 3] / 255.0f);
    }
}

ParticleSystemHandle ParticleSystem::create() {
    const ParticleSystemHandle handle = nextAssetHandle();
    auto stored = std::make_shared<ParticleSystem>(*this);
    std::lock_guard<std::mutex> lock(systemRegistry().mutex);
    systemRegistry().systems[handle] = std::move(stored);
    return handle;
}

void ParticleSystem::enableComputeUpdate(const std::string& shaderPath) {
    // The compute shader is dispatched by the renderer that owns GPU-driven
    // systems; the generator records which shader to use.
    m_computeShaderPath = shaderPath;
}

void ParticleSystem::enableCPUUpdate(std::function<void(Particle&, float)> updateFunc) {
    m_cpuUpdateFunc = std::move(updateFunc);
}

void ParticleSystem::update(float deltaTime) {
    updateParticles(deltaTime);
}

size_t ParticleSystem::getParticleCount() const {
    return m_particles.size();
}

size_t ParticleSystem::getActiveParticleCount() const {
    return static_cast<size_t>(std::count_if(m_particles.begin(), m_particles.end(),
                                              [](const Particle& p) { return p.active; }));
}

const std::vector<Particle>& ParticleSystem::getParticles() const {
    return m_particles;
}

std::vector<Particle>& ParticleSystem::getParticles() {
    return m_particles;
}

float ParticleSystem::getUpdateTime() const {
    return m_updateTime;
}

float ParticleSystem::getRenderTime() const {
    return m_renderTime;
}

void ParticleSystem::initializeGPU() {
    // GPU-driven systems are uploaded and simulated by the renderer; nothing to
    // allocate on the CPU side beyond the particle seed data.
    m_particles.clear();
}

void ParticleSystem::initializeCPU() {
    m_particles.clear();
}

void ParticleSystem::updateParticles(float deltaTime) {
    auto start = std::chrono::high_resolution_clock::now();

    if (m_cpuUpdateFunc) {
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

namespace {
// Thread-local FastNoiseLite instances (their sampling is const but configuration is per instance).
float sampleFastNoise(FastNoiseLite::NoiseType type, const glm::vec3& pos, float frequency,
                      FastNoiseLite::CellularReturnType cellularReturn = FastNoiseLite::CellularReturnType_Distance) {
    thread_local FastNoiseLite noise;
    noise.SetNoiseType(type);
    noise.SetFrequency(frequency);
    noise.SetCellularReturnType(cellularReturn);
    return noise.GetNoise(pos.x, pos.y, pos.z);
}
} // namespace

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

    // Sample the noise over the field bounds into an RGBA8 volume:
    // R = density, G/B/A = density gradient direction (packed to [0, 1]).
    const int res = kVolumeResolution;
    FieldTextureData volume;
    volume.width = res;
    volume.height = res;
    volume.depth = res;
    volume.rgba.resize(static_cast<size_t>(res) * res * res * 4);

    const glm::vec3 extent = max - min;
    std::vector<float> density(static_cast<size_t>(res) * res * res);
    for (int z = 0; z < res; ++z) {
        for (int y = 0; y < res; ++y) {
            for (int x = 0; x < res; ++x) {
                const glm::vec3 t((x + 0.5f) / res, (y + 0.5f) / res, (z + 0.5f) / res);
                const glm::vec3 pos = domainWarp(min + t * extent, warp, noiseType);
                density[(static_cast<size_t>(z) * res + y) * res + x] =
                    sample(noiseType, pos, octaves, frequency, lacunarity, gain);
            }
        }
    }

    auto at = [&](int x, int y, int z) {
        x = std::clamp(x, 0, res - 1);
        y = std::clamp(y, 0, res - 1);
        z = std::clamp(z, 0, res - 1);
        return density[(static_cast<size_t>(z) * res + y) * res + x];
    };
    for (int z = 0; z < res; ++z) {
        for (int y = 0; y < res; ++y) {
            for (int x = 0; x < res; ++x) {
                glm::vec3 grad(at(x + 1, y, z) - at(x - 1, y, z),
                               at(x, y + 1, z) - at(x, y - 1, z),
                               at(x, y, z + 1) - at(x, y, z - 1));
                if (glm::length(grad) > 1e-6f) grad = glm::normalize(grad);
                const size_t i = ((static_cast<size_t>(z) * res + y) * res + x) * 4;
                volume.rgba[i + 0] = toByte(at(x, y, z));
                volume.rgba[i + 1] = toByte(grad.x * 0.5f + 0.5f);
                volume.rgba[i + 2] = toByte(grad.y * 0.5f + 0.5f);
                volume.rgba[i + 3] = toByte(grad.z * 0.5f + 0.5f);
            }
        }
    }

    return storeFieldTexture(std::move(volume));
}

float VolumeNoise::perlin3D(const glm::vec3& pos, float frequency) {
    return 0.5f + 0.5f * sampleFastNoise(FastNoiseLite::NoiseType_Perlin, pos, frequency);
}

float VolumeNoise::simplex3D(const glm::vec3& pos, float frequency) {
    return 0.5f + 0.5f * sampleFastNoise(FastNoiseLite::NoiseType_OpenSimplex2, pos, frequency);
}

float VolumeNoise::worley3D(const glm::vec3& pos, float frequency) {
    // Cellular F1 distance: FastNoiseLite returns it remapped to roughly [-1, 1].
    return std::clamp(0.5f + 0.5f * sampleFastNoise(FastNoiseLite::NoiseType_Cellular, pos, frequency,
                                                    FastNoiseLite::CellularReturnType_Distance), 0.0f, 1.0f);
}

float VolumeNoise::fbm3D(const glm::vec3& pos,
                         int octaves,
                         float frequency,
                         float lacunarity,
                         float gain) {
    float value = 0.0f;
    float amplitude = 1.0f;
    float freq = frequency;
    float norm = 0.0f;

    for (int i = 0; i < octaves; ++i) {
        value += amplitude * perlin3D(pos, freq);
        norm += amplitude;
        amplitude *= gain;
        freq *= lacunarity;
    }

    // Normalized back to [0, 1]
    return norm > 0.0f ? value / norm : 0.0f;
}

float VolumeNoise::sample(const std::string& noiseType, const glm::vec3& pos, int octaves,
                          float frequency, float lacunarity, float gain) {
    if (noiseType == "Perlin" || noiseType == "perlin") return perlin3D(pos, frequency);
    if (noiseType == "Simplex" || noiseType == "simplex") return simplex3D(pos, frequency);
    if (noiseType == "Worley" || noiseType == "worley" || noiseType == "Cellular") return worley3D(pos, frequency);
    return fbm3D(pos, octaves, frequency, lacunarity, gain); // "FBM" and default
}

glm::vec3 VolumeNoise::domainWarp(const glm::vec3& pos,
                                  const glm::vec3& warp,
                                  const std::string& noiseType) {
    if (warp == glm::vec3(0.0f)) return pos;
    // Offset each axis by an independent noise sample (decorrelated by fixed offsets),
    // scaled by the per-axis warp amount relative to the feature size.
    const float frequency = 0.05f;
    const float scale = 1.0f / frequency;
    const glm::vec3 offset(
        sample(noiseType, pos + glm::vec3(31.7f, 0.0f, 0.0f), 2, frequency, 2.0f, 0.5f) * 2.0f - 1.0f,
        sample(noiseType, pos + glm::vec3(0.0f, 57.3f, 0.0f), 2, frequency, 2.0f, 0.5f) * 2.0f - 1.0f,
        sample(noiseType, pos + glm::vec3(0.0f, 0.0f, 91.1f), 2, frequency, 2.0f, 0.5f) * 2.0f - 1.0f);
    return pos + warp * offset * scale;
}

float VolumeNoise::random01() {
    std::lock_guard<std::mutex> lock(m_randomMutex);
    return m_distribution(m_generator);
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

    FieldTextureData ramp;
    ramp.width = std::max(resolution, 2);
    ramp.height = 1;
    ramp.depth = 1;
    ramp.rgba = generateRampTexture(stops, ramp.width, cyclic);
    return storeFieldTexture(std::move(ramp));
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

glm::vec4 RampBuilder::evaluate(const std::vector<std::pair<float, glm::vec4>>& stops, float t, bool cyclic) {
    if (stops.empty()) return glm::vec4(1.0f);
    if (stops.size() == 1) return stops.front().second;

    const auto& first = stops.front();
    const auto& last = stops.back();
    if (t <= first.first || t >= last.first) {
        if (!cyclic) return t <= first.first ? first.second : last.second;
        // Cyclic: blend from the last stop around to the first one.
        const float gap = (1.0f - last.first) + first.first;
        if (gap <= 1e-6f) return t <= first.first ? first.second : last.second;
        const float local = t >= last.first ? (t - last.first) / gap : (t + 1.0f - last.first) / gap;
        return interpolateColors(last.second, first.second, std::clamp(local, 0.0f, 1.0f));
    }
    for (size_t j = 1; j < stops.size(); ++j) {
        if (t <= stops[j].first) {
            const float localT = (t - stops[j - 1].first) / (stops[j].first - stops[j - 1].first);
            return interpolateColors(stops[j - 1].second, stops[j].second, localT);
        }
    }
    return last.second;
}

std::vector<uint8_t> RampBuilder::generateRampTexture(const std::vector<std::pair<float, glm::vec4>>& stops,
                                                     int resolution,
                                                     bool cyclic) {
    std::vector<uint8_t> texture(static_cast<size_t>(resolution) * 4); // RGBA

    for (int i = 0; i < resolution; ++i) {
        // Cyclic ramps sample [0, 1) so the last texel does not duplicate the first.
        float t = cyclic ? static_cast<float>(i) / resolution
                         : static_cast<float>(i) / std::max(resolution - 1, 1);
        glm::vec4 color = evaluate(stops, t, cyclic);

        // Convert to RGBA8
        texture[i*4 + 0] = toByte(color.r);
        texture[i*4 + 1] = toByte(color.g);
        texture[i*4 + 2] = toByte(color.b);
        texture[i*4 + 3] = toByte(color.a);
    }

    return texture;
}

} // namespace ColorGen

// SimGen Implementation
namespace SimGen {

namespace {
struct SimulationRegistry {
    std::mutex mutex;
    std::unordered_map<ParticleSystemHandle, std::shared_ptr<SimulationModule>> modules;
};
SimulationRegistry& simulationRegistry() {
    static SimulationRegistry registry;
    return registry;
}
} // namespace

void attachSim(ParticleSystemHandle ps, bool gpu) {
    if (ps == 0) return;
    auto module = std::make_shared<SimulationModule>(gpu);
    if (auto system = FieldGen::getSystem(ps)) {
        if (gpu && !system->getComputeShaderPath().empty()) {
            module->enableComputeUpdate(system->getComputeShaderPath());
        }
    }
    std::lock_guard<std::mutex> lock(simulationRegistry().mutex);
    simulationRegistry().modules[ps] = std::move(module);
}

std::shared_ptr<SimulationModule> getSimulation(ParticleSystemHandle ps) {
    std::lock_guard<std::mutex> lock(simulationRegistry().mutex);
    auto it = simulationRegistry().modules.find(ps);
    return it == simulationRegistry().modules.end() ? nullptr : it->second;
}

// SimulationModule Implementation
SimulationModule::SimulationModule(bool gpuDriven)
    : m_gpuDriven(gpuDriven)
    , m_gravity(0.0f, -9.81f, 0.0f)
    , m_wind(0.0f)
    , m_turbulence(0.0f)
    , m_time(0.0f)
    , m_updateTime(0.0f)
    , m_activeParticles(0) {
}

SimulationModule::~SimulationModule() = default;

void SimulationModule::enableComputeUpdate(const std::string& shaderPath) {
    m_computeShaderPath = shaderPath;
}

void SimulationModule::enableCPUUpdate(std::function<void(Particle&, float)> updateFunc) {
    m_cpuUpdateFunc = std::move(updateFunc);
}

void SimulationModule::update(std::vector<Particle>& particles, float deltaTime) {
    auto start = std::chrono::high_resolution_clock::now();
    m_time += deltaTime;

    // CPU integration (GPU-driven systems use the same rules in the compute shader
    // when the renderer provides one; this path keeps them simulated otherwise).
    int active = 0;
    for (auto& particle : particles) {
        if (!particle.active) continue;

        glm::vec3 acceleration = m_gravity + m_wind;
        if (m_turbulence > 0.0f) {
            const glm::vec3 p = particle.position * 0.1f + glm::vec3(0.0f, 0.0f, m_time);
            acceleration += m_turbulence * glm::vec3(
                NoiseGen::VolumeNoise::perlin3D(p, 1.0f) * 2.0f - 1.0f,
                NoiseGen::VolumeNoise::perlin3D(p + glm::vec3(17.0f), 1.0f) * 2.0f - 1.0f,
                NoiseGen::VolumeNoise::perlin3D(p + glm::vec3(41.0f), 1.0f) * 2.0f - 1.0f);
        }
        particle.velocity += acceleration * deltaTime;
        particle.position += particle.velocity * deltaTime;

        if (m_cpuUpdateFunc) {
            m_cpuUpdateFunc(particle, deltaTime);
        }

        particle.age += deltaTime;
        if (particle.age >= particle.lifetime) {
            particle.active = false;
            continue;
        }
        ++active;
    }
    m_activeParticles = active;

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

LODManager::LODManager(const LODData& data) {
    m_thresholds = data.thresholds;
    m_scales = data.scales;
}

int LODManager::selectLOD(float screenSize) const {
    if (m_thresholds.empty()) return 0;
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
            {"NOISE_TYPE", np.noiseType},
            {"RAMP_CYCLIC", TemplateGen::toString(cr.cyclic)},
            {"RAMP_RESOLUTION", TemplateGen::toString(cr.resolution)}
        },
        {}
    );

    return CompileGen::compile(src, ShaderStage::Fragment);
}

namespace {
// Built-in particle field fragment shader used when no template file is present.
const char* kDefaultFieldShader = R"(#version 450
layout(location = 0) in vec2 vTexCoord;
layout(location = 1) in vec4 vColor;
layout(location = 2) in vec3 vWorldPos;
layout(location = 0) out vec4 fragColor;

uniform sampler1D uColorRamp;
uniform sampler3D uNoiseVolume;
uniform vec3 uBoundsMin;
uniform vec3 uBoundsMax;
uniform float uLifeT;

void main() {
    vec2 centered = vTexCoord * 2.0 - 1.0;
    float falloff = 1.0;
#if SOFT_PARTICLES
    falloff = clamp(1.0 - dot(centered, centered), 0.0, 1.0);
#endif
    vec4 color = vColor * texture(uColorRamp, uLifeT);
#if USE_VOLUME
    vec3 uvw = (vWorldPos - uBoundsMin) / max(uBoundsMax - uBoundsMin, vec3(1e-4));
    color.a *= texture(uNoiseVolume, uvw).r;
#endif
    fragColor = vec4(color.rgb, color.a * falloff);
}
)";
} // namespace

std::string TemplateGen::expand(const std::string& templatePath,
                               const std::map<std::string, std::string>& defines,
                               const std::map<std::string, std::string>& includes) {
    std::string source;
    {
        std::ifstream file(templatePath);
        if (file.is_open()) {
            std::stringstream buffer;
            buffer << file.rdbuf();
            source = buffer.str();
        }
    }
    if (source.empty()) {
        source = kDefaultFieldShader;
    }

    // GLSL preprocessor values: booleans become 1/0.
    std::stringstream defineBlock;
    for (const auto& [key, value] : defines) {
        const std::string v = value == "true" ? "1" : (value == "false" ? "0" : value);
        defineBlock << "#define " << key << " " << v << "\n";
    }

    // Defines must follow the #version line.
    const size_t versionPos = source.find("#version");
    if (versionPos != std::string::npos) {
        const size_t lineEnd = source.find('\n', versionPos);
        const size_t insertAt = lineEnd == std::string::npos ? source.size() : lineEnd + 1;
        source.insert(insertAt, defineBlock.str());
    } else {
        source = defineBlock.str() + source;
    }

    // {{KEY}} placeholders: includes (snippets) and defines (values).
    std::map<std::string, std::string> variables = defines;
    for (const auto& [key, value] : includes) variables[key] = value;
    return replaceVariables(source, variables);
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
            pos = result.find(placeholder, pos + value.length());
        }
    }

    return result;
}

// CompileGen Implementation
ShaderHandle CompileGen::compile(const std::string& source, ShaderStage stage) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_compilationErrors.clear();

    if (source.find("void main") == std::string::npos) {
        m_compilationErrors = "Shader source has no entry point (void main)";
        return 0;
    }

    ShaderDesc desc;
    desc.stage = stage;
    desc.source = source;
    if (stage == ShaderStage::Vertex) {
        desc.vertexSource = source;
    } else if (stage == ShaderStage::Fragment) {
        desc.fragmentSource = source;
    }
    if (m_debugInfoEnabled) desc.defines.push_back("DEBUG_INFO");
    desc.defines.push_back("OPTIMIZATION_LEVEL=" + std::to_string(m_optimizationLevel));

    const ShaderHandle handle = Shaders::compile(desc);
    if (handle == 0) {
        m_compilationErrors = "Shader compilation failed";
    }
    return handle;
}

void CompileGen::setOptimizationLevel(int level) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_optimizationLevel = std::clamp(level, 0, 3);
}

void CompileGen::enableDebugInfo(bool enable) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_debugInfoEnabled = enable;
}

std::string CompileGen::getCompilationErrors() {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_compilationErrors;
}

bool CompileGen::hasCompilationErrors() {
    std::lock_guard<std::mutex> lock(m_mutex);
    return !m_compilationErrors.empty();
}

} // namespace ShaderGen

} // namespace ParticleFields
} // namespace MagiTech
