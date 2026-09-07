#include "AlchemicalGrenadeLuaBindings.hpp"
#include "AlchemicalGrenadeFactory.hpp"
#include "AlchemicalGrenadeTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "core/Log.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace AlchemicalGrenades {

static std::vector<std::pair<std::future<GrenadeAssetBundle>, std::string>> pendingGrenades;
static std::map<std::string, GrenadeAssetBundle> loadedGrenades;

void AlchemicalGrenadeLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum<GrenadeType>("GrenadeType", {
        {"FIRE", GrenadeType::FIRE},
        {"ACID", GrenadeType::ACID},
        {"SMOKE", GrenadeType::SMOKE},
        {"FROST", GrenadeType::FROST},
        {"SHOCK", GrenadeType::SHOCK},
        {"HEALING", GrenadeType::HEALING},
        {"POISON", GrenadeType::POISON},
        {"EXPLOSIVE", GrenadeType::EXPLOSIVE},
        {"STUN", GrenadeType::STUN},
        {"CUSTOM", GrenadeType::CUSTOM}
    });

    lua.new_enum<CasingMaterial>("CasingMaterial", {
        {"GLASS", CasingMaterial::GLASS},
        {"METAL", CasingMaterial::METAL},
        {"CERAMIC", CasingMaterial::CERAMIC},
        {"CRYSTAL", CasingMaterial::CRYSTAL},
        {"ORGANIC", CasingMaterial::ORGANIC},
        {"CUSTOM", CasingMaterial::CUSTOM}
    });

    lua.new_enum<ParticleType>("ParticleType", {
        {"EMBER", ParticleType::EMBER},
        {"ACID_SPLASH", ParticleType::ACID_SPLASH},
        {"SMOKE_PUFF", ParticleType::SMOKE_PUFF},
        {"FROST_SPIKE", ParticleType::FROST_SPIKE},
        {"SPARK", ParticleType::SPARK},
        {"HEALING_GLOW", ParticleType::HEALING_GLOW},
        {"POISON_CLOUD", ParticleType::POISON_CLOUD},
        {"EXPLOSION_DEBRIS", ParticleType::EXPLOSION_DEBRIS},
        {"STUN_WAVE", ParticleType::STUN_WAVE},
        {"CUSTOM", ParticleType::CUSTOM}
    });

    lua.new_enum<BackgroundShape>("BackgroundShape", {
        {"CIRCLE", BackgroundShape::CIRCLE},
        {"SQUARE", BackgroundShape::SQUARE},
        {"HEXAGON", BackgroundShape::HEXAGON},
        {"DIAMOND", BackgroundShape::DIAMOND},
        {"NONE", BackgroundShape::NONE},
        {"CUSTOM", BackgroundShape::CUSTOM}
    });

    // Bind parameter structures
    lua.new_usertype<AlchemicalGrenadeParams>("AlchemicalGrenadeParams",
        sol::constructors<AlchemicalGrenadeParams()>(),
        "id", &AlchemicalGrenadeParams::id,
        "grenadeType", &AlchemicalGrenadeParams::grenadeType,
        "casingMaterial", &AlchemicalGrenadeParams::casingMaterial,
        "particleType", &AlchemicalGrenadeParams::particleType,
        "explosionType", &AlchemicalGrenadeParams::explosionType,
        "residueType", &AlchemicalGrenadeParams::residueType,
        "soundEffect", &AlchemicalGrenadeParams::soundEffect,
        "fuseTime", &AlchemicalGrenadeParams::fuseTime,
        "detonationDelay", &AlchemicalGrenadeParams::detonationDelay,
        "residueDuration", &AlchemicalGrenadeParams::residueDuration,
        "particleLifetime", &AlchemicalGrenadeParams::particleLifetime,
        "shardLifetime", &AlchemicalGrenadeParams::shardLifetime,
        "coreRadius", &AlchemicalGrenadeParams::coreRadius,
        "casingThickness", &AlchemicalGrenadeParams::casingThickness,
        "mass", &AlchemicalGrenadeParams::mass,
        "density", &AlchemicalGrenadeParams::density,
        "bounciness", &AlchemicalGrenadeParams::bounciness,
        "friction", &AlchemicalGrenadeParams::friction,
        "airResistance", &AlchemicalGrenadeParams::airResistance,
        "casingColorPrimary", &AlchemicalGrenadeParams::casingColorPrimary,
        "casingColorSecondary", &AlchemicalGrenadeParams::casingColorSecondary,
        "liquidColor", &AlchemicalGrenadeParams::liquidColor,
        "glowColor", &AlchemicalGrenadeParams::glowColor,
        "explosionColor", &AlchemicalGrenadeParams::explosionColor,
        "residueColor", &AlchemicalGrenadeParams::residueColor,
        "noiseScale", &AlchemicalGrenadeParams::noiseScale,
        "noiseSpeed", &AlchemicalGrenadeParams::noiseSpeed,
        "noiseIntensity", &AlchemicalGrenadeParams::noiseIntensity,
        "glowIntensity", &AlchemicalGrenadeParams::glowIntensity,
        "emissivePower", &AlchemicalGrenadeParams::emissivePower,
        "transparency", &AlchemicalGrenadeParams::transparency,
        "refractionIndex", &AlchemicalGrenadeParams::refractionIndex,
        "metallicness", &AlchemicalGrenadeParams::metallicness,
        "roughness", &AlchemicalGrenadeParams::roughness,
        "explosionRadius", &AlchemicalGrenadeParams::explosionRadius,
        "explosionIntensity", &AlchemicalGrenadeParams::explosionIntensity,
        "explosionForce", &AlchemicalGrenadeParams::explosionForce,
        "explosionDamage", &AlchemicalGrenadeParams::explosionDamage,
        "enableShockwave", &AlchemicalGrenadeParams::enableShockwave,
        "shockwaveRadius", &AlchemicalGrenadeParams::shockwaveRadius,
        "shockwaveForce", &AlchemicalGrenadeParams::shockwaveForce,
        "shrapnelCount", &AlchemicalGrenadeParams::shrapnelCount,
        "shardSpeed", &AlchemicalGrenadeParams::shardSpeed,
        "shardSize", &AlchemicalGrenadeParams::shardSize,
        "shardMass", &AlchemicalGrenadeParams::shardMass,
        "enableShrapnelPhysics", &AlchemicalGrenadeParams::enableShrapnelPhysics,
        "enableShrapnelDamage", &AlchemicalGrenadeParams::enableShrapnelDamage,
        "particleBurstCount", &AlchemicalGrenadeParams::particleBurstCount,
        "particleSpeed", &AlchemicalGrenadeParams::particleSpeed,
        "particleSize", &AlchemicalGrenadeParams::particleSize,
        "particleSpread", &AlchemicalGrenadeParams::particleSpread,
        "enableParticlePhysics", &AlchemicalGrenadeParams::enableParticlePhysics,
        "enableParticleTrails", &AlchemicalGrenadeParams::enableParticleTrails,
        "particleGravity", &AlchemicalGrenadeParams::particleGravity,
        "residueSpread", &AlchemicalGrenadeParams::residueSpread,
        "residueIntensity", &AlchemicalGrenadeParams::residueIntensity,
        "residueOpacity", &AlchemicalGrenadeParams::residueOpacity,
        "enableResiduePhysics", &AlchemicalGrenadeParams::enableResiduePhysics,
        "enableResidueDamage", &AlchemicalGrenadeParams::enableResidueDamage,
        "residueDamageRate", &AlchemicalGrenadeParams::residueDamageRate,
        "soundVolume", &AlchemicalGrenadeParams::soundVolume,
        "soundPitch", &AlchemicalGrenadeParams::soundPitch,
        "soundDuration", &AlchemicalGrenadeParams::soundDuration,
        "enableSpatialAudio", &AlchemicalGrenadeParams::enableSpatialAudio,
        "audioDistance", &AlchemicalGrenadeParams::audioDistance,
        "enableEcho", &AlchemicalGrenadeParams::enableEcho,
        "echoDelay", &AlchemicalGrenadeParams::echoDelay,
        "echoDecay", &AlchemicalGrenadeParams::echoDecay,
        "shaderType", &AlchemicalGrenadeParams::shaderType,
        "shaderIntensity", &AlchemicalGrenadeParams::shaderIntensity,
        "enableDistortion", &AlchemicalGrenadeParams::enableDistortion,
        "distortionStrength", &AlchemicalGrenadeParams::distortionStrength,
        "enableRefraction", &AlchemicalGrenadeParams::enableRefraction,
        "refractionStrength", &AlchemicalGrenadeParams::refractionStrength,
        "enableReflection", &AlchemicalGrenadeParams::enableReflection,
        "reflectionStrength", &AlchemicalGrenadeParams::reflectionStrength,
        "enableEmission", &AlchemicalGrenadeParams::enableEmission,
        "emissionStrength", &AlchemicalGrenadeParams::emissionStrength,
        "enablePhysics", &AlchemicalGrenadeParams::enablePhysics,
        "enableCollision", &AlchemicalGrenadeParams::enableCollision,
        "collisionRadius", &AlchemicalGrenadeParams::collisionRadius,
        "enableGravity", &AlchemicalGrenadeParams::enableGravity,
        "enableAirResistance", &AlchemicalGrenadeParams::enableAirResistance,
        "airResistanceFactor", &AlchemicalGrenadeParams::airResistanceFactor,
        "enableBounce", &AlchemicalGrenadeParams::enableBounce,
        "bounceFactor", &AlchemicalGrenadeParams::bounceFactor,
        "enableCaching", &AlchemicalGrenadeParams::enableCaching,
        "enableHotReload", &AlchemicalGrenadeParams::enableHotReload,
        "enableParallelProcessing", &AlchemicalGrenadeParams::enableParallelProcessing,
        "lodLevel", &AlchemicalGrenadeParams::lodLevel,
        "description", &AlchemicalGrenadeParams::description,
        "tags", &AlchemicalGrenadeParams::tags,
        "metadata", &AlchemicalGrenadeParams::metadata
    );

    lua.new_usertype<UIItemParams>("UIItemParams",
        sol::constructors<UIItemParams()>(),
        "iconSize", &UIItemParams::iconSize,
        "borderColor", &UIItemParams::borderColor,
        "backgroundShape", &UIItemParams::backgroundShape,
        "flashOnSelect", &UIItemParams::flashOnSelect,
        "borderThickness", &UIItemParams::borderThickness,
        "cornerRadius", &UIItemParams::cornerRadius,
        "enableGlow", &UIItemParams::enableGlow,
        "glowColor", &UIItemParams::glowColor,
        "glowIntensity", &UIItemParams::glowIntensity,
        "enablePulse", &UIItemParams::enablePulse,
        "pulseFrequency", &UIItemParams::pulseFrequency,
        "pulseAmplitude", &UIItemParams::pulseAmplitude,
        "enableHoverEffect", &UIItemParams::enableHoverEffect,
        "hoverScale", &UIItemParams::hoverScale,
        "hoverDuration", &UIItemParams::hoverDuration,
        "enableClickEffect", &UIItemParams::enableClickEffect,
        "clickScale", &UIItemParams::clickScale,
        "clickDuration", &UIItemParams::clickDuration,
        "label", &UIItemParams::label,
        "enableLabel", &UIItemParams::enableLabel,
        "labelColor", &UIItemParams::labelColor,
        "labelSize", &UIItemParams::labelSize,
        "labelFont", &UIItemParams::labelFont,
        "enableCaching", &UIItemParams::enableCaching,
        "enableHotReload", &UIItemParams::enableHotReload,
        "lodLevel", &UIItemParams::lodLevel,
        "description", &UIItemParams::description,
        "tags", &UIItemParams::tags,
        "metadata", &UIItemParams::metadata
    );

    // Main generation function
    lua.set_function("spawn_alchemical_grenade", [&](const AlchemicalGrenadeParams& g, const UIItemParams& u) {
        auto factory = MainPlugin::instance().getAlchemicalGrenadeFactory();
        if (!factory) {
            Log::error("AlchemicalGrenadeFactory not available");
            return GrenadeAssetBundle{};
        }
        
        auto fut = factory->generateAsync(g, u);
        pendingGrenades.emplace_back(std::move(fut), g.id);
        Log::info("Queued grenade generation for: {}", g.id);
        
        // Return the future result
        return fut.get();
    });

    // Helper functions for common grenade types
    lua.set_function("create_fire_grenade", [&](std::string id, float radius, float fuseTime) {
        AlchemicalGrenadeParams g;
        g.id = id;
        g.grenadeType = GrenadeType::FIRE;
        g.casingMaterial = CasingMaterial::GLASS;
        g.particleType = ParticleType::EMBER;
        g.explosionType = ExplosionType::BURST;
        g.residueType = ResidueType::BURNING_GROUND;
        g.soundEffect = SoundEffect::FIRE_CRACKLE;
        g.fuseTime = fuseTime;
        g.coreRadius = radius;
        g.casingThickness = radius * 0.1f;
        g.casingColorPrimary = glm::vec3(1.0f, 0.3f, 0.0f);
        g.casingColorSecondary = glm::vec3(1.0f, 0.8f, 0.2f);
        g.liquidColor = glm::vec4(1.0f, 0.4f, 0.0f, 0.8f);
        g.glowColor = glm::vec3(1.0f, 0.5f, 0.0f);
        g.explosionColor = glm::vec3(1.0f, 0.6f, 0.2f);
        g.residueColor = glm::vec4(1.0f, 0.3f, 0.0f, 0.6f);
        g.noiseScale = 3.0f;
        g.noiseSpeed = 1.0f;
        g.glowIntensity = 0.8f;
        g.emissivePower = 0.5f;
        g.explosionRadius = radius * 3.0f;
        g.explosionIntensity = 1.2f;
        g.shrapnelCount = 8;
        g.shardSpeed = 12.0f;
        g.particleBurstCount = 60;
        g.residueDuration = 5.0f;
        
        UIItemParams u;
        u.iconSize = 64;
        u.backgroundShape = BackgroundShape::CIRCLE;
        u.borderColor = glm::vec4(1.0f, 0.5f, 0.0f, 0.8f);
        u.flashOnSelect = true;
        u.enableGlow = true;
        u.glowColor = g.glowColor;
        u.glowIntensity = 0.6f;
        
        return spawn_alchemical_grenade(g, u);
    });

    lua.set_function("create_acid_grenade", [&](std::string id, float radius, float fuseTime) {
        AlchemicalGrenadeParams g;
        g.id = id;
        g.grenadeType = GrenadeType::ACID;
        g.casingMaterial = CasingMaterial::GLASS;
        g.particleType = ParticleType::ACID_SPLASH;
        g.explosionType = ExplosionType::IMPACT;
        g.residueType = ResidueType::DRIPPING_FLUID;
        g.soundEffect = SoundEffect::ACID_HISS;
        g.fuseTime = fuseTime;
        g.coreRadius = radius;
        g.casingThickness = radius * 0.1f;
        g.casingColorPrimary = glm::vec3(0.2f, 1.0f, 0.2f);
        g.casingColorSecondary = glm::vec3(0.6f, 1.0f, 0.6f);
        g.liquidColor = glm::vec4(0.0f, 0.8f, 0.0f, 0.7f);
        g.glowColor = glm::vec3(0.3f, 1.0f, 0.3f);
        g.explosionColor = glm::vec3(0.4f, 1.0f, 0.4f);
        g.residueColor = glm::vec4(0.0f, 0.6f, 0.0f, 0.8f);
        g.noiseScale = 4.0f;
        g.noiseSpeed = 1.2f;
        g.glowIntensity = 0.6f;
        g.emissivePower = 0.3f;
        g.explosionRadius = radius * 4.0f;
        g.explosionIntensity = 1.0f;
        g.shrapnelCount = 6;
        g.shardSpeed = 8.0f;
        g.particleBurstCount = 80;
        g.residueDuration = 6.0f;
        
        UIItemParams u;
        u.iconSize = 64;
        u.backgroundShape = BackgroundShape::CIRCLE;
        u.borderColor = glm::vec4(0.2f, 1.0f, 0.2f, 0.8f);
        u.flashOnSelect = true;
        u.enableGlow = true;
        u.glowColor = g.glowColor;
        u.glowIntensity = 0.4f;
        
        return spawn_alchemical_grenade(g, u);
    });

    lua.set_function("create_frost_grenade", [&](std::string id, float radius, float fuseTime) {
        AlchemicalGrenadeParams g;
        g.id = id;
        g.grenadeType = GrenadeType::FROST;
        g.casingMaterial = CasingMaterial::CRYSTAL;
        g.particleType = ParticleType::FROST_SPIKE;
        g.explosionType = ExplosionType::BURST;
        g.residueType = ResidueType::FROST_PATCH;
        g.soundEffect = SoundEffect::FROST_CRYSTAL;
        g.fuseTime = fuseTime;
        g.coreRadius = radius;
        g.casingThickness = radius * 0.15f;
        g.casingColorPrimary = glm::vec3(0.7f, 0.9f, 1.0f);
        g.casingColorSecondary = glm::vec3(1.0f, 1.0f, 1.0f);
        g.liquidColor = glm::vec4(0.4f, 0.8f, 1.0f, 0.8f);
        g.glowColor = glm::vec3(0.6f, 0.9f, 1.0f);
        g.explosionColor = glm::vec3(0.8f, 0.95f, 1.0f);
        g.residueColor = glm::vec4(0.5f, 0.8f, 1.0f, 0.7f);
        g.noiseScale = 2.5f;
        g.noiseSpeed = 0.8f;
        g.glowIntensity = 0.7f;
        g.emissivePower = 0.4f;
        g.explosionRadius = radius * 2.5f;
        g.explosionIntensity = 1.1f;
        g.shrapnelCount = 10;
        g.shardSpeed = 15.0f;
        g.particleBurstCount = 70;
        g.residueDuration = 4.0f;
        
        UIItemParams u;
        u.iconSize = 64;
        u.backgroundShape = BackgroundShape::HEXAGON;
        u.borderColor = glm::vec4(0.7f, 0.9f, 1.0f, 0.8f);
        u.flashOnSelect = true;
        u.enableGlow = true;
        u.glowColor = g.glowColor;
        u.glowIntensity = 0.5f;
        
        return spawn_alchemical_grenade(g, u);
    });

    lua.set_function("create_shock_grenade", [&](std::string id, float radius, float fuseTime) {
        AlchemicalGrenadeParams g;
        g.id = id;
        g.grenadeType = GrenadeType::SHOCK;
        g.casingMaterial = CasingMaterial::METAL;
        g.particleType = ParticleType::SPARK;
        g.explosionType = ExplosionType::PROXIMITY;
        g.residueType = ResidueType::NONE;
        g.soundEffect = SoundEffect::SHOCK_ZAP;
        g.fuseTime = fuseTime;
        g.coreRadius = radius;
        g.casingThickness = radius * 0.12f;
        g.casingColorPrimary = glm::vec3(1.0f, 1.0f, 0.3f);
        g.casingColorSecondary = glm::vec3(1.0f, 1.0f, 0.8f);
        g.liquidColor = glm::vec4(1.0f, 1.0f, 0.2f, 0.9f);
        g.glowColor = glm::vec3(1.0f, 1.0f, 0.4f);
        g.explosionColor = glm::vec3(1.0f, 1.0f, 0.6f);
        g.residueColor = glm::vec4(1.0f, 1.0f, 0.3f, 0.5f);
        g.noiseScale = 5.0f;
        g.noiseSpeed = 2.0f;
        g.glowIntensity = 1.0f;
        g.emissivePower = 0.8f;
        g.explosionRadius = radius * 3.5f;
        g.explosionIntensity = 1.3f;
        g.shrapnelCount = 12;
        g.shardSpeed = 18.0f;
        g.particleBurstCount = 90;
        g.residueDuration = 2.0f;
        
        UIItemParams u;
        u.iconSize = 64;
        u.backgroundShape = BackgroundShape::DIAMOND;
        u.borderColor = glm::vec4(1.0f, 1.0f, 0.3f, 0.8f);
        u.flashOnSelect = true;
        u.enableGlow = true;
        u.glowColor = g.glowColor;
        u.glowIntensity = 0.8f;
        
        return spawn_alchemical_grenade(g, u);
    });

    lua.set_function("create_healing_grenade", [&](std::string id, float radius, float fuseTime) {
        AlchemicalGrenadeParams g;
        g.id = id;
        g.grenadeType = GrenadeType::HEALING;
        g.casingMaterial = CasingMaterial::CRYSTAL;
        g.particleType = ParticleType::HEALING_GLOW;
        g.explosionType = ExplosionType::BURST;
        g.residueType = ResidueType::LINGERING_CLOUD;
        g.soundEffect = SoundEffect::HEALING_CHIME;
        g.fuseTime = fuseTime;
        g.coreRadius = radius;
        g.casingThickness = radius * 0.1f;
        g.casingColorPrimary = glm::vec3(0.3f, 1.0f, 0.3f);
        g.casingColorSecondary = glm::vec3(0.7f, 1.0f, 0.7f);
        g.liquidColor = glm::vec4(0.2f, 0.8f, 0.2f, 0.8f);
        g.glowColor = glm::vec3(0.4f, 1.0f, 0.4f);
        g.explosionColor = glm::vec3(0.5f, 1.0f, 0.5f);
        g.residueColor = glm::vec4(0.3f, 0.9f, 0.3f, 0.6f);
        g.noiseScale = 2.0f;
        g.noiseSpeed = 0.6f;
        g.glowIntensity = 0.9f;
        g.emissivePower = 0.6f;
        g.explosionRadius = radius * 2.0f;
        g.explosionIntensity = 0.8f;
        g.shrapnelCount = 4;
        g.shardSpeed = 6.0f;
        g.particleBurstCount = 50;
        g.residueDuration = 8.0f;
        
        UIItemParams u;
        u.iconSize = 64;
        u.backgroundShape = BackgroundShape::CIRCLE;
        u.borderColor = glm::vec4(0.3f, 1.0f, 0.3f, 0.8f);
        u.flashOnSelect = true;
        u.enableGlow = true;
        u.glowColor = g.glowColor;
        u.glowIntensity = 0.7f;
        
        return spawn_alchemical_grenade(g, u);
    });

    // Asset management functions
    lua.set_function("is_grenade_ready", [&](std::string id) {
        return loadedGrenades.find(id) != loadedGrenades.end();
    });

    lua.set_function("get_grenade", [&](std::string id) {
        auto it = loadedGrenades.find(id);
        if (it != loadedGrenades.end()) {
            return it->second;
        }
        return GrenadeAssetBundle{};
    });

    lua.set_function("clear_grenade_cache", [&]() {
        loadedGrenades.clear();
        Log::info("Grenade cache cleared");
    });

    // Utility functions
    lua.set_function("validate_grenade_params", [&](const AlchemicalGrenadeParams& g) {
        auto factory = MainPlugin::instance().getAlchemicalGrenadeFactory();
        if (!factory) return false;
        return factory->validateGrenadeParams(g);
    });

    lua.set_function("get_grenade_validation_errors", [&](const AlchemicalGrenadeParams& g) {
        auto factory = MainPlugin::instance().getAlchemicalGrenadeFactory();
        if (!factory) return std::vector<std::string>{};
        return factory->getGrenadeValidationErrors(g);
    });
}

void AlchemicalGrenadeLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingGrenades.begin(); it != pendingGrenades.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                loadedGrenades[it->second] = bundle;
                
                // Call Lua callback if available
                if (lua["on_grenade_ready"]) {
                    lua["on_grenade_ready"](it->second, bundle);
                }
                
                Log::info("Grenade ready: {}", it->second);
                it = pendingGrenades.erase(it);
            }
            catch (const std::exception& e) {
                Log::error("Failed to load grenade {}: {}", it->second, e.what());
                it = pendingGrenades.erase(it);
            }
        } else {
            ++it;
        }
    }
}

} // namespace AlchemicalGrenades
} // namespace MagiTech
