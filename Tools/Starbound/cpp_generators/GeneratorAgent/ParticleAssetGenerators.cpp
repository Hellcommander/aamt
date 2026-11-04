#include "ParticleAssetFactory.hpp"
#include "core/Log.hpp"
#include <atomic>
#include <type_traits>

namespace MagiTech {
namespace Particles {

#define LOG_PARTICLE_GEN(Action, Id) Log::info("ParticleAsset", "ParticleGenerator - {}: {}", #Action, Id)

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
        template <typename T>
        Hasher& vec(const std::vector<T>& v) {
            pod(static_cast<uint64_t>(v.size()));
            for (const auto& e : v) pod(e);
            return *this;
        }
        Hasher& strings(const std::vector<std::string>& v) {
            pod(static_cast<uint64_t>(v.size()));
            for (const auto& s : v) str(s);
            return *this;
        }
        template <typename V>
        Hasher& map(const std::map<std::string, V>& m) {
            pod(static_cast<uint64_t>(m.size()));
            for (const auto& [key, value] : m) {
                str(key);
                if constexpr (std::is_same_v<V, std::string>) str(value); else pod(value);
            }
            return *this;
        }
        uint64_t digest() { return XXH64_digest(&state); }
    };
}

// Hash function implementations
uint64_t EmitterParams::hashKey() const {
    return Hasher().str(id).pod(position).pod(rotation).pod(scale).pod(rate).pod(duration).pod(loop)
                   .pod(burstMode).pod(burstCount).pod(burstInterval).pod(gpuDriven).map(customParameters).digest();
}

uint64_t BehaviorParams::hashKey() const {
    return Hasher().pod(initialVelocity).pod(velocityVariance).pod(acceleration).pod(gravity).pod(drag)
                   .pod(collision).pod(turbulence).pod(turbulenceStrength).pod(wind).pod(attractorMode)
                   .pod(attractorPosition).pod(attractorStrength).pod(attractorRadius).map(customParameters).digest();
}

uint64_t ShapeParams::hashKey() const {
    return Hasher().pod(type).pod(dimensions).pod(angle).pod(radius).pod(innerRadius).str(meshPath)
                   .pod(randomRotation).pod(alignToVelocity).map(customParameters).digest();
}

uint64_t LifetimeParams::hashKey() const {
    return Hasher().pod(minLife).pod(maxLife).pod(sizeRange).pod(sizeOverLife).pod(fadeIn).pod(fadeOut)
                   .pod(fadeInTime).pod(fadeOutTime).pod(colorOverLife).pod(startColor).pod(endColor)
                   .pod(velocityOverLife).pod(velocityStart).pod(velocityEnd).map(customParameters).digest();
}

uint64_t RenderParams::hashKey() const {
    Hasher h;
    h.str(texturePath).pod(animated).pod(frameCount).pod(frameRate).pod(frameSize).pod(billboard)
     .pod(alignToCamera).pod(softParticles);
    for (const auto& c : colorOverLife) h.pod(c);
    return h.pod(alphaOverLife).pod(additive).pod(multiply).pod(distortion).pod(distortionStrength)
            .pod(glow).pod(glowIntensity).str(normalMapPath).str(emissionMapPath).map(customParameters).digest();
}

uint64_t LODParams::hashKey() const {
    return Hasher().vec(screenSizes).vec(rateScales).vec(qualityScales).pod(adaptiveLOD).pod(adaptiveThreshold)
                   .map(customParameters).digest();
}

uint64_t AdvancedParticleParams::hashKey() const {
    return Hasher().pod(useGPU).pod(useInstancing).pod(useGeometryShaders).pod(maxParticles).pod(batchSize)
                   .pod(enableSorting).pod(enableCulling).pod(cullDistance).pod(enableOcclusion)
                   .pod(enableDepthPrePass).map(customParameters).digest();
}

uint64_t ParticleEffectDefinition::hashKey() const {
    // Descriptive fields (description, category, tags, metadata) do not change the generated asset
    return Hasher().str(name).pod(emitter.hashKey()).pod(behavior.hashKey()).pod(shape.hashKey())
                   .pod(lifetime.hashKey()).pod(render.hashKey()).pod(lod.hashKey()).digest();
}

uint64_t ParticleEffectTemplate::hashKey() const {
    Hasher h;
    h.str(name).str(description).strings(tags).pod(baseDefinition.hashKey());
    h.pod(static_cast<uint64_t>(subEmitters.size()));
    for (const auto& s : subEmitters) {
        h.str(s.effectName).pod(s.probability).pod(s.offset).pod(s.inheritVelocity).pod(s.inheritRotation)
         .pod(s.inheritColor).pod(s.inheritSize);
    }
    h.pod(static_cast<uint64_t>(forceFields.size()));
    for (const auto& f : forceFields) {
        // customForce is a callable and cannot be hashed; its presence is.
        h.pod(f.type).str(f.id).pod(f.position).pod(f.direction).pod(f.strength).pod(f.radius).pod(f.falloff)
         .pod(f.active).pod(static_cast<bool>(f.customForce));
    }
    h.pod(static_cast<uint64_t>(collisions.size()));
    for (const auto& c : collisions) {
        h.pod(c.type).str(c.id).pod(c.position).pod(c.dimensions).pod(c.normal).pod(c.restitution)
         .pod(c.friction).pod(c.active).str(c.meshPath);
    }
    h.pod(trail.enabled).pod(trail.maxPoints).pod(trail.fadeTime).pod(trail.width).pod(trail.color)
     .pod(trail.useTexture).str(trail.texturePath);
    return h.pod(advanced.hashKey()).map(metadata).digest();
}

// Generator stages
namespace EmitterGen {
    ParticleSystemHandle build(const EmitterParams& ep, const ShapeParams& sp) {
        LOG_PARTICLE_GEN(BuildingEmitter, ep.id);
        static std::atomic<ParticleSystemHandle> h{1};
        return h++;
    }
}
namespace BehaviorGen {
    void configure(ParticleSystemHandle ps, const BehaviorParams& bp) {
        LOG_PARTICLE_GEN(ConfiguringBehavior, ps);
    }
}
namespace LifetimeGen {
    void setup(ParticleSystemHandle ps, const LifetimeParams& lp) {
        LOG_PARTICLE_GEN(SettingLifetime, ps);
    }
}
namespace RenderGen {
    void apply(ParticleSystemHandle ps, const RenderParams& rp) {
        LOG_PARTICLE_GEN(ApplyingRender, ps);
    }
}
namespace LODGen {
    LODData compute(const LODParams& lp) {
        LOG_PARTICLE_GEN(ComputingLODs, lp.screenSizes.size());
        LODData data;
        data.screenSizes = lp.screenSizes;
        data.rateScales = lp.rateScales;
        data.qualityScales = lp.qualityScales;
        for (size_t i = 0; i < lp.screenSizes.size(); ++i) {
            const float rate = i < lp.rateScales.size() ? lp.rateScales[i] : 1.0f;
            const float quality = i < lp.qualityScales.size() ? lp.qualityScales[i] : 1.0f;
            data.maxParticles.push_back(static_cast<int>(1000.0f * rate));
            data.cullDistances.push_back(50.0f * quality);
        }
        return data;
    }
}

} // namespace Particles
} // namespace MagiTech
