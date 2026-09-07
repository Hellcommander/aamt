#include "CockpitFactory.hpp"
#include "core/Log.hpp"
#include "core/graphics/Common.hpp" // For Mesh, Image, etc.
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace MagiTech {
namespace Cockpits {

#define LOG_GEN(Asset, Id) Log::info("Building Cockpit {}: {}", #Asset, Id)

namespace MeshGen {
    MeshHandle buildSeat(const CockpitParams& p) {
        LOG_GEN(Seat Mesh, p.id);
        Graphics::Mesh seatMesh;
        // Logic to generate a sculpted cushion mesh
        return Graphics::AssetRegistry::registerMesh(seatMesh);
    }
    MeshHandle buildCanopy(const CockpitParams& p) {
        LOG_GEN(Canopy Mesh, p.id);
        Graphics::Mesh canopyMesh;
        // Logic to build a hemisphere or custom dome
        return Graphics::AssetRegistry::registerMesh(canopyMesh);
    }
    MeshHandle buildConsole(const CockpitParams& p) {
        LOG_GEN(Console Mesh, p.id);
        Graphics::Mesh consoleMesh;
        // Logic to arrange display quads and model controls
        return Graphics::AssetRegistry::registerMesh(consoleMesh);
    }
    MeshHandle buildGauges(const CockpitParams& p) {
        LOG_GEN(Gauges Mesh, p.id);
        Graphics::Mesh gaugeMesh;
        // Logic to generate circular dial meshes
        return Graphics::AssetRegistry::registerMesh(gaugeMesh);
    }
    MeshHandle buildHUD(const CockpitParams& p) {
        LOG_GEN(HUD Mesh, p.id);
        Graphics::Mesh hudMesh;
        // Logic to instantiate a transparent quad for the HUD
        return Graphics::AssetRegistry::registerMesh(hudMesh);
    }
} // namespace MeshGen

namespace ShaderGen {
    ShaderHandle buildGlassShader(const CockpitParams& p) {
        LOG_GEN(Glass Shader, p.id);
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
    ShaderHandle buildScreenShader(const CockpitParams& p) {
        LOG_GEN(Screen Shader, p.id);
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
} // namespace ShaderGen

namespace AnimGen {
    AnimationHandle buildCanopyAnimation(const CockpitParams& p) {
        LOG_GEN(Canopy Animation, p.id);
        static uint32_t nextAnimId = 1;
        return p.canopyAnimEnabled ? nextAnimId++ : 0;
    }
} // namespace AnimGen

namespace DecalGen {
    DecalHandle buildUIDecals(const CockpitParams& p) {
        LOG_GEN(UI Decals, p.id);
        static uint32_t nextDecalId = 1;
        return nextDecalId++;
    }
} // namespace DecalGen

namespace PhysGen {
    PhysicsHandle buildCollision(const CockpitParams& p) {
        LOG_GEN(Collision, p.id);
        static uint32_t nextPhysicsHandle = 1;
        return nextPhysicsHandle++;
    }
} // namespace PhysGen

} // namespace Cockpits
} // namespace MagiTech
