#include "AcidLiquidProjectileLuaBindings.hpp"
#include "AcidLiquidProjectileFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace AcidLiquidProjectiles {

static std::vector<std::pair<std::future<LiquidAssetBundle>, std::string>> pendingProjectiles;

void AcidLiquidProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<LiquidProjectileParams>("LiquidProjectileParams",
        sol::constructors<LiquidProjectileParams()>(),
        "id", &LiquidProjectileParams::id,
        "baseRadius", &LiquidProjectileParams::baseRadius,
        "radialSegments", &LiquidProjectileParams::radialSegments,
        "lengthVariance", &LiquidProjectileParams::lengthVariance,
        "viscosity", &LiquidProjectileParams::viscosity,
        "surfaceTension", &LiquidProjectileParams::surfaceTension,
        "gravityScale", &LiquidProjectileParams::gravityScale,
        "emissionRate", &LiquidProjectileParams::emissionRate,
        "dropletSpeedMin", &LiquidProjectileParams::dropletSpeedMin,
        "dropletSpeedMax", &LiquidProjectileParams::dropletSpeedMax,
        "dropletSizeMin", &LiquidProjectileParams::dropletSizeMin,
        "dropletSizeMax", &LiquidProjectileParams::dropletSizeMax,
        "splatterCount", &LiquidProjectileParams::splatterCount,
        "splatterRadius", &LiquidProjectileParams::splatterRadius,
        "splatterLifetime", &LiquidProjectileParams::splatterLifetime,
        "liquidColor", &LiquidProjectileParams::liquidColor,
        "refractionStrength", &LiquidProjectileParams::refractionStrength,
        "sheenIntensity", &LiquidProjectileParams::sheenIntensity
    );

    lua.new_usertype<LiquidAssetBundle>("LiquidAssetBundle",
        sol::no_constructor,
        "dropletMesh", &LiquidAssetBundle::dropletMesh,
        "liquidShader", &LiquidAssetBundle::liquidShader,
        "mistParticles", &LiquidAssetBundle::mistParticles,
        "splatterDecal", &LiquidAssetBundle::splatterDecal,
        "fluidPhysics", &LiquidAssetBundle::fluidPhysics
    );

    lua.set_function("spawn_liquid_projectile",
        [&](const LiquidProjectileParams& p) {
            auto factory = MainPlugin::instance().getAcidLiquidProjectileFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_liquid_projectile_async",
        [&](const LiquidProjectileParams& p) {
            auto factory = MainPlugin::instance().getAcidLiquidProjectileFactory();
            pendingProjectiles.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void AcidLiquidProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Liquid projectile ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingProjectiles.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace AcidLiquidProjectiles
} // namespace MagiTech
