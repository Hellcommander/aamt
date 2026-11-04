#include "HomingMissileLuaBindings.hpp"
#include "HomingMissileFactory.hpp"
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace HomingMissiles {

static std::vector<std::pair<std::future<MissileAssetBundle>, std::string>> pendingMissiles;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<HomingMissileFactory>& factorySlot() {
    static std::shared_ptr<HomingMissileFactory> f;
    return f;
}
} // namespace

void HomingMissileLuaBindings::setFactory(std::shared_ptr<HomingMissileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<HomingMissileFactory> HomingMissileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No instance injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<HomingMissileFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void HomingMissileLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<HomingMissileParams>("HomingMissileParams",
        sol::constructors<HomingMissileParams()>(),
        "id", &HomingMissileParams::id,
        "noseLength", &HomingMissileParams::noseLength,
        "bodyRadius", &HomingMissileParams::bodyRadius,
        "bodySegments", &HomingMissileParams::bodySegments,
        "finCount", &HomingMissileParams::finCount,
        "finSpan", &HomingMissileParams::finSpan,
        "finThickness", &HomingMissileParams::finThickness,
        "maxTurnRateDeg", &HomingMissileParams::maxTurnRateDeg,
        "speed", &HomingMissileParams::speed,
        "trailLength", &HomingMissileParams::trailLength,
        "trailWidth", &HomingMissileParams::trailWidth,
        "flameColor", &HomingMissileParams::flameColor,
        "smokeColor", &HomingMissileParams::smokeColor,
        "flameLifetime", &HomingMissileParams::flameLifetime,
        "smokeLifetime", &HomingMissileParams::smokeLifetime
    );

    lua.new_usertype<MissileAssetBundle>("MissileAssetBundle",
        sol::no_constructor,
        "missileMesh", &MissileAssetBundle::missileMesh,
        "guidancePath", &MissileAssetBundle::guidancePath,
        "trailMesh", &MissileAssetBundle::trailMesh,
        "bodyShader", &MissileAssetBundle::bodyShader,
        "flameExhaust", &MissileAssetBundle::flameExhaust,
        "smokeExhaust", &MissileAssetBundle::smokeExhaust
    );

    lua.set_function("spawn_homing_missile",
        [&](const HomingMissileParams& p) {
            auto factory = HomingMissileLuaBindings::factory();
            return factory->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_homing_missile_async",
        [&](const HomingMissileParams& p) {
            auto factory = HomingMissileLuaBindings::factory();
            pendingMissiles.emplace_back(factory->generateAsync(p), p.id);
        }
    );
}

void HomingMissileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingMissiles.begin(); it != pendingMissiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Homing missile ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingMissiles.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace HomingMissiles
} // namespace MagiTech
