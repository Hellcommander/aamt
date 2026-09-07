#include "HomingMissileLuaBindings.hpp"
#include "HomingMissileFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace HomingMissiles {

static std::vector<std::pair<std::future<MissileAssetBundle>, std::string>> pendingMissiles;

void HomingMissileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<HomingMissileParams>("HomingMissileParams",
        sol::constructors<HomingMissileParams()>(),
        "id", &HomingMissileParams::id,
        "noseLength", &HomingMissileParams::noseLength,
        "bodyRadius", &HomingMissileParams::bodyRadius,
        "bodySegments", &HomingMissileParams::bodySegments,
        "finCount", &HomingMissileParams::finCount,
        "finSpan", &HomingMissileParams::finSpan,
        "finThickness", &HomingMissileParams::finThickness,
        "maxTurnRateDeg", &HomingMissileParams::maxTurnRateDeg,
        "speed", &HomingMissileParams::speed,
        "trailLength", &HomingMissileParams::trailLength,
        "trailWidth", &HomingMissileParams::trailWidth,
        "flameColor", &HomingMissileParams::flameColor,
        "smokeColor", &HomingMissileParams::smokeColor,
        "flameLifetime", &HomingMissileParams::flameLifetime,
        "smokeLifetime", &HomingMissileParams::smokeLifetime
    );

    lua.new_usertype<MissileAssetBundle>("MissileAssetBundle",
        sol::no_constructor,
        "missileMesh", &MissileAssetBundle::missileMesh,
        "guidancePath", &MissileAssetBundle::guidancePath,
        "trailMesh", &MissileAssetBundle::trailMesh,
        "bodyShader", &MissileAssetBundle::bodyShader,
        "flameExhaust", &MissileAssetBundle::flameExhaust,
        "smokeExhaust", &MissileAssetBundle::smokeExhaust
    );

    lua.set_function("spawn_homing_missile",
        [&](const HomingMissileParams& p) {
            auto factory = MainPlugin::instance().getHomingMissileFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_homing_missile_async",
        [&](const HomingMissileParams& p) {
            auto factory = MainPlugin::instance().getHomingMissileFactory();
            pendingMissiles.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void HomingMissileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingMissiles.begin(); it != pendingMissiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Homing missile ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingMissiles.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace HomingMissiles
} // namespace MagiTech
