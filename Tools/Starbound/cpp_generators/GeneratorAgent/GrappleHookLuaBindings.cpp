#include "GrappleHookLuaBindings.hpp"
#include "GrappleAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace GrappleHooks {

static std::vector<std::pair<std::future<GrappleBundle>, std::string>> pendingGrapples;

void GrappleHookLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<HookParams>("HookParams", sol::constructors<HookParams()>(),
        "id", &HookParams::id, "tipPosition", &HookParams::tipPosition,
        "hookRadius", &HookParams::hookRadius, "hookThickness", &HookParams::hookThickness, "segmentCount", &HookParams::segmentCount);

    lua.new_usertype<ChainParams>("ChainParams", sol::constructors<ChainParams()>(),
        "linkCount", &ChainParams::linkCount, "linkLength", &ChainParams::linkLength,
        "linkThickness", &ChainParams::linkThickness, "linkScale", &ChainParams::linkScale, "twistAngle", &ChainParams::twistAngle);

    lua.new_usertype<MaterialParams>("MaterialParams", sol::constructors<MaterialParams()>(),
        "baseColorMap", &MaterialParams::baseColorMap, "normalMap", &MaterialParams::normalMap,
        "metallicRoughnessMap", &MaterialParams::metallicRoughnessMap, "colorTint", &MaterialParams::colorTint);

    lua.new_usertype<PhysicsParams>("PhysicsParams", sol::constructors<PhysicsParams()>(),
        "enablePhysics", &PhysicsParams::enablePhysics, "linkMass", &PhysicsParams::linkMass,
        "jointStiffness", &PhysicsParams::jointStiffness, "jointDamping", &PhysicsParams::jointDamping, "gravityOverride", &PhysicsParams::gravityOverride);

    lua.new_usertype<LODParams>("LODParams", sol::constructors<LODParams()>(),
        "meshLODs", &LODParams::meshLODs, "displayRanges", &LODParams::displayRanges);
    
    lua.new_usertype<GrappleBundle>("GrappleBundle", sol::no_constructor,
        "hookMesh", &GrappleBundle::hookMesh, "chainMeshes", &GrappleBundle::chainMeshes, "material", &GrappleBundle::material,
        "physics", &GrappleBundle::physics, "lodData", &GrappleBundle::lodData, "shader", &GrappleBundle::shader);

    lua.set_function("spawn_grapple_asset",
        [&](const HookParams& hp, const ChainParams& cp, const MaterialParams& mp, const PhysicsParams& pp, const LODParams& lp) {
            auto factory = MainPlugin::instance().getGrappleAssetFactory();
            pendingGrapples.emplace_back(factory->generateAsync(hp, cp, mp, pp, lp), hp.id);
        }
    );
}

void GrappleHookLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingGrapples.begin(); it != pendingGrapples.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Grapple asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingGrapples.erase(it);
        } else { ++it; }
    }
}

} // namespace GrappleHooks
} // namespace MagiTech
