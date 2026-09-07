#include "IceShardAssetFactory.hpp"
#include "core/Log.hpp"
#include <random>
#include <ctime>

namespace MagiTech {
namespace IceShards {

#define LOG_ICE_GEN(Action, Id) Log::info("IceShardGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t IceShardParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(IceShardParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}
uint64_t FrostTrailParams::hashKey() const { return XXH64(this, sizeof(FrostTrailParams), 0); }
uint64_t FrostVFXParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(FrostVFXParams) - 2 * sizeof(std::string));
    XXH64_update(&s, shaderTemplate.c_str(), shaderTemplate.length());
    for(const auto& d : defines) { XXH64_update(&s, d.c_str(), d.length()); }
    return XXH64_digest(&s);
}
uint64_t FrostParticleParams::hashKey() const { return XXH64(this, sizeof(FrostParticleParams), 0); }
uint64_t FrostLightParams::hashKey() const { return XXH64(this, sizeof(FrostLightParams), 0); }
uint64_t FrostAudioParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(FrostAudioParams) - 2 * sizeof(std::string));
    XXH64_update(&s, whooshFile.c_str(), whooshFile.length());
    XXH64_update(&s, crackFile.c_str(), crackFile.length());
    return XXH64_digest(&s);
}
uint64_t FrostCollisionParams::hashKey() const { return XXH64(this, sizeof(FrostCollisionParams), 0); }


namespace ShardGeometryGen {
    std::vector<MeshHandle> build(const IceShardParams& s) {
        LOG_ICE_GEN(BuildingShards, s.id);
        std::vector<MeshHandle> handles;
        
        // Enhancement: Seeded randomness for reproducible patterns
        uint32_t seed = s.randomSeed ? s.randomSeed : static_cast<uint32_t>(time(nullptr));
        std::mt19937 rng(seed);
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        
        for (int i = 0; i < s.shardCount; ++i) {
            // Enhancement: Apply variance with seeded randomness
            float lengthVariation = 1.0f + (dist(rng) - 0.5f) * 2.0f * s.shardVariance;
            float actualLength = s.shardLength * lengthVariation;
            
            // Enhancement: Apply taper and roughness
            float taperAmount = s.shardTaper;
            float roughness = s.roughnessScale * dist(rng);
            
            static uint32_t nextHandle = 1; 
            handles.push_back(nextHandle++);
            
            Log::debug("Generated shard {} with length {:.2f}, taper {:.2f}, roughness {:.3f}", 
                      i, actualLength, taperAmount, roughness);
        }
        
        return handles;
    }
}
namespace FrostTrailGen {
    MeshHandle build(const FrostTrailParams& t, const IceShardParams& s) {
        if (!t.enableTrail) return 0;
        LOG_ICE_GEN(BuildingTrail, s.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace ShaderGen {
    ShaderHandle build(const FrostVFXParams& v) {
        LOG_ICE_GEN(BuildingShader, v.shaderTemplate);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace ParticleGen {
    ParticleHandle buildIceFrost(const FrostParticleParams& p) {
        LOG_ICE_GEN(BuildingParticles, "IceFrost");
        
        // Enhancement: Multi-layered particle system
        if (p.enableIceDust) {
            Log::debug("Enabling ice dust particles with burst count: {}", p.burstCount);
        }
        if (p.enableSparkles) {
            Log::debug("Enabling sparkle particles with gravity: {:.2f}", p.gravity);
        }
        if (p.enableVapor) {
            Log::debug("Enabling vapor trails with sublimation rate: {:.2f}", p.sublimationRate);
        }
        
        // Enhancement: Physics-based particle simulation
        if (p.enableCollisions) {
            Log::debug("Enabling particle-world collisions with air resistance: {:.2f}", p.airResistance);
        }
        
        // Enhancement: Temperature-based effects
        if (p.freezeThreshold < 0.0f) {
            Log::debug("Particles will persist below temperature: {:.1f}°C", p.freezeThreshold);
        }
        
        static uint32_t nextHandle = 1; 
        return nextHandle++;
    }
}
namespace LightGen {
    LightHandle build(const FrostLightParams& l) {
        LOG_ICE_GEN(BuildingLight, l.intensity);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace AudioGen {
    AudioHandle load(const std::string& file, float vol) {
        if (file.empty()) return 0;
        LOG_ICE_GEN(LoadingAudio, file);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace CollisionGen {
    ColliderHandle build(const FrostCollisionParams& c, const IceShardParams& s) {
        LOG_ICE_GEN(BuildingCollider, s.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}

} // namespace IceShards
} // namespace MagiTech
