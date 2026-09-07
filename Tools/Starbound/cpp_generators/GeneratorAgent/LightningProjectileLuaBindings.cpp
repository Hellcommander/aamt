#include "LightningProjectileLuaBindings.hpp"
#include "LightningProjectileFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace LightningProjectiles {

static std::vector<std::pair<std::future<LightningBundle>, std::string>> pendingBolts;

void LightningProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<LightningProjectileParams>("LightningProjectileParams",
        sol::constructors<LightningProjectileParams()>(),
        "id", &LightningProjectileParams::id,
        "length", &LightningProjectileParams::length,
        "thickness", &LightningProjectileParams::thickness,
        "mainColor", &LightningProjectileParams::mainColor,
        "glowColor", &LightningProjectileParams::glowColor,
        "noiseIntensity", &LightningProjectileParams::noiseIntensity,
        "noiseScale", &LightningProjectileParams::noiseScale,
        "flickerSpeed", &LightningProjectileParams::flickerSpeed,
        "branchCount", &LightningProjectileParams::branchCount,
        "branchLengthFactor", &LightningProjectileParams::branchLengthFactor,
        "jitterAmplitude", &LightningProjectileParams::jitterAmplitude,
        "jitterFrequency", &LightningProjectileParams::jitterFrequency,
        "arcWidthVariation", &LightningProjectileParams::arcWidthVariation,
        "pulseFrequency", &LightningProjectileParams::pulseFrequency,
        "trailType", &LightningProjectileParams::trailType,
        "trailLength", &LightningProjectileParams::trailLength,
        "sparkCount", &LightningProjectileParams::sparkCount,
        "sparkLifetime", &LightningProjectileParams::sparkLifetime,
        "sparkColor", &LightningProjectileParams::sparkColor,
        "soundPitch", &LightningProjectileParams::soundPitch
    );

    lua.new_usertype<LightningBundle>("LightningBundle",
        "mesh", &LightningBundle::mesh,
        "shader", &LightningBundle::shader,
        "texture", &LightningBundle::texture,
        "sparks", &LightningBundle::sparks,
        "sfx", &LightningBundle::sfx
    );

    lua.set_function("spawn_lightning_projectile",
        [&](const LightningProjectileParams& p) {
            auto factory = MainPlugin::instance().getLightningProjectileFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_lightning_projectile_async",
        [&](const LightningProjectileParams& p) {
            auto factory = MainPlugin::instance().getLightningProjectileFactory();
            auto fut = factory->generateAsync(p);
            pendingBolts.emplace_back(std::move(fut), p.id);
        }
    );
}

void LightningProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingBolts.begin(); it != pendingBolts.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Lightning Bolt ready: " + it->second);
            it = pendingBolts.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace LightningProjectiles
} // namespace MagiTech
