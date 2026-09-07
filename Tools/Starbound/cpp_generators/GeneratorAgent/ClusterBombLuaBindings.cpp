#include "ClusterBombLuaBindings.hpp"
#include "ClusterBombFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace ClusterBombs {

static std::vector<std::pair<std::future<BombAssetBundle>, std::string>> pendingBombs;

void ClusterBombLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<ClusterBombParams>("ClusterBombParams",
        sol::constructors<ClusterBombParams()>(),
        "id", &ClusterBombParams::id,
        "shellRadius", &ClusterBombParams::shellRadius,
        "shellSegments", &ClusterBombParams::shellSegments,
        "fuseLength", &ClusterBombParams::fuseLength,
        "fuseThickness", &ClusterBombParams::fuseThickness,
        "detonationDelay", &ClusterBombParams::detonationDelay,
        "proximityFuse", &ClusterBombParams::proximityFuse,
        "fragmentCount", &ClusterBombParams::fragmentCount,
        "fragmentMinScale", &ClusterBombParams::fragmentMinScale,
        "fragmentMaxScale", &ClusterBombParams::fragmentMaxScale,
        "spreadAngleDeg", &ClusterBombParams::spreadAngleDeg,
        "spawnSpeedMin", &ClusterBombParams::spawnSpeedMin,
        "spawnSpeedMax", &ClusterBombParams::spawnSpeedMax,
        "explosionColor", &ClusterBombParams::explosionColor,
        "explosionRadius", &ClusterBombParams::explosionRadius,
        "smokeLifetime", &ClusterBombParams::smokeLifetime,
        "debrisLifetime", &ClusterBombParams::debrisLifetime
    );

    lua.new_usertype<BombAssetBundle>("BombAssetBundle",
        sol::no_constructor,
        "casingMesh", &BombAssetBundle::casingMesh,
        "casingShader", &BombAssetBundle::casingShader,
        "fuseHandle", &BombAssetBundle::fuseHandle,
        "explosionCoreFX", &BombAssetBundle::explosionCoreFX,
        "smokeRingFX", &BombAssetBundle::smokeRingFX,
        "debrisFX", &BombAssetBundle::debrisFX
    );

    lua.set_function("spawn_cluster_bomb",
        [&](const ClusterBombParams& p) {
            auto factory = MainPlugin::instance().getClusterBombFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_cluster_bomb_async",
        [&](const ClusterBombParams& p) {
            auto factory = MainPlugin::instance().getClusterBombFactory();
            pendingBombs.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void ClusterBombLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingBombs.begin(); it != pendingBombs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Cluster bomb ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingBombs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace ClusterBombs
} // namespace MagiTech
