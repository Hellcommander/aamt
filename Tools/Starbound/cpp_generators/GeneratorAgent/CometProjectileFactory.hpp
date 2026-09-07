#pragma once
#include <future>
#include <vector>
#include <string>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "CometProjectileTypes.hpp"

namespace MagiTech {
namespace CometProjectiles {

// Forward declarations for generator namespaces
namespace MeshGen {
    MeshHandle buildCometCore(const CometProjectileParams& p);
    MeshHandle buildCometTrail(const CometProjectileParams& p);
    MeshHandle generateIcoSphere(float radius, int detail);
    MeshHandle applyVertexNoise(MeshHandle mesh, float irregularity);
    MeshHandle createRibbonMesh(float length, float speed, int segmentCount);
    MeshHandle buildFragments(const CometProjectileParams& p);
}

namespace ShaderGen {
    ShaderHandle buildCometShader(const CometProjectileParams& p);
    ShaderHandle buildHeatDistortion(const CometProjectileParams& p);
    std::string generateCometShaderCode(const CometProjectileParams& p);
}

namespace TextureGen {
    TextureHandle buildCometTexture(const CometProjectileParams& p);
    TextureHandle buildRockTexture(float frequency);
    TextureHandle buildColorMap(const glm::vec3& heatColor, const glm::vec3& burnColor);
    TextureHandle mergeTextures(const TextureHandle& rock, const TextureHandle& color);
}

namespace ParticleGen {
    ParticleHandle buildDustTrail(const CometProjectileParams& p);
    ParticleHandle buildSparks(const CometProjectileParams& p);
    ParticleHandle buildFragments(const CometProjectileParams& p);
}

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
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            CometAssetBundle b;
            b.mesh = MeshGen::buildCometCore(p);
            b.texture = TextureGen::buildCometTexture(p);
            b.shader = ShaderGen::buildCometShader(p);
            b.dustTrail = ParticleGen::buildDustTrail(p);
            b.sparks = ParticleGen::buildSparks(p);
            b.fragments = ParticleGen::buildFragments(p);
            b.heatDistortion = ShaderGen::buildHeatDistortion(p);
            
            // Performance metrics
            b.generationTime = 0.0f; // Would be calculated
            b.vertexCount = 0; // Would be calculated
            b.triangleCount = 0; // Would be calculated
            b.particleCount = p.dustParticleCount + p.sparkParticleCount;
            b.gpuAccelerated = p.enableParallelProcessing;
            
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation
    CometAssetBundle generateSync(const CometProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return *hit;
        }
        
        CometAssetBundle b;
        b.mesh = MeshGen::buildCometCore(p);
        b.texture = TextureGen::buildCometTexture(p);
        b.shader = ShaderGen::buildCometShader(p);
        b.dustTrail = ParticleGen::buildDustTrail(p);
        b.sparks = ParticleGen::buildSparks(p);
        b.fragments = ParticleGen::buildFragments(p);
        b.heatDistortion = ShaderGen::buildHeatDistortion(p);
        
        // Performance metrics
        b.generationTime = 0.0f; // Would be calculated
        b.vertexCount = 0; // Would be calculated
        b.triangleCount = 0; // Would be calculated
        b.particleCount = p.dustParticleCount + p.sparkParticleCount;
        b.gpuAccelerated = p.enableParallelProcessing;
        
        m_cache.insert(key, b);
        return b;
    }

    // JSON-based generation
    std::future<CometAssetBundle> generateFromJson(const std::string& jsonPath) {
        return m_pool.enqueue([=]() {
            // Load JSON and parse parameters
            CometProjectileParams params = loadParamsFromJson(jsonPath);
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
        return m_cache.hit_rate();
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
        return m_performanceMetrics;
    }

    void resetPerformanceMetrics() {
        m_performanceMetrics.reset();
    }

private:
    CometProjectileParams loadParamsFromJson(const std::string& jsonPath) {
        // Implementation would load JSON file and parse parameters
        // For now, return default parameters
        CometProjectileParams params;
        params.id = "loaded_from_json";
        params.cometType = CometType::METEOR;
        params.cometShape = CometShape::SPHERE;
        params.trailType = TrailType::DUST;
        params.fragmentationType = FragmentationType::NONE;
        params.noiseType = NoiseType::PERLIN;
        params.blendMode = BlendMode::ADDITIVE;
        params.coreRadius = 0.5f;
        params.irregularity = 0.8f;
        params.speed = 30.0f;
        params.gravityInfluence = 1.0f;
        params.mass = 1.0f;
        params.drag = 0.1f;
        params.lift = 0.0f;
        params.heatColor = {1.0f, 0.5f, 0.1f};
        params.burnColor = {1.0f, 0.8f, 0.3f};
        params.coreColor = {0.8f, 0.6f, 0.4f};
        params.glowColor = {1.0f, 0.4f, 0.0f};
        params.dustColor = {0.5f, 0.5f, 0.5f, 0.6f};
        params.sparkColor = {1.0f, 0.4f, 0.1f, 1.0f};
        params.glowIntensity = 2.0f;
        params.emissivePower = 1.0f;
        params.coreOpacity = 1.0f;
        params.trailOpacity = 0.8f;
        params.enableCoreGlow = true;
        params.enableTrailGlow = true;
        params.trailLength = 2.0f;
        params.trailWidth = 0.1f;
        params.trailNoiseScale = 1.5f;
        params.trailNoiseSpeed = 3.0f;
        params.trailFadeSpeed = 1.0f;
        params.enableTrailFade = true;
        params.enableTrailDistortion = true;
        params.trailDistortionStrength = 0.1f;
        params.dustParticleCount = 100;
        params.dustLifetime = 1.5f;
        params.dustSize = 0.05f;
        params.dustSpeed = 1.0f;
        params.enableDustFade = true;
        params.dustFadeSpeed = 1.0f;
        params.sparkParticleCount = 30;
        params.sparkLifetime = 0.6f;
        params.sparkSize = 0.03f;
        params.sparkSpeed = 1.5f;
        params.enableSparkFade = true;
        params.sparkFadeSpeed = 1.0f;
        params.fragmentationCount = 0;
        params.fragmentSizeFactor = 0.3f;
        params.fragmentSpread = 1.0f;
        params.fragmentVelocity = 2.0f;
        params.enableFragmentPhysics = true;
        params.fragmentLifetime = 2.0f;
        params.shaderType = "comet";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableBlur = false;
        params.blurStrength = 0.1f;
        params.enableHeatDistortion = false;
        params.heatDistortionStrength = 0.1f;
        params.enablePhysics = true;
        params.enableCollision = true;
        params.collisionRadius = 0.5f;
        params.enableGravity = true;
        params.enableAirResistance = true;
        params.airResistanceFactor = 0.1f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Loaded from JSON";
        params.tags = {"comet", "projectile", "json"};
        params.metadata = {{"source", "json_file"}};
        
        return params;
    }

    ConcurrentLRUCache<uint64_t, CometAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
    mutable PerformanceMetrics m_performanceMetrics;
};

// Global factory instance
extern CometProjectileFactory g_cometFactory;

} // namespace CometProjectiles
} // namespace MagiTech
