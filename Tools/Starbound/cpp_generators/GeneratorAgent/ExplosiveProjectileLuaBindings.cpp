#include "ExplosiveProjectileLuaBindings.hpp"
#include "ExplosiveProjectileFactory.hpp"
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace ExplosiveProjectiles {

static std::vector<std::pair<std::future<ExplosiveAssetBundle>, std::string>> pendingProjectiles;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<ExplosiveProjectileFactory>& factorySlot() {
    static std::shared_ptr<ExplosiveProjectileFactory> f;
    return f;
}
} // namespace

void ExplosiveProjectileLuaBindings::setFactory(std::shared_ptr<ExplosiveProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<ExplosiveProjectileFactory> ExplosiveProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No instance injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<ExplosiveProjectileFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void ExplosiveProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<ExplosiveProjectileParams>("ExplosiveProjectileParams",
        sol::constructors<ExplosiveProjectileParams()>(),
        "id", &ExplosiveProjectileParams::id,
        "noseLength", &ExplosiveProjectileParams::noseLength,
        "bodyLength", &ExplosiveProjectileParams::bodyLength,
        "bodyRadius", &ExplosiveProjectileParams::bodyRadius,
        "finCount", &ExplosiveProjectileParams::finCount,
        "finSpan", &ExplosiveProjectileParams::finSpan,
        "finThickness", &ExplosiveProjectileParams::finThickness,
        "motorThrust", &ExplosiveProjectileParams::motorThrust,
        "motorDuration", &ExplosiveProjectileParams::motorDuration,
        "flameColor", &ExplosiveProjectileParams::flameColor,
        "flameLifetime", &ExplosiveProjectileParams::flameLifetime,
        "explosionRadius", &ExplosiveProjectileParams::explosionRadius,
        "explosionColor", &ExplosiveProjectileParams::explosionColor,
        "flashDuration", &ExplosiveProjectileParams::flashDuration,
        "proximityDetonate", &ExplosiveProjectileParams::proximityDetonate,
        "fragmentCount", &ExplosiveProjectileParams::fragmentCount,
        "fragmentMinScale", &ExplosiveProjectileParams::fragmentMinScale,
        "fragmentMaxScale", &ExplosiveProjectileParams::fragmentMaxScale,
        "fragmentSpeedMin", &ExplosiveProjectileParams::fragmentSpeedMin,
        "fragmentSpeedMax", &ExplosiveProjectileParams::fragmentSpeedMax,
        "fragmentSpreadAngleDeg", &ExplosiveProjectileParams::fragmentSpreadAngleDeg,
        "smokeColor", &ExplosiveProjectileParams::smokeColor,
        "smokeLifetime", &ExplosiveProjectileParams::smokeLifetime,
        "debrisLifetime", &ExplosiveProjectileParams::debrisLifetime
    );

    lua.new_usertype<ExplosiveAssetBundle>("ExplosiveAssetBundle",
        sol::no_constructor,
        "projectileMesh", &ExplosiveAssetBundle::projectileMesh,
        "motorTrail", &ExplosiveAssetBundle::motorTrail,
        "smokeTrail", &ExplosiveAssetBundle::smokeTrail,
        "explosionFlash", &ExplosiveAssetBundle::explosionFlash,
        "fragmentMesh", &ExplosiveAssetBundle::fragmentMesh,
        "debrisParticles", &ExplosiveAssetBundle::debrisParticles,
        "materialShader", &ExplosiveAssetBundle::materialShader,
        "scorchDecal", &ExplosiveAssetBundle::scorchDecal
    );

    lua.set_function("spawn_explosive_projectile",
        [&](const ExplosiveProjectileParams& p) {
            auto factory = ExplosiveProjectileLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_explosive_projectile_async",
        [&](const ExplosiveProjectileParams& p) {
            auto factory = ExplosiveProjectileLuaBindings::factory();
            pendingProjectiles.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void ExplosiveProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Explosive projectile ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingProjectiles.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace ExplosiveProjectiles
} // namespace MagiTech
