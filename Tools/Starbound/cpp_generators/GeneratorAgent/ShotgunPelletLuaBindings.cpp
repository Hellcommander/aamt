#include "ShotgunPelletLuaBindings.hpp"
#include "ShotgunPelletFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace ShotgunPellets {

static std::vector<std::pair<std::future<ShotgunAssetBundle>, std::string>> pendingSystems;

void ShotgunPelletLuaBindings::bind(sol::state& lua) {
    lua.new_enum("SpreadPattern",
        "Uniform", SpreadPattern::Uniform,
        "Gaussian", SpreadPattern::Gaussian
    );

    lua.new_usertype<ShotgunPelletParams>("ShotgunPelletParams",
        sol::constructors<ShotgunPelletParams()>(),
        "id", &ShotgunPelletParams::id,
        "pelletCount", &ShotgunPelletParams::pelletCount,
        "spreadAngleDeg", &ShotgunPelletParams::spreadAngleDeg,
        "spreadPattern", &ShotgunPelletParams::spreadPattern,
        "pelletRadius", &ShotgunPelletParams::pelletRadius,
        "pelletLength", &ShotgunPelletParams::pelletLength,
        "radialSegments", &ShotgunPelletParams::radialSegments,
        "initialSpeedMin", &ShotgunPelletParams::initialSpeedMin,
        "initialSpeedMax", &ShotgunPelletParams::initialSpeedMax,
        "gravityScale", &ShotgunPelletParams::gravityScale,
        "drag", &ShotgunPelletParams::drag,
        "enableTrail", &ShotgunPelletParams::enableTrail,
        "trailLength", &ShotgunPelletParams::trailLength,
        "trailWidth", &ShotgunPelletParams::trailWidth,
        "trailColor", &ShotgunPelletParams::trailColor,
        "maxDecals", &ShotgunPelletParams::maxDecals,
        "decalRadius", &ShotgunPelletParams::decalRadius,
        "decalLifetime", &ShotgunPelletParams::decalLifetime,
        "decalColor", &ShotgunPelletParams::decalColor
    );

    lua.new_usertype<ShotgunAssetBundle>("ShotgunAssetBundle",
        sol::no_constructor,
        "pelletMesh", &ShotgunAssetBundle::pelletMesh,
        "pelletShader", &ShotgunAssetBundle::pelletShader,
        "instanceBuffer", &ShotgunAssetBundle::instanceBuffer,
        "impactDecal", &ShotgunAssetBundle::impactDecal
    );

    lua.set_function("fire_shotgun",
        [&](const ShotgunPelletParams& p) {
            auto factory = MainPlugin::instance().getShotgunPelletFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("fire_shotgun_async",
        [&](const ShotgunPelletParams& p) {
            auto factory = MainPlugin::instance().getShotgunPelletFactory();
            pendingSystems.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void ShotgunPelletLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingSystems.begin(); it != pendingSystems.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Shotgun system ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingSystems.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace ShotgunPellets
} // namespace MagiTech
