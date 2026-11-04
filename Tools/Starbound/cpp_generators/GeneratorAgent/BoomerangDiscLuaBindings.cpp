#include "BoomerangDiscLuaBindings.hpp"
#include "BoomerangDiscFactory.hpp"
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace BoomerangDiscs {

static std::vector<std::pair<std::future<BoomerangAssetBundle>, std::string>> pendingBoomerangs;
static std::vector<std::pair<std::future<DiscAssetBundle>, std::string>> pendingDiscs;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<BoomerangDiscFactory>& factorySlot() {
    static std::shared_ptr<BoomerangDiscFactory> f;
    return f;
}
} // namespace

void BoomerangDiscLuaBindings::setFactory(std::shared_ptr<BoomerangDiscFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<BoomerangDiscFactory> BoomerangDiscLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<BoomerangDiscFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void BoomerangDiscLuaBindings::bind(sol::state& lua) {
    // Boomerang
    lua.new_usertype<BoomerangParams>("BoomerangParams",
        sol::constructors<BoomerangParams()>(),
        "id", &BoomerangParams::id,
        "armSpan", &BoomerangParams::armSpan,
        "armThickness", &BoomerangParams::armThickness,
        "twistCount", &BoomerangParams::twistCount,
        "spinRateRPM", &BoomerangParams::spinRateRPM,
        "returnDelay", &BoomerangParams::returnDelay,
        "returnArcHeight", &BoomerangParams::returnArcHeight,
        "trailLength", &BoomerangParams::trailLength,
        "trailWidth", &BoomerangParams::trailWidth,
        "trailColor", &BoomerangParams::trailColor,
        "groundBounceDamping", &BoomerangParams::groundBounceDamping
    );

    lua.new_usertype<BoomerangAssetBundle>("BoomerangAssetBundle",
        sol::no_constructor,
        "mesh", &BoomerangAssetBundle::mesh,
        "shader", &BoomerangAssetBundle::shader,
        "flightPath", &BoomerangAssetBundle::flightPath,
        "trailMesh", &BoomerangAssetBundle::trailMesh,
        "airGustFX", &BoomerangAssetBundle::airGustFX
    );

    // Disc
    lua.new_usertype<ReturningDiscParams>("ReturningDiscParams",
        sol::constructors<ReturningDiscParams()>(),
        "id", &ReturningDiscParams::id,
        "discRadius", &ReturningDiscParams::discRadius,
        "discThickness", &ReturningDiscParams::discThickness,
        "radialSegments", &ReturningDiscParams::radialSegments,
        "spinRateRPM", &ReturningDiscParams::spinRateRPM,
        "boomerangAngleDeg", &ReturningDiscParams::boomerangAngleDeg,
        "returnDelay", &ReturningDiscParams::returnDelay,
        "returnArcHeight", &ReturningDiscParams::returnArcHeight,
        "rimGlowWidth", &ReturningDiscParams::rimGlowWidth,
        "rimGlowColor", &ReturningDiscParams::rimGlowColor,
        "spawnDustOnHit", &ReturningDiscParams::spawnDustOnHit,
        "maxDustParticles", &ReturningDiscParams::maxDustParticles
    );

    lua.new_usertype<DiscAssetBundle>("DiscAssetBundle",
        sol::no_constructor,
        "mesh", &DiscAssetBundle::mesh,
        "shader", &DiscAssetBundle::shader,
        "flightPath", &DiscAssetBundle::flightPath,
        "rimGlowMesh", &DiscAssetBundle::rimGlowMesh,
        "dustImpactFX", &DiscAssetBundle::dustImpactFX
    );

    // API
    lua.set_function("spawn_boomerang",
        [](const BoomerangParams& p) {
            auto factory = BoomerangDiscLuaBindings::factory();
            return factory->generateBoomerangAsync(p).get();
        }
    );
     lua.set_function("spawn_returning_disc",
        [](const ReturningDiscParams& p) {
            auto factory = BoomerangDiscLuaBindings::factory();
            return factory->generateDiscAsync(p).get();
        }
    );
}

void BoomerangDiscLuaBindings::poll_assets(sol::state& lua) {
    // Polling logic can be added here if async versions are created.
}

} // namespace BoomerangDiscs
} // namespace MagiTech
