#include "CometProjectileTypes.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace CometProjectiles {

namespace ParamUtils {

// String to enum conversions
CometType parseCometType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "meteor" || lower == "meteorite") return CometType::METEOR;
    if (lower == "comet") return CometType::COMET;
    if (lower == "asteroid") return CometType::ASTEROID;
    if (lower == "falling_star" || lower == "fallingstar" || lower == "shooting_star") return CometType::FALLING_STAR;
    if (lower == "celestial_rock" || lower == "celestialrock") return CometType::CELESTIAL_ROCK;
    if (lower == "custom") return CometType::CUSTOM;
    
    Log::warn("Unknown comet type: {}, defaulting to METEOR", str);
    return CometType::METEOR;
}

CometShape parseCometShape(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "sphere" || lower == "round") return CometShape::SPHERE;
    if (lower == "irregular" || lower == "rough") return CometShape::IRREGULAR;
    if (lower == "fragmented" || lower == "fragment") return CometShape::FRAGMENTED;
    if (lower == "crystalline" || lower == "crystal") return CometShape::CRYSTALLINE;
    if (lower == "custom_shape" || lower == "custom") return CometShape::CUSTOM_SHAPE;
    
    Log::warn("Unknown comet shape: {}, defaulting to SPHERE", str);
    return CometShape::SPHERE;
}

TrailType parseTrailType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none" || lower == "no_trail") return TrailType::NONE;
    if (lower == "dust" || lower == "particles") return TrailType::DUST;
    if (lower == "fire" || lower == "flame") return TrailType::FIRE;
    if (lower == "smoke") return TrailType::SMOKE;
    if (lower == "sparks" || lower == "spark") return TrailType::SPARKS;
    if (lower == "custom") return TrailType::CUSTOM;
    
    Log::warn("Unknown trail type: {}, defaulting to DUST", str);
    return TrailType::DUST;
}

FragmentationType parseFragmentationType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none" || lower == "no_fragmentation") return FragmentationType::NONE;
    if (lower == "explosive" || lower == "explosion") return FragmentationType::EXPLOSIVE;
    if (lower == "shatter" || lower == "break") return FragmentationType::SHATTER;
    if (lower == "disintegrate" || lower == "vaporize") return FragmentationType::DISINTEGRATE;
    if (lower == "custom") return FragmentationType::CUSTOM;
    
    Log::warn("Unknown fragmentation type: {}, defaulting to NONE", str);
    return FragmentationType::NONE;
}

NoiseType parseNoiseType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "perlin") return NoiseType::PERLIN;
    if (lower == "simplex") return NoiseType::SIMPLEX;
    if (lower == "curl") return NoiseType::CURL;
    if (lower == "fractal") return NoiseType::FRACTAL;
    if (lower == "custom") return NoiseType::CUSTOM;
    
    Log::warn("Unknown noise type: {}, defaulting to PERLIN", str);
    return NoiseType::PERLIN;
}

BlendMode parseBlendMode(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "additive" || lower == "add") return BlendMode::ADDITIVE;
    if (lower == "multiply" || lower == "mult") return BlendMode::MULTIPLY;
    if (lower == "screen") return BlendMode::SCREEN;
    if (lower == "overlay") return BlendMode::OVERLAY;
    if (lower == "normal" || lower == "alpha") return BlendMode::NORMAL;
    
    Log::warn("Unknown blend mode: {}, defaulting to ADDITIVE", str);
    return BlendMode::ADDITIVE;
}

// Enum to string conversions
std::string cometTypeToString(CometType type) {
    switch (type) {
        case CometType::METEOR: return "meteor";
        case CometType::COMET: return "comet";
        case CometType::ASTEROID: return "asteroid";
        case CometType::FALLING_STAR: return "falling_star";
        case CometType::CELESTIAL_ROCK: return "celestial_rock";
        case CometType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string cometShapeToString(CometShape shape) {
    switch (shape) {
        case CometShape::SPHERE: return "sphere";
        case CometShape::IRREGULAR: return "irregular";
        case CometShape::FRAGMENTED: return "fragmented";
        case CometShape::CRYSTALLINE: return "crystalline";
        case CometShape::CUSTOM_SHAPE: return "custom_shape";
        default: return "unknown";
    }
}

std::string trailTypeToString(TrailType type) {
    switch (type) {
        case TrailType::NONE: return "none";
        case TrailType::DUST: return "dust";
        case TrailType::FIRE: return "fire";
        case TrailType::SMOKE: return "smoke";
        case TrailType::SPARKS: return "sparks";
        case TrailType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string fragmentationTypeToString(FragmentationType type) {
    switch (type) {
        case FragmentationType::NONE: return "none";
        case FragmentationType::EXPLOSIVE: return "explosive";
        case FragmentationType::SHATTER: return "shatter";
        case FragmentationType::DISINTEGRATE: return "disintegrate";
        case FragmentationType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string noiseTypeToString(NoiseType type) {
    switch (type) {
        case NoiseType::PERLIN: return "perlin";
        case NoiseType::SIMPLEX: return "simplex";
        case NoiseType::CURL: return "curl";
        case NoiseType::FRACTAL: return "fractal";
        case NoiseType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string blendModeToString(BlendMode mode) {
    switch (mode) {
        case BlendMode::ADDITIVE: return "additive";
        case BlendMode::MULTIPLY: return "multiply";
        case BlendMode::SCREEN: return "screen";
        case BlendMode::OVERLAY: return "overlay";
        case BlendMode::NORMAL: return "normal";
        default: return "unknown";
    }
}

// JSON serialization/deserialization
nlohmann::json toJson(const CometProjectileParams& params) {
    nlohmann::json j;
    
    // Basic properties
    j["id"] = params.id;
    j["cometType"] = cometTypeToString(params.cometType);
    j["cometShape"] = cometShapeToString(params.cometShape);
    j["trailType"] = trailTypeToString(params.trailType);
    j["fragmentationType"] = fragmentationTypeToString(params.fragmentationType);
    j["noiseType"] = noiseTypeToString(params.noiseType);
    j["blendMode"] = blendModeToString(params.blendMode);
    
    // Physical properties
    j["coreRadius"] = params.coreRadius;
    j["irregularity"] = params.irregularity;
    j["speed"] = params.speed;
    j["gravityInfluence"] = params.gravityInfluence;
    j["mass"] = params.mass;
    j["drag"] = params.drag;
    j["lift"] = params.lift;
    
    // Color properties
    j["heatColor"] = {params.heatColor.x, params.heatColor.y, params.heatColor.z};
    j["burnColor"] = {params.burnColor.x, params.burnColor.y, params.burnColor.z};
    j["coreColor"] = {params.coreColor.x, params.coreColor.y, params.coreColor.z};
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    j["dustColor"] = {params.dustColor.x, params.dustColor.y, params.dustColor.z, params.dustColor.w};
    j["sparkColor"] = {params.sparkColor.x, params.sparkColor.y, params.sparkColor.z, params.sparkColor.w};
    
    // Visual properties
    j["glowIntensity"] = params.glowIntensity;
    j["emissivePower"] = params.emissivePower;
    j["coreOpacity"] = params.coreOpacity;
    j["trailOpacity"] = params.trailOpacity;
    j["enableCoreGlow"] = params.enableCoreGlow;
    j["enableTrailGlow"] = params.enableTrailGlow;
    
    // Trail properties
    j["trailLength"] = params.trailLength;
    j["trailWidth"] = params.trailWidth;
    j["trailNoiseScale"] = params.trailNoiseScale;
    j["trailNoiseSpeed"] = params.trailNoiseSpeed;
    j["trailFadeSpeed"] = params.trailFadeSpeed;
    j["enableTrailFade"] = params.enableTrailFade;
    j["enableTrailDistortion"] = params.enableTrailDistortion;
    j["trailDistortionStrength"] = params.trailDistortionStrength;
    
    // Particle properties
    j["dustParticleCount"] = params.dustParticleCount;
    j["dustLifetime"] = params.dustLifetime;
    j["dustSize"] = params.dustSize;
    j["dustSpeed"] = params.dustSpeed;
    j["enableDustFade"] = params.enableDustFade;
    j["dustFadeSpeed"] = params.dustFadeSpeed;
    
    j["sparkParticleCount"] = params.sparkParticleCount;
    j["sparkLifetime"] = params.sparkLifetime;
    j["sparkSize"] = params.sparkSize;
    j["sparkSpeed"] = params.sparkSpeed;
    j["enableSparkFade"] = params.enableSparkFade;
    j["sparkFadeSpeed"] = params.sparkFadeSpeed;
    
    // Fragmentation properties
    j["fragmentationCount"] = params.fragmentationCount;
    j["fragmentSizeFactor"] = params.fragmentSizeFactor;
    j["fragmentSpread"] = params.fragmentSpread;
    j["fragmentVelocity"] = params.fragmentVelocity;
    j["enableFragmentPhysics"] = params.enableFragmentPhysics;
    j["fragmentLifetime"] = params.fragmentLifetime;
    
    // Shader properties
    j["shaderType"] = params.shaderType;
    j["shaderIntensity"] = params.shaderIntensity;
    j["enableDistortion"] = params.enableDistortion;
    j["distortionStrength"] = params.distortionStrength;
    j["enableBlur"] = params.enableBlur;
    j["blurStrength"] = params.blurStrength;
    j["enableHeatDistortion"] = params.enableHeatDistortion;
    j["heatDistortionStrength"] = params.heatDistortionStrength;
    
    // Physics properties
    j["enablePhysics"] = params.enablePhysics;
    j["enableCollision"] = params.enableCollision;
    j["collisionRadius"] = params.collisionRadius;
    j["enableGravity"] = params.enableGravity;
    j["enableAirResistance"] = params.enableAirResistance;
    j["airResistanceFactor"] = params.airResistanceFactor;
    
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

CometProjectileParams fromJson(const nlohmann::json& json) {
    CometProjectileParams params;
    
    try {
        // Basic properties
        params.id = json.value("id", "unnamed_comet");
        params.cometType = parseCometType(json.value("cometType", "meteor"));
        params.cometShape = parseCometShape(json.value("cometShape", "sphere"));
        params.trailType = parseTrailType(json.value("trailType", "dust"));
        params.fragmentationType = parseFragmentationType(json.value("fragmentationType", "none"));
        params.noiseType = parseNoiseType(json.value("noiseType", "perlin"));
        params.blendMode = parseBlendMode(json.value("blendMode", "additive"));
        
        // Physical properties
        params.coreRadius = json.value("coreRadius", 0.5f);
        params.irregularity = json.value("irregularity", 0.8f);
        params.speed = json.value("speed", 30.0f);
        params.gravityInfluence = json.value("gravityInfluence", 1.0f);
        params.mass = json.value("mass", 1.0f);
        params.drag = json.value("drag", 0.1f);
        params.lift = json.value("lift", 0.0f);
        
        // Color properties
        if (json.contains("heatColor") && json["heatColor"].is_array()) {
            auto& heat = json["heatColor"];
            params.heatColor = {heat[0], heat[1], heat[2]};
        } else {
            params.heatColor = {1.0f, 0.5f, 0.1f};
        }
        
        if (json.contains("burnColor") && json["burnColor"].is_array()) {
            auto& burn = json["burnColor"];
            params.burnColor = {burn[0], burn[1], burn[2]};
        } else {
            params.burnColor = {1.0f, 0.8f, 0.3f};
        }
        
        if (json.contains("coreColor") && json["coreColor"].is_array()) {
            auto& core = json["coreColor"];
            params.coreColor = {core[0], core[1], core[2]};
        } else {
            params.coreColor = {0.8f, 0.6f, 0.4f};
        }
        
        if (json.contains("glowColor") && json["glowColor"].is_array()) {
            auto& glow = json["glowColor"];
            params.glowColor = {glow[0], glow[1], glow[2]};
        } else {
            params.glowColor = {1.0f, 0.4f, 0.0f};
        }
        
        if (json.contains("dustColor") && json["dustColor"].is_array()) {
            auto& dust = json["dustColor"];
            params.dustColor = {dust[0], dust[1], dust[2], dust[3]};
        } else {
            params.dustColor = {0.5f, 0.5f, 0.5f, 0.6f};
        }
        
        if (json.contains("sparkColor") && json["sparkColor"].is_array()) {
            auto& spark = json["sparkColor"];
            params.sparkColor = {spark[0], spark[1], spark[2], spark[3]};
        } else {
            params.sparkColor = {1.0f, 0.4f, 0.1f, 1.0f};
        }
        
        // Visual properties
        params.glowIntensity = json.value("glowIntensity", 2.0f);
        params.emissivePower = json.value("emissivePower", 1.0f);
        params.coreOpacity = json.value("coreOpacity", 1.0f);
        params.trailOpacity = json.value("trailOpacity", 0.8f);
        params.enableCoreGlow = json.value("enableCoreGlow", true);
        params.enableTrailGlow = json.value("enableTrailGlow", true);
        
        // Trail properties
        params.trailLength = json.value("trailLength", 2.0f);
        params.trailWidth = json.value("trailWidth", 0.1f);
        params.trailNoiseScale = json.value("trailNoiseScale", 1.5f);
        params.trailNoiseSpeed = json.value("trailNoiseSpeed", 3.0f);
        params.trailFadeSpeed = json.value("trailFadeSpeed", 1.0f);
        params.enableTrailFade = json.value("enableTrailFade", true);
        params.enableTrailDistortion = json.value("enableTrailDistortion", true);
        params.trailDistortionStrength = json.value("trailDistortionStrength", 0.1f);
        
        // Particle properties
        params.dustParticleCount = json.value("dustParticleCount", 100);
        params.dustLifetime = json.value("dustLifetime", 1.5f);
        params.dustSize = json.value("dustSize", 0.05f);
        params.dustSpeed = json.value("dustSpeed", 1.0f);
        params.enableDustFade = json.value("enableDustFade", true);
        params.dustFadeSpeed = json.value("dustFadeSpeed", 1.0f);
        
        params.sparkParticleCount = json.value("sparkParticleCount", 30);
        params.sparkLifetime = json.value("sparkLifetime", 0.6f);
        params.sparkSize = json.value("sparkSize", 0.03f);
        params.sparkSpeed = json.value("sparkSpeed", 1.5f);
        params.enableSparkFade = json.value("enableSparkFade", true);
        params.sparkFadeSpeed = json.value("sparkFadeSpeed", 1.0f);
        
        // Fragmentation properties
        params.fragmentationCount = json.value("fragmentationCount", 0);
        params.fragmentSizeFactor = json.value("fragmentSizeFactor", 0.3f);
        params.fragmentSpread = json.value("fragmentSpread", 1.0f);
        params.fragmentVelocity = json.value("fragmentVelocity", 2.0f);
        params.enableFragmentPhysics = json.value("enableFragmentPhysics", true);
        params.fragmentLifetime = json.value("fragmentLifetime", 2.0f);
        
        // Shader properties
        params.shaderType = json.value("shaderType", "comet");
        params.shaderIntensity = json.value("shaderIntensity", 1.0f);
        params.enableDistortion = json.value("enableDistortion", true);
        params.distortionStrength = json.value("distortionStrength", 0.1f);
        params.enableBlur = json.value("enableBlur", false);
        params.blurStrength = json.value("blurStrength", 0.1f);
        params.enableHeatDistortion = json.value("enableHeatDistortion", false);
        params.heatDistortionStrength = json.value("heatDistortionStrength", 0.1f);
        
        // Physics properties
        params.enablePhysics = json.value("enablePhysics", true);
        params.enableCollision = json.value("enableCollision", true);
        params.collisionRadius = json.value("collisionRadius", 0.5f);
        params.enableGravity = json.value("enableGravity", true);
        params.enableAirResistance = json.value("enableAirResistance", true);
        params.airResistanceFactor = json.value("airResistanceFactor", 0.1f);
        
        // Performance properties
        params.enableCaching = json.value("enableCaching", true);
        params.enableHotReload = json.value("enableHotReload", true);
        params.enableParallelProcessing = json.value("enableParallelProcessing", true);
        params.lodLevel = json.value("lodLevel", 0);
        
        // Metadata
        params.description = json.value("description", "Generated comet projectile");
        if (json.contains("tags") && json["tags"].is_array()) {
            params.tags = json["tags"].get<std::vector<std::string>>();
        } else {
            params.tags = {"comet", "projectile"};
        }
        
        if (json.contains("metadata") && json["metadata"].is_object()) {
            params.metadata = json["metadata"].get<std::map<std::string, std::string>>();
        } else {
            params.metadata = {{"source", "json"}};
        }
        
    } catch (const std::exception& e) {
        Log::error("Error parsing comet projectile JSON: {}", e.what());
        // Return default parameters on error
        params.id = "error_loading";
        params.cometType = CometType::METEOR;
        params.cometShape = CometShape::SPHERE;
        params.trailType = TrailType::DUST;
        params.fragmentationType = FragmentationType::NONE;
        params.noiseType = NoiseType::PERLIN;
        params.blendMode = BlendMode::ADDITIVE;
        params.coreRadius = 0.5f;
        params.irregularity = 0.8f;
        params.speed = 30.0f;
        params.gravityInfluence = 1.0f;
        params.mass = 1.0f;
        params.drag = 0.1f;
        params.lift = 0.0f;
        params.heatColor = {1.0f, 0.5f, 0.1f};
        params.burnColor = {1.0f, 0.8f, 0.3f};
        params.coreColor = {0.8f, 0.6f, 0.4f};
        params.glowColor = {1.0f, 0.4f, 0.0f};
        params.dustColor = {0.5f, 0.5f, 0.5f, 0.6f};
        params.sparkColor = {1.0f, 0.4f, 0.1f, 1.0f};
        params.glowIntensity = 2.0f;
        params.emissivePower = 1.0f;
        params.coreOpacity = 1.0f;
        params.trailOpacity = 0.8f;
        params.enableCoreGlow = true;
        params.enableTrailGlow = true;
        params.trailLength = 2.0f;
        params.trailWidth = 0.1f;
        params.trailNoiseScale = 1.5f;
        params.trailNoiseSpeed = 3.0f;
        params.trailFadeSpeed = 1.0f;
        params.enableTrailFade = true;
        params.enableTrailDistortion = true;
        params.trailDistortionStrength = 0.1f;
        params.dustParticleCount = 100;
        params.dustLifetime = 1.5f;
        params.dustSize = 0.05f;
        params.dustSpeed = 1.0f;
        params.enableDustFade = true;
        params.dustFadeSpeed = 1.0f;
        params.sparkParticleCount = 30;
        params.sparkLifetime = 0.6f;
        params.sparkSize = 0.03f;
        params.sparkSpeed = 1.5f;
        params.enableSparkFade = true;
        params.sparkFadeSpeed = 1.0f;
        params.fragmentationCount = 0;
        params.fragmentSizeFactor = 0.3f;
        params.fragmentSpread = 1.0f;
        params.fragmentVelocity = 2.0f;
        params.enableFragmentPhysics = true;
        params.fragmentLifetime = 2.0f;
        params.shaderType = "comet";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableBlur = false;
        params.blurStrength = 0.1f;
        params.enableHeatDistortion = false;
        params.heatDistortionStrength = 0.1f;
        params.enablePhysics = true;
        params.enableCollision = true;
        params.collisionRadius = 0.5f;
        params.enableGravity = true;
        params.enableAirResistance = true;
        params.airResistanceFactor = 0.1f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Error loading comet projectile";
        params.tags = {"error", "comet", "projectile"};
        params.metadata = {{"error", "json_parse_failed"}};
    }
    
    return params;
}

} // namespace ParamUtils

} // namespace CometProjectiles
} // namespace MagiTech 
