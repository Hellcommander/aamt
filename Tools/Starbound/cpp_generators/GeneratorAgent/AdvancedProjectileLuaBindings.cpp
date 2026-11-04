#include "AdvancedProjectileLuaBindings.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <exception>
#include <format>
#include <mutex>
#include <optional>

namespace MagiTech {
namespace AdvancedProjectiles {

// Static member initialization
std::vector<std::pair<std::future<MissileBundle>, std::string>> AdvancedProjectileLuaBindings::pendingMissiles;
std::vector<std::pair<std::future<ShardBundle>, std::string>> AdvancedProjectileLuaBindings::pendingGrenades;
std::vector<std::pair<std::future<BeamBundle>, std::string>> AdvancedProjectileLuaBindings::pendingBeams;
std::vector<std::pair<std::future<BoomerangBundle>, std::string>> AdvancedProjectileLuaBindings::pendingBoomerangs;
std::vector<std::pair<std::future<GrapnelBundle>, std::string>> AdvancedProjectileLuaBindings::pendingGrapnels;

namespace {

constexpr const char* kLogCategory = "AdvancedProjectile";
constexpr size_t kDefaultGeneratorThreads = 4;

std::mutex& managerMutex() {
    static std::mutex m;
    return m;
}

std::shared_ptr<AdvancedProjectileManager>& managerSlot() {
    static std::shared_ptr<AdvancedProjectileManager> manager;
    return manager;
}

/** Calls an optional Lua callback; a missing callback is skipped and Lua errors are logged, not thrown. */
template <typename... Args>
void invokeLuaCallback(sol::state& lua, const char* name, Args&&... args) {
    sol::protected_function callback = lua[name];
    if (!callback.valid()) return;
    sol::protected_function_result result = callback(std::forward<Args>(args)...);
    if (!result.valid()) {
        sol::error err = result;
        Log::error(kLogCategory, "Lua callback {} failed: {}", name, err.what());
    }
}

/**
 * Moves every finished generation out of `pending` first and only then runs
 * the Lua callbacks, so a callback that spawns a new projectile (and appends
 * to `pending`) cannot invalidate the iteration.
 */
template <typename Bundle, typename Describe>
void drainCompleted(sol::state& lua,
                    std::vector<std::pair<std::future<Bundle>, std::string>>& pending,
                    const char* kind,
                    const char* readyCallback,
                    const char* errorCallback,
                    Describe describe) {
    struct Completed {
        std::string tag;
        std::optional<Bundle> bundle;
        std::string error;
    };

    std::vector<Completed> completed;
    for (auto it = pending.begin(); it != pending.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) != std::future_status::ready) {
            ++it;
            continue;
        }
        Completed done;
        done.tag = std::move(it->second);
        try {
            done.bundle = it->first.get();
        } catch (const std::exception& e) {
            done.error = e.what();
        }
        completed.push_back(std::move(done));
        it = pending.erase(it);
    }

    for (auto& done : completed) {
        if (done.bundle) {
            Log::info(kLogCategory, "{} ready: {} ({})", kind, done.tag, describe(*done.bundle));
            invokeLuaCallback(lua, readyCallback, done.tag, *done.bundle);
        } else {
            Log::error(kLogCategory, "{} generation failed for {}: {}", kind, done.tag, done.error);
            invokeLuaCallback(lua, errorCallback, done.tag, done.error);
        }
    }
}

} // namespace

void AdvancedProjectileLuaBindings::setManager(std::shared_ptr<AdvancedProjectileManager> manager) {
    std::lock_guard<std::mutex> lock(managerMutex());
    managerSlot() = std::move(manager);
}

std::shared_ptr<AdvancedProjectileManager> AdvancedProjectileLuaBindings::manager() {
    std::lock_guard<std::mutex> lock(managerMutex());
    auto& slot = managerSlot();
    if (!slot) {
        // No manager injected by the host: create a default one.
        slot = std::make_shared<AdvancedProjectileManager>();
        slot->initialize(kDefaultGeneratorThreads);
    }
    return slot;
}

void AdvancedProjectileLuaBindings::bind(sol::state& lua) {
    // Make sure the generator threads are running before Lua can spawn anything
    manager();

    // ============================================================================
    // GUIDED MISSILE BINDINGS
    // ============================================================================
    
    lua.new_usertype<GuidanceParams>("GuidanceParams", sol::constructors<GuidanceParams()>(),
        "enableLockOn", &GuidanceParams::enableLockOn,
        "lockOnDelay", &GuidanceParams::lockOnDelay,
        "turnRateDegPerSec", &GuidanceParams::turnRateDegPerSec,
        "proximityFuseDist", &GuidanceParams::proximityFuseDist,
        "validate", [](GuidanceParams& p) -> bool { return validateGuidanceParams(p); });

    lua.new_usertype<PropulsionParams>("PropulsionParams", sol::constructors<PropulsionParams()>(),
        "maxThrust", &PropulsionParams::maxThrust,
        "fuelCapacity", &PropulsionParams::fuelCapacity,
        "dragCoefficient", &PropulsionParams::dragCoefficient,
        "validate", [](PropulsionParams& p) -> bool { return validatePropulsionParams(p); });

    lua.new_usertype<TargetParams>("TargetParams", sol::constructors<TargetParams()>(),
        "targetTag", &TargetParams::targetTag,
        "homingRadius", &TargetParams::homingRadius,
        "targetPosition", &TargetParams::targetPosition,
        "validate", [](TargetParams& p) -> bool { return validateTargetParams(p); });

    lua.new_usertype<MissileBundle>("MissileBundle", sol::no_constructor,
        "mesh", &MissileBundle::mesh,
        "vfxShader", &MissileBundle::vfxShader,
        "particleSys", &MissileBundle::particleSys,
        "humAudio", &MissileBundle::humAudio,
        "guidanceSim", &MissileBundle::guidanceSim,
        "thrustSim", &MissileBundle::thrustSim);

    // ============================================================================
    // SHARD-BURST GRENADE BINDINGS
    // ============================================================================
    
    lua.new_usertype<GrenadeParams>("GrenadeParams", sol::constructors<GrenadeParams()>(),
        "fuseTime", &GrenadeParams::fuseTime,
        "blastRadius", &GrenadeParams::blastRadius,
        "shardCount", &GrenadeParams::shardCount,
        "spreadAngleDeg", &GrenadeParams::spreadAngleDeg,
        "randomizeCount", &GrenadeParams::randomizeCount,
        "validate", [](GrenadeParams& p) -> bool { return validateGrenadeParams(p); });

    lua.new_usertype<ShardParams>("ShardParams", sol::constructors<ShardParams()>(),
        "meshType", &ShardParams::meshType,
        "materialType", &ShardParams::materialType,
        "minVelocity", &ShardParams::minVelocity,
        "maxVelocity", &ShardParams::maxVelocity,
        "lifeTime", &ShardParams::lifeTime,
        "validate", [](ShardParams& p) -> bool { return validateShardParams(p); });

    lua.new_usertype<ShardBundle>("ShardBundle", sol::no_constructor,
        "bodyMesh", &ShardBundle::bodyMesh,
        "shards", &ShardBundle::shards,
        "timerSim", &ShardBundle::timerSim,
        "explosionVFX", &ShardBundle::explosionVFX,
        "explosionAudio", &ShardBundle::explosionAudio);

    // ============================================================================
    // ARC BEAM BINDINGS
    // ============================================================================
    
    lua.new_usertype<BeamParams>("AdvancedBeamParams", sol::constructors<BeamParams()>(),
        "duration", &BeamParams::duration,
        "maxRange", &BeamParams::maxRange,
        "thickness", &BeamParams::thickness,
        "branchProbability", &BeamParams::branchProbability,
        "segmentCount", &BeamParams::segmentCount,
        "validate", [](BeamParams& p) -> bool { return validateBeamParams(p); });

    lua.new_usertype<GlowParams>("GlowParams", sol::constructors<GlowParams()>(),
        "innerColor", &GlowParams::innerColor,
        "outerColor", &GlowParams::outerColor,
        "pulseFrequency", &GlowParams::pulseFrequency,
        "intensity", &GlowParams::intensity,
        "validate", [](GlowParams& p) -> bool { return validateGlowParams(p); });

    lua.new_usertype<BeamBundle>("BeamBundle", sol::no_constructor,
        "beamMesh", &BeamBundle::beamMesh,
        "waveSim", &BeamBundle::waveSim,
        "shader", &BeamBundle::shader,
        "crackleAudio", &BeamBundle::crackleAudio);

    // ============================================================================
    // BOOMERANG BINDINGS
    // ============================================================================
    
    lua.new_usertype<BoomerangParams>("AdvancedBoomerangParams", sol::constructors<BoomerangParams()>(),
        "returnDelay", &BoomerangParams::returnDelay,
        "returnSpeed", &BoomerangParams::returnSpeed,
        "liftCoefficient", &BoomerangParams::liftCoefficient,
        "dragCoefficient", &BoomerangParams::dragCoefficient,
        "spinRateRPM", &BoomerangParams::spinRateRPM,
        "validate", [](BoomerangParams& p) -> bool { return validateBoomerangParams(p); });

    lua.new_usertype<BoomerangBundle>("BoomerangBundle", sol::no_constructor,
        "mesh", &BoomerangBundle::mesh,
        "flightSim", &BoomerangBundle::flightSim,
        "whooshAudio", &BoomerangBundle::whooshAudio,
        "trailVFX", &BoomerangBundle::trailVFX);

    // ============================================================================
    // GRAPNEL BINDINGS
    // ============================================================================
    
    lua.new_usertype<GrapnelParams>("GrapnelParams", sol::constructors<GrapnelParams()>(),
        "maxRange", &GrapnelParams::maxRange,
        "launchSpeed", &GrapnelParams::launchSpeed,
        "retractionSpeed", &GrapnelParams::retractionSpeed,
        "enableElasticity", &GrapnelParams::enableElasticity,
        "springConstant", &GrapnelParams::springConstant,
        "validate", [](GrapnelParams& p) -> bool { return validateGrapnelParams(p); });

    lua.new_usertype<HookParams>("AdvancedHookParams", sol::constructors<HookParams()>(),
        "meshType", &HookParams::meshType,
        "materialType", &HookParams::materialType,
        "autoDetach", &HookParams::autoDetach,
        "hookStrength", &HookParams::hookStrength,
        "validate", [](HookParams& p) -> bool { return validateHookParams(p); });

    lua.new_usertype<GrapnelBundle>("GrapnelBundle", sol::no_constructor,
        "hookMesh", &GrapnelBundle::hookMesh,
        "tether", &GrapnelBundle::tether,
        "launchSim", &GrapnelBundle::launchSim,
        "retractSim", &GrapnelBundle::retractSim,
        "reelAudio", &GrapnelBundle::reelAudio);

    // ============================================================================
    // GENERATION FUNCTIONS
    // ============================================================================
    
    // Guided Missile Generation
    lua.set_function("spawn_guided_missile", [](const GuidanceParams& guidance,
                                                const PropulsionParams& propulsion,
                                                const TargetParams& target) -> bool {
        if (!validateGuidanceParams(guidance) || !validatePropulsionParams(propulsion) || !validateTargetParams(target)) {
            return false;
        }

        try {
            auto mgr = manager();
            pendingMissiles.emplace_back(mgr->getMissileFactory()->generateAsync(guidance, propulsion, target), target.targetTag);
            Log::info(kLogCategory, "Guided missile generation started: {}", target.targetTag);
            return true;
        } catch (const std::exception& e) {
            Log::error(kLogCategory, "Failed to spawn guided missile: {}", e.what());
            return false;
        }
    });

    // Shard Grenade Generation
    lua.set_function("spawn_shard_grenade", [](const GrenadeParams& grenade,
                                               const ShardParams& shard) -> bool {
        if (!validateGrenadeParams(grenade) || !validateShardParams(shard)) {
            return false;
        }

        try {
            auto mgr = manager();
            pendingGrenades.emplace_back(mgr->getGrenadeFactory()->generateAsync(grenade, shard), "grenade_" + std::to_string(grenade.shardCount));
            Log::info(kLogCategory, "Shard grenade generation started with {} shards", grenade.shardCount);
            return true;
        } catch (const std::exception& e) {
            Log::error(kLogCategory, "Failed to spawn shard grenade: {}", e.what());
            return false;
        }
    });

    // Arc Beam Generation
    lua.set_function("spawn_arc_beam", [](const BeamParams& beam,
                                          const GlowParams& glow) -> bool {
        if (!validateBeamParams(beam) || !validateGlowParams(glow)) {
            return false;
        }

        try {
            auto mgr = manager();
            pendingBeams.emplace_back(mgr->getBeamFactory()->generateAsync(beam, glow), "beam_" + std::to_string(beam.segmentCount));
            Log::info(kLogCategory, "Arc beam generation started with {} segments", beam.segmentCount);
            return true;
        } catch (const std::exception& e) {
            Log::error(kLogCategory, "Failed to spawn arc beam: {}", e.what());
            return false;
        }
    });

    // Boomerang Generation
    lua.set_function("spawn_boomerang", [](const BoomerangParams& params) -> bool {
        if (!validateBoomerangParams(params)) {
            return false;
        }

        try {
            auto mgr = manager();
            pendingBoomerangs.emplace_back(mgr->getBoomerangFactory()->generateAsync(params), "boomerang_" + std::to_string(static_cast<int>(params.returnSpeed)));
            Log::info(kLogCategory, "Boomerang generation started with return speed: {}", params.returnSpeed);
            return true;
        } catch (const std::exception& e) {
            Log::error(kLogCategory, "Failed to spawn boomerang: {}", e.what());
            return false;
        }
    });

    // Grapnel Generation
    lua.set_function("spawn_grapnel", [](const GrapnelParams& grapnel,
                                         const HookParams& hook) -> bool {
        if (!validateGrapnelParams(grapnel) || !validateHookParams(hook)) {
            return false;
        }

        try {
            auto mgr = manager();
            pendingGrapnels.emplace_back(mgr->getGrapnelFactory()->generateAsync(grapnel, hook), "grapnel_" + std::to_string(static_cast<int>(grapnel.maxRange)));
            Log::info(kLogCategory, "Grapnel generation started with max range: {}", grapnel.maxRange);
            return true;
        } catch (const std::exception& e) {
            Log::error(kLogCategory, "Failed to spawn grapnel: {}", e.what());
            return false;
        }
    });

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================
    
    // Default parameter creators
    lua.set_function("create_default_guidance", &createDefaultGuidance);
    lua.set_function("create_default_propulsion", &createDefaultPropulsion);
    lua.set_function("create_default_target", &createDefaultTarget);
    lua.set_function("create_default_grenade", &createDefaultGrenade);
    lua.set_function("create_default_shard", &createDefaultShard);
    lua.set_function("create_default_beam", &createDefaultBeam);
    lua.set_function("create_default_glow", &createDefaultGlow);
    lua.set_function("create_default_boomerang", &createDefaultBoomerang);
    lua.set_function("create_default_grapnel", &createDefaultGrapnel);
    lua.set_function("create_default_hook", &createDefaultHook);

    // Status and management functions
    lua.set_function("get_advanced_pending_count", [](sol::this_state ts) -> sol::table {
        sol::state_view state(ts);
        sol::table result = state.create_table();
        result["missiles"] = pendingMissiles.size();
        result["grenades"] = pendingGrenades.size();
        result["beams"] = pendingBeams.size();
        result["boomerangs"] = pendingBoomerangs.size();
        result["grapnels"] = pendingGrapnels.size();
        return result;
    });

    lua.set_function("clear_advanced_pending", []() {
        pendingMissiles.clear();
        pendingGrenades.clear();
        pendingBeams.clear();
        pendingBoomerangs.clear();
        pendingGrapnels.clear();
        Log::info(kLogCategory, "Cleared all pending advanced projectile generations");
    });
}

void AdvancedProjectileLuaBindings::poll_assets(sol::state& lua) {
    // Process completed missiles
    drainCompleted(lua, pendingMissiles, "Guided missile", "on_missile_ready", "on_missile_error",
        [](const MissileBundle& b) {
            return std::format("mesh: {}, guidance: {}, thrust: {}", b.mesh, b.guidanceSim, b.thrustSim);
        });

    // Process completed grenades
    drainCompleted(lua, pendingGrenades, "Shard grenade", "on_grenade_ready", "on_grenade_error",
        [](const ShardBundle& b) {
            return std::format("body: {}, shards: {}, timer: {}", b.bodyMesh, b.shards.size(), b.timerSim);
        });

    // Process completed beams
    drainCompleted(lua, pendingBeams, "Arc beam", "on_beam_ready", "on_beam_error",
        [](const BeamBundle& b) {
            return std::format("mesh: {}, wave: {}, shader: {}", b.beamMesh, b.waveSim, b.shader);
        });

    // Process completed boomerangs
    drainCompleted(lua, pendingBoomerangs, "Boomerang", "on_boomerang_ready", "on_boomerang_error",
        [](const BoomerangBundle& b) {
            return std::format("mesh: {}, flight: {}, audio: {}", b.mesh, b.flightSim, b.whooshAudio);
        });

    // Process completed grapnels
    drainCompleted(lua, pendingGrapnels, "Grapnel", "on_grapnel_ready", "on_grapnel_error",
        [](const GrapnelBundle& b) {
            return std::format("hook: {}, tether: {}, launch: {}, retract: {}",
                               b.hookMesh, b.tether, b.launchSim, b.retractSim);
        });
}

// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================

bool AdvancedProjectileLuaBindings::validateGuidanceParams(const GuidanceParams& p) {
    if (p.lockOnDelay < 0.0f || p.lockOnDelay > 10.0f) {
        Log::error("GuidanceParams: lockOnDelay must be between 0.0 and 10.0");
        return false;
    }
    if (p.turnRateDegPerSec <= 0.0f || p.turnRateDegPerSec > 720.0f) {
        Log::error("GuidanceParams: turnRateDegPerSec must be between 1.0 and 720.0");
        return false;
    }
    if (p.proximityFuseDist <= 0.0f || p.proximityFuseDist > 50.0f) {
        Log::error("GuidanceParams: proximityFuseDist must be between 0.1 and 50.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validatePropulsionParams(const PropulsionParams& p) {
    if (p.maxThrust <= 0.0f || p.maxThrust > 2000.0f) {
        Log::error("PropulsionParams: maxThrust must be between 10.0 and 2000.0");
        return false;
    }
    if (p.fuelCapacity <= 0.0f || p.fuelCapacity > 30.0f) {
        Log::error("PropulsionParams: fuelCapacity must be between 0.1 and 30.0");
        return false;
    }
    if (p.dragCoefficient < 0.0f || p.dragCoefficient > 2.0f) {
        Log::error("PropulsionParams: dragCoefficient must be between 0.0 and 2.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateTargetParams(const TargetParams& p) {
    if (p.targetTag.empty()) {
        Log::error("TargetParams: targetTag cannot be empty");
        return false;
    }
    if (p.homingRadius <= 0.0f || p.homingRadius > 200.0f) {
        Log::error("TargetParams: homingRadius must be between 1.0 and 200.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateGrenadeParams(const GrenadeParams& p) {
    if (p.fuseTime <= 0.0f || p.fuseTime > 30.0f) {
        Log::error("GrenadeParams: fuseTime must be between 0.1 and 30.0");
        return false;
    }
    if (p.blastRadius <= 0.0f || p.blastRadius > 50.0f) {
        Log::error("GrenadeParams: blastRadius must be between 0.5 and 50.0");
        return false;
    }
    if (p.shardCount <= 0 || p.shardCount > 100) {
        Log::error("GrenadeParams: shardCount must be between 1 and 100");
        return false;
    }
    if (p.spreadAngleDeg <= 0.0f || p.spreadAngleDeg > 180.0f) {
        Log::error("GrenadeParams: spreadAngleDeg must be between 1.0 and 180.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateShardParams(const ShardParams& p) {
    if (p.minVelocity <= 0.0f || p.minVelocity > 100.0f) {
        Log::error("ShardParams: minVelocity must be between 0.1 and 100.0");
        return false;
    }
    if (p.maxVelocity <= p.minVelocity || p.maxVelocity > 200.0f) {
        Log::error("ShardParams: maxVelocity must be greater than minVelocity and less than 200.0");
        return false;
    }
    if (p.lifeTime <= 0.0f || p.lifeTime > 10.0f) {
        Log::error("ShardParams: lifeTime must be between 0.1 and 10.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateBeamParams(const BeamParams& p) {
    if (p.duration <= 0.0f || p.duration > 60.0f) {
        Log::error("BeamParams: duration must be between 0.1 and 60.0");
        return false;
    }
    if (p.maxRange <= 0.0f || p.maxRange > 100.0f) {
        Log::error("BeamParams: maxRange must be between 0.5 and 100.0");
        return false;
    }
    if (p.thickness <= 0.0f || p.thickness > 2.0f) {
        Log::error("BeamParams: thickness must be between 0.01 and 2.0");
        return false;
    }
    if (p.branchProbability < 0.0f || p.branchProbability > 1.0f) {
        Log::error("BeamParams: branchProbability must be between 0.0 and 1.0");
        return false;
    }
    if (p.segmentCount <= 0 || p.segmentCount > 500) {
        Log::error("BeamParams: segmentCount must be between 1 and 500");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateGlowParams(const GlowParams& p) {
    if (p.pulseFrequency < 0.0f || p.pulseFrequency > 100.0f) {
        Log::error("GlowParams: pulseFrequency must be between 0.0 and 100.0");
        return false;
    }
    if (p.intensity <= 0.0f || p.intensity > 10.0f) {
        Log::error("GlowParams: intensity must be between 0.1 and 10.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateBoomerangParams(const BoomerangParams& p) {
    if (p.returnDelay < 0.0f || p.returnDelay > 10.0f) {
        Log::error("BoomerangParams: returnDelay must be between 0.0 and 10.0");
        return false;
    }
    if (p.returnSpeed <= 0.0f || p.returnSpeed > 50.0f) {
        Log::error("BoomerangParams: returnSpeed must be between 1.0 and 50.0");
        return false;
    }
    if (p.liftCoefficient < 0.0f || p.liftCoefficient > 2.0f) {
        Log::error("BoomerangParams: liftCoefficient must be between 0.0 and 2.0");
        return false;
    }
    if (p.dragCoefficient < 0.0f || p.dragCoefficient > 2.0f) {
        Log::error("BoomerangParams: dragCoefficient must be between 0.0 and 2.0");
        return false;
    }
    if (p.spinRateRPM <= 0.0f || p.spinRateRPM > 5000.0f) {
        Log::error("BoomerangParams: spinRateRPM must be between 1.0 and 5000.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateGrapnelParams(const GrapnelParams& p) {
    if (p.maxRange <= 0.0f || p.maxRange > 100.0f) {
        Log::error("GrapnelParams: maxRange must be between 1.0 and 100.0");
        return false;
    }
    if (p.launchSpeed <= 0.0f || p.launchSpeed > 100.0f) {
        Log::error("GrapnelParams: launchSpeed must be between 1.0 and 100.0");
        return false;
    }
    if (p.retractionSpeed <= 0.0f || p.retractionSpeed > 50.0f) {
        Log::error("GrapnelParams: retractionSpeed must be between 1.0 and 50.0");
        return false;
    }
    if (p.springConstant <= 0.0f || p.springConstant > 1000.0f) {
        Log::error("GrapnelParams: springConstant must be between 1.0 and 1000.0");
        return false;
    }
    return true;
}

bool AdvancedProjectileLuaBindings::validateHookParams(const HookParams& p) {
    if (p.hookStrength <= 0.0f || p.hookStrength > 10000.0f) {
        Log::error("HookParams: hookStrength must be between 1.0 and 10000.0");
        return false;
    }
    return true;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

GuidanceParams AdvancedProjectileLuaBindings::createDefaultGuidance() {
    GuidanceParams p;
    p.enableLockOn = true;
    p.lockOnDelay = 0.5f;
    p.turnRateDegPerSec = 180.0f;
    p.proximityFuseDist = 2.0f;
    return p;
}

PropulsionParams AdvancedProjectileLuaBindings::createDefaultPropulsion() {
    PropulsionParams p;
    p.maxThrust = 500.0f;
    p.fuelCapacity = 5.0f;
    p.dragCoefficient = 0.3f;
    return p;
}

TargetParams AdvancedProjectileLuaBindings::createDefaultTarget() {
    TargetParams p;
    p.targetTag = "enemy";
    p.homingRadius = 50.0f;
    p.targetPosition = glm::vec3(0, 0, 0);
    return p;
}

GrenadeParams AdvancedProjectileLuaBindings::createDefaultGrenade() {
    GrenadeParams p;
    p.fuseTime = 3.0f;
    p.blastRadius = 8.0f;
    p.shardCount = 12;
    p.spreadAngleDeg = 45.0f;
    p.randomizeCount = true;
    return p;
}

ShardParams AdvancedProjectileLuaBindings::createDefaultShard() {
    ShardParams p;
    p.meshType = "spike";
    p.materialType = "metal";
    p.minVelocity = 10.0f;
    p.maxVelocity = 25.0f;
    p.lifeTime = 2.0f;
    return p;
}

BeamParams AdvancedProjectileLuaBindings::createDefaultBeam() {
    BeamParams p;
    p.duration = 2.0f;
    p.maxRange = 20.0f;
    p.thickness = 0.1f;
    p.branchProbability = 0.3f;
    p.segmentCount = 50;
    return p;
}

GlowParams AdvancedProjectileLuaBindings::createDefaultGlow() {
    GlowParams p;
    p.innerColor = glm::vec3(0.8f, 0.9f, 1.0f);
    p.outerColor = glm::vec3(0.2f, 0.4f, 0.8f);
    p.pulseFrequency = 10.0f;
    p.intensity = 1.0f;
    return p;
}

BoomerangParams AdvancedProjectileLuaBindings::createDefaultBoomerang() {
    BoomerangParams p;
    p.returnDelay = 1.5f;
    p.returnSpeed = 15.0f;
    p.liftCoefficient = 0.8f;
    p.dragCoefficient = 0.4f;
    p.spinRateRPM = 1200.0f;
    return p;
}

GrapnelParams AdvancedProjectileLuaBindings::createDefaultGrapnel() {
    GrapnelParams p;
    p.maxRange = 30.0f;
    p.launchSpeed = 25.0f;
    p.retractionSpeed = 8.0f;
    p.enableElasticity = true;
    p.springConstant = 100.0f;
    return p;
}

HookParams AdvancedProjectileLuaBindings::createDefaultHook() {
    HookParams p;
    p.meshType = "hook";
    p.materialType = "metal";
    p.autoDetach = false;
    p.hookStrength = 1000.0f;
    return p;
}

} // namespace AdvancedProjectiles
} // namespace MagiTech 
