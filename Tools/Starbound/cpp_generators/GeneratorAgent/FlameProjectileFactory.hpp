#pragma once
#include <future>
#include <vector>
#include <string>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "FlameProjectileTypes.hpp"

namespace MagiTech {
namespace FlameProjectiles {

// Forward declarations for generator namespaces
namespace MeshGen {
    MeshHandle buildFlame(const FlameProjectileParams& p);
    MeshHandle buildCone(float length, float width, float height);
    MeshHandle buildTrailRibbon(float length, float trailLength, float width);
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes);
}

namespace ShaderGen {
    ShaderHandle buildFlame(const FlameProjectileParams& p);
    ShaderHandle buildHeatDistortion(const FlameProjectileParams& p);
}

namespace TextureGen {
    TextureHandle buildFlame(const FlameProjectileParams& p);
    TextureHandle buildNoiseTexture(float scale, NoiseType type);
    TextureHandle buildGradientTexture(const glm::vec3& startColor, const glm::vec3& endColor);
    TextureHandle mergeTextures(const TextureHandle& noise, const TextureHandle& gradient);
}

namespace ParticleGen {
    ParticleHandle buildEmbers(const FlameProjectileParams& p);
    ParticleHandle buildTrail(const FlameProjectileParams& p);
    ParticleHandle buildSmoke(const FlameProjectileParams& p);
}

class FlameProjectileFactory {
public:
    FlameProjectileFactory() : m_initialized(false) {}
    ~FlameProjectileFactory() { shutdown(); }

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
    std::future<FlameAssetBundle> generateAsync(const FlameProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            FlameAssetBundle b;
            b.mesh = MeshGen::buildFlame(p);
            b.texture = TextureGen::buildFlame(p);
            b.shader = ShaderGen::buildFlame(p);
            b.embers = ParticleGen::buildEmbers(p);
            b.trail = ParticleGen::buildTrail(p);
            b.smoke = ParticleGen::buildSmoke(p);
            b.heatDistortion = ShaderGen::buildHeatDistortion(p);
            
            // Performance metrics
            b.generationTime = 0.0f; // Would be calculated
            b.vertexCount = 0; // Would be calculated
            b.triangleCount = 0; // Would be calculated
            b.particleCount = p.emberCount;
            b.gpuAccelerated = p.enableParallelProcessing;
            
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation
    FlameAssetBundle generateSync(const FlameProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return *hit;
        }
        
        FlameAssetBundle b;
        b.mesh = MeshGen::buildFlame(p);
        b.texture = TextureGen::buildFlame(p);
        b.shader = ShaderGen::buildFlame(p);
        b.embers = ParticleGen::buildEmbers(p);
        b.trail = ParticleGen::buildTrail(p);
        b.smoke = ParticleGen::buildSmoke(p);
        b.heatDistortion = ShaderGen::buildHeatDistortion(p);
        
        // Performance metrics
        b.generationTime = 0.0f; // Would be calculated
        b.vertexCount = 0; // Would be calculated
        b.triangleCount = 0; // Would be calculated
        b.particleCount = p.emberCount;
        b.gpuAccelerated = p.enableParallelProcessing;
        
        m_cache.insert(key, b);
        return b;
    }

    // JSON-based generation
    std::future<FlameAssetBundle> generateFromJson(const std::string& jsonPath) {
        return m_pool.enqueue([=]() {
            // Load JSON and parse parameters
            FlameProjectileParams params = loadParamsFromJson(jsonPath);
            return generateSync(params);
        });
    }

    // Batch generation
    std::vector<std::future<FlameAssetBundle>> generateBatchAsync(const std::vector<FlameProjectileParams>& params) {
        std::vector<std::future<FlameAssetBundle>> futures;
        futures.reserve(params.size());
        
        for (const auto& param : params) {
            futures.push_back(generateAsync(param));
        }
        
        return futures;
    }

    // Parameter validation
    bool validateParams(const FlameProjectileParams& params) {
        if (params.id.empty()) return false;
        if (params.speed <= 0.0f) return false;
        if (params.length <= 0.0f) return false;
        if (params.width <= 0.0f) return false;
        if (params.emberCount < 0) return false;
        if (params.emberLifetime <= 0.0f) return false;
        if (params.trailLength < 0.0f) return false;
        if (params.flickerIntensity < 0.0f || params.flickerIntensity > 1.0f) return false;
        if (params.turbulenceStrength < 0.0f) return false;
        if (params.turbulenceScale <= 0.0f) return false;
        if (params.oscillationFreq < 0.0f) return false;
        if (params.oscillationAmplitude < 0.0f) return false;
        if (params.physicsMass < 0.0f) return false;
        if (params.collisionRadius < 0.0f) return false;
        if (params.lodLevel < 0) return false;
        
        return true;
    }

    std::vector<std::string> getValidationErrors(const FlameProjectileParams& params) {
        std::vector<std::string> errors;
        
        if (params.id.empty()) {
            errors.push_back("ID cannot be empty");
        }
        if (params.speed <= 0.0f) {
            errors.push_back("Speed must be greater than 0");
        }
        if (params.length <= 0.0f) {
            errors.push_back("Length must be greater than 0");
        }
        if (params.width <= 0.0f) {
            errors.push_back("Width must be greater than 0");
        }
        if (params.emberCount < 0) {
            errors.push_back("Ember count cannot be negative");
        }
        if (params.emberLifetime <= 0.0f) {
            errors.push_back("Ember lifetime must be greater than 0");
        }
        if (params.trailLength < 0.0f) {
            errors.push_back("Trail length cannot be negative");
        }
        if (params.flickerIntensity < 0.0f || params.flickerIntensity > 1.0f) {
            errors.push_back("Flicker intensity must be between 0 and 1");
        }
        if (params.turbulenceStrength < 0.0f) {
            errors.push_back("Turbulence strength cannot be negative");
        }
        if (params.turbulenceScale <= 0.0f) {
            errors.push_back("Turbulence scale must be greater than 0");
        }
        if (params.oscillationFreq < 0.0f) {
            errors.push_back("Oscillation frequency cannot be negative");
        }
        if (params.oscillationAmplitude < 0.0f) {
            errors.push_back("Oscillation amplitude cannot be negative");
        }
        if (params.physicsMass < 0.0f) {
            errors.push_back("Physics mass cannot be negative");
        }
        if (params.collisionRadius < 0.0f) {
            errors.push_back("Collision radius cannot be negative");
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
    FlameProjectileParams loadParamsFromJson(const std::string& jsonPath) {
        // Implementation would load JSON file and parse parameters
        // For now, return default parameters
        FlameProjectileParams params;
        params.id = "loaded_from_json";
        params.flameType = FlameType::FIREBALL;
        params.flameShape = FlameShape::CONE;
        params.blendMode = BlendMode::ADDITIVE;
        params.noiseType = NoiseType::CURL;
        params.trailType = TrailType::RIBBON;
        params.speed = 25.0f;
        params.length = 1.2f;
        params.width = 0.2f;
        params.flameHeight = 1.0f;
        params.flameWidthVariation = 0.5f;
        params.coreColor = {1.0f, 0.6f, 0.1f};
        params.outerColor = {0.8f, 0.1f, 0.0f};
        params.glowColor = {1.0f, 0.4f, 0.0f};
        params.emberColor = {1.0f, 0.4f, 0.1f, 0.8f};
        params.flickerIntensity = 0.7f;
        params.flickerSpeed = 3.0f;
        params.turbulenceStrength = 1.0f;
        params.turbulenceScale = 2.5f;
        params.oscillationFreq = 1.0f;
        params.oscillationAmplitude = 0.1f;
        params.trailLength = 0.8f;
        params.trailWidth = 0.1f;
        params.trailOpacity = 0.8f;
        params.enableTrailFade = true;
        params.trailFadeSpeed = 1.0f;
        params.emberCount = 60;
        params.emberLifetime = 0.5f;
        params.emberSize = 0.05f;
        params.emberSpeed = 1.0f;
        params.enableEmberFade = true;
        params.emberFadeSpeed = 1.0f;
        params.shaderType = "flame";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableBlur = false;
        params.blurStrength = 0.1f;
        params.enableHeatDistortion = false;
        params.heatDistortionStrength = 0.1f;
        params.enablePhysics = true;
        params.physicsMass = 0.1f;
        params.physicsDrag = 0.1f;
        params.physicsLift = 0.0f;
        params.enableCollision = true;
        params.collisionRadius = 0.1f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Loaded from JSON";
        params.tags = {"flame", "projectile", "json"};
        params.metadata = {{"source", "json_file"}};
        
        return params;
    }

    ConcurrentLRUCache<uint64_t, FlameAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
    mutable PerformanceMetrics m_performanceMetrics;
};

// Global factory instance
extern FlameProjectileFactory g_flameFactory;

} // namespace FlameProjectiles
} // namespace MagiTech
