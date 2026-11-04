#pragma once
#include <sol/sol.hpp>
#include <future>
#include <memory>
#include <string>
#include <utility>
#include <vector>
#include "GyroProjectileTypes.hpp"

namespace MagiTech {
namespace GyroProjectiles {

class GyroProjectileFactory;

class GyroProjectileLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);

    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<GyroProjectileFactory> factory);
    static std::shared_ptr<GyroProjectileFactory> factory();

    // Parameter validation (logs the first problem found)
    static bool validateGyroParams(const GyroParams& p);
    static bool validateFlightParams(const FlightParams& p);
    static bool validateTrailParams(const TrailParams& p);
    static bool validateVFXParams(const VFXParams& p);
    static bool validateParticleParams(const ParticleParams& p);
    static bool validateAudioParams(const AudioParams& p);
    static bool validateCollisionParams(const CollisionParams& p);

    // Default parameter sets
    static GyroParams createDefaultGyro();
    static FlightParams createDefaultFlight();
    static TrailParams createDefaultTrail();
    static VFXParams createDefaultVFX();
    static ParticleParams createDefaultParticles();
    static AudioParams createDefaultAudio();
    static CollisionParams createDefaultCollision();

    // Presets (gyro body + matching flight profile)
    static GyroParams createFastSpinner();
    static FlightParams createFastSpinnerFlight();
    static GyroParams createHeavyGyro();
    static FlightParams createHeavyGyroFlight();
    static GyroParams createStealthGyro();
    static FlightParams createStealthGyroFlight();
    static GyroParams createShowyGyro();
    static FlightParams createShowyGyroFlight();

private:
    static std::vector<std::pair<std::future<GyroAssetBundle>, std::string>> pendingGyros;
};

} // namespace GyroProjectiles
} // namespace MagiTech
