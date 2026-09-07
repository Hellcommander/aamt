#include "CosmicLuaBindings.hpp"
#include "CosmicFactory.hpp"
#include "projectile/CosmicProjectileTypes.hpp"
#include "space_object/SpaceObjectTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace Cosmic {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingProjectiles;
static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingObjects;

void CosmicLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<CosmicProjectileParams>("CosmicProjectileParams",
        "id", &CosmicProjectileParams::id,
        "type", &CosmicProjectileParams::type,
        "length", &CosmicProjectileParams::length,
        "radius", &CosmicProjectileParams::radius,
        "colorCore", &CosmicProjectileParams::colorCore,
        "colorEdge", &CosmicProjectileParams::colorEdge,
        "noiseIntensity", &CosmicProjectileParams::noiseIntensity,
        "noiseScale", &CosmicProjectileParams::noiseScale,
        "flickerRate", &CosmicProjectileParams::flickerRate,
        "trailType", &CosmicProjectileParams::trailType,
        "trailLength", &CosmicProjectileParams::trailLength,
        "impactEffect", &CosmicProjectileParams::impactEffect,
        "damageType", &CosmicProjectileParams::damageType,
        "homingStrength", &CosmicProjectileParams::homingStrength,
        "fragmentation", &CosmicProjectileParams::fragmentation
    );

    lua.set_function("spawn_cosmic_proj", [&](CosmicProjectileParams p) {
        auto factory = MainPlugin::instance().getCosmicProjectileFactory();
        auto fut = factory->generateAsync(p);
        pendingProjectiles.emplace_back(std::move(fut), p.id);
    });

    lua.new_usertype<SpaceObjectParams>("SpaceObjectParams",
        "id", &SpaceObjectParams::id,
        "objectType", &SpaceObjectParams::objectType,
        "radius", &SpaceObjectParams::radius,
        "detailLevel", &SpaceObjectParams::detailLevel,
        "colorPalette", &SpaceObjectParams::colorPalette,
        "surfaceRoughness", &SpaceObjectParams::surfaceRoughness,
        "craterDensity", &SpaceObjectParams::craterDensity,
        "ringSystem", &SpaceObjectParams::ringSystem,
        "ringDetail", &SpaceObjectParams::ringDetail,
        "nebulaVolumetrics", &SpaceObjectParams::nebulaVolumetrics,
        "starCount", &SpaceObjectParams::starCount,
        "starBrightness", &SpaceObjectParams::starBrightness
    );

    lua.set_function("spawn_space_obj", [&](SpaceObjectParams p) {
        auto factory = MainPlugin::instance().getSpaceObjectFactory();
        auto fut = factory->generateAsync(p);
        pendingObjects.emplace_back(std::move(fut), p.id);
    });
}

void CosmicLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Cosmic Projectile ready: " + it->second);
            it = pendingProjectiles.erase(it);
        } else {
            ++it;
        }
    }

    for (auto it = pendingObjects.begin(); it != pendingObjects.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Space Object ready: " + it->second);
            it = pendingObjects.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Cosmic
} // namespace MagiTech
