#include "DroneMinionLuaBindings.hpp"
#include "DroneMinionFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace DroneMinions {

static std::vector<std::pair<std::future<DroneMinionBundle>, std::string>> pendingDrones;
static std::mutex pendingDronesMutex;

static std::mutex factoryMutex;
static std::shared_ptr<DroneMinionFactory> sharedFactory;

void DroneMinionLuaBindings::setFactory(std::shared_ptr<DroneMinionFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<DroneMinionFactory> DroneMinionLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<DroneMinionFactory>();
        sharedFactory->initialize(64, 4);
    }
    return sharedFactory;
}

void DroneMinionLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<DroneMinionParams>("DroneMinionParams",
        sol::constructors<DroneMinionParams()>(),
        "id", &DroneMinionParams::id,
        "bodyRadius", &DroneMinionParams::bodyRadius,
        "bodyHeight", &DroneMinionParams::bodyHeight,
        "bodyDetail", &DroneMinionParams::bodyDetail,
        "rotorCount", &DroneMinionParams::rotorCount,
        "rotorRadius", &DroneMinionParams::rotorRadius,
        "rotorThickness", &DroneMinionParams::rotorThickness,
        "hoverHeight", &DroneMinionParams::hoverHeight,
        "bodyColorPrimary", &DroneMinionParams::bodyColorPrimary,
        "bodyColorSecondary", &DroneMinionParams::bodyColorSecondary,
        "ledColor", &DroneMinionParams::ledColor,
        "enableSensorArray", &DroneMinionParams::enableSensorArray,
        "sensorCount", &DroneMinionParams::sensorCount,
        "enableWeaponMount", &DroneMinionParams::enableWeaponMount,
        "weaponCount", &DroneMinionParams::weaponCount,
        "weaponLength", &DroneMinionParams::weaponLength,
        "enableThrusterFX", &DroneMinionParams::enableThrusterFX,
        "thrusterColor", &DroneMinionParams::thrusterColor,
        "thrusterLifetime", &DroneMinionParams::thrusterLifetime,
        "sparkCount", &DroneMinionParams::sparkCount,
        "sparkColor", &DroneMinionParams::sparkColor,
        "maxSpeed", &DroneMinionParams::maxSpeed,
        "acceleration", &DroneMinionParams::acceleration,
        "turnRateDeg", &DroneMinionParams::turnRateDeg,
        "mass", &DroneMinionParams::mass,
        "detectionRange", &DroneMinionParams::detectionRange,
        "attackRange", &DroneMinionParams::attackRange,
        "retreatThreshold", &DroneMinionParams::retreatThreshold,
        "idlePatrolRadius", &DroneMinionParams::idlePatrolRadius,
        "dynamicLOD", &DroneMinionParams::dynamicLOD,
        "maxLODLevel", &DroneMinionParams::maxLODLevel
    );

    lua.new_usertype<DroneMinionBundle>("DroneMinionBundle",
        sol::no_constructor,
        "bodyMesh", &DroneMinionBundle::bodyMesh,
        "rotorMesh", &DroneMinionBundle::rotorMesh,
        "bodyTexture", &DroneMinionBundle::bodyTexture,
        "bodyShader", &DroneMinionBundle::bodyShader,
        "thrusterFX", &DroneMinionBundle::thrusterFX,
        "jointSparks", &DroneMinionBundle::jointSparks,
        "flightPhysics", &DroneMinionBundle::flightPhysics,
        "aiController", &DroneMinionBundle::aiController,
        "icon", &DroneMinionBundle::icon
    );

    lua.set_function("spawn_drone_minion",
        [](const DroneMinionParams& p) {
            return factory()->generateAsync(p).get();
        }
    );

    lua.set_function("spawn_drone_minion_async",
        [](const DroneMinionParams& p) {
            auto future = factory()->generateAsync(p);
            std::lock_guard<std::mutex> lock(pendingDronesMutex);
            pendingDrones.emplace_back(std::move(future), p.id);
        }
    );
}

void DroneMinionLuaBindings::poll_assets(sol::state& lua) {
    std::lock_guard<std::mutex> lock(pendingDronesMutex);
    for (auto it = pendingDrones.begin(); it != pendingDrones.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Drone Minion asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("DroneMinions", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingDrones.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace DroneMinions
} // namespace MagiTech
