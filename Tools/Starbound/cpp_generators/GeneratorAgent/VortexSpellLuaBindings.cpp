#include "VortexSpellLuaBindings.hpp"
#include "VortexSpellFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace VortexSpells {

static std::vector<std::pair<std::future<VortexSpellAssetBundle>, std::string>> pendingSpells;

void VortexSpellLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<VortexSpellParams>("VortexSpellParams",
        sol::constructors<VortexSpellParams()>(),
        "id", &VortexSpellParams::id,
        "baseRadius", &VortexSpellParams::baseRadius,
        "topRadius", &VortexSpellParams::topRadius,
        "height", &VortexSpellParams::height,
        "radialSegments", &VortexSpellParams::radialSegments,
        "heightSegments", &VortexSpellParams::heightSegments,
        "swirlSpeed", &VortexSpellParams::swirlSpeed,
        "upwardSpeed", &VortexSpellParams::upwardSpeed,
        "noiseAmplitude", &VortexSpellParams::noiseAmplitude,
        "noiseFrequency", &VortexSpellParams::noiseFrequency,
        "dustParticleCount", &VortexSpellParams::dustParticleCount,
        "dustLifetime", &VortexSpellParams::dustLifetime,
        "dustColor", &VortexSpellParams::dustColor,
        "lightScattering", &VortexSpellParams::lightScattering,
        "vortexColor", &VortexSpellParams::vortexColor,
        "groundCrackRadius", &VortexSpellParams::groundCrackRadius,
        "groundCrackLifetime", &VortexSpellParams::groundCrackLifetime
    );

    lua.new_usertype<VortexSpellAssetBundle>("VortexSpellAssetBundle",
        sol::no_constructor,
        "vortexMesh", &VortexSpellAssetBundle::vortexMesh,
        "dustParticles", &VortexSpellAssetBundle::dustParticles,
        "debrisParticles", &VortexSpellAssetBundle::debrisParticles,
        "windRibbons", &VortexSpellAssetBundle::windRibbons,
        "vortexShader", &VortexSpellAssetBundle::vortexShader,
        "groundDecal", &VortexSpellAssetBundle::groundDecal
    );

    lua.set_function("cast_vortex_spell",
        [&](const VortexSpellParams& p) {
            auto factory = MainPlugin::instance().getVortexSpellFactory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("cast_vortex_spell_async",
        [&](const VortexSpellParams& p) {
            auto factory = MainPlugin::instance().getVortexSpellFactory();
            pendingSpells.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void VortexSpellLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingSpells.begin(); it != pendingSpells.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Vortex spell ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingSpells.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace VortexSpells
} // namespace MagiTech
