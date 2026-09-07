#include "AlchemicalGrenadeTypes.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace AlchemicalGrenades {

namespace ParamUtils {

// String to enum conversions
GrenadeType parseGrenadeType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "fire" || lower == "flame") return GrenadeType::FIRE;
    if (lower == "acid" || lower == "corrosive") return GrenadeType::ACID;
    if (lower == "smoke" || lower == "fog") return GrenadeType::SMOKE;
    if (lower == "frost" || lower == "ice") return GrenadeType::FROST;
    if (lower == "shock" || lower == "electric") return GrenadeType::SHOCK;
    if (lower == "healing" || lower == "cure") return GrenadeType::HEALING;
    if (lower == "poison" || lower == "toxic") return GrenadeType::POISON;
    if (lower == "explosive" || lower == "bomb") return GrenadeType::EXPLOSIVE;
    if (lower == "stun" || lower == "concussion") return GrenadeType::STUN;
    if (lower == "custom") return GrenadeType::CUSTOM;
    
    Log::warn("Unknown grenade type: {}, defaulting to FIRE", str);
    return GrenadeType::FIRE;
}

CasingMaterial parseCasingMaterial(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "glass" || lower == "crystal") return CasingMaterial::GLASS;
    if (lower == "metal" || lower == "steel") return CasingMaterial::METAL;
    if (lower == "ceramic" || lower == "clay") return CasingMaterial::CERAMIC;
    if (lower == "crystal" || lower == "gem") return CasingMaterial::CRYSTAL;
    if (lower == "organic" || lower == "wood") return CasingMaterial::ORGANIC;
    if (lower == "custom") return CasingMaterial::CUSTOM;
    
    Log::warn("Unknown casing material: {}, defaulting to GLASS", str);
    return CasingMaterial::GLASS;
}

ParticleType parseParticleType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "ember" || lower == "spark") return ParticleType::EMBER;
    if (lower == "acid_splash" || lower == "acid") return ParticleType::ACID_SPLASH;
    if (lower == "smoke_puff" || lower == "smoke") return ParticleType::SMOKE_PUFF;
    if (lower == "frost_spike" || lower == "ice") return ParticleType::FROST_SPIKE;
    if (lower == "spark" || lower == "electric") return ParticleType::SPARK;
    if (lower == "healing_glow" || lower == "heal") return ParticleType::HEALING_GLOW;
    if (lower == "poison_cloud" || lower == "poison") return ParticleType::POISON_CLOUD;
    if (lower == "explosion_debris" || lower == "debris") return ParticleType::EXPLOSION_DEBRIS;
    if (lower == "stun_wave" || lower == "stun") return ParticleType::STUN_WAVE;
    if (lower == "custom") return ParticleType::CUSTOM;
    
    Log::warn("Unknown particle type: {}, defaulting to EMBER", str);
    return ParticleType::EMBER;
}

ExplosionType parseExplosionType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "burst" || lower == "instant") return ExplosionType::BURST;
    if (lower == "impact" || lower == "contact") return ExplosionType::IMPACT;
    if (lower == "timed" || lower == "delay") return ExplosionType::TIMED;
    if (lower == "proximity" || lower == "near") return ExplosionType::PROXIMITY;
    if (lower == "custom") return ExplosionType::CUSTOM;
    
    Log::warn("Unknown explosion type: {}, defaulting to BURST", str);
    return ExplosionType::BURST;
}

ResidueType parseResidueType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none" || lower == "no_residue") return ResidueType::NONE;
    if (lower == "lingering_cloud" || lower == "cloud") return ResidueType::LINGERING_CLOUD;
    if (lower == "surface_decal" || lower == "decal") return ResidueType::SURFACE_DECAL;
    if (lower == "dripping_fluid" || lower == "drip") return ResidueType::DRIPPING_FLUID;
    if (lower == "burning_ground" || lower == "burn") return ResidueType::BURNING_GROUND;
    if (lower == "frost_patch" || lower == "frost") return ResidueType::FROST_PATCH;
    if (lower == "custom") return ResidueType::CUSTOM;
    
    Log::warn("Unknown residue type: {}, defaulting to NONE", str);
    return ResidueType::NONE;
}

SoundEffect parseSoundEffect(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "grenade_explode" || lower == "explode") return SoundEffect::GRENADE_EXPLODE;
    if (lower == "glass_shatter" || lower == "shatter") return SoundEffect::GLASS_SHATTER;
    if (lower == "metal_crack" || lower == "crack") return SoundEffect::METAL_CRACK;
    if (lower == "acid_hiss" || lower == "hiss") return SoundEffect::ACID_HISS;
    if (lower == "fire_crackle" || lower == "crackle") return SoundEffect::FIRE_CRACKLE;
    if (lower == "frost_crystal" || lower == "crystal") return SoundEffect::FROST_CRYSTAL;
    if (lower == "shock_zap" || lower == "zap") return SoundEffect::SHOCK_ZAP;
    if (lower == "healing_chime" || lower == "chime") return SoundEffect::HEALING_CHIME;
    if (lower == "poison_gurgle" || lower == "gurgle") return SoundEffect::POISON_GURGLE;
    if (lower == "stun_thud" || lower == "thud") return SoundEffect::STUN_THUD;
    if (lower == "custom") return SoundEffect::CUSTOM;
    
    Log::warn("Unknown sound effect: {}, defaulting to GRENADE_EXPLODE", str);
    return SoundEffect::GRENADE_EXPLODE;
}

BackgroundShape parseBackgroundShape(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "circle" || lower == "round") return BackgroundShape::CIRCLE;
    if (lower == "square" || lower == "box") return BackgroundShape::SQUARE;
    if (lower == "hexagon" || lower == "hex") return BackgroundShape::HEXAGON;
    if (lower == "diamond" || lower == "rhombus") return BackgroundShape::DIAMOND;
    if (lower == "none" || lower == "transparent") return BackgroundShape::NONE;
    if (lower == "custom") return BackgroundShape::CUSTOM;
    
    Log::warn("Unknown background shape: {}, defaulting to CIRCLE", str);
    return BackgroundShape::CIRCLE;
}

// Enum to string conversions
std::string grenadeTypeToString(GrenadeType type) {
    switch (type) {
        case GrenadeType::FIRE: return "fire";
        case GrenadeType::ACID: return "acid";
        case GrenadeType::SMOKE: return "smoke";
        case GrenadeType::FROST: return "frost";
        case GrenadeType::SHOCK: return "shock";
        case GrenadeType::HEALING: return "healing";
        case GrenadeType::POISON: return "poison";
        case GrenadeType::EXPLOSIVE: return "explosive";
        case GrenadeType::STUN: return "stun";
        case GrenadeType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string casingMaterialToString(CasingMaterial material) {
    switch (material) {
        case CasingMaterial::GLASS: return "glass";
        case CasingMaterial::METAL: return "metal";
        case CasingMaterial::CERAMIC: return "ceramic";
        case CasingMaterial::CRYSTAL: return "crystal";
        case CasingMaterial::ORGANIC: return "organic";
        case CasingMaterial::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string particleTypeToString(ParticleType type) {
    switch (type) {
        case ParticleType::EMBER: return "ember";
        case ParticleType::ACID_SPLASH: return "acid_splash";
        case ParticleType::SMOKE_PUFF: return "smoke_puff";
        case ParticleType::FROST_SPIKE: return "frost_spike";
        case ParticleType::SPARK: return "spark";
        case ParticleType::HEALING_GLOW: return "healing_glow";
        case ParticleType::POISON_CLOUD: return "poison_cloud";
        case ParticleType::EXPLOSION_DEBRIS: return "explosion_debris";
        case ParticleType::STUN_WAVE: return "stun_wave";
        case ParticleType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string explosionTypeToString(ExplosionType type) {
    switch (type) {
        case ExplosionType::BURST: return "burst";
        case ExplosionType::IMPACT: return "impact";
        case ExplosionType::TIMED: return "timed";
        case ExplosionType::PROXIMITY: return "proximity";
        case ExplosionType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string residueTypeToString(ResidueType type) {
    switch (type) {
        case ResidueType::NONE: return "none";
        case ResidueType::LINGERING_CLOUD: return "lingering_cloud";
        case ResidueType::SURFACE_DECAL: return "surface_decal";
        case ResidueType::DRIPPING_FLUID: return "dripping_fluid";
        case ResidueType::BURNING_GROUND: return "burning_ground";
        case ResidueType::FROST_PATCH: return "frost_patch";
        case ResidueType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string soundEffectToString(SoundEffect effect) {
    switch (effect) {
        case SoundEffect::GRENADE_EXPLODE: return "grenade_explode";
        case SoundEffect::GLASS_SHATTER: return "glass_shatter";
        case SoundEffect::METAL_CRACK: return "metal_crack";
        case SoundEffect::ACID_HISS: return "acid_hiss";
        case SoundEffect::FIRE_CRACKLE: return "fire_crackle";
        case SoundEffect::FROST_CRYSTAL: return "frost_crystal";
        case SoundEffect::SHOCK_ZAP: return "shock_zap";
        case SoundEffect::HEALING_CHIME: return "healing_chime";
        case SoundEffect::POISON_GURGLE: return "poison_gurgle";
        case SoundEffect::STUN_THUD: return "stun_thud";
        case SoundEffect::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string backgroundShapeToString(BackgroundShape shape) {
    switch (shape) {
        case BackgroundShape::CIRCLE: return "circle";
        case BackgroundShape::SQUARE: return "square";
        case BackgroundShape::HEXAGON: return "hexagon";
        case BackgroundShape::DIAMOND: return "diamond";
        case BackgroundShape::NONE: return "none";
        case BackgroundShape::CUSTOM: return "custom";
        default: return "unknown";
    }
}

// JSON serialization/deserialization
nlohmann::json toJson(const AlchemicalGrenadeParams& params) {
    nlohmann::json j;
    
    // Basic properties
    j["id"] = params.id;
    j["grenadeType"] = grenadeTypeToString(params.grenadeType);
    j["casingMaterial"] = casingMaterialToString(params.casingMaterial);
    j["particleType"] = particleTypeToString(params.particleType);
    j["explosionType"] = explosionTypeToString(params.explosionType);
    j["residueType"] = residueTypeToString(params.residueType);
    j["soundEffect"] = soundEffectToString(params.soundEffect);
    
    // Timing properties
    j["fuseTime"] = params.fuseTime;
    j["detonationDelay"] = params.detonationDelay;
    j["residueDuration"] = params.residueDuration;
    j["particleLifetime"] = params.particleLifetime;
    j["shardLifetime"] = params.shardLifetime;
    
    // Physical properties
    j["coreRadius"] = params.coreRadius;
    j["casingThickness"] = params.casingThickness;
    j["mass"] = params.mass;
    j["density"] = params.density;
    j["bounciness"] = params.bounciness;
    j["friction"] = params.friction;
    j["airResistance"] = params.airResistance;
    
    // Color properties
    j["casingColorPrimary"] = {params.casingColorPrimary.x, params.casingColorPrimary.y, params.casingColorPrimary.z};
    j["casingColorSecondary"] = {params.casingColorSecondary.x, params.casingColorSecondary.y, params.casingColorSecondary.z};
    j["liquidColor"] = {params.liquidColor.x, params.liquidColor.y, params.liquidColor.z, params.liquidColor.w};
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    j["explosionColor"] = {params.explosionColor.x, params.explosionColor.y, params.explosionColor.z};
    j["residueColor"] = {params.residueColor.x, params.residueColor.y, params.residueColor.z, params.residueColor.w};
    
    // Visual properties
    j["noiseScale"] = params.noiseScale;
    j["noiseSpeed"] = params.noiseSpeed;
    j["noiseIntensity"] = params.noiseIntensity;
    j["glowIntensity"] = params.glowIntensity;
    j["emissivePower"] = params.emissivePower;
    j["transparency"] = params.transparency;
    j["refractionIndex"] = params.refractionIndex;
    j["metallicness"] = params.metallicness;
    j["roughness"] = params.roughness;
    
    // Explosion properties
    j["explosionRadius"] = params.explosionRadius;
    j["explosionIntensity"] = params.explosionIntensity;
    j["explosionForce"] = params.explosionForce;
    j["explosionDamage"] = params.explosionDamage;
    j["enableShockwave"] = params.enableShockwave;
    j["shockwaveRadius"] = params.shockwaveRadius;
    j["shockwaveForce"] = params.shockwaveForce;
    
    // Shrapnel properties
    j["shrapnelCount"] = params.shrapnelCount;
    j["shardSpeed"] = params.shardSpeed;
    j["shardSize"] = params.shardSize;
    j["shardMass"] = params.shardMass;
    j["enableShrapnelPhysics"] = params.enableShrapnelPhysics;
    j["enableShrapnelDamage"] = params.enableShrapnelDamage;
    
    // Particle properties
    j["particleBurstCount"] = params.particleBurstCount;
    j["particleSpeed"] = params.particleSpeed;
    j["particleSize"] = params.particleSize;
    j["particleSpread"] = params.particleSpread;
    j["enableParticlePhysics"] = params.enableParticlePhysics;
    j["enableParticleTrails"] = params.enableParticleTrails;
    j["particleGravity"] = params.particleGravity;
    
    // Residue properties
    j["residueSpread"] = params.residueSpread;
    j["residueIntensity"] = params.residueIntensity;
    j["residueOpacity"] = params.residueOpacity;
    j["enableResiduePhysics"] = params.enableResiduePhysics;
    j["enableResidueDamage"] = params.enableResidueDamage;
    j["residueDamageRate"] = params.residueDamageRate;
    
    // Audio properties
    j["soundVolume"] = params.soundVolume;
    j["soundPitch"] = params.soundPitch;
    j["soundDuration"] = params.soundDuration;
    j["enableSpatialAudio"] = params.enableSpatialAudio;
    j["audioDistance"] = params.audioDistance;
    j["enableEcho"] = params.enableEcho;
    j["echoDelay"] = params.echoDelay;
    j["echoDecay"] = params.echoDecay;
    
    // Shader properties
    j["shaderType"] = params.shaderType;
    j["shaderIntensity"] = params.shaderIntensity;
    j["enableDistortion"] = params.enableDistortion;
    j["distortionStrength"] = params.distortionStrength;
    j["enableRefraction"] = params.enableRefraction;
    j["refractionStrength"] = params.refractionStrength;
    j["enableReflection"] = params.enableReflection;
    j["reflectionStrength"] = params.reflectionStrength;
    j["enableEmission"] = params.enableEmission;
    j["emissionStrength"] = params.emissionStrength;
    
    // Physics properties
    j["enablePhysics"] = params.enablePhysics;
    j["enableCollision"] = params.enableCollision;
    j["collisionRadius"] = params.collisionRadius;
    j["enableGravity"] = params.enableGravity;
    j["enableAirResistance"] = params.enableAirResistance;
    j["airResistanceFactor"] = params.airResistanceFactor;
    j["enableBounce"] = params.enableBounce;
    j["bounceFactor"] = params.bounceFactor;
    
    // Performance properties
    j["enableCaching"] = params.enableCaching;
    j["enableHotReload"] = params.enableHotReload;
    j["enableParallelProcessing"] = params.enableParallelProcessing;
    j["lodLevel"] = params.lodLevel;
    
    // Metadata
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    return j;
}

AlchemicalGrenadeParams fromJson(const nlohmann::json& json) {
    AlchemicalGrenadeParams params;
    
    try {
        // Basic properties
        params.id = json.value("id", "unnamed_grenade");
        params.grenadeType = parseGrenadeType(json.value("grenadeType", "fire"));
        params.casingMaterial = parseCasingMaterial(json.value("casingMaterial", "glass"));
        params.particleType = parseParticleType(json.value("particleType", "ember"));
        params.explosionType = parseExplosionType(json.value("explosionType", "burst"));
        params.residueType = parseResidueType(json.value("residueType", "none"));
        params.soundEffect = parseSoundEffect(json.value("soundEffect", "grenade_explode"));
        
        // Timing properties
        params.fuseTime = json.value("fuseTime", 2.0f);
        params.detonationDelay = json.value("detonationDelay", 0.0f);
        params.residueDuration = json.value("residueDuration", 5.0f);
        params.particleLifetime = json.value("particleLifetime", 0.5f);
        params.shardLifetime = json.value("shardLifetime", 0.6f);
        
        // Physical properties
        params.coreRadius = json.value("coreRadius", 0.15f);
        params.casingThickness = json.value("casingThickness", 0.02f);
        params.mass = json.value("mass", 1.0f);
        params.density = json.value("density", 1.0f);
        params.bounciness = json.value("bounciness", 0.3f);
        params.friction = json.value("friction", 0.5f);
        params.airResistance = json.value("airResistance", 0.1f);
        
        // Color properties
        if (json.contains("casingColorPrimary") && json["casingColorPrimary"].is_array()) {
            auto& primary = json["casingColorPrimary"];
            params.casingColorPrimary = {primary[0], primary[1], primary[2]};
        } else {
            params.casingColorPrimary = {0.8f, 0.2f, 0.0f};
        }
        
        if (json.contains("casingColorSecondary") && json["casingColorSecondary"].is_array()) {
            auto& secondary = json["casingColorSecondary"];
            params.casingColorSecondary = {secondary[0], secondary[1], secondary[2]};
        } else {
            params.casingColorSecondary = {1.0f, 0.6f, 0.4f};
        }
        
        if (json.contains("liquidColor") && json["liquidColor"].is_array()) {
            auto& liquid = json["liquidColor"];
            params.liquidColor = {liquid[0], liquid[1], liquid[2], liquid[3]};
        } else {
            params.liquidColor = {1.0f, 0.3f, 0.0f, 0.8f};
        }
        
        if (json.contains("glowColor") && json["glowColor"].is_array()) {
            auto& glow = json["glowColor"];
            params.glowColor = {glow[0], glow[1], glow[2]};
        } else {
            params.glowColor = {1.0f, 0.8f, 0.5f};
        }
        
        if (json.contains("explosionColor") && json["explosionColor"].is_array()) {
            auto& explosion = json["explosionColor"];
            params.explosionColor = {explosion[0], explosion[1], explosion[2]};
        } else {
            params.explosionColor = {1.0f, 0.5f, 0.0f};
        }
        
        if (json.contains("residueColor") && json["residueColor"].is_array()) {
            auto& residue = json["residueColor"];
            params.residueColor = {residue[0], residue[1], residue[2], residue[3]};
        } else {
            params.residueColor = {0.5f, 0.5f, 0.5f, 0.6f};
        }
        
        // Visual properties
        params.noiseScale = json.value("noiseScale", 3.0f);
        params.noiseSpeed = json.value("noiseSpeed", 1.0f);
        params.noiseIntensity = json.value("noiseIntensity", 0.5f);
        params.glowIntensity = json.value("glowIntensity", 1.0f);
        params.emissivePower = json.value("emissivePower", 1.0f);
        params.transparency = json.value("transparency", 0.8f);
        params.refractionIndex = json.value("refractionIndex", 1.5f);
        params.metallicness = json.value("metallicness", 0.0f);
        params.roughness = json.value("roughness", 0.5f);
        
        // Explosion properties
        params.explosionRadius = json.value("explosionRadius", 3.0f);
        params.explosionIntensity = json.value("explosionIntensity", 1.2f);
        params.explosionForce = json.value("explosionForce", 10.0f);
        params.explosionDamage = json.value("explosionDamage", 50.0f);
        params.enableShockwave = json.value("enableShockwave", true);
        params.shockwaveRadius = json.value("shockwaveRadius", 5.0f);
        params.shockwaveForce = json.value("shockwaveForce", 5.0f);
        
        // Shrapnel properties
        params.shrapnelCount = json.value("shrapnelCount", 8);
        params.shardSpeed = json.value("shardSpeed", 12.0f);
        params.shardSize = json.value("shardSize", 0.01f);
        params.shardMass = json.value("shardMass", 0.02f);
        params.enableShrapnelPhysics = json.value("enableShrapnelPhysics", true);
        params.enableShrapnelDamage = json.value("enableShrapnelDamage", true);
        
        // Particle properties
        params.particleBurstCount = json.value("particleBurstCount", 60);
        params.particleSpeed = json.value("particleSpeed", 5.0f);
        params.particleSize = json.value("particleSize", 0.02f);
        params.particleSpread = json.value("particleSpread", 1.0f);
        params.enableParticlePhysics = json.value("enableParticlePhysics", true);
        params.enableParticleTrails = json.value("enableParticleTrails", true);
        params.particleGravity = json.value("particleGravity", 0.5f);
        
        // Residue properties
        params.residueSpread = json.value("residueSpread", 2.0f);
        params.residueIntensity = json.value("residueIntensity", 1.0f);
        params.residueOpacity = json.value("residueOpacity", 0.6f);
        params.enableResiduePhysics = json.value("enableResiduePhysics", true);
        params.enableResidueDamage = json.value("enableResidueDamage", false);
        params.residueDamageRate = json.value("residueDamageRate", 5.0f);
        
        // Audio properties
        params.soundVolume = json.value("soundVolume", 1.0f);
        params.soundPitch = json.value("soundPitch", 1.0f);
        params.soundDuration = json.value("soundDuration", 1.0f);
        params.enableSpatialAudio = json.value("enableSpatialAudio", true);
        params.audioDistance = json.value("audioDistance", 10.0f);
        params.enableEcho = json.value("enableEcho", false);
        params.echoDelay = json.value("echoDelay", 0.1f);
        params.echoDecay = json.value("echoDecay", 0.5f);
        
        // Shader properties
        params.shaderType = json.value("shaderType", "grenade");
        params.shaderIntensity = json.value("shaderIntensity", 1.0f);
        params.enableDistortion = json.value("enableDistortion", true);
        params.distortionStrength = json.value("distortionStrength", 0.1f);
        params.enableRefraction = json.value("enableRefraction", true);
        params.refractionStrength = json.value("refractionStrength", 0.1f);
        params.enableReflection = json.value("enableReflection", false);
        params.reflectionStrength = json.value("reflectionStrength", 0.1f);
        params.enableEmission = json.value("enableEmission", true);
        params.emissionStrength = json.value("emissionStrength", 0.5f);
        
        // Physics properties
        params.enablePhysics = json.value("enablePhysics", true);
        params.enableCollision = json.value("enableCollision", true);
        params.collisionRadius = json.value("collisionRadius", 0.15f);
        params.enableGravity = json.value("enableGravity", true);
        params.enableAirResistance = json.value("enableAirResistance", true);
        params.airResistanceFactor = json.value("airResistanceFactor", 0.1f);
        params.enableBounce = json.value("enableBounce", true);
        params.bounceFactor = json.value("bounceFactor", 0.3f);
        
        // Performance properties
        params.enableCaching = json.value("enableCaching", true);
        params.enableHotReload = json.value("enableHotReload", true);
        params.enableParallelProcessing = json.value("enableParallelProcessing", true);
        params.lodLevel = json.value("lodLevel", 0);
        
        // Metadata
        params.description = json.value("description", "Generated alchemical grenade");
        if (json.contains("tags") && json["tags"].is_array()) {
            params.tags = json["tags"].get<std::vector<std::string>>();
        } else {
            params.tags = {"grenade", "alchemical"};
        }
        
        if (json.contains("metadata") && json["metadata"].is_object()) {
            params.metadata = json["metadata"].get<std::map<std::string, std::string>>();
        } else {
            params.metadata = {{"source", "json"}};
        }
        
    } catch (const std::exception& e) {
        Log::error("Error parsing alchemical grenade JSON: {}", e.what());
        // Return default parameters on error
        params.id = "error_loading";
        params.grenadeType = GrenadeType::FIRE;
        params.casingMaterial = CasingMaterial::GLASS;
        params.particleType = ParticleType::EMBER;
        params.explosionType = ExplosionType::BURST;
        params.residueType = ResidueType::NONE;
        params.soundEffect = SoundEffect::GRENADE_EXPLODE;
        params.fuseTime = 2.0f;
        params.detonationDelay = 0.0f;
        params.residueDuration = 5.0f;
        params.particleLifetime = 0.5f;
        params.shardLifetime = 0.6f;
        params.coreRadius = 0.15f;
        params.casingThickness = 0.02f;
        params.mass = 1.0f;
        params.density = 1.0f;
        params.bounciness = 0.3f;
        params.friction = 0.5f;
        params.airResistance = 0.1f;
        params.casingColorPrimary = {0.8f, 0.2f, 0.0f};
        params.casingColorSecondary = {1.0f, 0.6f, 0.4f};
        params.liquidColor = {1.0f, 0.3f, 0.0f, 0.8f};
        params.glowColor = {1.0f, 0.8f, 0.5f};
        params.explosionColor = {1.0f, 0.5f, 0.0f};
        params.residueColor = {0.5f, 0.5f, 0.5f, 0.6f};
        params.noiseScale = 3.0f;
        params.noiseSpeed = 1.0f;
        params.noiseIntensity = 0.5f;
        params.glowIntensity = 1.0f;
        params.emissivePower = 1.0f;
        params.transparency = 0.8f;
        params.refractionIndex = 1.5f;
        params.metallicness = 0.0f;
        params.roughness = 0.5f;
        params.explosionRadius = 3.0f;
        params.explosionIntensity = 1.2f;
        params.explosionForce = 10.0f;
        params.explosionDamage = 50.0f;
        params.enableShockwave = true;
        params.shockwaveRadius = 5.0f;
        params.shockwaveForce = 5.0f;
        params.shrapnelCount = 8;
        params.shardSpeed = 12.0f;
        params.shardSize = 0.01f;
        params.shardMass = 0.02f;
        params.enableShrapnelPhysics = true;
        params.enableShrapnelDamage = true;
        params.particleBurstCount = 60;
        params.particleSpeed = 5.0f;
        params.particleSize = 0.02f;
        params.particleSpread = 1.0f;
        params.enableParticlePhysics = true;
        params.enableParticleTrails = true;
        params.particleGravity = 0.5f;
        params.residueSpread = 2.0f;
        params.residueIntensity = 1.0f;
        params.residueOpacity = 0.6f;
        params.enableResiduePhysics = true;
        params.enableResidueDamage = false;
        params.residueDamageRate = 5.0f;
        params.soundVolume = 1.0f;
        params.soundPitch = 1.0f;
        params.soundDuration = 1.0f;
        params.enableSpatialAudio = true;
        params.audioDistance = 10.0f;
        params.enableEcho = false;
        params.echoDelay = 0.1f;
        params.echoDecay = 0.5f;
        params.shaderType = "grenade";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableRefraction = true;
        params.refractionStrength = 0.1f;
        params.enableReflection = false;
        params.reflectionStrength = 0.1f;
        params.enableEmission = true;
        params.emissionStrength = 0.5f;
        params.enablePhysics = true;
        params.enableCollision = true;
        params.collisionRadius = 0.15f;
        params.enableGravity = true;
        params.enableAirResistance = true;
        params.airResistanceFactor = 0.1f;
        params.enableBounce = true;
        params.bounceFactor = 0.3f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Error loading alchemical grenade";
        params.tags = {"error", "grenade", "alchemical"};
        params.metadata = {{"error", "json_parse_failed"}};
    }
    
    return params;
}

nlohmann::json toJson(const UIItemParams& params) {
    nlohmann::json j;
    
    // Icon properties
    j["iconSize"] = params.iconSize;
    j["borderColor"] = {params.borderColor.x, params.borderColor.y, params.borderColor.z, params.borderColor.w};
    j["backgroundShape"] = backgroundShapeToString(params.backgroundShape);
    j["flashOnSelect"] = params.flashOnSelect;
    
    // Visual properties
    j["borderThickness"] = params.borderThickness;
    j["cornerRadius"] = params.cornerRadius;
    j["enableGlow"] = params.enableGlow;
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    j["glowIntensity"] = params.glowIntensity;
    j["enablePulse"] = params.enablePulse;
    j["pulseFrequency"] = params.pulseFrequency;
    j["pulseAmplitude"] = params.pulseAmplitude;
    
    // Animation properties
    j["enableHoverEffect"] = params.enableHoverEffect;
    j["hoverScale"] = params.hoverScale;
    j["hoverDuration"] = params.hoverDuration;
    j["enableClickEffect"] = params.enableClickEffect;
    j["clickScale"] = params.clickScale;
    j["clickDuration"] = params.clickDuration;
    
    // Text properties
    j["label"] = params.label;
    j["enableLabel"] = params.enableLabel;
    j["labelColor"] = {params.labelColor.x, params.labelColor.y, params.labelColor.z};
    j["labelSize"] = params.labelSize;
    j["labelFont"] = params.labelFont;
    
    // Performance properties
    j["enableCaching"] = params.enableCaching;
    j["enableHotReload"] = params.enableHotReload;
    j["lodLevel"] = params.lodLevel;
    
    // Metadata
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    return j;
}

UIItemParams fromJson(const nlohmann::json& json) {
    UIItemParams params;
    
    try {
        // Icon properties
        params.iconSize = json.value("iconSize", 48);
        if (json.contains("borderColor") && json["borderColor"].is_array()) {
            auto& border = json["borderColor"];
            params.borderColor = {border[0], border[1], border[2], border[3]};
        } else {
            params.borderColor = {1.0f, 1.0f, 1.0f, 0.8f};
        }
        params.backgroundShape = parseBackgroundShape(json.value("backgroundShape", "circle"));
        params.flashOnSelect = json.value("flashOnSelect", true);
        
        // Visual properties
        params.borderThickness = json.value("borderThickness", 2.0f);
        params.cornerRadius = json.value("cornerRadius", 4.0f);
        params.enableGlow = json.value("enableGlow", false);
        if (json.contains("glowColor") && json["glowColor"].is_array()) {
            auto& glow = json["glowColor"];
            params.glowColor = {glow[0], glow[1], glow[2]};
        } else {
            params.glowColor = {1.0f, 1.0f, 1.0f};
        }
        params.glowIntensity = json.value("glowIntensity", 1.0f);
        params.enablePulse = json.value("enablePulse", false);
        params.pulseFrequency = json.value("pulseFrequency", 2.0f);
        params.pulseAmplitude = json.value("pulseAmplitude", 0.1f);
        
        // Animation properties
        params.enableHoverEffect = json.value("enableHoverEffect", true);
        params.hoverScale = json.value("hoverScale", 1.1f);
        params.hoverDuration = json.value("hoverDuration", 0.2f);
        params.enableClickEffect = json.value("enableClickEffect", true);
        params.clickScale = json.value("clickScale", 0.95f);
        params.clickDuration = json.value("clickDuration", 0.1f);
        
        // Text properties
        params.label = json.value("label", "");
        params.enableLabel = json.value("enableLabel", false);
        if (json.contains("labelColor") && json["labelColor"].is_array()) {
            auto& label = json["labelColor"];
            params.labelColor = {label[0], label[1], label[2]};
        } else {
            params.labelColor = {1.0f, 1.0f, 1.0f};
        }
        params.labelSize = json.value("labelSize", 12.0f);
        params.labelFont = json.value("labelFont", "default");
        
        // Performance properties
        params.enableCaching = json.value("enableCaching", true);
        params.enableHotReload = json.value("enableHotReload", true);
        params.lodLevel = json.value("lodLevel", 0);
        
        // Metadata
        params.description = json.value("description", "Generated UI item");
        if (json.contains("tags") && json["tags"].is_array()) {
            params.tags = json["tags"].get<std::vector<std::string>>();
        } else {
            params.tags = {"ui", "item"};
        }
        
        if (json.contains("metadata") && json["metadata"].is_object()) {
            params.metadata = json["metadata"].get<std::map<std::string, std::string>>();
        } else {
            params.metadata = {{"source", "json"}};
        }
        
    } catch (const std::exception& e) {
        Log::error("Error parsing UI item JSON: {}", e.what());
        // Return default parameters on error
        params.iconSize = 48;
        params.borderColor = {1.0f, 1.0f, 1.0f, 0.8f};
        params.backgroundShape = BackgroundShape::CIRCLE;
        params.flashOnSelect = true;
        params.borderThickness = 2.0f;
        params.cornerRadius = 4.0f;
        params.enableGlow = false;
        params.glowColor = {1.0f, 1.0f, 1.0f};
        params.glowIntensity = 1.0f;
        params.enablePulse = false;
        params.pulseFrequency = 2.0f;
        params.pulseAmplitude = 0.1f;
        params.enableHoverEffect = true;
        params.hoverScale = 1.1f;
        params.hoverDuration = 0.2f;
        params.enableClickEffect = true;
        params.clickScale = 0.95f;
        params.clickDuration = 0.1f;
        params.label = "";
        params.enableLabel = false;
        params.labelColor = {1.0f, 1.0f, 1.0f};
        params.labelSize = 12.0f;
        params.labelFont = "default";
        params.enableCaching = true;
        params.enableHotReload = true;
        params.lodLevel = 0;
        params.description = "Error loading UI item";
        params.tags = {"error", "ui", "item"};
        params.metadata = {{"error", "json_parse_failed"}};
    }
    
    return params;
}

} // namespace ParamUtils

} // namespace AlchemicalGrenades
} // namespace MagiTech 
