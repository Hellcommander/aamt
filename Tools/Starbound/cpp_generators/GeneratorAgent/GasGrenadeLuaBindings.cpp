#include "GasGrenadeLuaBindings.hpp"
#include "GasGrenadeFactory.hpp"
#include <memory>
#include <mutex>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace GasGrenades {

static std::vector<std::pair<std::future<GrenadeBundle>, std::string>> pendingGrenades;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<GasGrenadeFactory>& factorySlot() {
    static std::shared_ptr<GasGrenadeFactory> f;
    return f;
}
} // namespace

void GasGrenadeLuaBindings::setFactory(std::shared_ptr<GasGrenadeFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<GasGrenadeFactory> GasGrenadeLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<GasGrenadeFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

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
            auto factory = GasGrenadeLuaBindings::factory();
            return factory->generateAsync(p, u).get();
        }
    );

    lua.set_function("spawn_gas_grenade_async",
        [&](const GasGrenadeParams& p, const UIParams& u) {
            auto factory = GasGrenadeLuaBindings::factory();
            pendingGrenades.emplace_back(factory->generateAsync(p, u), p.id);
        }
    );
}

void GasGrenadeLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingGrenades.begin(); it != pendingGrenades.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                it->first.get();
                lua["print"]("Gas Grenade asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("GasGrenades", "Gas grenade asset {} failed: {}", it->second, e.what());
            }
            it = pendingGrenades.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace GasGrenades
} // namespace MagiTech
