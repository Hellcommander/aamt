#include "GasGrenadeLuaBindings.hpp"
#include "GasGrenadeFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace GasGrenades {

static std::vector<std::pair<std::future<GrenadeBundle>, std::string>> pendingGrenades;

void GasGrenadeLuaBindings::bind(sol::state& lua) {

    lua.new_enum("CloudType",
        "Smoke", CloudType::Smoke,
        "Poison", CloudType::Poison,
        "TearGas", CloudType::TearGas,
        "Corrosive", CloudType::Corrosive
    );

    lua.new_usertype<GasGrenadeParams>("GasGrenadeParams",
        sol::constructors<GasGrenadeParams()>(),
        "id", &GasGrenadeParams::id,
        "fuseTime", &GasGrenadeParams::fuseTime,
        "proximityTrigger", &GasGrenadeParams::proximityTrigger,
        "bodyRadius", &GasGrenadeParams::bodyRadius,
        "bodyHeight", &GasGrenadeParams::bodyHeight,
        "seamSegments", &GasGrenadeParams::seamSegments,
        "cloudType", &GasGrenadeParams::cloudType,
        "cloudRadius", &GasGrenadeParams::cloudRadius,
        "cloudDuration", &GasGrenadeParams::cloudDuration,
        "density", &GasGrenadeParams::density,
        "turbulence", &GasGrenadeParams::turbulence,
        "swirlSpeed", &GasGrenadeParams::swirlSpeed,
        "riseSpeed", &GasGrenadeParams::riseSpeed,
        "particleSpawnRate", &GasGrenadeParams::particleSpawnRate,
        "particleSizeRange", &GasGrenadeParams::particleSizeRange,
        "particleLifeRange", &GasGrenadeParams::particleLifeRange,
        "particleColor", &GasGrenadeParams::particleColor,
        "particleNoiseScale", &GasGrenadeParams::particleNoiseScale,
        "particleNoiseSpeed", &GasGrenadeParams::particleNoiseSpeed,
        "decalRadius", &GasGrenadeParams::decalRadius,
        "decalDuration", &GasGrenadeParams::decalDuration,
        "hissVolume", &GasGrenadeParams::hissVolume,
        "hissPitch", &GasGrenadeParams::hissPitch
    );

    lua.new_usertype<UIParams>("UIParams",
        sol::constructors<UIParams()>(),
        "iconSize", &UIParams::iconSize,
        "borderColor", &UIParams::borderColor,
        "flashOnSelect", &UIParams::flashOnSelect
    );

    lua.new_usertype<GrenadeBundle>("GrenadeBundle",
        sol::no_constructor,
        "bodyMesh", &GrenadeBundle::bodyMesh,
        "cloudShader", &GrenadeBundle::cloudShader,
        "bodyTexture", &GrenadeBundle::bodyTexture,
        "cloudParticles", &GrenadeBundle::cloudParticles,
        "triggerPhysics", &GrenadeBundle::triggerPhysics,
        "sfxHiss", &GrenadeBundle::sfxHiss,
        "iconTexture", &GrenadeBundle::iconTexture
    );

    lua.set_function("spawn_gas_grenade",
        [&](const GasGrenadeParams& p, const UIParams& u) {
            auto factory = MainPlugin::instance().getGasGrenadeFactory();
            return factory->generateAsync(p, u).get();
        }
    );

    lua.set_function("spawn_gas_grenade_async",
        [&](const GasGrenadeParams& p, const UIParams& u) {
            auto factory = MainPlugin::instance().getGasGrenadeFactory();
            pendingGrenades.emplace_back(factory->generateAsync(p, u), p.id);
        }
    );
}

void GasGrenadeLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingGrenades.begin(); it != pendingGrenades.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Gas Grenade asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingGrenades.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace GasGrenades
} // namespace MagiTech
