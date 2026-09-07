#include "FireballLuaBindings.hpp"
#include "FireballFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace Fireballs {

static std::vector<std::pair<std::future<FireballAssetBundle>, std::string>> pendingFireballs;

void FireballLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<FireballParams>("FireballParams",
        sol::constructors<FireballParams()>(),
        "id", &FireballParams::id,
        "coreRadius", &FireballParams::coreRadius,
        "coreLatitudeSegs", &FireballParams::coreLatitudeSegs,
        "coreLongitudeSegs", &FireballParams::coreLongitudeSegs,
        "flameHeight", &FireballParams::flameHeight,
        "flameTaper", &FireballParams::flameTaper,
        "flameRadialSegs", &FireballParams::flameRadialSegs,
        "flameHeightSegs", &FireballParams::flameHeightSegs,
        "emberCount", &FireballParams::emberCount,
        "emberColor", &FireballParams::emberColor,
        "emberLifetime", &FireballParams::emberLifetime,
        "emberSpeedMin", &FireballParams::emberSpeedMin,
        "emberSpeedMax", &FireballParams::emberSpeedMax,
        "smokeTrailCount", &FireballParams::smokeTrailCount,
        "smokeColor", &FireballParams::smokeColor,
        "smokeLifetime", &FireballParams::smokeLifetime,
        "smokeSpawnRate", &FireballParams::smokeSpawnRate,
        "explosionRadius", &FireballParams::explosionRadius,
        "explosionColor", &FireballParams::explosionColor,
        "explosionDuration", &FireballParams::explosionDuration,
        "scorchDecalCount", &FireballParams::scorchDecalCount,
        "scorchRadius", &FireballParams::scorchRadius,
        "scorchFadeTime", &FireballParams::scorchFadeTime,
        "initialSpeed", &FireballParams::initialSpeed,
        "gravityScale", &FireballParams::gravityScale,
        "arcTrajectory", &FireballParams::arcTrajectory,
        "heatDistortionStrength", &FireballParams::heatDistortionStrength,
        "flameNoiseScale", &FireballParams::flameNoiseScale,
        "flameNoiseSpeed", &FireballParams::flameNoiseSpeed
    );

    lua.new_usertype<FireballAssetBundle>("FireballAssetBundle",
        sol::no_constructor,
        "coreMesh", &FireballAssetBundle::coreMesh,
        "flameMesh", &FireballAssetBundle::flameMesh,
        "emberParticles", &FireballAssetBundle::emberParticles,
        "smokeParticles", &FireballAssetBundle::smokeParticles,
        "fireShader", &FireballAssetBundle::fireShader,
        "scorchDecal", &FireballAssetBundle::scorchDecal,
        "physicsData", &FireballAssetBundle::physicsData
    );

    lua.set_function("spawn_fireball",
        [&](const FireballParams& p) {
            auto factory = MainPlugin::instance().getFireballFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_fireball_async",
        [&](const FireballParams& p) {
            auto factory = MainPlugin::instance().getFireballFactory();
            pendingFireballs.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void FireballLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingFireballs.begin(); it != pendingFireballs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Fireball asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingFireballs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Fireballs
} // namespace MagiTech
