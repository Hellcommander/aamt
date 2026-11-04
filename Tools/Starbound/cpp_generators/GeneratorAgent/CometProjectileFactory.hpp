#pragma once
#include <future>
#include <mutex>
#include <vector>
#include <string>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "GeneratorConcurrency.hpp"
#include "CometProjectileTypes.hpp"

namespace MagiTech {
namespace CometProjectiles {

// Forward declarations for generator namespaces
namespace MeshGen {
    MeshHandle buildCometCore(const CometProjectileParams& p);
    MeshHandle buildCometTrail(const CometProjectileParams& p);
    MeshHandle generateIcoSphere(float radius, int detail);
    MeshHandle applyVertexNoise(MeshHandle mesh, float irregularity);
    MeshHandle applyCrystallineNoise(MeshHandle mesh, float irregularity);
    MeshHandle applyPhysicsDeformation(MeshHandle mesh, float mass, float speed);
    MeshHandle createRibbonMesh(float length, float width, int segmentCount);
    MeshHandle applyTrailDistortion(MeshHandle mesh, float strength, float scale, float speed);
    MeshHandle buildFragments(const CometProjectileParams& p);
}

namespace ShaderGen {
    ShaderHandle buildCometShader(const CometProjectileParams& p);
    ShaderHandle buildHeatDistortion(const CometProjectileParams& p);
    std::string generateCometShaderCode(const CometProjectileParams& p);
    std::string generateCometVertexShader(const CometProjectileParams& p);
    std::string generateHeatDistortionVertexShader(const CometProjectileParams& p);
    std::string generateHeatDistortionFragmentShader(const CometProjectileParams& p);
}

namespace TextureGen {
    TextureHandle buildCometTexture(const CometProjectileParams& p);
    TextureHandle buildRockTexture(float frequency);
    TextureHandle buildColorMap(const glm::vec3& heatColor, const glm::vec3& burnColor);
    TextureHandle mergeTextures(const TextureHandle& rock, const TextureHandle& color);
    TextureHandle applyMeteorEffects(TextureHandle texture, const CometProjectileParams& p);
    TextureHandle applyCometEffects(TextureHandle texture, const CometProjectileParams& p);
    TextureHandle applyAsteroidEffects(TextureHandle texture, const CometProjectileParams& p);
    TextureHandle applyFallingStarEffects(TextureHandle texture, const CometProjectileParams& p);
    TextureHandle applyCelestialRockEffects(TextureHandle texture, const CometProjectileParams& p);
}

namespace ParticleGen {
    ParticleHandle buildDustTrail(const CometProjectileParams& p);
    ParticleHandle buildSparks(const CometProjectileParams& p);
    ParticleHandle buildFragments(const CometProjectileParams& p);
}

/** Runs every generator for p and fills the bundle, including its metrics. */
CometAssetBundle buildCometAssetBundle(const CometProjectileParams& p);

/** Reads a comet parameter file (JSON, see ParamUtils::fromJson); throws on I/O or parse errors. */
CometProjectileParams loadCometParamsFromJsonFile(const std::string& jsonPath);

class CometProjectileFactory {
public:
    CometProjectileFactory() : m_initialized(false) {}
    ~CometProjectileFactory() { shutdown(); }

    void initialize(size_t cache_size, size_t num_threads) {
        if (m_initialized) return;
        m_cache.set_capacity(cache_size);
        m_pool.start(num_threads);
        m_initialized = true;
    }

    void shutdown() {
        if (!m_initialized) return;
        m_pool.stop();
        m_initialized = false;
    }

    // Asynchronous generation
    std::future<CometAssetBundle> generateAsync(const CometProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            recordGeneration(true, 0.0);
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([this, p, key]() {
            CometAssetBundle b = buildCometAssetBundle(p);
            recordGeneration(false, b.generationTime);
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation
    CometAssetBundle generateSync(const CometProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            recordGeneration(true, 0.0);
            return *hit;
        }
        
        CometAssetBundle b = buildCometAssetBundle(p);
        recordGeneration(false, b.generationTime);
        m_cache.insert(key, b);
        return b;
    }

    // JSON-based generation
    std::future<CometAssetBundle> generateFromJson(const std::string& jsonPath) {
        return m_pool.enqueue([this, jsonPath]() {
            // Load JSON and parse parameters
            CometProjectileParams params = loadCometParamsFromJsonFile(jsonPath);
            return generateSync(params);
        });
    }

    // Batch generation
    std::vector<std::future<CometAssetBundle>> generateBatchAsync(const std::vector<CometProjectileParams>& params) {
        std::vector<std::future<CometAssetBundle>> futures;
        futures.reserve(params.size());
        
        for (const auto& param : params) {
            futures.push_back(generateAsync(param));
        }
        
        return futures;
    }

    // Parameter validation
    bool validateParams(const CometProjectileParams& params) {
        if (params.id.empty()) return false;
        if (params.coreRadius <= 0.0f) return false;
        if (params.irregularity < 0.0f || params.irregularity > 1.0f) return false;
        if (params.speed <= 0.0f) return false;
        if (params.gravityInfluence < 0.0f) return false;
        if (params.mass <= 0.0f) return false;
        if (params.drag < 0.0f) return false;
        if (params.lift < 0.0f) return false;
        if (params.glowIntensity < 0.0f) return false;
        if (params.emissivePower < 0.0f) return false;
        if (params.coreOpacity < 0.0f || params.coreOpacity > 1.0f) return false;
        if (params.trailOpacity < 0.0f || params.trailOpacity > 1.0f) return false;
        if (params.trailLength < 0.0f) return false;
        if (params.trailWidth <= 0.0f) return false;
        if (params.trailNoiseScale <= 0.0f) return false;
        if (params.trailNoiseSpeed < 0.0f) return false;
        if (params.trailFadeSpeed < 0.0f) return false;
        if (params.trailDistortionStrength < 0.0f) return false;
        if (params.dustParticleCount < 0) return false;
        if (params.dustLifetime <= 0.0f) return false;
        if (params.dustSize <= 0.0f) return false;
        if (params.dustSpeed < 0.0f) return false;
        if (params.dustFadeSpeed < 0.0f) return false;
        if (params.sparkParticleCount < 0) return false;
        if (params.sparkLifetime <= 0.0f) return false;
        if (params.sparkSize <= 0.0f) return false;
        if (params.sparkSpeed < 0.0f) return false;
        if (params.sparkFadeSpeed < 0.0f) return false;
        if (params.fragmentationCount < 0) return false;
        if (params.fragmentSizeFactor < 0.0f) return false;
        if (params.fragmentSpread < 0.0f) return false;
        if (params.fragmentVelocity < 0.0f) return false;
        if (params.fragmentLifetime <= 0.0f) return false;
        if (params.shaderIntensity < 0.0f) return false;
        if (params.distortionStrength < 0.0f) return false;
        if (params.blurStrength < 0.0f) return false;
        if (params.heatDistortionStrength < 0.0f) return false;
        if (params.collisionRadius <= 0.0f) return false;
        if (params.airResistanceFactor < 0.0f) return false;
        if (params.lodLevel < 0) return false;
        
        return true;
    }

    std::vector<std::string> getValidationErrors(const CometProjectileParams& params) {
        std::vector<std::string> errors;
        
        if (params.id.empty()) {
            errors.push_back("ID cannot be empty");
        }
        if (params.coreRadius <= 0.0f) {
            errors.push_back("Core radius must be greater than 0");
        }
        if (params.irregularity < 0.0f || params.irregularity > 1.0f) {
            errors.push_back("Irregularity must be between 0 and 1");
        }
        if (params.speed <= 0.0f) {
            errors.push_back("Speed must be greater than 0");
        }
        if (params.gravityInfluence < 0.0f) {
            errors.push_back("Gravity influence cannot be negative");
        }
        if (params.mass <= 0.0f) {
            errors.push_back("Mass must be greater than 0");
        }
        if (params.drag < 0.0f) {
            errors.push_back("Drag cannot be negative");
        }
        if (params.lift < 0.0f) {
            errors.push_back("Lift cannot be negative");
        }
        if (params.glowIntensity < 0.0f) {
            errors.push_back("Glow intensity cannot be negative");
        }
        if (params.emissivePower < 0.0f) {
            errors.push_back("Emissive power cannot be negative");
        }
        if (params.coreOpacity < 0.0f || params.coreOpacity > 1.0f) {
            errors.push_back("Core opacity must be between 0 and 1");
        }
        if (params.trailOpacity < 0.0f || params.trailOpacity > 1.0f) {
            errors.push_back("Trail opacity must be between 0 and 1");
        }
        if (params.trailLength < 0.0f) {
            errors.push_back("Trail length cannot be negative");
        }
        if (params.trailWidth <= 0.0f) {
            errors.push_back("Trail width must be greater than 0");
        }
        if (params.trailNoiseScale <= 0.0f) {
            errors.push_back("Trail noise scale must be greater than 0");
        }
        if (params.trailNoiseSpeed < 0.0f) {
            errors.push_back("Trail noise speed cannot be negative");
        }
        if (params.trailFadeSpeed < 0.0f) {
            errors.push_back("Trail fade speed cannot be negative");
        }
        if (params.trailDistortionStrength < 0.0f) {
            errors.push_back("Trail distortion strength cannot be negative");
        }
        if (params.dustParticleCount < 0) {
            errors.push_back("Dust particle count cannot be negative");
        }
        if (params.dustLifetime <= 0.0f) {
            errors.push_back("Dust lifetime must be greater than 0");
        }
        if (params.dustSize <= 0.0f) {
            errors.push_back("Dust size must be greater than 0");
        }
        if (params.dustSpeed < 0.0f) {
            errors.push_back("Dust speed cannot be negative");
        }
        if (params.dustFadeSpeed < 0.0f) {
            errors.push_back("Dust fade speed cannot be negative");
        }
        if (params.sparkParticleCount < 0) {
            errors.push_back("Spark particle count cannot be negative");
        }
        if (params.sparkLifetime <= 0.0f) {
            errors.push_back("Spark lifetime must be greater than 0");
        }
        if (params.sparkSize <= 0.0f) {
            errors.push_back("Spark size must be greater than 0");
        }
        if (params.sparkSpeed < 0.0f) {
            errors.push_back("Spark speed cannot be negative");
        }
        if (params.sparkFadeSpeed < 0.0f) {
            errors.push_back("Spark fade speed cannot be negative");
        }
        if (params.fragmentationCount < 0) {
            errors.push_back("Fragmentation count cannot be negative");
        }
        if (params.fragmentSizeFactor < 0.0f) {
            errors.push_back("Fragment size factor cannot be negative");
        }
        if (params.fragmentSpread < 0.0f) {
            errors.push_back("Fragment spread cannot be negative");
        }
        if (params.fragmentVelocity < 0.0f) {
            errors.push_back("Fragment velocity cannot be negative");
        }
        if (params.fragmentLifetime <= 0.0f) {
            errors.push_back("Fragment lifetime must be greater than 0");
        }
        if (params.shaderIntensity < 0.0f) {
            errors.push_back("Shader intensity cannot be negative");
        }
        if (params.distortionStrength < 0.0f) {
            errors.push_back("Distortion strength cannot be negative");
        }
        if (params.blurStrength < 0.0f) {
            errors.push_back("Blur strength cannot be negative");
        }
        if (params.heatDistortionStrength < 0.0f) {
            errors.push_back("Heat distortion strength cannot be negative");
        }
        if (params.collisionRadius <= 0.0f) {
            errors.push_back("Collision radius must be greater than 0");
        }
        if (params.airResistanceFactor < 0.0f) {
            errors.push_back("Air resistance factor cannot be negative");
        }
        if (params.lodLevel < 0) {
            errors.push_back("LOD level cannot be negative");
        }
        
        return errors;
    }

    // Cache management
    void clearCache() {
        m_cache.clear();
    }

    size_t getCacheSize() const {
        return m_cache.size();
    }

    size_t getCacheCapacity() const {
        return m_cache.capacity();
    }

    double getCacheHitRate() const {
        return m_cache.getHitRate();
    }

    void setCacheCapacity(size_t capacity) {
        m_cache.set_capacity(capacity);
    }

    // Performance monitoring
    struct PerformanceMetrics {
        size_t totalGenerations = 0;
        size_t cacheHits = 0;
        size_t cacheMisses = 0;
        double totalGenerationTime = 0.0;
        double averageGenerationTime = 0.0;
        
        void reset() {
            totalGenerations = 0;
            cacheHits = 0;
            cacheMisses = 0;
            totalGenerationTime = 0.0;
            averageGenerationTime = 0.0;
        }
        
        double getHitRate() const {
            size_t total = cacheHits + cacheMisses;
            return total > 0 ? static_cast<double>(cacheHits) / total : 0.0;
        }
    };

    PerformanceMetrics getPerformanceMetrics() const {
        std::lock_guard<std::mutex> lock(m_metricsMutex);
        return m_performanceMetrics;
    }

    void resetPerformanceMetrics() {
        std::lock_guard<std::mutex> lock(m_metricsMutex);
        m_performanceMetrics.reset();
    }

private:
    void recordGeneration(bool cacheHit, double seconds) {
        std::lock_guard<std::mutex> lock(m_metricsMutex);
        if (cacheHit) {
            ++m_performanceMetrics.cacheHits;
            return;
        }
        ++m_performanceMetrics.cacheMisses;
        ++m_performanceMetrics.totalGenerations;
        m_performanceMetrics.totalGenerationTime += seconds;
        m_performanceMetrics.averageGenerationTime =
            m_performanceMetrics.totalGenerationTime / static_cast<double>(m_performanceMetrics.totalGenerations);
    }

    ConcurrentLRUCache<uint64_t, CometAssetBundle> m_cache;
    GeneratorTaskPool m_pool;
    bool m_initialized;
    PerformanceMetrics m_performanceMetrics;
    mutable std::mutex m_metricsMutex;
};

// Global factory instance
extern CometProjectileFactory g_cometFactory;

} // namespace CometProjectiles
} // namespace MagiTech
