#include "BarbedExplosiveProjectileFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

#define LOG_BARBED_GEN(Action, Id) Log::info("BarbedExplosiveProjectileGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t GeometryParams::hashKey() const { return XXH64(this, sizeof(GeometryParams), 0); }
uint64_t ExplosionParams::hashKey() const { return XXH64(this, sizeof(ExplosionParams), 0); }
uint64_t VisualParams::hashKey() const { return XXH64(this, sizeof(VisualParams), 0); }


// Generator stubs
namespace MeshGen {
    std::vector<MeshHandle> buildBarbedMesh(const GeometryParams& p) {
        LOG_BARBED_GEN(BuildingBarbedMesh, p.length);
        static uint32_t nextHandle = 1;
        return {nextHandle++, nextHandle++, nextHandle++}; // 3 LODs
    }
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const VisualParams& p) {
        LOG_BARBED_GEN(BuildingMaterial, p.baseColor.r);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace ExplosionGen {
    ExplosionHandle buildExplosion(const ExplosionParams& p) {
        LOG_BARBED_GEN(BuildingExplosion, p.radius);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
