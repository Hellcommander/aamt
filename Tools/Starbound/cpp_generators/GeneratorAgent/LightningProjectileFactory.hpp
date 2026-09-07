#pragma once
#include <future>
#include <vector>
#include <string>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "LightningProjectileTypes.hpp"

namespace MagiTech {
namespace LightningProjectiles {

// Forward declarations for generator namespaces
namespace MeshGen {
    MeshHandle buildLightning(const LightningProjectileParams& p);
    MeshHandle buildLightningArc(const LightningProjectileParams& p);
    MeshHandle buildLightningBranches(const LightningProjectileParams& p);
    MeshHandle buildLightningTrail(const LightningProjectileParams& p);
    std::vector<glm::vec3> generateArcPoints(float length, int segments, float noiseScale, float noiseIntensity);
    void applyJitter(std::vector<glm::vec3>& points, float amplitude, float frequency);
    MeshHandle buildPolylineRibbon(const std::vector<glm::vec3>& points, float thickness, float widthVariation);
    MeshHandle buildTrailRibbon(const std::vector<glm::vec3>& points, float trailLength, float thickness);
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes);
}

namespace ShaderGen {
    ShaderHandle buildLightning(const LightningProjectileParams& p);
    ShaderHandle buildLightningVertexShader(const LightningProjectileParams& p);
    ShaderHandle buildLightningFragmentShader(const LightningProjectileParams& p);
    std::string generateLightningShaderCode(const LightningProjectileParams& p);
}

namespace TextureGen {
    TextureHandle buildLightning(const LightningProjectileParams& p);
    TextureHandle buildLightningGradient(const glm::vec3& mainColor, const glm::vec3& glowColor);
    TextureHandle buildLightningNoise(float noiseScale, float flickerSpeed);
    TextureHandle mergeLightningTextures(const TextureHandle& gradient, const TextureHandle& noise);
}

namespace ParticleGen {
    ParticleHandle buildSparks(const LightningProjectileParams& p);
    ParticleHandle buildLightningParticles(const LightningProjectileParams& p);
    ParticleHandle buildElectricTrail(const LightningProjectileParams& p);
}

namespace AudioGen {
    AudioHandle buildCrackle(const LightningProjectileParams& p);
    AudioHandle buildLightningAudio(const LightningProjectileParams& p);
    AudioHandle buildElectricSound(const LightningProjectileParams& p);
}

class LightningProjectileFactory {
public:
    LightningProjectileFactory() : m_initialized(false) {}
    ~LightningProjectileFactory() { shutdown(); }

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
    std::future<LightningBundle> generateAsync(const LightningProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            LightningBundle b;
            b.mesh = MeshGen::buildLightning(p);
            b.texture = TextureGen::buildLightning(p);
            b.shader = ShaderGen::buildLightning(p);
            b.sparks = ParticleGen::buildSparks(p);
            b.sfx = AudioGen::buildCrackle(p);
            
            // Performance metrics
            b.generationTime = 0.0f; // Would be calculated
            b.vertexCount = 0; // Would be calculated
            b.triangleCount = 0; // Would be calculated
            b.particleCount = p.sparkCount;
            b.gpuAccelerated = p.enableParallelProcessing;
            
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation
    LightningBundle generateSync(const LightningProjectileParams& p) {
        uint64_t key = p.hashKey();
        if (auto hit = m_cache.find(key)) {
            return *hit;
        }
        
        LightningBundle b;
        b.mesh = MeshGen::buildLightning(p);
        b.texture = TextureGen::buildLightning(p);
        b.shader = ShaderGen::buildLightning(p);
        b.sparks = ParticleGen::buildSparks(p);
        b.sfx = AudioGen::buildCrackle(p);
        
        // Performance metrics
        b.generationTime = 0.0f; // Would be calculated
        b.vertexCount = 0; // Would be calculated
        b.triangleCount = 0; // Would be calculated
        b.particleCount = p.sparkCount;
        b.gpuAccelerated = p.enableParallelProcessing;
        
        m_cache.insert(key, b);
        return b;
    }

    // JSON-based generation
    std::future<LightningBundle> generateFromJson(const std::string& jsonPath) {
        return m_pool.enqueue([=]() {
            // Load JSON and parse parameters
            LightningProjectileParams params = loadParamsFromJson(jsonPath);
            return generateSync(params);
        });
    }

    // Batch generation
    std::vector<std::future<LightningBundle>> generateBatchAsync(const std::vector<LightningProjectileParams>& params) {
        std::vector<std::future<LightningBundle>> futures;
        futures.reserve(params.size());
        
        for (const auto& param : params) {
            futures.push_back(generateAsync(param));
        }
        
        return futures;
    }

    // Parameter validation
    bool validateParams(const LightningProjectileParams& params) {
        if (params.id.empty()) return false;
        if (params.length <= 0.0f) return false;
        if (params.thickness <= 0.0f) return false;
        if (params.speed <= 0.0f) return false;
        if (params.mass <= 0.0f) return false;
        if (params.charge < 0.0f) return false;
        if (params.conductivity <= 0.0f) return false;
        if (params.noiseIntensity < 0.0f || params.noiseIntensity > 1.0f) return false;
        if (params.noiseScale <= 0.0f) return false;
        if (params.flickerSpeed < 0.0f) return false;
        if (params.pulseFrequency < 0.0f) return false;
        if (params.glowIntensity < 0.0f) return false;
        if (params.emissivePower < 0.0f) return false;
        if (params.coreOpacity < 0.0f || params.coreOpacity > 1.0f) return false;
        if (params.trailOpacity < 0.0f || params.trailOpacity > 1.0f) return false;
        if (params.branchCount < 0) return false;
        if (params.branchLengthFactor < 0.0f) return false;
        if (params.branchSpread < 0.0f) return false;
        if (params.branchAngle < 0.0f || params.branchAngle > 3.14159f) return false;
        if (params.jitterAmplitude < 0.0f) return false;
        if (params.jitterFrequency < 0.0f) return false;
        if (params.arcWidthVariation < 0.0f) return false;
        if (params.arcSegments <= 0.0f) return false;
        if (params.arcSmoothness < 0.0f || params.arcSmoothness > 1.0f) return false;
        if (params.arcStiffness < 0.0f) return false;
        if (params.trailLength < 0.0f) return false;
        if (params.trailWidth <= 0.0f) return false;
        if (params.trailFadeSpeed < 0.0f) return false;
        if (params.trailDistortionStrength < 0.0f) return false;
        if (params.sparkCount < 0) return false;
        if (params.sparkLifetime <= 0.0f) return false;
        if (params.sparkSize <= 0.0f) return false;
        if (params.sparkSpeed < 0.0f) return false;
        if (params.sparkFadeSpeed < 0.0f) return false;
        if (params.sparkGravity < 0.0f) return false;
        if (params.soundPitch <= 0.0f) return false;
        if (params.soundVolume < 0.0f || params.soundVolume > 1.0f) return false;
        if (params.soundDuration <= 0.0f) return false;
        if (params.audioDistance <= 0.0f) return false;
        if (params.shaderIntensity < 0.0f) return false;
        if (params.distortionStrength < 0.0f) return false;
        if (params.blurStrength < 0.0f) return false;
        if (params.heatDistortionStrength < 0.0f) return false;
        if (params.collisionRadius <= 0.0f) return false;
        if (params.airResistanceFactor < 0.0f) return false;
        if (params.lodLevel < 0) return false;
        
        return true;
    }

    std::vector<std::string> getValidationErrors(const LightningProjectileParams& params) {
        std::vector<std::string> errors;
        
        if (params.id.empty()) {
            errors.push_back("ID cannot be empty");
        }
        if (params.length <= 0.0f) {
            errors.push_back("Length must be greater than 0");
        }
        if (params.thickness <= 0.0f) {
            errors.push_back("Thickness must be greater than 0");
        }
        if (params.speed <= 0.0f) {
            errors.push_back("Speed must be greater than 0");
        }
        if (params.mass <= 0.0f) {
            errors.push_back("Mass must be greater than 0");
        }
        if (params.charge < 0.0f) {
            errors.push_back("Charge cannot be negative");
        }
        if (params.conductivity <= 0.0f) {
            errors.push_back("Conductivity must be greater than 0");
        }
        if (params.noiseIntensity < 0.0f || params.noiseIntensity > 1.0f) {
            errors.push_back("Noise intensity must be between 0 and 1");
        }
        if (params.noiseScale <= 0.0f) {
            errors.push_back("Noise scale must be greater than 0");
        }
        if (params.flickerSpeed < 0.0f) {
            errors.push_back("Flicker speed cannot be negative");
        }
        if (params.pulseFrequency < 0.0f) {
            errors.push_back("Pulse frequency cannot be negative");
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
        if (params.branchCount < 0) {
            errors.push_back("Branch count cannot be negative");
        }
        if (params.branchLengthFactor < 0.0f) {
            errors.push_back("Branch length factor cannot be negative");
        }
        if (params.branchSpread < 0.0f) {
            errors.push_back("Branch spread cannot be negative");
        }
        if (params.branchAngle < 0.0f || params.branchAngle > 3.14159f) {
            errors.push_back("Branch angle must be between 0 and π");
        }
        if (params.jitterAmplitude < 0.0f) {
            errors.push_back("Jitter amplitude cannot be negative");
        }
        if (params.jitterFrequency < 0.0f) {
            errors.push_back("Jitter frequency cannot be negative");
        }
        if (params.arcWidthVariation < 0.0f) {
            errors.push_back("Arc width variation cannot be negative");
        }
        if (params.arcSegments <= 0.0f) {
            errors.push_back("Arc segments must be greater than 0");
        }
        if (params.arcSmoothness < 0.0f || params.arcSmoothness > 1.0f) {
            errors.push_back("Arc smoothness must be between 0 and 1");
        }
        if (params.arcStiffness < 0.0f) {
            errors.push_back("Arc stiffness cannot be negative");
        }
        if (params.trailLength < 0.0f) {
            errors.push_back("Trail length cannot be negative");
        }
        if (params.trailWidth <= 0.0f) {
            errors.push_back("Trail width must be greater than 0");
        }
        if (params.trailFadeSpeed < 0.0f) {
            errors.push_back("Trail fade speed cannot be negative");
        }
        if (params.trailDistortionStrength < 0.0f) {
            errors.push_back("Trail distortion strength cannot be negative");
        }
        if (params.sparkCount < 0) {
            errors.push_back("Spark count cannot be negative");
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
        if (params.sparkGravity < 0.0f) {
            errors.push_back("Spark gravity cannot be negative");
        }
        if (params.soundPitch <= 0.0f) {
            errors.push_back("Sound pitch must be greater than 0");
        }
        if (params.soundVolume < 0.0f || params.soundVolume > 1.0f) {
            errors.push_back("Sound volume must be between 0 and 1");
        }
        if (params.soundDuration <= 0.0f) {
            errors.push_back("Sound duration must be greater than 0");
        }
        if (params.audioDistance <= 0.0f) {
            errors.push_back("Audio distance must be greater than 0");
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
    LightningProjectileParams loadParamsFromJson(const std::string& jsonPath) {
        // Implementation would load JSON file and parse parameters
        // For now, return default parameters
        LightningProjectileParams params;
        params.id = "loaded_from_json";
        params.lightningType = LightningType::BOLT;
        params.trailType = TrailType::ELECTRIC_TAIL;
        params.noiseType = NoiseType::PERLIN;
        params.blendMode = BlendMode::ADDITIVE;
        params.audioType = AudioType::CRACKLE;
        params.length = 8.0f;
        params.thickness = 0.05f;
        params.speed = 30.0f;
        params.mass = 1.0f;
        params.charge = 1.0f;
        params.conductivity = 1.0f;
        params.mainColor = {0.8f, 1.0f, 1.0f};
        params.glowColor = {0.2f, 0.6f, 1.0f};
        params.coreColor = {1.0f, 1.0f, 1.0f};
        params.sparkColor = {1.0f, 0.8f, 0.5f};
        params.trailColor = {0.5f, 0.8f, 1.0f, 0.6f};
        params.noiseIntensity = 0.5f;
        params.noiseScale = 4.0f;
        params.flickerSpeed = 25.0f;
        params.pulseFrequency = 2.0f;
        params.glowIntensity = 1.0f;
        params.emissivePower = 1.0f;
        params.coreOpacity = 1.0f;
        params.trailOpacity = 0.8f;
        params.enableCoreGlow = true;
        params.enableTrailGlow = true;
        params.branchCount = 3;
        params.branchLengthFactor = 0.5f;
        params.branchSpread = 1.0f;
        params.branchAngle = 0.5f;
        params.enableBranching = true;
        params.enableBranchPhysics = true;
        params.jitterAmplitude = 0.1f;
        params.jitterFrequency = 30.0f;
        params.jitterPhase = 0.0f;
        params.enableJitter = true;
        params.enableRandomJitter = true;
        params.arcWidthVariation = 0.3f;
        params.arcSegments = 16.0f;
        params.arcSmoothness = 0.5f;
        params.enableArcPhysics = true;
        params.arcStiffness = 1.0f;
        params.trailLength = 0.5f;
        params.trailWidth = 0.1f;
        params.trailFadeSpeed = 1.0f;
        params.enableTrailFade = true;
        params.enableTrailDistortion = true;
        params.trailDistortionStrength = 0.1f;
        params.sparkCount = 60;
        params.sparkLifetime = 0.3f;
        params.sparkSize = 0.02f;
        params.sparkSpeed = 1.0f;
        params.enableSparkFade = true;
        params.sparkFadeSpeed = 1.0f;
        params.enableSparkPhysics = true;
        params.sparkGravity = 0.5f;
        params.soundPitch = 1.0f;
        params.soundVolume = 1.0f;
        params.soundDuration = 1.0f;
        params.enableAudio = true;
        params.enableSpatialAudio = true;
        params.audioDistance = 10.0f;
        params.shaderType = "lightning";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableBlur = false;
        params.blurStrength = 0.1f;
        params.enableHeatDistortion = false;
        params.heatDistortionStrength = 0.1f;
        params.enablePhysics = true;
        params.enableCollision = true;
        params.collisionRadius = 0.1f;
        params.enableGravity = false;
        params.enableAirResistance = true;
        params.airResistanceFactor = 0.1f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Loaded from JSON";
        params.tags = {"lightning", "projectile", "json"};
        params.metadata = {{"source", "json_file"}};
        
        return params;
    }

    ConcurrentLRUCache<uint64_t, LightningBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
    mutable PerformanceMetrics m_performanceMetrics;
};

// Global factory instance
extern LightningProjectileFactory g_lightningFactory;

} // namespace LightningProjectiles
} // namespace MagiTech
