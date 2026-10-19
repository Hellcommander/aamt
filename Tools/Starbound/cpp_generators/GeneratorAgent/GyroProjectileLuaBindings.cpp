#include "GyroProjectileLuaBindings.hpp"
#include "GyroProjectileFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>

namespace MagiTech {
namespace GyroProjectiles {

// Static member initialization
std::vector<std::pair<std::future<GyroAssetBundle>, std::string>> GyroProjectileLuaBindings::pendingGyros;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<GyroProjectileFactory>& factorySlot() {
    static std::shared_ptr<GyroProjectileFactory> f;
    return f;
}
} // namespace

void GyroProjectileLuaBindings::setFactory(std::shared_ptr<GyroProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<GyroProjectileFactory> GyroProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<GyroProjectileFactory>();
        slot->initialize(100, 4); // 100 cache entries, 4 threads
    }
    return slot;
}

void GyroProjectileLuaBindings::bind(sol::state& lua) {
    // ============================================================================
    // ENUMS
    // ============================================================================

    lua.new_enum("GyroShape",
        "Disc", GyroShape::Disc,
        "Ring", GyroShape::Ring,
        "Spindle", GyroShape::Spindle,
        "CustomMesh", GyroShape::CustomMesh);
    lua.new_enum("GyroTrailType",
        "Ribbon", TrailType::Ribbon,
        "Streaks", TrailType::Streaks,
        "Particles", TrailType::Particles);
    lua.new_enum("GyroParticleStyle",
        "Sparks", ParticleStyle::Sparks,
        "Smoke", ParticleStyle::Smoke,
        "Sparkle", ParticleStyle::Sparkle);
    lua.new_enum("GyroFlickerMode",
        "None", FlickerMode::None,
        "Sinusoidal", FlickerMode::Sinusoidal,
        "NoiseDriven", FlickerMode::NoiseDriven);

    // ============================================================================
    // GYRO PARAMETERS BINDINGS
    // ============================================================================

    lua.new_usertype<GyroParams>("GyroParams", sol::constructors<GyroParams()>(),
        "id", &GyroParams::id,
        "shape", &GyroParams::shape,
        "radius", &GyroParams::radius,
        "thickness", &GyroParams::thickness,
        "hollow", &GyroParams::hollow,
        "dynamicTess", &GyroParams::dynamicTess,
        "validate", [](GyroParams& p) -> bool { return validateGyroParams(p); });

    lua.new_usertype<FlightParams>("FlightParams", sol::constructors<FlightParams()>(),
        "initialSpeed", &FlightParams::initialSpeed,
        "spinRateRPM", &FlightParams::spinRateRPM,
        "precessionRateDeg", &FlightParams::precessionRateDeg,
        "stabilityFactor", &FlightParams::stabilityFactor,
        "gravityEnabled", &FlightParams::gravityEnabled,
        "gravityScale", &FlightParams::gravityScale,
        "validate", [](FlightParams& p) -> bool { return validateFlightParams(p); });

    lua.new_usertype<TrailParams>("GyroTrailParams", sol::constructors<TrailParams()>(),
        "enableTrail", &TrailParams::enableTrail,
        "type", &TrailParams::type,
        "length", &TrailParams::length,
        "width", &TrailParams::width,
        "headColor", &TrailParams::headColor,
        "tailColor", &TrailParams::tailColor,
        "uvScrollSpeed", &TrailParams::uvScrollSpeed,
        "validate", [](TrailParams& p) -> bool { return validateTrailParams(p); });

    lua.new_usertype<VFXParams>("GyroVFXParams", sol::constructors<VFXParams()>(),
        "shaderTemplate", &VFXParams::shaderTemplate,
        "defines", &VFXParams::defines,
        "glowIntensity", &VFXParams::glowIntensity,
        "flickerSpeed", &VFXParams::flickerSpeed,
        "flickerMode", &VFXParams::flickerMode,
        "validate", [](VFXParams& p) -> bool { return validateVFXParams(p); });

    lua.new_usertype<ParticleParams>("GyroParticleParams", sol::constructors<ParticleParams()>(),
        "enableParticles", &ParticleParams::enableParticles,
        "style", &ParticleParams::style,
        "count", &ParticleParams::count,
        "spawnRate", &ParticleParams::spawnRate,
        "lifeTime", &ParticleParams::lifeTime,
        "velocityMin", &ParticleParams::velocityMin,
        "velocityMax", &ParticleParams::velocityMax,
        "validate", [](ParticleParams& p) -> bool { return validateParticleParams(p); });

    lua.new_usertype<AudioParams>("GyroAudioParams", sol::constructors<AudioParams()>(),
        "playOnLaunch", &AudioParams::playOnLaunch,
        "humFile", &AudioParams::humFile,
        "impactFile", &AudioParams::impactFile,
        "volume", &AudioParams::volume,
        "pitchVariance", &AudioParams::pitchVariance,
        "validate", [](AudioParams& p) -> bool { return validateAudioParams(p); });

    lua.new_usertype<CollisionParams>("GyroCollisionParams", sol::constructors<CollisionParams()>(),
        "enableCollider", &CollisionParams::enableCollider,
        "meshCollider", &CollisionParams::meshCollider,
        "radius", &CollisionParams::radius,
        "triggerOnly", &CollisionParams::triggerOnly,
        "enableCCD", &CollisionParams::enableCCD,
        "validate", [](CollisionParams& p) -> bool { return validateCollisionParams(p); });

    lua.new_usertype<GyroAssetBundle>("GyroAssetBundle", sol::no_constructor,
        "mesh", &GyroAssetBundle::mesh,
        "flightSim", &GyroAssetBundle::flightSim,
        "trailMesh", &GyroAssetBundle::trailMesh,
        "vfxShader", &GyroAssetBundle::vfxShader,
        "particleSys", &GyroAssetBundle::particleSys,
        "humAudio", &GyroAssetBundle::humAudio,
        "impactAudio", &GyroAssetBundle::impactAudio,
        "collider", &GyroAssetBundle::collider);

    // ============================================================================
    // GENERATION FUNCTION
    // ============================================================================
    
    lua.set_function("spawn_gyro", [](const GyroParams& g,
                                       const FlightParams& f,
                                       const TrailParams& t,
                                       const VFXParams& v,
                                       const ParticleParams& p,
                                       const AudioParams& a,
                                       const CollisionParams& c) -> bool {
        if (!validateGyroParams(g) || !validateFlightParams(f) || !validateTrailParams(t) ||
            !validateVFXParams(v) || !validateParticleParams(p) || !validateAudioParams(a) ||
            !validateCollisionParams(c)) {
            return false;
        }
        
        try {
            pendingGyros.emplace_back(factory()->generateAsync(g, f, t, v, p, a, c), g.id);
            Log::info("GyroProjectile", "Gyro projectile generation started: {}", g.id);
            return true;
        } catch (const std::exception& e) {
            Log::error("GyroProjectile", "Failed to spawn gyro projectile: {}", e.what());
            return false;
        }
    });

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================
    
    // Default parameter creators
    lua.set_function("create_default_gyro", &createDefaultGyro);
    lua.set_function("create_default_flight", &createDefaultFlight);
    lua.set_function("create_default_trail", &createDefaultTrail);
    lua.set_function("create_default_vfx", &createDefaultVFX);
    lua.set_function("create_default_particles", &createDefaultParticles);
    lua.set_function("create_default_audio", &createDefaultAudio);
    lua.set_function("create_default_collision", &createDefaultCollision);

    // Preset configurations
    lua.set_function("create_fast_spinner", &createFastSpinner);
    lua.set_function("create_heavy_gyro", &createHeavyGyro);
    lua.set_function("create_stealth_gyro", &createStealthGyro);
    lua.set_function("create_showy_gyro", &createShowyGyro);
    lua.set_function("create_fast_spinner_flight", &createFastSpinnerFlight);
    lua.set_function("create_heavy_gyro_flight", &createHeavyGyroFlight);
    lua.set_function("create_stealth_gyro_flight", &createStealthGyroFlight);
    lua.set_function("create_showy_gyro_flight", &createShowyGyroFlight);

    // Status and management functions
    lua.set_function("get_gyro_pending_count", []() -> int {
        return static_cast<int>(pendingGyros.size());
    });

    lua.set_function("clear_gyro_pending", []() {
        pendingGyros.clear();
        Log::info("Cleared all pending gyro projectile generations");
    });
}

void GyroProjectileLuaBindings::poll_assets(sol::state& lua) {
    // Process completed gyros
    for (auto it = pendingGyros.begin(); it != pendingGyros.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                Log::info("GyroProjectile", "Gyro projectile ready: {} (mesh: {}, flight: {}, trail: {}, shader: {}, particles: {}, audio: {}, collider: {})", 
                    it->second, bundle.mesh, bundle.flightSim, bundle.trailMesh, bundle.vfxShader, 
                    bundle.particleSys, bundle.humAudio, bundle.collider);
                sol::protected_function onReady = lua["on_gyro_ready"];
                if (onReady.valid()) {
                    auto result = onReady(it->second, bundle);
                    if (!result.valid()) {
                        sol::error err = result;
                        Log::error("GyroProjectile", "on_gyro_ready failed for {}: {}", it->second, err.what());
                    }
                }
            } catch (const std::exception& e) {
                Log::error("GyroProjectile", "Gyro generation failed for {}: {}", it->second, e.what());
                sol::protected_function onError = lua["on_gyro_error"];
                if (onError.valid()) {
                    onError(it->second, std::string(e.what()));
                }
            }
            it = pendingGyros.erase(it);
        } else { ++it; }
    }
}

// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================

bool GyroProjectileLuaBindings::validateGyroParams(const GyroParams& p) {
    if (p.id.empty()) {
        Log::error("GyroParams: id cannot be empty");
        return false;
    }
    if (p.radius <= 0.0f || p.radius > 10.0f) {
        Log::error("GyroParams: radius must be between 0.1 and 10.0");
        return false;
    }
    if (p.thickness <= 0.0f || p.thickness > 2.0f) {
        Log::error("GyroParams: thickness must be between 0.01 and 2.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateFlightParams(const FlightParams& p) {
    if (p.initialSpeed <= 0.0f || p.initialSpeed > 500.0f) {
        Log::error("FlightParams: initialSpeed must be between 1.0 and 500.0");
        return false;
    }
    if (p.spinRateRPM <= 0.0f || p.spinRateRPM > 10000.0f) {
        Log::error("FlightParams: spinRateRPM must be between 1.0 and 10000.0");
        return false;
    }
    if (p.precessionRateDeg < -360.0f || p.precessionRateDeg > 360.0f) {
        Log::error("FlightParams: precessionRateDeg must be between -360.0 and 360.0");
        return false;
    }
    if (p.stabilityFactor < 0.0f || p.stabilityFactor > 1.0f) {
        Log::error("FlightParams: stabilityFactor must be between 0.0 and 1.0");
        return false;
    }
    if (p.gravityScale < 0.0f || p.gravityScale > 5.0f) {
        Log::error("FlightParams: gravityScale must be between 0.0 and 5.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateTrailParams(const TrailParams& p) {
    if (p.length <= 0.0f || p.length > 10.0f) {
        Log::error("TrailParams: length must be between 0.1 and 10.0");
        return false;
    }
    if (p.width <= 0.0f || p.width > 2.0f) {
        Log::error("TrailParams: width must be between 0.01 and 2.0");
        return false;
    }
    if (p.uvScrollSpeed < 0.0f || p.uvScrollSpeed > 20.0f) {
        Log::error("TrailParams: uvScrollSpeed must be between 0.0 and 20.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateVFXParams(const VFXParams& p) {
    if (p.glowIntensity < 0.0f || p.glowIntensity > 10.0f) {
        Log::error("VFXParams: glowIntensity must be between 0.0 and 10.0");
        return false;
    }
    if (p.flickerSpeed < 0.0f || p.flickerSpeed > 100.0f) {
        Log::error("VFXParams: flickerSpeed must be between 0.0 and 100.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateParticleParams(const ParticleParams& p) {
    if (p.count <= 0 || p.count > 1000) {
        Log::error("ParticleParams: count must be between 1 and 1000");
        return false;
    }
    if (p.spawnRate <= 0.0f || p.spawnRate > 1000.0f) {
        Log::error("ParticleParams: spawnRate must be between 1.0 and 1000.0");
        return false;
    }
    if (p.lifeTime <= 0.0f || p.lifeTime > 10.0f) {
        Log::error("ParticleParams: lifeTime must be between 0.1 and 10.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateAudioParams(const AudioParams& p) {
    if (p.volume < 0.0f || p.volume > 2.0f) {
        Log::error("AudioParams: volume must be between 0.0 and 2.0");
        return false;
    }
    if (p.pitchVariance < 0.0f || p.pitchVariance > 1.0f) {
        Log::error("AudioParams: pitchVariance must be between 0.0 and 1.0");
        return false;
    }
    return true;
}

bool GyroProjectileLuaBindings::validateCollisionParams(const CollisionParams& p) {
    if (p.radius <= 0.0f || p.radius > 10.0f) {
        Log::error("CollisionParams: radius must be between 0.1 and 10.0");
        return false;
    }
    return true;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

GyroParams GyroProjectileLuaBindings::createDefaultGyro() {
    GyroParams p;
    p.id = "default_gyro";
    p.shape = GyroShape::Disc;
    p.radius = 0.5f;
    p.thickness = 0.1f;
    p.hollow = false;
    p.dynamicTess = false;
    return p;
}

FlightParams GyroProjectileLuaBindings::createDefaultFlight() {
    FlightParams p;
    p.initialSpeed = 50.0f;
    p.spinRateRPM = 3600.0f;
    p.precessionRateDeg = 30.0f;
    p.stabilityFactor = 0.9f;
    p.gravityEnabled = true;
    p.gravityScale = 1.0f;
    return p;
}

TrailParams GyroProjectileLuaBindings::createDefaultTrail() {
    TrailParams p;
    p.enableTrail = true;
    p.type = TrailType::Ribbon;
    p.length = 2.0f;
    p.width = 0.1f;
    p.headColor = glm::vec4(1.0f, 1.0f, 1.0f, 1.0f);
    p.tailColor = glm::vec4(1.0f, 1.0f, 1.0f, 0.0f);
    p.uvScrollSpeed = 1.0f;
    return p;
}

VFXParams GyroProjectileLuaBindings::createDefaultVFX() {
    VFXParams p;
    p.shaderTemplate = "shaders/gyro_glow.frag";
    p.defines = {"USE_GYRO_BLUR"};
    p.glowIntensity = 1.0f;
    p.flickerSpeed = 5.0f;
    p.flickerMode = FlickerMode::None;
    return p;
}

ParticleParams GyroProjectileLuaBindings::createDefaultParticles() {
    ParticleParams p;
    p.enableParticles = true;
    p.style = ParticleStyle::Sparks;
    p.count = 100;
    p.spawnRate = 200.0f;
    p.lifeTime = 0.5f;
    p.velocityMin = glm::vec3(-1.0f, -1.0f, -1.0f);
    p.velocityMax = glm::vec3(1.0f, 1.0f, 1.0f);
    return p;
}

AudioParams GyroProjectileLuaBindings::createDefaultAudio() {
    AudioParams p;
    p.playOnLaunch = true;
    p.humFile = "sfx/gyro_hum.wav";
    p.impactFile = "sfx/gyro_impact.wav";
    p.volume = 1.0f;
    p.pitchVariance = 0.0f;
    return p;
}

CollisionParams GyroProjectileLuaBindings::createDefaultCollision() {
    CollisionParams p;
    p.enableCollider = true;
    p.meshCollider = false;
    p.radius = 0.5f;
    p.triggerOnly = false;
    p.enableCCD = true;
    return p;
}

// ============================================================================
// PRESET CONFIGURATIONS
// ============================================================================

GyroParams GyroProjectileLuaBindings::createFastSpinner() {
    GyroParams p;
    p.id = "fast_spinner";
    p.shape = GyroShape::Ring;
    p.radius = 0.3f;
    p.thickness = 0.05f;
    p.hollow = true;
    p.dynamicTess = true;
    return p;
}

FlightParams GyroProjectileLuaBindings::createFastSpinnerFlight() {
    FlightParams p;
    p.initialSpeed = 80.0f;
    p.spinRateRPM = 6000.0f;
    p.precessionRateDeg = 60.0f;
    p.stabilityFactor = 0.95f;
    p.gravityEnabled = true;
    p.gravityScale = 0.8f;
    return p;
}

GyroParams GyroProjectileLuaBindings::createHeavyGyro() {
    GyroParams p;
    p.id = "heavy_gyro";
    p.shape = GyroShape::Disc;
    p.radius = 0.8f;
    p.thickness = 0.2f;
    p.hollow = false;
    p.dynamicTess = false;
    return p;
}

FlightParams GyroProjectileLuaBindings::createHeavyGyroFlight() {
    FlightParams p;
    p.initialSpeed = 30.0f;
    p.spinRateRPM = 2400.0f;
    p.precessionRateDeg = 15.0f;
    p.stabilityFactor = 0.98f;
    p.gravityEnabled = true;
    p.gravityScale = 1.5f;
    return p;
}

GyroParams GyroProjectileLuaBindings::createStealthGyro() {
    GyroParams p;
    p.id = "stealth_gyro";
    p.shape = GyroShape::Spindle;
    p.radius = 0.2f;
    p.thickness = 0.4f;
    p.hollow = false;
    p.dynamicTess = false;
    return p;
}

FlightParams GyroProjectileLuaBindings::createStealthGyroFlight() {
    FlightParams p;
    p.initialSpeed = 100.0f;
    p.spinRateRPM = 4800.0f;
    p.precessionRateDeg = 10.0f;
    p.stabilityFactor = 0.99f;
    p.gravityEnabled = false;
    p.gravityScale = 0.0f;
    return p;
}

GyroParams GyroProjectileLuaBindings::createShowyGyro() {
    GyroParams p;
    p.id = "showy_gyro";
    p.shape = GyroShape::Ring;
    p.radius = 0.6f;
    p.thickness = 0.08f;
    p.hollow = true;
    p.dynamicTess = true;
    return p;
}

FlightParams GyroProjectileLuaBindings::createShowyGyroFlight() {
    FlightParams p;
    p.initialSpeed = 40.0f;
    p.spinRateRPM = 3600.0f;
    p.precessionRateDeg = 45.0f;
    p.stabilityFactor = 0.85f;
    p.gravityEnabled = true;
    p.gravityScale = 0.6f;
    return p;
}

} // namespace GyroProjectiles
} // namespace MagiTech
