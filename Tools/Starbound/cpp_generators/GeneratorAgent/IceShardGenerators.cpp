#include "IceShardAssetFactory.hpp"
#include "core/Log.hpp"
#include <random>
#include <atomic>
#include <ctime>
#include <type_traits>

namespace MagiTech {
namespace IceShards {

#define LOG_ICE_GEN(Action, Id) Log::info("IceShardGen", "{}: {}", #Action, Id)

namespace {
    // Field-wise hashing (raw struct bytes would include padding and heap pointers).
    struct Hasher {
        XXH64_state_t state;
        Hasher() { XXH64_reset(&state, 0); }
        template <typename T>
        Hasher& pod(const T& v) {
            static_assert(std::is_trivially_copyable_v<T>);
            XXH64_update(&state, &v, sizeof(T));
            return *this;
        }
        Hasher& str(const std::string& v) {
            pod(static_cast<uint64_t>(v.size()));
            XXH64_update(&state, v.data(), v.size());
            return *this;
        }
        uint64_t digest() { return XXH64_digest(&state); }
    };
}

// Hash function implementations
uint64_t IceShardParams::hashKey() const {
    return Hasher().str(id).pod(coreRadius).pod(shardCount).pod(shardLength).pod(shardVariance)
                   .pod(distribution).pod(dynamicTess).pod(randomSeed).pod(lodDistance)
                   .pod(minShardCount).pod(shardTaper).pod(roughnessScale).digest();
}
uint64_t FrostTrailParams::hashKey() const {
    return Hasher().pod(enableTrail).pod(trailLength).pod(width).pod(tipColor).pod(baseColor)
                   .pod(uvScrollSpeed).digest();
}
uint64_t FrostVFXParams::hashKey() const {
    Hasher h;
    h.str(shaderTemplate).pod(static_cast<uint64_t>(defines.size()));
    for (const auto& d : defines) h.str(d);
    return h.pod(noiseIntensity).pod(rimPower).pod(enableMelting).pod(meltSpeed).pod(meltTemperature)
            .pod(refractionIndex).pod(enableCaustics).pod(causticsIntensity)
            .pod(crackPropagationSpeed).pod(crackOrigin).digest();
}
uint64_t FrostParticleParams::hashKey() const {
    return Hasher().pod(enableParticles).pod(burstCount).pod(spawnRate).pod(lifeTime).pod(initialVelocity)
                   .pod(spreadAngle).pod(enableIceDust).pod(enableSparkles).pod(enableVapor).pod(gravity)
                   .pod(airResistance).pod(enableCollisions).pod(freezeThreshold).pod(sublimationRate).digest();
}
uint64_t FrostLightParams::hashKey() const {
    return Hasher().pod(enableLight).pod(color).pod(intensity).pod(flickerFreq).digest();
}
uint64_t FrostAudioParams::hashKey() const {
    return Hasher().pod(playOnCast).str(whooshFile).str(crackFile).pod(volume).digest();
}
uint64_t FrostCollisionParams::hashKey() const {
    return Hasher().pod(enableCollider).pod(radius).pod(convexHull).pod(triggerOnly).pod(enableCCD)
                   .pod(bounceElasticity).pod(maxBounces).pod(shatterOnImpact).pod(impactThreshold).digest();
}


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
            
            static std::atomic<uint32_t> nextHandle{1}; 
            handles.push_back(nextHandle++);
            
            Log::debug("IceShardGen", "Generated shard {} with length {:.2f}, taper {:.2f}, roughness {:.3f}", 
                      i, actualLength, taperAmount, roughness);
        }
        
        return handles;
    }
}
namespace FrostTrailGen {
    MeshHandle build(const FrostTrailParams& t, const IceShardParams& s) {
        if (!t.enableTrail) return 0;
        LOG_ICE_GEN(BuildingTrail, s.id);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}
namespace ShaderGen {
    ShaderHandle build(const FrostVFXParams& v) {
        LOG_ICE_GEN(BuildingShader, v.shaderTemplate);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}
namespace ParticleGen {
    ParticleHandle buildIceFrost(const FrostParticleParams& p) {
        LOG_ICE_GEN(BuildingParticles, "IceFrost");
        
        // Enhancement: Multi-layered particle system
        if (p.enableIceDust) {
            Log::debug("IceShardGen", "Enabling ice dust particles with burst count: {}", p.burstCount);
        }
        if (p.enableSparkles) {
            Log::debug("IceShardGen", "Enabling sparkle particles with gravity: {:.2f}", p.gravity);
        }
        if (p.enableVapor) {
            Log::debug("IceShardGen", "Enabling vapor trails with sublimation rate: {:.2f}", p.sublimationRate);
        }
        
        // Enhancement: Physics-based particle simulation
        if (p.enableCollisions) {
            Log::debug("IceShardGen", "Enabling particle-world collisions with air resistance: {:.2f}", p.airResistance);
        }
        
        // Enhancement: Temperature-based effects
        if (p.freezeThreshold < 0.0f) {
            Log::debug("IceShardGen", "Particles will persist below temperature: {:.1f}°C", p.freezeThreshold);
        }
        
        static std::atomic<uint32_t> nextHandle{1}; 
        return nextHandle++;
    }
}
namespace LightGen {
    LightHandle build(const FrostLightParams& l) {
        LOG_ICE_GEN(BuildingLight, l.intensity);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}
namespace AudioGen {
    AudioHandle load(const std::string& file, float vol) {
        if (file.empty()) return 0;
        LOG_ICE_GEN(LoadingAudio, file);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}
namespace CollisionGen {
    ColliderHandle build(const FrostCollisionParams& c, const IceShardParams& s) {
        LOG_ICE_GEN(BuildingCollider, s.id);
        static std::atomic<uint32_t> nextHandle{1}; return nextHandle++;
    }
}

} // namespace IceShards
} // namespace MagiTech
