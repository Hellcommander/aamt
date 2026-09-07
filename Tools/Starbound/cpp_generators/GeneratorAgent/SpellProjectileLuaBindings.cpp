#include "SpellProjectileLuaBindings.hpp"
#include "SpellAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace SpellProjectiles {

static std::vector<std::pair<std::future<SpellAssetBundle>, std::string>> pendingAssets;

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

    lua.new_usertype<TrailParams>("TrailParams", sol::constructors<TrailParams()>(),
        "enableTrail", &TrailParams::enableTrail, "mode", &TrailParams::mode, "trailLength", &TrailParams::trailLength,
        "width", &TrailParams::width, "uptime", &TrailParams::uptime, "headColor", &TrailParams::headColor, "tailColor", &TrailParams::tailColor);

    lua.new_usertype<VFXParams>("VFXParams", sol::constructors<VFXParams()>(),
        "shaderTemplate", &VFXParams::shaderTemplate, "defines", &VFXParams::defines,
        "noiseIntensity", &VFXParams::noiseIntensity, "pulseFreq", &VFXParams::pulseFreq);

    lua.new_usertype<ParticleParams>("ParticleParams", sol::constructors<ParticleParams()>(),
        "enableParticles", &ParticleParams::enableParticles, "style", &ParticleParams::style, "maxCount", &ParticleParams::maxCount,
        "spawnRate", &ParticleParams::spawnRate, "lifeTime", &ParticleParams::lifeTime,
        "initialVelocity", &ParticleParams::initialVelocity, "spreadAngle", &ParticleParams::spreadAngle);

    lua.new_usertype<LightParams>("LightParams", sol::constructors<LightParams()>(),
        "enableLight", &LightParams::enableLight, "color", &LightParams::color, "intensity", &LightParams::intensity,
        "flickerMode", &LightParams::flickerMode, "flickerSpeed", &LightParams::flickerSpeed);

    lua.new_usertype<AudioParams>("AudioParams", sol::constructors<AudioParams()>(),
        "playOnCast", &AudioParams::playOnCast, "sfxFile", &AudioParams::sfxFile,
        "volume", &AudioParams::volume, "loop", &AudioParams::loop);

    lua.new_usertype<CollisionParams>("CollisionParams", sol::constructors<CollisionParams()>(),
        "enableCollider", &CollisionParams::enableCollider, "radius", &CollisionParams::radius,
        "meshCollider", &CollisionParams::meshCollider, "triggerOnly", &CollisionParams::triggerOnly);

    lua.new_usertype<SpellAssetBundle>("SpellAssetBundle", sol::no_constructor,
        "geometry", &SpellAssetBundle::geometry, "trailMesh", &SpellAssetBundle::trailMesh, "vfxShader", &SpellAssetBundle::vfxShader,
        "particleSystem", &SpellAssetBundle::particleSystem, "dynamicLight", &SpellAssetBundle::dynamicLight,
        "audioCue", &SpellAssetBundle::audioCue, "collider", &SpellAssetBundle::collider);

    // Convenience functions for common spell types
    lua.set_function("create_fireball_spell", [](float radius = 0.3f) {
        SpellParams spell;
        spell.id = "fireball";
        spell.shape = SpellShape::Sphere;
        spell.baseRadius = radius;
        spell.dynamicTess = true;
        
        TrailParams trail;
        trail.enableTrail = true;
        trail.mode = TrailMode::SDFRibbon;
        trail.trailLength = 2.0f;
        trail.width = 0.1f;
        trail.uptime = 1.5f;
        trail.headColor = {1.0f, 0.3f, 0.0f, 1.0f}; // Orange
        trail.tailColor = {0.8f, 0.2f, 0.0f, 0.0f}; // Fade to transparent
        
        VFXParams vfx;
        vfx.shaderTemplate = "shaders/fireball.frag";
        vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
        vfx.noiseIntensity = 0.3f;
        vfx.pulseFreq = 3.0f;
        
        ParticleParams particles;
        particles.enableParticles = true;
        particles.style = ParticleStyle::Ember;
        particles.maxCount = 150;
        particles.spawnRate = 80.0f;
        particles.lifeTime = 0.8f;
        particles.initialVelocity = {0.0f, 0.5f, 1.0f};
        particles.spreadAngle = 25.0f;
        
        LightParams light;
        light.enableLight = true;
        light.color = {1.0f, 0.4f, 0.0f, 1.0f};
        light.intensity = 2.0f;
        light.flickerMode = LightFlicker::NoiseDriven;
        light.flickerSpeed = 8.0f;
        
        AudioParams audio;
        audio.playOnCast = true;
        audio.sfxFile = "fireball_cast.wav";
        audio.volume = 0.7f;
        audio.loop = false;
        
        CollisionParams collision;
        collision.enableCollider = true;
        collision.radius = radius * 0.8f;
        collision.meshCollider = false;
        collision.triggerOnly = true;
        
        return std::make_tuple(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("create_ice_shard_spell", [](float radius = 0.2f) {
        SpellParams spell;
        spell.id = "ice_shard";
        spell.shape = SpellShape::Cone;
        spell.baseRadius = radius;
        spell.length = 0.8f;
        spell.dynamicTess = true;
        
        TrailParams trail;
        trail.enableTrail = true;
        trail.mode = TrailMode::Ribbon;
        trail.trailLength = 1.5f;
        trail.width = 0.05f;
        trail.uptime = 2.0f;
        trail.headColor = {0.5f, 0.8f, 1.0f, 1.0f}; // Light blue
        trail.tailColor = {0.3f, 0.6f, 0.8f, 0.0f}; // Fade to transparent
        
        VFXParams vfx;
        vfx.shaderTemplate = "shaders/ice.frag";
        vfx.defines = {"USE_NOISE"};
        vfx.noiseIntensity = 0.2f;
        vfx.pulseFreq = 1.0f;
        
        ParticleParams particles;
        particles.enableParticles = true;
        particles.style = ParticleStyle::Sparks;
        particles.maxCount = 80;
        particles.spawnRate = 60.0f;
        particles.lifeTime = 1.2f;
        particles.initialVelocity = {0.0f, 0.3f, 1.0f};
        particles.spreadAngle = 15.0f;
        
        LightParams light;
        light.enableLight = true;
        light.color = {0.5f, 0.8f, 1.0f, 1.0f};
        light.intensity = 1.5f;
        light.flickerMode = LightFlicker::Sinusoidal;
        light.flickerSpeed = 2.0f;
        
        AudioParams audio;
        audio.playOnCast = true;
        audio.sfxFile = "ice_cast.wav";
        audio.volume = 0.6f;
        audio.loop = false;
        
        CollisionParams collision;
        collision.enableCollider = true;
        collision.radius = radius * 0.9f;
        collision.meshCollider = false;
        collision.triggerOnly = true;
        
        return std::make_tuple(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("create_lightning_bolt_spell", [](float radius = 0.15f) {
        SpellParams spell;
        spell.id = "lightning_bolt";
        spell.shape = SpellShape::Ribbon;
        spell.baseRadius = radius;
        spell.length = 1.2f;
        spell.dynamicTess = true;
        
        TrailParams trail;
        trail.enableTrail = true;
        trail.mode = TrailMode::SDFRibbon;
        trail.trailLength = 3.0f;
        trail.width = 0.08f;
        trail.uptime = 0.8f;
        trail.headColor = {1.0f, 1.0f, 0.0f, 1.0f}; // Bright yellow
        trail.tailColor = {0.8f, 0.8f, 0.0f, 0.0f}; // Fade to transparent
        
        VFXParams vfx;
        vfx.shaderTemplate = "shaders/lightning.frag";
        vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
        vfx.noiseIntensity = 0.8f;
        vfx.pulseFreq = 10.0f;
        
        ParticleParams particles;
        particles.enableParticles = true;
        particles.style = ParticleStyle::Sparks;
        particles.maxCount = 200;
        particles.spawnRate = 120.0f;
        particles.lifeTime = 0.5f;
        particles.initialVelocity = {0.0f, 0.8f, 1.0f};
        particles.spreadAngle = 45.0f;
        
        LightParams light;
        light.enableLight = true;
        light.color = {1.0f, 1.0f, 0.0f, 1.0f};
        light.intensity = 3.0f;
        light.flickerMode = LightFlicker::Pulse;
        light.flickerSpeed = 15.0f;
        
        AudioParams audio;
        audio.playOnCast = true;
        audio.sfxFile = "lightning_cast.wav";
        audio.volume = 0.9f;
        audio.loop = false;
        
        CollisionParams collision;
        collision.enableCollider = true;
        collision.radius = radius * 0.7f;
        collision.meshCollider = false;
        collision.triggerOnly = true;
        
        return std::make_tuple(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("create_arcane_orb_spell", [](float radius = 0.4f) {
        SpellParams spell;
        spell.id = "arcane_orb";
        spell.shape = SpellShape::Torus;
        spell.baseRadius = radius;
        spell.length = 0.6f;
        spell.dynamicTess = true;
        
        TrailParams trail;
        trail.enableTrail = true;
        trail.mode = TrailMode::Particles;
        trail.trailLength = 2.5f;
        trail.width = 0.12f;
        trail.uptime = 2.5f;
        trail.headColor = {0.8f, 0.0f, 1.0f, 1.0f}; // Purple
        trail.tailColor = {0.4f, 0.0f, 0.6f, 0.0f}; // Fade to transparent
        
        VFXParams vfx;
        vfx.shaderTemplate = "shaders/arcane.frag";
        vfx.defines = {"USE_NOISE", "ALPHA_PULSE"};
        vfx.noiseIntensity = 0.4f;
        vfx.pulseFreq = 2.5f;
        
        ParticleParams particles;
        particles.enableParticles = true;
        particles.style = ParticleStyle::Cosmic;
        particles.maxCount = 120;
        particles.spawnRate = 90.0f;
        particles.lifeTime = 1.5f;
        particles.initialVelocity = {0.0f, 0.4f, 1.0f};
        particles.spreadAngle = 30.0f;
        
        LightParams light;
        light.enableLight = true;
        light.color = {0.8f, 0.0f, 1.0f, 1.0f};
        light.intensity = 2.5f;
        light.flickerMode = LightFlicker::Sinusoidal;
        light.flickerSpeed = 3.0f;
        
        AudioParams audio;
        audio.playOnCast = true;
        audio.sfxFile = "arcane_cast.wav";
        audio.volume = 0.8f;
        audio.loop = false;
        
        CollisionParams collision;
        collision.enableCollider = true;
        collision.radius = radius * 0.8f;
        collision.meshCollider = false;
        collision.triggerOnly = true;
        
        return std::make_tuple(spell, trail, vfx, particles, light, audio, collision);
    });

    // Utility functions for parameter creation
    lua.set_function("create_spell_params", [](const std::string& id, const std::string& shapeStr, float radius = 0.3f) {
        SpellParams params;
        params.id = id;
        params.baseRadius = radius;
        params.dynamicTess = true;
        
        if (shapeStr == "sphere") params.shape = SpellShape::Sphere;
        else if (shapeStr == "cone") params.shape = SpellShape::Cone;
        else if (shapeStr == "torus") params.shape = SpellShape::Torus;
        else if (shapeStr == "ribbon") params.shape = SpellShape::Ribbon;
        else params.shape = SpellShape::Sphere; // Default
        
        return params;
    });

    lua.set_function("create_trail_params", [](bool enable = true, const std::string& modeStr = "ribbon") {
        TrailParams params;
        params.enableTrail = enable;
        params.trailLength = 2.0f;
        params.width = 0.1f;
        params.uptime = 1.5f;
        params.headColor = {1.0f, 1.0f, 1.0f, 1.0f};
        params.tailColor = {1.0f, 1.0f, 1.0f, 0.0f};
        
        if (modeStr == "ribbon") params.mode = TrailMode::Ribbon;
        else if (modeStr == "particles") params.mode = TrailMode::Particles;
        else if (modeStr == "sdfribbon") params.mode = TrailMode::SDFRibbon;
        else params.mode = TrailMode::Ribbon; // Default
        
        return params;
    });

    lua.set_function("create_vfx_params", [](const std::string& template = "shaders/default.frag") {
        VFXParams params;
        params.shaderTemplate = template;
        params.defines = {};
        params.noiseIntensity = 0.1f;
        params.pulseFreq = 1.0f;
        return params;
    });

    lua.set_function("create_particle_params", [](bool enable = true, const std::string& styleStr = "sparks") {
        ParticleParams params;
        params.enableParticles = enable;
        params.maxCount = 100;
        params.spawnRate = 50.0f;
        params.lifeTime = 1.0f;
        params.initialVelocity = {0.0f, 0.5f, 1.0f};
        params.spreadAngle = 20.0f;
        
        if (styleStr == "sparks") params.style = ParticleStyle::Sparks;
        else if (styleStr == "smoke") params.style = ParticleStyle::Smoke;
        else if (styleStr == "ember") params.style = ParticleStyle::Ember;
        else if (styleStr == "cosmic") params.style = ParticleStyle::Cosmic;
        else params.style = ParticleStyle::Sparks; // Default
        
        return params;
    });

    lua.set_function("create_light_params", [](bool enable = true) {
        LightParams params;
        params.enableLight = enable;
        params.color = {1.0f, 1.0f, 1.0f, 1.0f};
        params.intensity = 1.0f;
        params.flickerMode = LightFlicker::None;
        params.flickerSpeed = 1.0f;
        return params;
    });

    lua.set_function("create_audio_params", [](bool enable = true, const std::string& sfx = "") {
        AudioParams params;
        params.playOnCast = enable;
        params.sfxFile = sfx;
        params.volume = 0.7f;
        params.loop = false;
        return params;
    });

    lua.set_function("create_collision_params", [](bool enable = true, float radius = 0.3f) {
        CollisionParams params;
        params.enableCollider = enable;
        params.radius = radius;
        params.meshCollider = false;
        params.triggerOnly = true;
        return params;
    });

    // Main spell generation function
    lua.set_function("spawn_spell",
        [&](const SpellParams& s, const TrailParams& t, const VFXParams& v, const ParticleParams& p,
            const LightParams& l, const AudioParams& a, const CollisionParams& c) {
            auto factory = MainPlugin::instance().getSpellAssetFactory();
            pendingAssets.emplace_back(factory->generateAsync(s, t, v, p, l, a, c), s.id);
        }
    );

    // Convenience function for spawning predefined spells
    lua.set_function("spawn_fireball", [&](float radius = 0.3f) {
        auto [spell, trail, vfx, particles, light, audio, collision] = create_fireball_spell(radius);
        spawn_spell(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("spawn_ice_shard", [&](float radius = 0.2f) {
        auto [spell, trail, vfx, particles, light, audio, collision] = create_ice_shard_spell(radius);
        spawn_spell(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("spawn_lightning_bolt", [&](float radius = 0.15f) {
        auto [spell, trail, vfx, particles, light, audio, collision] = create_lightning_bolt_spell(radius);
        spawn_spell(spell, trail, vfx, particles, light, audio, collision);
    });

    lua.set_function("spawn_arcane_orb", [&](float radius = 0.4f) {
        auto [spell, trail, vfx, particles, light, audio, collision] = create_arcane_orb_spell(radius);
        spawn_spell(spell, trail, vfx, particles, light, audio, collision);
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
