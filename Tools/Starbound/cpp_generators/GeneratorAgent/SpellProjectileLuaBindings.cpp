#include "SpellProjectileLuaBindings.hpp"
#include "SpellAssetFactory.hpp"
#include <chrono>
#include <memory>
#include <mutex>
#include <tuple>
#include <vector>

namespace MagiTech {
namespace SpellProjectiles {

static std::vector<std::pair<std::future<SpellAssetBundle>, std::string>> pendingAssets;

namespace {

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<SpellAssetFactory>& factorySlot() {
    static std::shared_ptr<SpellAssetFactory> f;
    return f;
}

/** Every parameter block one spell needs; returned to Lua as multiple values. */
struct SpellPreset {
    SpellParams spell;
    TrailParams trail;
    VFXParams vfx;
    ParticleParams particles;
    LightParams light;
    AudioParams audio;
    CollisionParams collision;

    auto asTuple() const { return std::make_tuple(spell, trail, vfx, particles, light, audio, collision); }
};

SpellPreset fireballSpell(float radius) {
    SpellPreset p;
    p.spell.id = "fireball";
    p.spell.shape = SpellShape::Sphere;
    p.spell.baseRadius = radius;
    p.spell.dynamicTess = true;

    p.trail.enableTrail = true;
    p.trail.mode = TrailMode::SDFRibbon;
    p.trail.trailLength = 2.0f;
    p.trail.width = 0.1f;
    p.trail.uptime = 1.5f;
    p.trail.headColor = {1.0f, 0.3f, 0.0f, 1.0f}; // Orange
    p.trail.tailColor = {0.8f, 0.2f, 0.0f, 0.0f}; // Fade to transparent

    p.vfx.shaderTemplate = "shaders/fireball.frag";
    p.vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
    p.vfx.noiseIntensity = 0.3f;
    p.vfx.pulseFreq = 3.0f;

    p.particles.enableParticles = true;
    p.particles.style = ParticleStyle::Ember;
    p.particles.maxCount = 150;
    p.particles.spawnRate = 80.0f;
    p.particles.lifeTime = 0.8f;
    p.particles.initialVelocity = {0.0f, 0.5f, 1.0f};
    p.particles.spreadAngle = 25.0f;

    p.light.enableLight = true;
    p.light.color = {1.0f, 0.4f, 0.0f, 1.0f};
    p.light.intensity = 2.0f;
    p.light.flickerMode = LightFlicker::NoiseDriven;
    p.light.flickerSpeed = 8.0f;

    p.audio.playOnCast = true;
    p.audio.sfxFile = "fireball_cast.wav";
    p.audio.volume = 0.7f;
    p.audio.loop = false;

    p.collision.enableCollider = true;
    p.collision.radius = radius * 0.8f;
    p.collision.meshCollider = false;
    p.collision.triggerOnly = true;
    return p;
}

SpellPreset iceShardSpell(float radius) {
    SpellPreset p;
    p.spell.id = "ice_shard";
    p.spell.shape = SpellShape::Cone;
    p.spell.baseRadius = radius;
    p.spell.length = 0.8f;
    p.spell.dynamicTess = true;

    p.trail.enableTrail = true;
    p.trail.mode = TrailMode::Ribbon;
    p.trail.trailLength = 1.5f;
    p.trail.width = 0.05f;
    p.trail.uptime = 2.0f;
    p.trail.headColor = {0.5f, 0.8f, 1.0f, 1.0f}; // Light blue
    p.trail.tailColor = {0.3f, 0.6f, 0.8f, 0.0f}; // Fade to transparent

    p.vfx.shaderTemplate = "shaders/ice.frag";
    p.vfx.defines = {"USE_NOISE"};
    p.vfx.noiseIntensity = 0.2f;
    p.vfx.pulseFreq = 1.0f;

    p.particles.enableParticles = true;
    p.particles.style = ParticleStyle::Sparks;
    p.particles.maxCount = 80;
    p.particles.spawnRate = 60.0f;
    p.particles.lifeTime = 1.2f;
    p.particles.initialVelocity = {0.0f, 0.3f, 1.0f};
    p.particles.spreadAngle = 15.0f;

    p.light.enableLight = true;
    p.light.color = {0.5f, 0.8f, 1.0f, 1.0f};
    p.light.intensity = 1.5f;
    p.light.flickerMode = LightFlicker::Sinusoidal;
    p.light.flickerSpeed = 2.0f;

    p.audio.playOnCast = true;
    p.audio.sfxFile = "ice_cast.wav";
    p.audio.volume = 0.6f;
    p.audio.loop = false;

    p.collision.enableCollider = true;
    p.collision.radius = radius * 0.9f;
    p.collision.meshCollider = false;
    p.collision.triggerOnly = true;
    return p;
}

SpellPreset lightningBoltSpell(float radius) {
    SpellPreset p;
    p.spell.id = "lightning_bolt";
    p.spell.shape = SpellShape::Ribbon;
    p.spell.baseRadius = radius;
    p.spell.length = 1.2f;
    p.spell.dynamicTess = true;

    p.trail.enableTrail = true;
    p.trail.mode = TrailMode::SDFRibbon;
    p.trail.trailLength = 3.0f;
    p.trail.width = 0.08f;
    p.trail.uptime = 0.8f;
    p.trail.headColor = {1.0f, 1.0f, 0.0f, 1.0f}; // Bright yellow
    p.trail.tailColor = {0.8f, 0.8f, 0.0f, 0.0f}; // Fade to transparent

    p.vfx.shaderTemplate = "shaders/lightning.frag";
    p.vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
    p.vfx.noiseIntensity = 0.8f;
    p.vfx.pulseFreq = 10.0f;

    p.particles.enableParticles = true;
    p.particles.style = ParticleStyle::Sparks;
    p.particles.maxCount = 200;
    p.particles.spawnRate = 120.0f;
    p.particles.lifeTime = 0.5f;
    p.particles.initialVelocity = {0.0f, 0.8f, 1.0f};
    p.particles.spreadAngle = 45.0f;

    p.light.enableLight = true;
    p.light.color = {1.0f, 1.0f, 0.0f, 1.0f};
    p.light.intensity = 3.0f;
    p.light.flickerMode = LightFlicker::Pulse;
    p.light.flickerSpeed = 15.0f;

    p.audio.playOnCast = true;
    p.audio.sfxFile = "lightning_cast.wav";
    p.audio.volume = 0.9f;
    p.audio.loop = false;

    p.collision.enableCollider = true;
    p.collision.radius = radius * 0.7f;
    p.collision.meshCollider = false;
    p.collision.triggerOnly = true;
    return p;
}

SpellPreset arcaneOrbSpell(float radius) {
    SpellPreset p;
    p.spell.id = "arcane_orb";
    p.spell.shape = SpellShape::Torus;
    p.spell.baseRadius = radius;
    p.spell.length = 0.6f;
    p.spell.dynamicTess = true;

    p.trail.enableTrail = true;
    p.trail.mode = TrailMode::Particles;
    p.trail.trailLength = 2.5f;
    p.trail.width = 0.12f;
    p.trail.uptime = 2.5f;
    p.trail.headColor = {0.8f, 0.0f, 1.0f, 1.0f}; // Purple
    p.trail.tailColor = {0.4f, 0.0f, 0.6f, 0.0f}; // Fade to transparent

    p.vfx.shaderTemplate = "shaders/arcane.frag";
    p.vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
    p.vfx.noiseIntensity = 0.4f;
    p.vfx.pulseFreq = 2.5f;

    p.particles.enableParticles = true;
    p.particles.style = ParticleStyle::Cosmic;
    p.particles.maxCount = 120;
    p.particles.spawnRate = 90.0f;
    p.particles.lifeTime = 1.5f;
    p.particles.initialVelocity = {0.0f, 0.4f, 1.0f};
    p.particles.spreadAngle = 30.0f;

    p.light.enableLight = true;
    p.light.color = {0.8f, 0.0f, 1.0f, 1.0f};
    p.light.intensity = 2.5f;
    p.light.flickerMode = LightFlicker::Sinusoidal;
    p.light.flickerSpeed = 3.0f;

    p.audio.playOnCast = true;
    p.audio.sfxFile = "arcane_cast.wav";
    p.audio.volume = 0.8f;
    p.audio.loop = false;

    p.collision.enableCollider = true;
    p.collision.radius = radius * 0.8f;
    p.collision.meshCollider = false;
    p.collision.triggerOnly = true;
    return p;
}

void spawnSpell(const SpellParams& s, const TrailParams& t, const VFXParams& v, const ParticleParams& p,
                const LightParams& l, const AudioParams& a, const CollisionParams& c) {
    auto factory = SpellProjectileLuaBindings::factory();
    pendingAssets.emplace_back(factory->generateAsync(s, t, v, p, l, a, c), s.id);
}

void spawnPreset(const SpellPreset& p) {
    spawnSpell(p.spell, p.trail, p.vfx, p.particles, p.light, p.audio, p.collision);
}

} // namespace

void SpellProjectileLuaBindings::setFactory(std::shared_ptr<SpellAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<SpellAssetFactory> SpellProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<SpellAssetFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void SpellProjectileLuaBindings::bind(sol::state& lua) {
    lua.new_enum("SpellShape",
        "Sphere", SpellShape::Sphere, "Cone", SpellShape::Cone, "Torus", SpellShape::Torus,
        "Ribbon", SpellShape::Ribbon, "CustomMesh", SpellShape::CustomMesh
    );
    lua.new_enum("TrailMode",
        "Ribbon", TrailMode::Ribbon, "Particles", TrailMode::Particles, "SDFRibbon", TrailMode::SDFRibbon
    );
    lua.new_enum("ParticleStyle",
        "Sparks", ParticleStyle::Sparks, "Smoke", ParticleStyle::Smoke,
        "Ember", ParticleStyle::Ember, "Cosmic", ParticleStyle::Cosmic
    );
    lua.new_enum("LightFlicker",
        "None", LightFlicker::None, "Sinusoidal", LightFlicker::Sinusoidal,
        "NoiseDriven", LightFlicker::NoiseDriven, "Pulse", LightFlicker::Pulse
    );

    lua.new_usertype<SpellParams>("SpellParams", sol::constructors<SpellParams()>(),
        "id", &SpellParams::id, "shape", &SpellParams::shape, "baseRadius", &SpellParams::baseRadius,
        "length", &SpellParams::length, "dynamicTess", &SpellParams::dynamicTess);

    lua.new_usertype<TrailParams>("SpellTrailParams", sol::constructors<TrailParams()>(),
        "enableTrail", &TrailParams::enableTrail, "mode", &TrailParams::mode, "trailLength", &TrailParams::trailLength,
        "width", &TrailParams::width, "uptime", &TrailParams::uptime, "headColor", &TrailParams::headColor, "tailColor", &TrailParams::tailColor);

    lua.new_usertype<VFXParams>("SpellVFXParams", sol::constructors<VFXParams()>(),
        "shaderTemplate", &VFXParams::shaderTemplate, "defines", &VFXParams::defines,
        "noiseIntensity", &VFXParams::noiseIntensity, "pulseFreq", &VFXParams::pulseFreq);

    lua.new_usertype<ParticleParams>("SpellParticleParams", sol::constructors<ParticleParams()>(),
        "enableParticles", &ParticleParams::enableParticles, "style", &ParticleParams::style, "maxCount", &ParticleParams::maxCount,
        "spawnRate", &ParticleParams::spawnRate, "lifeTime", &ParticleParams::lifeTime,
        "initialVelocity", &ParticleParams::initialVelocity, "spreadAngle", &ParticleParams::spreadAngle);

    lua.new_usertype<LightParams>("SpellLightParams", sol::constructors<LightParams()>(),
        "enableLight", &LightParams::enableLight, "color", &LightParams::color, "intensity", &LightParams::intensity,
        "flickerMode", &LightParams::flickerMode, "flickerSpeed", &LightParams::flickerSpeed);

    lua.new_usertype<AudioParams>("SpellAudioParams", sol::constructors<AudioParams()>(),
        "playOnCast", &AudioParams::playOnCast, "sfxFile", &AudioParams::sfxFile,
        "volume", &AudioParams::volume, "loop", &AudioParams::loop);

    lua.new_usertype<CollisionParams>("SpellCollisionParams", sol::constructors<CollisionParams()>(),
        "enableCollider", &CollisionParams::enableCollider, "radius", &CollisionParams::radius,
        "meshCollider", &CollisionParams::meshCollider, "triggerOnly", &CollisionParams::triggerOnly);

    lua.new_usertype<SpellAssetBundle>("SpellAssetBundle", sol::no_constructor,
        "geometry", &SpellAssetBundle::geometry, "trailMesh", &SpellAssetBundle::trailMesh, "vfxShader", &SpellAssetBundle::vfxShader,
        "particleSystem", &SpellAssetBundle::particleSystem, "dynamicLight", &SpellAssetBundle::dynamicLight,
        "audioCue", &SpellAssetBundle::audioCue, "collider", &SpellAssetBundle::collider);

    // Convenience functions for common spell types (radius optional); each returns
    // spell, trail, vfx, particles, light, audio, collision
    lua.set_function("create_fireball_spell", [](sol::optional<float> radius) {
        return fireballSpell(radius.value_or(0.3f)).asTuple();
    });
    lua.set_function("create_ice_shard_spell", [](sol::optional<float> radius) {
        return iceShardSpell(radius.value_or(0.2f)).asTuple();
    });
    lua.set_function("create_lightning_bolt_spell", [](sol::optional<float> radius) {
        return lightningBoltSpell(radius.value_or(0.15f)).asTuple();
    });
    lua.set_function("create_arcane_orb_spell", [](sol::optional<float> radius) {
        return arcaneOrbSpell(radius.value_or(0.4f)).asTuple();
    });

    // Utility functions for parameter creation (trailing arguments optional)
    lua.set_function("create_spell_params", [](const std::string& id, const std::string& shapeStr, sol::optional<float> radius) {
        SpellParams params;
        params.id = id;
        params.baseRadius = radius.value_or(0.3f);
        params.dynamicTess = true;

        if (shapeStr == "sphere") params.shape = SpellShape::Sphere;
        else if (shapeStr == "cone") params.shape = SpellShape::Cone;
        else if (shapeStr == "torus") params.shape = SpellShape::Torus;
        else if (shapeStr == "ribbon") params.shape = SpellShape::Ribbon;
        else params.shape = SpellShape::Sphere; // Default

        return params;
    });

    lua.set_function("create_trail_params", [](sol::optional<bool> enable, sol::optional<std::string> mode) {
        TrailParams params;
        params.enableTrail = enable.value_or(true);
        params.trailLength = 2.0f;
        params.width = 0.1f;
        params.uptime = 1.5f;
        params.headColor = {1.0f, 1.0f, 1.0f, 1.0f};
        params.tailColor = {1.0f, 1.0f, 1.0f, 0.0f};

        const std::string modeStr = mode.value_or("ribbon");
        if (modeStr == "ribbon") params.mode = TrailMode::Ribbon;
        else if (modeStr == "particles") params.mode = TrailMode::Particles;
        else if (modeStr == "sdfribbon") params.mode = TrailMode::SDFRibbon;
        else params.mode = TrailMode::Ribbon; // Default

        return params;
    });

    lua.set_function("create_vfx_params", [](sol::optional<std::string> shaderTemplate) {
        VFXParams params;
        params.shaderTemplate = shaderTemplate.value_or("shaders/default.frag");
        params.defines = {};
        params.noiseIntensity = 0.1f;
        params.pulseFreq = 1.0f;
        return params;
    });

    lua.set_function("create_particle_params", [](sol::optional<bool> enable, sol::optional<std::string> style) {
        ParticleParams params;
        params.enableParticles = enable.value_or(true);
        params.maxCount = 100;
        params.spawnRate = 50.0f;
        params.lifeTime = 1.0f;
        params.initialVelocity = {0.0f, 0.5f, 1.0f};
        params.spreadAngle = 20.0f;

        const std::string styleStr = style.value_or("sparks");
        if (styleStr == "sparks") params.style = ParticleStyle::Sparks;
        else if (styleStr == "smoke") params.style = ParticleStyle::Smoke;
        else if (styleStr == "ember") params.style = ParticleStyle::Ember;
        else if (styleStr == "cosmic") params.style = ParticleStyle::Cosmic;
        else params.style = ParticleStyle::Sparks; // Default

        return params;
    });

    lua.set_function("create_light_params", [](sol::optional<bool> enable) {
        LightParams params;
        params.enableLight = enable.value_or(true);
        params.color = {1.0f, 1.0f, 1.0f, 1.0f};
        params.intensity = 1.0f;
        params.flickerMode = LightFlicker::None;
        params.flickerSpeed = 1.0f;
        return params;
    });

    lua.set_function("create_audio_params", [](sol::optional<bool> enable, sol::optional<std::string> sfx) {
        AudioParams params;
        params.playOnCast = enable.value_or(true);
        params.sfxFile = sfx.value_or("");
        params.volume = 0.7f;
        params.loop = false;
        return params;
    });

    lua.set_function("create_collision_params", [](sol::optional<bool> enable, sol::optional<float> radius) {
        CollisionParams params;
        params.enableCollider = enable.value_or(true);
        params.radius = radius.value_or(0.3f);
        params.meshCollider = false;
        params.triggerOnly = true;
        return params;
    });

    // Main spell generation function
    lua.set_function("spawn_spell", &spawnSpell);

    // Convenience functions for spawning predefined spells
    lua.set_function("spawn_fireball", [](sol::optional<float> radius) {
        spawnPreset(fireballSpell(radius.value_or(0.3f)));
    });
    lua.set_function("spawn_ice_shard", [](sol::optional<float> radius) {
        spawnPreset(iceShardSpell(radius.value_or(0.2f)));
    });
    lua.set_function("spawn_lightning_bolt", [](sol::optional<float> radius) {
        spawnPreset(lightningBoltSpell(radius.value_or(0.15f)));
    });
    lua.set_function("spawn_arcane_orb", [](sol::optional<float> radius) {
        spawnPreset(arcaneOrbSpell(radius.value_or(0.4f)));
    });
}

void SpellProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                lua["print"]("Spell asset ready: " + it->second +
                            " (geometry: " + std::to_string(bundle.geometry) +
                            ", trail: " + std::to_string(bundle.trailMesh) +
                            ", shader: " + std::to_string(bundle.vfxShader) +
                            ", particles: " + std::to_string(bundle.particleSystem) +
                            ", light: " + std::to_string(bundle.dynamicLight) +
                            ", audio: " + std::to_string(bundle.audioCue) +
                            ", collider: " + std::to_string(bundle.collider) + ")");
            } catch (const std::exception& e) {
                lua["print"]("Spell asset error: " + it->second + " - " + e.what());
            }
            it = pendingAssets.erase(it);
        } else { ++it; }
    }
}

} // namespace SpellProjectiles
} // namespace MagiTech
