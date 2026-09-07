#include "AdvancedProjectileLuaBindings.hpp"
#include "core/Log.hpp"
#include <chrono>

namespace MagiTech {
namespace AdvancedProjectiles {

// Static member initialization
std::unique_ptr<AdvancedProjectileManager> AdvancedProjectileLuaBindings::g_manager;
std::vector<std::pair<std::future<MissileBundle>, std::string>> AdvancedProjectileLuaBindings::pendingMissiles;
std::vector<std::pair<std::future<ShardBundle>, std::string>> AdvancedProjectileLuaBindings::pendingGrenades;
std::vector<std::pair<std::future<BeamBundle>, std::string>> AdvancedProjectileLuaBindings::pendingBeams;
std::vector<std::pair<std::future<BoomerangBundle>, std::string>> AdvancedProjectileLuaBindings::pendingBoomerangs;
std::vector<std::pair<std::future<GrapnelBundle>, std::string>> AdvancedProjectileLuaBindings::pendingGrapnels;

void AdvancedProjectileLuaBindings::bind(sol::state& lua) {
    // Initialize manager if not already done
    if (!g_manager) {
        g_manager = std::make_unique<AdvancedProjectileManager>();
        g_manager->initialize(4); // 4 threads for asset generation
    }

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
    
    lua.new_usertype<BeamParams>("BeamParams", sol::constructors<BeamParams()>(),
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
    
    lua.new_usertype<BoomerangParams>("BoomerangParams", sol::constructors<BoomerangParams()>(),
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

    lua.new_usertype<HookParams>("HookParams", sol::constructors<HookParams()>(),
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
    lua.set_function("spawn_guided_missile", [&](const GuidanceParams& guidance, 
                                                 const PropulsionParams& propulsion,
                                                 const TargetParams& target) -> bool {
        if (!validateGuidanceParams(guidance) || !validatePropulsionParams(propulsion) || !validateTargetParams(target)) {
            return false;
        }
        
        try {
            auto factory = g_manager->getMissileFactory();
            pendingMissiles.emplace_back(factory->generateAsync(guidance, propulsion, target), target.targetTag);
            Log::info("Guided missile generation started: {}", target.targetTag);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn guided missile: {}", e.what());
            return false;
        }
    });

    // Shard Grenade Generation
    lua.set_function("spawn_shard_grenade", [&](const GrenadeParams& grenade, 
                                                const ShardParams& shard) -> bool {
        if (!validateGrenadeParams(grenade) || !validateShardParams(shard)) {
            return false;
        }
        
        try {
            auto factory = g_manager->getGrenadeFactory();
            pendingGrenades.emplace_back(factory->generateAsync(grenade, shard), "grenade_" + std::to_string(grenade.shardCount));
            Log::info("Shard grenade generation started with {} shards", grenade.shardCount);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn shard grenade: {}", e.what());
            return false;
        }
    });

    // Arc Beam Generation
    lua.set_function("spawn_arc_beam", [&](const BeamParams& beam, 
                                           const GlowParams& glow) -> bool {
        if (!validateBeamParams(beam) || !validateGlowParams(glow)) {
            return false;
        }
        
        try {
            auto factory = g_manager->getBeamFactory();
            pendingBeams.emplace_back(factory->generateAsync(beam, glow), "beam_" + std::to_string(beam.segmentCount));
            Log::info("Arc beam generation started with {} segments", beam.segmentCount);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn arc beam: {}", e.what());
            return false;
        }
    });

    // Boomerang Generation
    lua.set_function("spawn_boomerang", [&](const BoomerangParams& params) -> bool {
        if (!validateBoomerangParams(params)) {
            return false;
        }
        
        try {
            auto factory = g_manager->getBoomerangFactory();
            pendingBoomerangs.emplace_back(factory->generateAsync(params), "boomerang_" + std::to_string(static_cast<int>(params.returnSpeed)));
            Log::info("Boomerang generation started with return speed: {}", params.returnSpeed);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn boomerang: {}", e.what());
            return false;
        }
    });

    // Grapnel Generation
    lua.set_function("spawn_grapnel", [&](const GrapnelParams& grapnel, 
                                          const HookParams& hook) -> bool {
        if (!validateGrapnelParams(grapnel) || !validateHookParams(hook)) {
            return false;
        }
        
        try {
            auto factory = g_manager->getGrapnelFactory();
            pendingGrapnels.emplace_back(factory->generateAsync(grapnel, hook), "grapnel_" + std::to_string(static_cast<int>(grapnel.maxRange)));
            Log::info("Grapnel generation started with max range: {}", grapnel.maxRange);
            return true;
        } catch (const std::exception& e) {
            Log::error("Failed to spawn grapnel: {}", e.what());
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
    lua.set_function("get_advanced_pending_count", []() -> sol::table {
        sol::table result = lua.create_table();
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
        Log::info("Cleared all pending advanced projectile generations");
    });
}

void AdvancedProjectileLuaBindings::poll_assets(sol::state& lua) {
    // Process completed missiles
    for (auto it = pendingMissiles.begin(); it != pendingMissiles.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Guided missile ready: {} (mesh: {}, guidance: {}, thrust: {})", 
                    it->second, bundle.mesh, bundle.guidanceSim, bundle.thrustSim);
                lua["on_missile_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Missile generation failed for {}: {}", it->second, e.what());
                lua["on_missile_error"](it->second, e.what());
            }
            it = pendingMissiles.erase(it);
        } else { ++it; }
    }
    
    // Process completed grenades
    for (auto it = pendingGrenades.begin(); it != pendingGrenades.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Shard grenade ready: {} (body: {}, shards: {}, timer: {})", 
                    it->second, bundle.bodyMesh, bundle.shards.size(), bundle.timerSim);
                lua["on_grenade_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Grenade generation failed for {}: {}", it->second, e.what());
                lua["on_grenade_error"](it->second, e.what());
            }
            it = pendingGrenades.erase(it);
        } else { ++it; }
    }
    
    // Process completed beams
    for (auto it = pendingBeams.begin(); it != pendingBeams.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Arc beam ready: {} (mesh: {}, wave: {}, shader: {})", 
                    it->second, bundle.beamMesh, bundle.waveSim, bundle.shader);
                lua["on_beam_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Beam generation failed for {}: {}", it->second, e.what());
                lua["on_beam_error"](it->second, e.what());
            }
            it = pendingBeams.erase(it);
        } else { ++it; }
    }
    
    // Process completed boomerangs
    for (auto it = pendingBoomerangs.begin(); it != pendingBoomerangs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Boomerang ready: {} (mesh: {}, flight: {}, audio: {})", 
                    it->second, bundle.mesh, bundle.flightSim, bundle.whooshAudio);
                lua["on_boomerang_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Boomerang generation failed for {}: {}", it->second, e.what());
                lua["on_boomerang_error"](it->second, e.what());
            }
            it = pendingBoomerangs.erase(it);
        } else { ++it; }
    }
    
    // Process completed grapnels
    for (auto it = pendingGrapnels.begin(); it != pendingGrapnels.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("Grapnel ready: {} (hook: {}, tether: {}, launch: {}, retract: {})", 
                    it->second, bundle.hookMesh, bundle.tether, bundle.launchSim, bundle.retractSim);
                lua["on_grapnel_ready"](it->second, bundle);
            } catch (const std::exception& e) {
                Log::error("Grapnel generation failed for {}: {}", it->second, e.what());
                lua["on_grapnel_error"](it->second, e.what());
            }
            it = pendingGrapnels.erase(it);
        } else { ++it; }
    }
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
