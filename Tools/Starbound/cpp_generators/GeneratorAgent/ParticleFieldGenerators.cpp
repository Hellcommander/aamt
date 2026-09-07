#include "ParticleFieldAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace ParticleFields {

#define LOG_FIELD_GEN(Action, Id) Log::info("ParticleFieldGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t LODParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, screenSizes.data(), screenSizes.size() * sizeof(float));
    XXH64_update(&s, densityScales.data(), densityScales.size() * sizeof(float));
    return XXH64_digest(&s);
}

uint64_t ParticleFieldParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(ParticleFieldParams) - sizeof(std::string) - sizeof(LODParams));
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, &lod, sizeof(LODParams));
    return XXH64_digest(&s);
}

uint64_t NoiseParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(NoiseParams) - sizeof(std::string));
    XXH64_update(&s, noiseType.c_str(), noiseType.length());
    return XXH64_digest(&s);
}

uint64_t ColorRampParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(ColorRampParams) - sizeof(std::vector<std::pair<float, glm::vec4>>));
    XXH64_update(&s, stops.data(), stops.size() * sizeof(std::pair<float, glm::vec4>));
    return XXH64_digest(&s);
}

uint64_t ParticleParams::hashKey() const { return XXH64(this, sizeof(ParticleParams), 0); }

// Generator stubs
namespace NoiseGen {
    TextureHandle buildVolume(const NoiseParams& np, const glm::vec3& min, const glm::vec3& max) {
        LOG_FIELD_GEN(BuildingNoiseVolume, np.noiseType);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace ColorGen {
    TextureHandle buildRamp(const ColorRampParams& cr) {
        LOG_FIELD_GEN(BuildingColorRamp, cr.resolution);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace LODGen {
    LODData compute(const LODParams& lp) {
        LOG_FIELD_GEN(ComputingLODs, lp.screenSizes.size());
        LODData d;
        d.thresholds = lp.screenSizes;
        d.scales = lp.densityScales;
        return d;
    }
}
namespace ShaderGen {
    ShaderHandle buildFieldShader(const ParticleFieldParams& fp, const NoiseParams& np, const ColorRampParams& cr, const ParticleParams& pp) {
        LOG_FIELD_GEN(BuildingFieldShader, fp.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace FieldGen {
    ParticleSystemHandle spawnField(const ParticleFieldParams& fp, const NoiseParams& np, const ParticleParams& pp, const TextureHandle& ramp) {
        LOG_FIELD_GEN(SpawningField, fp.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}

} // namespace ParticleFields
} // namespace MagiTech
