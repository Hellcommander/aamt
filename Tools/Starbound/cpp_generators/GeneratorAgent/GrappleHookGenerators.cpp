#include "GrappleAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace GrappleHooks {

#define LOG_GRAPPLE_GEN(Action, Id) Log::info("GrappleHookGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t HookParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(HookParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}
uint64_t ChainParams::hashKey() const { return XXH64(this, sizeof(ChainParams), 0); }
uint64_t MaterialParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(MaterialParams) - 3 * sizeof(std::string));
    XXH64_update(&s, baseColorMap.c_str(), baseColorMap.length());
    XXH64_update(&s, normalMap.c_str(), normalMap.length());
    XXH64_update(&s, metallicRoughnessMap.c_str(), metallicRoughnessMap.length());
    return XXH64_digest(&s);
}
uint64_t PhysicsParams::hashKey() const { return XXH64(this, sizeof(PhysicsParams), 0); }
uint64_t LODParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, meshLODs.data(), meshLODs.size() * sizeof(int));
    XXH64_update(&s, displayRanges.data(), displayRanges.size() * sizeof(float));
    return XXH64_digest(&s);
}

// Generator stubs
namespace HookGen {
    MeshHandle buildHook(const HookParams& hp) {
        LOG_GRAPPLE_GEN(BuildingHook, hp.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace ChainGen {
    std::vector<MeshHandle> buildChain(const ChainParams& cp) {
        LOG_GRAPPLE_GEN(BuildingChain, cp.linkCount);
        std::vector<MeshHandle> links;
        for (int i = 0; i < cp.linkCount; ++i) {
            static uint32_t nextHandle = 100;
            links.push_back(nextHandle++);
        }
        return links;
    }
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const MaterialParams& mp) {
        LOG_GRAPPLE_GEN(BuildingMaterial, mp.baseColorMap);
        static uint32_t nextHandle = 200; return nextHandle++;
    }
}
namespace PhysicsGen {
    PhysicsAsset buildPhysics(const std::vector<MeshHandle>& links, const PhysicsParams& pp) {
        LOG_GRAPPLE_GEN(BuildingPhysics, links.size());
        static uint32_t nextHandle = 300; return nextHandle++;
    }
}
namespace LODGen {
    LODData compute(const LODParams& lp, MeshHandle hook, const std::vector<MeshHandle>& links) {
        LOG_GRAPPLE_GEN(ComputingLODs, lp.meshLODs.size());
        LODData data;
        data.thresholds = lp.displayRanges;
        return data;
    }
}
namespace ShaderGen {
    ShaderHandle buildGrappleShader(const MaterialParams& mp) {
        LOG_GRAPPLE_GEN(BuildingShader, mp.baseColorMap);
        static uint32_t nextHandle = 400; return nextHandle++;
    }
}

} // namespace GrappleHooks
} // namespace MagiTech
