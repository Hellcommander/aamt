#pragma once
#include <future>
#include <vector>
#include <string>
#include "core/ConcurrentLRU.hpp"
#include "core/threading/ThreadPool.hpp"
#include "AlchemicalGrenadeTypes.hpp"

namespace MagiTech {
namespace AlchemicalGrenades {

// Forward declarations for generator namespaces
namespace MeshGen {
    MeshHandle buildItem(const AlchemicalGrenadeParams& g);
    MeshHandle buildProjectile(const AlchemicalGrenadeParams& g);
    MeshHandle buildGrenadeCore(const AlchemicalGrenadeParams& g);
    MeshHandle buildCasing(const AlchemicalGrenadeParams& g);
    MeshHandle buildLabel(const AlchemicalGrenadeParams& g);
    MeshHandle buildTrail(const AlchemicalGrenadeParams& g);
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes);
}

namespace ShaderGen {
    ShaderHandle buildItem(const AlchemicalGrenadeParams& g);
    ShaderHandle buildProjectile(const AlchemicalGrenadeParams& g);
    ShaderHandle buildGrenadeShader(const AlchemicalGrenadeParams& g);
    ShaderHandle buildCasingShader(const AlchemicalGrenadeParams& g);
    ShaderHandle buildLiquidShader(const AlchemicalGrenadeParams& g);
    std::string generateGrenadeShaderCode(const AlchemicalGrenadeParams& g);
}

namespace TextureGen {
    TextureHandle buildItem(const AlchemicalGrenadeParams& g);
    TextureHandle buildGrenadeTexture(const AlchemicalGrenadeParams& g);
    TextureHandle buildCasingTexture(const AlchemicalGrenadeParams& g);
    TextureHandle buildLiquidTexture(const AlchemicalGrenadeParams& g);
    TextureHandle buildNoiseTexture(const AlchemicalGrenadeParams& g);
    TextureHandle mergeGrenadeTextures(const TextureHandle& casing, const TextureHandle& liquid);
}

namespace ParticleGen {
    ParticleHandle buildExplosion(const AlchemicalGrenadeParams& g);
    ParticleHandle buildResidue(const AlchemicalGrenadeParams& g);
    ParticleHandle buildShrapnel(const AlchemicalGrenadeParams& g);
    ParticleHandle buildTrail(const AlchemicalGrenadeParams& g);
    ParticleHandle buildBurstEffect(const AlchemicalGrenadeParams& g);
}

namespace AudioGen {
    AudioHandle buildExplosion(const AlchemicalGrenadeParams& g);
    AudioHandle buildGrenadeAudio(const AlchemicalGrenadeParams& g);
    AudioHandle buildCasingSound(const AlchemicalGrenadeParams& g);
}

namespace IconGen {
    IconHandle buildItemIcon(const AlchemicalGrenadeParams& g, const UIItemParams& u);
    IconHandle buildGrenadeIcon(const AlchemicalGrenadeParams& g);
    IconHandle buildBackgroundShape(const UIItemParams& u);
    IconHandle buildElementalOverlay(const AlchemicalGrenadeParams& g);
}

namespace PhysGen {
    PhysicsHandle buildShrapnel(const AlchemicalGrenadeParams& g);
    PhysicsHandle buildGrenadePhysics(const AlchemicalGrenadeParams& g);
    PhysicsHandle buildExplosionPhysics(const AlchemicalGrenadeParams& g);
}

class AlchemicalGrenadeFactory {
public:
    AlchemicalGrenadeFactory() : m_initialized(false) {}
    ~AlchemicalGrenadeFactory() { shutdown(); }

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
    std::future<GrenadeAssetBundle> generateAsync(const AlchemicalGrenadeParams& g, const UIItemParams& u) {
        uint64_t key = hashCombine(g.hashKey(), u.hashKey());
        if (auto hit = m_cache.find(key)) {
            return std::async(std::launch::deferred, [=] { return *hit; });
        }
        return m_pool.enqueue([=]() {
            GrenadeAssetBundle b;
            b.meshItem = MeshGen::buildItem(g);
            b.textureItem = TextureGen::buildItem(g);
            b.shaderItem = ShaderGen::buildItem(g);
            b.meshProj = MeshGen::buildProjectile(g);
            b.shaderProj = ShaderGen::buildProjectile(g);
            b.explosionFX = ParticleGen::buildExplosion(g);
            b.residueFX = ParticleGen::buildResidue(g);
            b.sfx = AudioGen::buildExplosion(g);
            b.icon = IconGen::buildItemIcon(g, u);
            
            // Performance metrics
            b.generationTime = 0.0f; // Would be calculated
            b.vertexCount = 0; // Would be calculated
            b.triangleCount = 0; // Would be calculated
            b.particleCount = g.particleBurstCount;
            b.gpuAccelerated = g.enableParallelProcessing;
            
            m_cache.insert(key, b);
            return b;
        });
    }

    // Synchronous generation
    GrenadeAssetBundle generateSync(const AlchemicalGrenadeParams& g, const UIItemParams& u) {
        uint64_t key = hashCombine(g.hashKey(), u.hashKey());
        if (auto hit = m_cache.find(key)) {
            return *hit;
        }
        
        GrenadeAssetBundle b;
        b.meshItem = MeshGen::buildItem(g);
        b.textureItem = TextureGen::buildItem(g);
        b.shaderItem = ShaderGen::buildItem(g);
        b.meshProj = MeshGen::buildProjectile(g);
        b.shaderProj = ShaderGen::buildProjectile(g);
        b.explosionFX = ParticleGen::buildExplosion(g);
        b.residueFX = ParticleGen::buildResidue(g);
        b.sfx = AudioGen::buildExplosion(g);
        b.icon = IconGen::buildItemIcon(g, u);
        
        // Performance metrics
        b.generationTime = 0.0f; // Would be calculated
        b.vertexCount = 0; // Would be calculated
        b.triangleCount = 0; // Would be calculated
        b.particleCount = g.particleBurstCount;
        b.gpuAccelerated = g.enableParallelProcessing;
        
        m_cache.insert(key, b);
        return b;
    }

    // JSON-based generation
    std::future<GrenadeAssetBundle> generateFromJson(const std::string& jsonPath) {
        return m_pool.enqueue([=]() {
            // Load JSON and parse parameters
            auto params = loadParamsFromJson(jsonPath);
            return generateSync(params.first, params.second);
        });
    }

    // Batch generation
    std::vector<std::future<GrenadeAssetBundle>> generateBatchAsync(
        const std::vector<std::pair<AlchemicalGrenadeParams, UIItemParams>>& params) {
        std::vector<std::future<GrenadeAssetBundle>> futures;
        futures.reserve(params.size());
        
        for (const auto& param : params) {
            futures.push_back(generateAsync(param.first, param.second));
        }
        
        return futures;
    }

    // Parameter validation
    bool validateGrenadeParams(const AlchemicalGrenadeParams& params) {
        if (params.id.empty()) return false;
        if (params.fuseTime <= 0.0f) return false;
        if (params.coreRadius <= 0.0f) return false;
        if (params.casingThickness <= 0.0f) return false;
        if (params.mass <= 0.0f) return false;
        if (params.density <= 0.0f) return false;
        if (params.bounciness < 0.0f || params.bounciness > 1.0f) return false;
        if (params.friction < 0.0f || params.friction > 1.0f) return false;
        if (params.airResistance < 0.0f) return false;
        if (params.noiseScale <= 0.0f) return false;
        if (params.noiseSpeed < 0.0f) return false;
        if (params.noiseIntensity < 0.0f || params.noiseIntensity > 1.0f) return false;
        if (params.glowIntensity < 0.0f) return false;
        if (params.emissivePower < 0.0f) return false;
        if (params.transparency < 0.0f || params.transparency > 1.0f) return false;
        if (params.refractionIndex <= 0.0f) return false;
        if (params.metallicness < 0.0f || params.metallicness > 1.0f) return false;
        if (params.roughness < 0.0f || params.roughness > 1.0f) return false;
        if (params.explosionRadius <= 0.0f) return false;
        if (params.explosionIntensity <= 0.0f) return false;
        if (params.explosionForce <= 0.0f) return false;
        if (params.explosionDamage < 0.0f) return false;
        if (params.shockwaveRadius <= 0.0f) return false;
        if (params.shockwaveForce <= 0.0f) return false;
        if (params.shrapnelCount < 0) return false;
        if (params.shardSpeed <= 0.0f) return false;
        if (params.shardSize <= 0.0f) return false;
        if (params.shardMass <= 0.0f) return false;
        if (params.particleBurstCount < 0) return false;
        if (params.particleSpeed < 0.0f) return false;
        if (params.particleSize <= 0.0f) return false;
        if (params.particleSpread < 0.0f) return false;
        if (params.particleGravity < 0.0f) return false;
        if (params.residueSpread < 0.0f) return false;
        if (params.residueIntensity < 0.0f) return false;
        if (params.residueOpacity < 0.0f || params.residueOpacity > 1.0f) return false;
        if (params.residueDamageRate < 0.0f) return false;
        if (params.soundVolume < 0.0f || params.soundVolume > 1.0f) return false;
        if (params.soundPitch <= 0.0f) return false;
        if (params.soundDuration <= 0.0f) return false;
        if (params.audioDistance <= 0.0f) return false;
        if (params.echoDelay < 0.0f) return false;
        if (params.echoDecay < 0.0f || params.echoDecay > 1.0f) return false;
        if (params.shaderIntensity < 0.0f) return false;
        if (params.distortionStrength < 0.0f) return false;
        if (params.refractionStrength < 0.0f) return false;
        if (params.reflectionStrength < 0.0f) return false;
        if (params.emissionStrength < 0.0f) return false;
        if (params.collisionRadius <= 0.0f) return false;
        if (params.airResistanceFactor < 0.0f) return false;
        if (params.bounceFactor < 0.0f || params.bounceFactor > 1.0f) return false;
        if (params.lodLevel < 0) return false;
        
        return true;
    }

    bool validateUIParams(const UIItemParams& params) {
        if (params.iconSize <= 0) return false;
        if (params.borderThickness < 0.0f) return false;
        if (params.cornerRadius < 0.0f) return false;
        if (params.glowIntensity < 0.0f) return false;
        if (params.pulseFrequency < 0.0f) return false;
        if (params.pulseAmplitude < 0.0f || params.pulseAmplitude > 1.0f) return false;
        if (params.hoverScale <= 0.0f) return false;
        if (params.hoverDuration < 0.0f) return false;
        if (params.clickScale <= 0.0f) return false;
        if (params.clickDuration < 0.0f) return false;
        if (params.labelSize <= 0.0f) return false;
        if (params.lodLevel < 0) return false;
        
        return true;
    }

    std::vector<std::string> getGrenadeValidationErrors(const AlchemicalGrenadeParams& params) {
        std::vector<std::string> errors;
        
        if (params.id.empty()) {
            errors.push_back("ID cannot be empty");
        }
        if (params.fuseTime <= 0.0f) {
            errors.push_back("Fuse time must be greater than 0");
        }
        if (params.coreRadius <= 0.0f) {
            errors.push_back("Core radius must be greater than 0");
        }
        if (params.casingThickness <= 0.0f) {
            errors.push_back("Casing thickness must be greater than 0");
        }
        if (params.mass <= 0.0f) {
            errors.push_back("Mass must be greater than 0");
        }
        if (params.density <= 0.0f) {
            errors.push_back("Density must be greater than 0");
        }
        if (params.bounciness < 0.0f || params.bounciness > 1.0f) {
            errors.push_back("Bounciness must be between 0 and 1");
        }
        if (params.friction < 0.0f || params.friction > 1.0f) {
            errors.push_back("Friction must be between 0 and 1");
        }
        if (params.airResistance < 0.0f) {
            errors.push_back("Air resistance cannot be negative");
        }
        if (params.noiseScale <= 0.0f) {
            errors.push_back("Noise scale must be greater than 0");
        }
        if (params.noiseSpeed < 0.0f) {
            errors.push_back("Noise speed cannot be negative");
        }
        if (params.noiseIntensity < 0.0f || params.noiseIntensity > 1.0f) {
            errors.push_back("Noise intensity must be between 0 and 1");
        }
        if (params.glowIntensity < 0.0f) {
            errors.push_back("Glow intensity cannot be negative");
        }
        if (params.emissivePower < 0.0f) {
            errors.push_back("Emissive power cannot be negative");
        }
        if (params.transparency < 0.0f || params.transparency > 1.0f) {
            errors.push_back("Transparency must be between 0 and 1");
        }
        if (params.refractionIndex <= 0.0f) {
            errors.push_back("Refraction index must be greater than 0");
        }
        if (params.metallicness < 0.0f || params.metallicness > 1.0f) {
            errors.push_back("Metallicness must be between 0 and 1");
        }
        if (params.roughness < 0.0f || params.roughness > 1.0f) {
            errors.push_back("Roughness must be between 0 and 1");
        }
        if (params.explosionRadius <= 0.0f) {
            errors.push_back("Explosion radius must be greater than 0");
        }
        if (params.explosionIntensity <= 0.0f) {
            errors.push_back("Explosion intensity must be greater than 0");
        }
        if (params.explosionForce <= 0.0f) {
            errors.push_back("Explosion force must be greater than 0");
        }
        if (params.explosionDamage < 0.0f) {
            errors.push_back("Explosion damage cannot be negative");
        }
        if (params.shockwaveRadius <= 0.0f) {
            errors.push_back("Shockwave radius must be greater than 0");
        }
        if (params.shockwaveForce <= 0.0f) {
            errors.push_back("Shockwave force must be greater than 0");
        }
        if (params.shrapnelCount < 0) {
            errors.push_back("Shrapnel count cannot be negative");
        }
        if (params.shardSpeed <= 0.0f) {
            errors.push_back("Shard speed must be greater than 0");
        }
        if (params.shardSize <= 0.0f) {
            errors.push_back("Shard size must be greater than 0");
        }
        if (params.shardMass <= 0.0f) {
            errors.push_back("Shard mass must be greater than 0");
        }
        if (params.particleBurstCount < 0) {
            errors.push_back("Particle burst count cannot be negative");
        }
        if (params.particleSpeed < 0.0f) {
            errors.push_back("Particle speed cannot be negative");
        }
        if (params.particleSize <= 0.0f) {
            errors.push_back("Particle size must be greater than 0");
        }
        if (params.particleSpread < 0.0f) {
            errors.push_back("Particle spread cannot be negative");
        }
        if (params.particleGravity < 0.0f) {
            errors.push_back("Particle gravity cannot be negative");
        }
        if (params.residueSpread < 0.0f) {
            errors.push_back("Residue spread cannot be negative");
        }
        if (params.residueIntensity < 0.0f) {
            errors.push_back("Residue intensity cannot be negative");
        }
        if (params.residueOpacity < 0.0f || params.residueOpacity > 1.0f) {
            errors.push_back("Residue opacity must be between 0 and 1");
        }
        if (params.residueDamageRate < 0.0f) {
            errors.push_back("Residue damage rate cannot be negative");
        }
        if (params.soundVolume < 0.0f || params.soundVolume > 1.0f) {
            errors.push_back("Sound volume must be between 0 and 1");
        }
        if (params.soundPitch <= 0.0f) {
            errors.push_back("Sound pitch must be greater than 0");
        }
        if (params.soundDuration <= 0.0f) {
            errors.push_back("Sound duration must be greater than 0");
        }
        if (params.audioDistance <= 0.0f) {
            errors.push_back("Audio distance must be greater than 0");
        }
        if (params.echoDelay < 0.0f) {
            errors.push_back("Echo delay cannot be negative");
        }
        if (params.echoDecay < 0.0f || params.echoDecay > 1.0f) {
            errors.push_back("Echo decay must be between 0 and 1");
        }
        if (params.shaderIntensity < 0.0f) {
            errors.push_back("Shader intensity cannot be negative");
        }
        if (params.distortionStrength < 0.0f) {
            errors.push_back("Distortion strength cannot be negative");
        }
        if (params.refractionStrength < 0.0f) {
            errors.push_back("Refraction strength cannot be negative");
        }
        if (params.reflectionStrength < 0.0f) {
            errors.push_back("Reflection strength cannot be negative");
        }
        if (params.emissionStrength < 0.0f) {
            errors.push_back("Emission strength cannot be negative");
        }
        if (params.collisionRadius <= 0.0f) {
            errors.push_back("Collision radius must be greater than 0");
        }
        if (params.airResistanceFactor < 0.0f) {
            errors.push_back("Air resistance factor cannot be negative");
        }
        if (params.bounceFactor < 0.0f || params.bounceFactor > 1.0f) {
            errors.push_back("Bounce factor must be between 0 and 1");
        }
        if (params.lodLevel < 0) {
            errors.push_back("LOD level cannot be negative");
        }
        
        return errors;
    }

    std::vector<std::string> getUIValidationErrors(const UIItemParams& params) {
        std::vector<std::string> errors;
        
        if (params.iconSize <= 0) {
            errors.push_back("Icon size must be greater than 0");
        }
        if (params.borderThickness < 0.0f) {
            errors.push_back("Border thickness cannot be negative");
        }
        if (params.cornerRadius < 0.0f) {
            errors.push_back("Corner radius cannot be negative");
        }
        if (params.glowIntensity < 0.0f) {
            errors.push_back("Glow intensity cannot be negative");
        }
        if (params.pulseFrequency < 0.0f) {
            errors.push_back("Pulse frequency cannot be negative");
        }
        if (params.pulseAmplitude < 0.0f || params.pulseAmplitude > 1.0f) {
            errors.push_back("Pulse amplitude must be between 0 and 1");
        }
        if (params.hoverScale <= 0.0f) {
            errors.push_back("Hover scale must be greater than 0");
        }
        if (params.hoverDuration < 0.0f) {
            errors.push_back("Hover duration cannot be negative");
        }
        if (params.clickScale <= 0.0f) {
            errors.push_back("Click scale must be greater than 0");
        }
        if (params.clickDuration < 0.0f) {
            errors.push_back("Click duration cannot be negative");
        }
        if (params.labelSize <= 0.0f) {
            errors.push_back("Label size must be greater than 0");
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
    uint64_t hashCombine(uint64_t seed, uint64_t value) {
        return seed ^ (value + 0x9e3779b9 + (seed << 6) + (seed >> 2));
    }

    std::pair<AlchemicalGrenadeParams, UIItemParams> loadParamsFromJson(const std::string& jsonPath) {
        // Implementation would load JSON file and parse parameters
        // For now, return default parameters
        AlchemicalGrenadeParams grenadeParams;
        grenadeParams.id = "loaded_from_json";
        grenadeParams.grenadeType = GrenadeType::FIRE;
        grenadeParams.casingMaterial = CasingMaterial::GLASS;
        grenadeParams.particleType = ParticleType::EMBER;
        grenadeParams.explosionType = ExplosionType::BURST;
        grenadeParams.residueType = ResidueType::NONE;
        grenadeParams.soundEffect = SoundEffect::GRENADE_EXPLODE;
        grenadeParams.fuseTime = 2.0f;
        grenadeParams.detonationDelay = 0.0f;
        grenadeParams.residueDuration = 5.0f;
        grenadeParams.particleLifetime = 0.5f;
        grenadeParams.shardLifetime = 0.6f;
        grenadeParams.coreRadius = 0.15f;
        grenadeParams.casingThickness = 0.02f;
        grenadeParams.mass = 1.0f;
        grenadeParams.density = 1.0f;
        grenadeParams.bounciness = 0.3f;
        grenadeParams.friction = 0.5f;
        grenadeParams.airResistance = 0.1f;
        grenadeParams.casingColorPrimary = {0.8f, 0.2f, 0.0f};
        grenadeParams.casingColorSecondary = {1.0f, 0.6f, 0.4f};
        grenadeParams.liquidColor = {1.0f, 0.3f, 0.0f, 0.8f};
        grenadeParams.glowColor = {1.0f, 0.8f, 0.5f};
        grenadeParams.explosionColor = {1.0f, 0.5f, 0.0f};
        grenadeParams.residueColor = {0.5f, 0.5f, 0.5f, 0.6f};
        grenadeParams.noiseScale = 3.0f;
        grenadeParams.noiseSpeed = 1.0f;
        grenadeParams.noiseIntensity = 0.5f;
        grenadeParams.glowIntensity = 1.0f;
        grenadeParams.emissivePower = 1.0f;
        grenadeParams.transparency = 0.8f;
        grenadeParams.refractionIndex = 1.5f;
        grenadeParams.metallicness = 0.0f;
        grenadeParams.roughness = 0.5f;
        grenadeParams.explosionRadius = 3.0f;
        grenadeParams.explosionIntensity = 1.2f;
        grenadeParams.explosionForce = 10.0f;
        grenadeParams.explosionDamage = 50.0f;
        grenadeParams.enableShockwave = true;
        grenadeParams.shockwaveRadius = 5.0f;
        grenadeParams.shockwaveForce = 5.0f;
        grenadeParams.shrapnelCount = 8;
        grenadeParams.shardSpeed = 12.0f;
        grenadeParams.shardSize = 0.01f;
        grenadeParams.shardMass = 0.02f;
        grenadeParams.enableShrapnelPhysics = true;
        grenadeParams.enableShrapnelDamage = true;
        grenadeParams.particleBurstCount = 60;
        grenadeParams.particleSpeed = 5.0f;
        grenadeParams.particleSize = 0.02f;
        grenadeParams.particleSpread = 1.0f;
        grenadeParams.enableParticlePhysics = true;
        grenadeParams.enableParticleTrails = true;
        grenadeParams.particleGravity = 0.5f;
        grenadeParams.residueSpread = 2.0f;
        grenadeParams.residueIntensity = 1.0f;
        grenadeParams.residueOpacity = 0.6f;
        grenadeParams.enableResiduePhysics = true;
        grenadeParams.enableResidueDamage = false;
        grenadeParams.residueDamageRate = 5.0f;
        grenadeParams.soundVolume = 1.0f;
        grenadeParams.soundPitch = 1.0f;
        grenadeParams.soundDuration = 1.0f;
        grenadeParams.enableSpatialAudio = true;
        grenadeParams.audioDistance = 10.0f;
        grenadeParams.enableEcho = false;
        grenadeParams.echoDelay = 0.1f;
        grenadeParams.echoDecay = 0.5f;
        grenadeParams.shaderType = "grenade";
        grenadeParams.shaderIntensity = 1.0f;
        grenadeParams.enableDistortion = true;
        grenadeParams.distortionStrength = 0.1f;
        grenadeParams.enableRefraction = true;
        grenadeParams.refractionStrength = 0.1f;
        grenadeParams.enableReflection = false;
        grenadeParams.reflectionStrength = 0.1f;
        grenadeParams.enableEmission = true;
        grenadeParams.emissionStrength = 0.5f;
        grenadeParams.enablePhysics = true;
        grenadeParams.enableCollision = true;
        grenadeParams.collisionRadius = 0.15f;
        grenadeParams.enableGravity = true;
        grenadeParams.enableAirResistance = true;
        grenadeParams.airResistanceFactor = 0.1f;
        grenadeParams.enableBounce = true;
        grenadeParams.bounceFactor = 0.3f;
        grenadeParams.enableCaching = true;
        grenadeParams.enableHotReload = true;
        grenadeParams.enableParallelProcessing = true;
        grenadeParams.lodLevel = 0;
        grenadeParams.description = "Loaded from JSON";
        grenadeParams.tags = {"grenade", "alchemical", "json"};
        grenadeParams.metadata = {{"source", "json_file"}};
        
        UIItemParams uiParams;
        uiParams.iconSize = 48;
        uiParams.borderColor = {1.0f, 1.0f, 1.0f, 0.8f};
        uiParams.backgroundShape = BackgroundShape::CIRCLE;
        uiParams.flashOnSelect = true;
        uiParams.borderThickness = 2.0f;
        uiParams.cornerRadius = 4.0f;
        uiParams.enableGlow = false;
        uiParams.glowColor = {1.0f, 1.0f, 1.0f};
        uiParams.glowIntensity = 1.0f;
        uiParams.enablePulse = false;
        uiParams.pulseFrequency = 2.0f;
        uiParams.pulseAmplitude = 0.1f;
        uiParams.enableHoverEffect = true;
        uiParams.hoverScale = 1.1f;
        uiParams.hoverDuration = 0.2f;
        uiParams.enableClickEffect = true;
        uiParams.clickScale = 0.95f;
        uiParams.clickDuration = 0.1f;
        uiParams.label = "";
        uiParams.enableLabel = false;
        uiParams.labelColor = {1.0f, 1.0f, 1.0f};
        uiParams.labelSize = 12.0f;
        uiParams.labelFont = "default";
        uiParams.enableCaching = true;
        uiParams.enableHotReload = true;
        uiParams.lodLevel = 0;
        uiParams.description = "Loaded from JSON";
        uiParams.tags = {"ui", "item", "json"};
        uiParams.metadata = {{"source", "json_file"}};
        
        return {grenadeParams, uiParams};
    }

    ConcurrentLRUCache<uint64_t, GrenadeAssetBundle> m_cache;
    ThreadPool m_pool;
    bool m_initialized;
    mutable PerformanceMetrics m_performanceMetrics;
};

// Global factory instance
extern AlchemicalGrenadeFactory g_grenadeFactory;

} // namespace AlchemicalGrenades
} // namespace MagiTech
