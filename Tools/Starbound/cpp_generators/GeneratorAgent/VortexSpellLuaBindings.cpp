#include "VortexSpellLuaBindings.hpp"
#include "VortexSpellFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace VortexSpells {

static std::vector<std::pair<std::future<VortexSpellAssetBundle>, std::string>> pendingSpells;
static std::mutex pendingSpellsMutex;

static std::mutex factoryMutex;
static std::shared_ptr<VortexSpellFactory> sharedFactory;

void VortexSpellLuaBindings::setFactory(std::shared_ptr<VortexSpellFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<VortexSpellFactory> VortexSpellLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<VortexSpellFactory>();
        sharedFactory->initialize(64, 4);
    }
    return sharedFactory;
}

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
        [](const VortexSpellParams& p) {
            return factory()->generateAsync(p).get();
        }
    );

    lua.set_function("cast_vortex_spell_async",
        [](const VortexSpellParams& p) {
            auto future = factory()->generateAsync(p);
            std::lock_guard<std::mutex> lock(pendingSpellsMutex);
            pendingSpells.emplace_back(std::move(future), p.id);
        }
    );
}

void VortexSpellLuaBindings::poll_assets(sol::state& lua) {
    std::lock_guard<std::mutex> lock(pendingSpellsMutex);
    for (auto it = pendingSpells.begin(); it != pendingSpells.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Vortex spell ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("VortexSpells", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingSpells.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace VortexSpells
} // namespace MagiTech
