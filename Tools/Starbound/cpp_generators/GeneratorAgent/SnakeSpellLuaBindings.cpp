#include "SnakeSpellLuaBindings.hpp"
#include "SnakeSpellFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace SnakeSpells {

static std::vector<std::pair<std::future<SnakeBundle>, std::string>> pendingSpells;

void SnakeSpellLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SnakeBodyParams>("SnakeBodyParams", sol::constructors<SnakeBodyParams()>(),
        "segmentCount", &SnakeBodyParams::segmentCount, "totalLength", &SnakeBodyParams::totalLength,
        "segmentRadius", &SnakeBodyParams::segmentRadius, "scaleMaterial", &SnakeBodyParams::scaleMaterial, "dynamicMorph", &SnakeBodyParams::dynamicMorph);

    lua.new_usertype<MotionParams>("MotionParams", sol::constructors<MotionParams()>(),
        "curlEnabled", &MotionParams::curlEnabled, "curlFrequency", &MotionParams::curlFrequency,
        "curlAmplitude", &MotionParams::curlAmplitude, "homing", &MotionParams::homing, "homingTurnRate", &MotionParams::homingTurnRate);

    lua.new_usertype<ScaleVFXParams>("ScaleVFXParams", sol::constructors<ScaleVFXParams()>(),
        "enableGlow", &ScaleVFXParams::enableGlow, "glowColor", &ScaleVFXParams::glowColor,
        "glowIntensity", &ScaleVFXParams::glowIntensity, "pulsate", &ScaleVFXParams::pulsate, "pulsateSpeed", &ScaleVFXParams::pulsateSpeed);

    lua.new_usertype<ParticleParams>("ParticleParams", sol::constructors<ParticleParams()>(),
        "venomDrip", &ParticleParams::venomDrip, "dripRate", &ParticleParams::dripRate,
        "venomColor", &ParticleParams::venomColor, "smokeTrail", &ParticleParams::smokeTrail, "smokeDensity", &ParticleParams::smokeDensity);

    lua.new_usertype<AudioParams>("AudioParams", sol::constructors<AudioParams()>(),
        "hissOnLaunch", &AudioParams::hissOnLaunch, "hissFile", &AudioParams::hissFile,
        "hissVolume", &AudioParams::hissVolume, "rattleOnImpact", &AudioParams::rattleOnImpact, "rattleFile", &AudioParams::rattleFile);

    lua.new_usertype<CollisionParams>("CollisionParams", sol::constructors<CollisionParams()>(),
        "capsuleSegments", &CollisionParams::capsuleSegments, "capsuleRadius", &CollisionParams::capsuleRadius, "enableCCD", &CollisionParams::enableCCD);

    lua.new_usertype<SnakeBundle>("SnakeBundle", sol::no_constructor,
        "mesh", &SnakeBundle::mesh, "motionSim", &SnakeBundle::motionSim, "vfx", &SnakeBundle::vfx,
        "particles", &SnakeBundle::particles, "audio", &SnakeBundle::audio, "collider", &SnakeBundle::collider);

    // Convenience functions for common snake spell types
    lua.set_function("create_venom_snake", [](float length = 4.0f, int segments = 12) {
        SnakeBodyParams body;
        body.segmentCount = segments;
        body.totalLength = length;
        body.segmentRadius = 0.15f;
        body.scaleMaterial = "mat/scales_venom";
        body.dynamicMorph = true;
        
        MotionParams motion;
        motion.curlEnabled = true;
        motion.curlFrequency = 2.5f;
        motion.curlAmplitude = 0.3f;
        motion.homing = true;
        motion.homingTurnRate = 45.0f;
        
        ScaleVFXParams vfx;
        vfx.enableGlow = true;
        vfx.glowColor = {0.0f, 0.8f, 0.0f, 1.0f}; // Green
        vfx.glowIntensity = 1.2f;
        vfx.pulsate = true;
        vfx.pulsateSpeed = 2.0f;
        
        ParticleParams particles;
        particles.venomDrip = true;
        particles.dripRate = 8.0f;
        particles.venomColor = {0.0f, 0.6f, 0.0f, 1.0f}; // Dark green
        particles.smokeTrail = true;
        particles.smokeDensity = 15.0f;
        
        AudioParams audio;
        audio.hissOnLaunch = true;
        audio.hissFile = "sfx/snake_venom_hiss.wav";
        audio.hissVolume = 0.8f;
        audio.rattleOnImpact = true;
        audio.rattleFile = "sfx/venom_impact.wav";
        
        CollisionParams collision;
        collision.capsuleSegments = segments;
        collision.capsuleRadius = 0.15f;
        collision.enableCCD = true;
        
        return std::make_tuple(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("create_fire_snake", [](float length = 4.0f, int segments = 12) {
        SnakeBodyParams body;
        body.segmentCount = segments;
        body.totalLength = length;
        body.segmentRadius = 0.18f;
        body.scaleMaterial = "mat/scales_fire";
        body.dynamicMorph = true;
        
        MotionParams motion;
        motion.curlEnabled = true;
        motion.curlFrequency = 3.0f;
        motion.curlAmplitude = 0.4f;
        motion.homing = true;
        motion.homingTurnRate = 60.0f;
        
        ScaleVFXParams vfx;
        vfx.enableGlow = true;
        vfx.glowColor = {1.0f, 0.3f, 0.0f, 1.0f}; // Orange
        vfx.glowIntensity = 2.0f;
        vfx.pulsate = true;
        vfx.pulsateSpeed = 4.0f;
        
        ParticleParams particles;
        particles.venomDrip = true;
        particles.dripRate = 12.0f;
        particles.venomColor = {1.0f, 0.2f, 0.0f, 1.0f}; // Red
        particles.smokeTrail = true;
        particles.smokeDensity = 20.0f;
        
        AudioParams audio;
        audio.hissOnLaunch = true;
        audio.hissFile = "sfx/snake_fire_hiss.wav";
        audio.hissVolume = 0.9f;
        audio.rattleOnImpact = true;
        audio.rattleFile = "sfx/fire_impact.wav";
        
        CollisionParams collision;
        collision.capsuleSegments = segments;
        collision.capsuleRadius = 0.18f;
        collision.enableCCD = true;
        
        return std::make_tuple(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("create_ice_snake", [](float length = 4.0f, int segments = 12) {
        SnakeBodyParams body;
        body.segmentCount = segments;
        body.totalLength = length;
        body.segmentRadius = 0.16f;
        body.scaleMaterial = "mat/scales_ice";
        body.dynamicMorph = true;
        
        MotionParams motion;
        motion.curlEnabled = true;
        motion.curlFrequency = 1.8f;
        motion.curlAmplitude = 0.25f;
        motion.homing = true;
        motion.homingTurnRate = 35.0f;
        
        ScaleVFXParams vfx;
        vfx.enableGlow = true;
        vfx.glowColor = {0.5f, 0.8f, 1.0f, 1.0f}; // Light blue
        vfx.glowIntensity = 1.5f;
        vfx.pulsate = true;
        vfx.pulsateSpeed = 1.5f;
        
        ParticleParams particles;
        particles.venomDrip = true;
        particles.dripRate = 6.0f;
        particles.venomColor = {0.3f, 0.7f, 1.0f, 1.0f}; // Blue
        particles.smokeTrail = true;
        particles.smokeDensity = 12.0f;
        
        AudioParams audio;
        audio.hissOnLaunch = true;
        audio.hissFile = "sfx/snake_ice_hiss.wav";
        audio.hissVolume = 0.7f;
        audio.rattleOnImpact = true;
        audio.rattleFile = "sfx/ice_impact.wav";
        
        CollisionParams collision;
        collision.capsuleSegments = segments;
        collision.capsuleRadius = 0.16f;
        collision.enableCCD = true;
        
        return std::make_tuple(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("create_lightning_snake", [](float length = 4.0f, int segments = 12) {
        SnakeBodyParams body;
        body.segmentCount = segments;
        body.totalLength = length;
        body.segmentRadius = 0.14f;
        body.scaleMaterial = "mat/scales_lightning";
        body.dynamicMorph = true;
        
        MotionParams motion;
        motion.curlEnabled = true;
        motion.curlFrequency = 4.0f;
        motion.curlAmplitude = 0.5f;
        motion.homing = true;
        motion.homingTurnRate = 80.0f;
        
        ScaleVFXParams vfx;
        vfx.enableGlow = true;
        vfx.glowColor = {1.0f, 1.0f, 0.0f, 1.0f}; // Yellow
        vfx.glowIntensity = 2.5f;
        vfx.pulsate = true;
        vfx.pulsateSpeed = 8.0f;
        
        ParticleParams particles;
        particles.venomDrip = true;
        particles.dripRate = 15.0f;
        particles.venomColor = {1.0f, 1.0f, 0.0f, 1.0f}; // Yellow
        particles.smokeTrail = true;
        particles.smokeDensity = 25.0f;
        
        AudioParams audio;
        audio.hissOnLaunch = true;
        audio.hissFile = "sfx/snake_lightning_hiss.wav";
        audio.hissVolume = 1.0f;
        audio.rattleOnImpact = true;
        audio.rattleFile = "sfx/lightning_impact.wav";
        
        CollisionParams collision;
        collision.capsuleSegments = segments;
        collision.capsuleRadius = 0.14f;
        collision.enableCCD = true;
        
        return std::make_tuple(body, motion, vfx, particles, audio, collision);
    });

    // Utility functions for parameter creation
    lua.set_function("create_snake_body", [](int segments = 12, float length = 4.0f, float radius = 0.2f) {
        SnakeBodyParams body;
        body.segmentCount = segments;
        body.totalLength = length;
        body.segmentRadius = radius;
        body.scaleMaterial = "mat/scales_default";
        body.dynamicMorph = true;
        return body;
    });

    lua.set_function("create_snake_motion", [](bool curl = true, bool homing = true) {
        MotionParams motion;
        motion.curlEnabled = curl;
        motion.curlFrequency = 2.0f;
        motion.curlAmplitude = 0.3f;
        motion.homing = homing;
        motion.homingTurnRate = 45.0f;
        return motion;
    });

    lua.set_function("create_snake_vfx", [](bool glow = true, const glm::vec4& color = {0, 1, 0, 1}) {
        ScaleVFXParams vfx;
        vfx.enableGlow = glow;
        vfx.glowColor = color;
        vfx.glowIntensity = 1.5f;
        vfx.pulsate = true;
        vfx.pulsateSpeed = 3.0f;
        return vfx;
    });

    lua.set_function("create_snake_particles", [](bool venom = true, bool smoke = true) {
        ParticleParams particles;
        particles.venomDrip = venom;
        particles.dripRate = 8.0f;
        particles.venomColor = {0, 0.8, 0, 1};
        particles.smokeTrail = smoke;
        particles.smokeDensity = 15.0f;
        return particles;
    });

    lua.set_function("create_snake_audio", [](bool hiss = true, bool rattle = true) {
        AudioParams audio;
        audio.hissOnLaunch = hiss;
        audio.hissFile = "sfx/snake_hiss.wav";
        audio.hissVolume = 0.7f;
        audio.rattleOnImpact = rattle;
        audio.rattleFile = "sfx/scale_rattle.wav";
        return audio;
    });

    lua.set_function("create_snake_collision", [](int segments = 12, float radius = 0.2f) {
        CollisionParams collision;
        collision.capsuleSegments = segments;
        collision.capsuleRadius = radius;
        collision.enableCCD = true;
        return collision;
    });

    // Main snake spell generation function
    lua.set_function("spawn_snake_spell",
        [&](const SnakeBodyParams& b, const MotionParams& m, const ScaleVFXParams& v,
            const ParticleParams& p, const AudioParams& a, const CollisionParams& c) {
            auto factory = MainPlugin::instance().getSnakeSpellFactory();
            pendingSpells.emplace_back(factory->generateAsync(b, m, v, p, a, c), b.scaleMaterial);
        }
    );

    // Convenience functions for spawning predefined snakes
    lua.set_function("spawn_venom_snake", [&](float length = 4.0f, int segments = 12) {
        auto [body, motion, vfx, particles, audio, collision] = create_venom_snake(length, segments);
        spawn_snake_spell(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("spawn_fire_snake", [&](float length = 4.0f, int segments = 12) {
        auto [body, motion, vfx, particles, audio, collision] = create_fire_snake(length, segments);
        spawn_snake_spell(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("spawn_ice_snake", [&](float length = 4.0f, int segments = 12) {
        auto [body, motion, vfx, particles, audio, collision] = create_ice_snake(length, segments);
        spawn_snake_spell(body, motion, vfx, particles, audio, collision);
    });

    lua.set_function("spawn_lightning_snake", [&](float length = 4.0f, int segments = 12) {
        auto [body, motion, vfx, particles, audio, collision] = create_lightning_snake(length, segments);
        spawn_snake_spell(body, motion, vfx, particles, audio, collision);
    });
}

void SnakeSpellLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingSpells.begin(); it != pendingSpells.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                lua["print"]("Snake spell asset ready: " + it->second + 
                            " (mesh: " + std::to_string(bundle.mesh) +
                            ", motion: " + std::to_string(bundle.motionSim) +
                            ", vfx: " + std::to_string(bundle.vfx) +
                            ", particles: " + std::to_string(bundle.particles) +
                            ", audio: " + std::to_string(bundle.audio) +
                            ", collider: " + std::to_string(bundle.collider) + ")");
            } catch (const std::exception& e) { 
                lua["print"]("Snake spell asset error: " + it->second + " - " + e.what());
            }
            it = pendingSpells.erase(it);
        } else { ++it; }
    }
}

} // namespace SnakeSpells
} // namespace MagiTech
