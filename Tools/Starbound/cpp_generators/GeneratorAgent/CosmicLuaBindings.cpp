#include "CosmicLuaBindings.hpp"
#include "CosmicFactory.hpp"
#include "projectile/CosmicProjectileGenerators.hpp"
#include "space_object/SpaceObjectGenerators.hpp"
#include <chrono>
#include <future>
#include <map>
#include <memory>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace Cosmic {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingProjectiles;
static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingObjects;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<CosmicProjectileFactory>& projectileSlot() {
    static std::shared_ptr<CosmicProjectileFactory> f;
    return f;
}
std::shared_ptr<SpaceObjectFactory>& spaceObjectSlot() {
    static std::shared_ptr<SpaceObjectFactory> f;
    return f;
}
} // namespace

void CosmicLuaBindings::setProjectileFactory(std::shared_ptr<CosmicProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    projectileSlot() = std::move(factory);
}

std::shared_ptr<CosmicProjectileFactory> CosmicLuaBindings::projectileFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = projectileSlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<CosmicProjectileFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void CosmicLuaBindings::setSpaceObjectFactory(std::shared_ptr<SpaceObjectFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    spaceObjectSlot() = std::move(factory);
}

std::shared_ptr<SpaceObjectFactory> CosmicLuaBindings::spaceObjectFactory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = spaceObjectSlot();
    if (!slot) {
        slot = std::make_shared<SpaceObjectFactory>();
        slot->initialize(32, 2);
    }
    return slot;
}

void CosmicLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<CosmicProjectileParams>("CosmicProjectileParams",
        sol::constructors<CosmicProjectileParams()>(),
        "id", &CosmicProjectileParams::id,
        "type", &CosmicProjectileParams::type,
        "length", &CosmicProjectileParams::length,
        "radius", &CosmicProjectileParams::radius,
        "colorCore", &CosmicProjectileParams::colorCore,
        "colorEdge", &CosmicProjectileParams::colorEdge,
        "noiseIntensity", &CosmicProjectileParams::noiseIntensity,
        "noiseScale", &CosmicProjectileParams::noiseScale,
        "flickerRate", &CosmicProjectileParams::flickerRate,
        "trailType", &CosmicProjectileParams::trailType,
        "trailLength", &CosmicProjectileParams::trailLength,
        "impactEffect", &CosmicProjectileParams::impactEffect,
        "damageType", &CosmicProjectileParams::damageType,
        "homingStrength", &CosmicProjectileParams::homingStrength,
        "fragmentation", &CosmicProjectileParams::fragmentation
    );

    lua.set_function("spawn_cosmic_proj", [](CosmicProjectileParams p) {
        auto factory = CosmicLuaBindings::projectileFactory();
        auto fut = factory->generateAsync(p);
        pendingProjectiles.emplace_back(std::move(fut), p.id);
    });

    lua.new_usertype<SpaceObjectParams>("SpaceObjectParams",
        sol::constructors<SpaceObjectParams()>(),
        "id", &SpaceObjectParams::id,
        "objectType", &SpaceObjectParams::objectType,
        "radius", &SpaceObjectParams::radius,
        "detailLevel", &SpaceObjectParams::detailLevel,
        "colorPalette", &SpaceObjectParams::colorPalette,
        "surfaceRoughness", &SpaceObjectParams::surfaceRoughness,
        "craterDensity", &SpaceObjectParams::craterDensity,
        "ringSystem", &SpaceObjectParams::ringSystem,
        "ringDetail", &SpaceObjectParams::ringDetail,
        "nebulaVolumetrics", &SpaceObjectParams::nebulaVolumetrics,
        "starCount", &SpaceObjectParams::starCount,
        "starBrightness", &SpaceObjectParams::starBrightness
    );

    lua.set_function("spawn_space_obj", [](SpaceObjectParams p) {
        auto factory = CosmicLuaBindings::spaceObjectFactory();
        auto fut = factory->generateAsync(p);
        pendingObjects.emplace_back(std::move(fut), p.id);
    });
}

void CosmicLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingProjectiles.begin(); it != pendingProjectiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Cosmic Projectile ready: " + it->second + " (mesh " + std::to_string(b.mesh) + ")");
            it = pendingProjectiles.erase(it);
        } else {
            ++it;
        }
    }

    for (auto it = pendingObjects.begin(); it != pendingObjects.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto b = it->first.get();
            lua["print"]("Space Object ready: " + it->second + " (mesh " + std::to_string(b.mesh) + ")");
            it = pendingObjects.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace Cosmic
} // namespace MagiTech
