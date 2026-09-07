#include "ParticleAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Particles {

#define LOG_PARTICLE_GEN(Action, Id) Log::info("ParticleGenerator - {}: {}", #Action, Id)

// Hash function implementations
uint64_t EmitterParams::hashKey() const { /* ... */ return 0; }
uint64_t BehaviorParams::hashKey() const { /* ... */ return 0; }
uint64_t ShapeParams::hashKey() const { /* ... */ return 0; }
uint64_t LifetimeParams::hashKey() const { /* ... */ return 0; }
uint64_t RenderParams::hashKey() const { /* ... */ return 0; }
uint64_t LODParams::hashKey() const { /* ... */ return 0; }

// Generator stubs
namespace EmitterGen {
    ParticleSystemHandle build(const EmitterParams& ep, const ShapeParams& sp) {
        LOG_PARTICLE_GEN(BuildingEmitter, ep.id);
        static ParticleSystemHandle h = 1; return h++;
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
        return { lp.screenSizes, lp.rateScales };
    }
}

} // namespace Particles
} // namespace MagiTech
