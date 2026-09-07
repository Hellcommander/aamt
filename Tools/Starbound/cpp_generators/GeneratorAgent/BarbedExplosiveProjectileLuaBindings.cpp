#include "BarbedExplosiveProjectileLuaBindings.hpp"
#include "BarbedExplosiveProjectileFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

static std::vector<std::pair<std::future<BarbedExplosiveProjectileBundle>, std::string>> pendingProjectiles;

void BarbedExplosiveProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<GeometryParams>("GeometryParams", sol::constructors<GeometryParams()>(),
        "length", &GeometryParams::length, "radius", &GeometryParams::radius,
        "numBarbs", &GeometryParams::numBarbs, "barbLength", &GeometryParams::barbLength,
        "barbThickness", &GeometryParams::barbThickness, "barbCurvature", &GeometryParams::barbCurvature);

    lua.new_usertype<ExplosionParams>("ExplosionParams", sol::constructors<ExplosionParams()>(),
        "radius", &ExplosionParams::radius, "impulseStrength", &ExplosionParams::impulseStrength,
        "particleCount", &ExplosionParams::particleCount, "particleLifespan", &ExplosionParams::particleLifespan,
        "shardSize", &ExplosionParams::shardSize, "shardVelocity", &ExplosionParams::shardVelocity);

    lua.new_usertype<VisualParams>("VisualParams", sol::constructors<VisualParams()>(),
        "baseColor", &VisualParams::baseColor, "dirtVariation", &VisualParams::dirtVariation,
        "emissiveIntensity", &VisualParams::emissiveIntensity, "specularHighlight", &VisualParams::specularHighlight);

    lua.new_usertype<BarbedExplosiveProjectileBundle>("BarbedExplosiveProjectileBundle", sol::no_constructor,
        "lods", &BarbedExplosiveProjectileBundle::lods, "material", &BarbedExplosiveProjectileBundle::material,
        "explosionEffect", &BarbedExplosiveProjectileBundle::explosionEffect);

    lua.set_function("generateBarbProj",
        [&](const GeometryParams& gp, const ExplosionParams& ep, const VisualParams& vp) {
            auto factory = MainPlugin::instance().getBarbedExplosiveProjectileFactory();
            auto id = std::to_string(gp.hashKey() ^ ep.hashKey() ^ vp.hashKey());
            pendingProjectiles.emplace_back(factory->generateAsync(gp, ep, vp), id);
        }
    );
}

void BarbedExplosiveProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Barbed explosive projectile asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingProjectiles.erase(it);
        } else { ++it; }
    }
}

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
