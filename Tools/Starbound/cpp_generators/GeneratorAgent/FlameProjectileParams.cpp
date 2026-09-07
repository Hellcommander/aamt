#include "FlameProjectileTypes.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace FlameProjectiles {

namespace ParamUtils {

// Convert string to enum
FlameType parseFlameType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "fireball") return FlameType::FIREBALL;
    if (lower == "inferno_bolt") return FlameType::INFERNO_BOLT;
    if (lower == "hellfire") return FlameType::HELLFIRE;
    if (lower == "plasma_flame") return FlameType::PLASMA_FLAME;
    if (lower == "magic_fire") return FlameType::MAGIC_FIRE;
    if (lower == "custom") return FlameType::CUSTOM;
    
    return FlameType::FIREBALL; // Default
}

FlameShape parseFlameShape(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "cone") return FlameShape::CONE;
    if (lower == "ribbon") return FlameShape::RIBBON;
    if (lower == "sphere") return FlameShape::SPHERE;
    if (lower == "cylinder") return FlameShape::CYLINDER;
    if (lower == "custom_shape") return FlameShape::CUSTOM_SHAPE;
    
    return FlameShape::CONE; // Default
}

BlendMode parseBlendMode(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "additive") return BlendMode::ADDITIVE;
    if (lower == "multiply") return BlendMode::MULTIPLY;
    if (lower == "screen") return BlendMode::SCREEN;
    if (lower == "overlay") return BlendMode::OVERLAY;
    if (lower == "normal") return BlendMode::NORMAL;
    
    return BlendMode::ADDITIVE; // Default
}

NoiseType parseNoiseType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "perlin") return NoiseType::PERLIN;
    if (lower == "simplex") return NoiseType::SIMPLEX;
    if (lower == "curl") return NoiseType::CURL;
    if (lower == "fractal") return NoiseType::FRACTAL;
    if (lower == "custom") return NoiseType::CUSTOM;
    
    return NoiseType::CURL; // Default
}

TrailType parseTrailType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return TrailType::NONE;
    if (lower == "ribbon") return TrailType::RIBBON;
    if (lower == "particles") return TrailType::PARTICLES;
    if (lower == "smoke") return TrailType::SMOKE;
    if (lower == "heat_distortion") return TrailType::HEAT_DISTORTION;
    if (lower == "custom") return TrailType::CUSTOM;
    
    return TrailType::RIBBON; // Default
}

// Convert enum to string
std::string flameTypeToString(FlameType type) {
    switch (type) {
        case FlameType::FIREBALL: return "fireball";
        case FlameType::INFERNO_BOLT: return "inferno_bolt";
        case FlameType::HELLFIRE: return "hellfire";
        case FlameType::PLASMA_FLAME: return "plasma_flame";
        case FlameType::MAGIC_FIRE: return "magic_fire";
        case FlameType::CUSTOM: return "custom";
        default: return "fireball";
    }
}

std::string flameShapeToString(FlameShape shape) {
    switch (shape) {
        case FlameShape::CONE: return "cone";
        case FlameShape::RIBBON: return "ribbon";
        case FlameShape::SPHERE: return "sphere";
        case FlameShape::CYLINDER: return "cylinder";
        case FlameShape::CUSTOM_SHAPE: return "custom_shape";
        default: return "cone";
    }
}

std::string blendModeToString(BlendMode mode) {
    switch (mode) {
        case BlendMode::ADDITIVE: return "additive";
        case BlendMode::MULTIPLY: return "multiply";
        case BlendMode::SCREEN: return "screen";
        case BlendMode::OVERLAY: return "overlay";
        case BlendMode::NORMAL: return "normal";
        default: return "additive";
    }
}

std::string noiseTypeToString(NoiseType type) {
    switch (type) {
        case NoiseType::PERLIN: return "perlin";
        case NoiseType::SIMPLEX: return "simplex";
        case NoiseType::CURL: return "curl";
        case NoiseType::FRACTAL: return "fractal";
        case NoiseType::CUSTOM: return "custom";
        default: return "curl";
    }
}

std::string trailTypeToString(TrailType type) {
    switch (type) {
        case TrailType::NONE: return "none";
        case TrailType::RIBBON: return "ribbon";
        case TrailType::PARTICLES: return "particles";
        case TrailType::SMOKE: return "smoke";
        case TrailType::HEAT_DISTORTION: return "heat_distortion";
        case TrailType::CUSTOM: return "custom";
        default: return "ribbon";
    }
}

// JSON serialization for FlameProjectileParams
nlohmann::json toJson(const FlameProjectileParams& params) {
    nlohmann::json j;
    
    j["id"] = params.id;
    j["flameType"] = flameTypeToString(params.flameType);
    j["flameShape"] = flameShapeToString(params.flameShape);
    j["blendMode"] = blendModeToString(params.blendMode);
    j["noiseType"] = noiseTypeToString(params.noiseType);
    j["trailType"] = trailTypeToString(params.trailType);
    
    // Physical properties
    j["speed"] = params.speed;
    j["length"] = params.length;
    j["width"] = params.width;
    j["flameHeight"] = params.flameHeight;
    j["flameWidthVariation"] = params.flameWidthVariation;
    
    // Color properties
    j["coreColor"] = {params.coreColor.x, params.coreColor.y, params.coreColor.z};
    j["outerColor"] = {params.outerColor.x, params.outerColor.y, params.outerColor.z};
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    j["emberColor"] = {params.emberColor.x, params.emberColor.y, params.emberColor.z, params.emberColor.w};
    
    // Animation properties
    j["flickerIntensity"] = params.flickerIntensity;
    j["flickerSpeed"] = params.flickerSpeed;
    j["turbulenceStrength"] = params.turbulenceStrength;
    j["turbulenceScale"] = params.turbulenceScale;
    j["oscillationFreq"] = params.oscillationFreq;
    j["oscillationAmplitude"] = params.oscillationAmplitude;
    
    // Trail properties
    j["trailLength"] = params.trailLength;
    j["trailWidth"] = params.trailWidth;
    j["trailOpacity"] = params.trailOpacity;
    j["enableTrailFade"] = params.enableTrailFade;
    j["trailFadeSpeed"] = params.trailFadeSpeed;
    
    // Particle properties
    j["emberCount"] = params.emberCount;
    j["emberLifetime"] = params.emberLifetime;
    j["emberSize"] = params.emberSize;
    j["emberSpeed"] = params.emberSpeed;
    j["enableEmberFade"] = params.enableEmberFade;
    j["emberFadeSpeed"] = params.emberFadeSpeed;
    
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
    j["physicsMass"] = params.physicsMass;
    j["physicsDrag"] = params.physicsDrag;
    j["physicsLift"] = params.physicsLift;
    j["enableCollision"] = params.enableCollision;
    j["collisionRadius"] = params.collisionRadius;
    
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

FlameProjectileParams fromJson(const nlohmann::json& json) {
    FlameProjectileParams params;
    
    // Helper function to safely get values with defaults
    auto getString = [&json](const std::string& key, const std::string& defaultValue = "") -> std::string {
        return json.contains(key) ? json[key].get<std::string>() : defaultValue;
    };
    
    auto getFloat = [&json](const std::string& key, float defaultValue = 0.0f) -> float {
        return json.contains(key) ? json[key].get<float>() : defaultValue;
    };
    
    auto getInt = [&json](const std::string& key, int defaultValue = 0) -> int {
        return json.contains(key) ? json[key].get<int>() : defaultValue;
    };
    
    auto getBool = [&json](const std::string& key, bool defaultValue = false) -> bool {
        return json.contains(key) ? json[key].get<bool>() : defaultValue;
    };
    
    auto getVec3 = [&json](const std::string& key) -> glm::vec3 {
        if (json.contains(key) && json[key].is_array() && json[key].size() >= 3) {
            return {json[key][0].get<float>(), json[key][1].get<float>(), json[key][2].get<float>()};
        }
        return {1.0f, 1.0f, 1.0f}; // Default color
    };
    
    auto getVec4 = [&json](const std::string& key) -> glm::vec4 {
        if (json.contains(key) && json[key].is_array() && json[key].size() >= 4) {
            return {json[key][0].get<float>(), json[key][1].get<float>(), 
                   json[key][2].get<float>(), json[key][3].get<float>()};
        }
        return {1.0f, 1.0f, 1.0f, 1.0f}; // Default color
    };
    
    auto getVector = [&json](const std::string& key) -> std::vector<std::string> {
        if (json.contains(key) && json[key].is_array()) {
            return json[key].get<std::vector<std::string>>();
        }
        return {};
    };
    
    auto getMap = [&json](const std::string& key) -> std::map<std::string, std::string> {
        if (json.contains(key) && json[key].is_object()) {
            std::map<std::string, std::string> result;
            for (auto it = json[key].begin(); it != json[key].end(); ++it) {
                if (it.value().is_string()) {
                    result[it.key()] = it.value().get<std::string>();
                }
            }
            return result;
        }
        return {};
    };
    
    // Parse basic properties
    params.id = getString("id", "default_flame");
    params.flameType = parseFlameType(getString("flameType", "fireball"));
    params.flameShape = parseFlameShape(getString("flameShape", "cone"));
    params.blendMode = parseBlendMode(getString("blendMode", "additive"));
    params.noiseType = parseNoiseType(getString("noiseType", "curl"));
    params.trailType = parseTrailType(getString("trailType", "ribbon"));
    
    // Parse physical properties
    params.speed = getFloat("speed", 25.0f);
    params.length = getFloat("length", 1.2f);
    params.width = getFloat("width", 0.2f);
    params.flameHeight = getFloat("flameHeight", 1.0f);
    params.flameWidthVariation = getFloat("flameWidthVariation", 0.5f);
    
    // Parse color properties
    params.coreColor = getVec3("coreColor");
    params.outerColor = getVec3("outerColor");
    params.glowColor = getVec3("glowColor");
    params.emberColor = getVec4("emberColor");
    
    // Parse animation properties
    params.flickerIntensity = getFloat("flickerIntensity", 0.7f);
    params.flickerSpeed = getFloat("flickerSpeed", 3.0f);
    params.turbulenceStrength = getFloat("turbulenceStrength", 1.0f);
    params.turbulenceScale = getFloat("turbulenceScale", 2.5f);
    params.oscillationFreq = getFloat("oscillationFreq", 1.0f);
    params.oscillationAmplitude = getFloat("oscillationAmplitude", 0.1f);
    
    // Parse trail properties
    params.trailLength = getFloat("trailLength", 0.8f);
    params.trailWidth = getFloat("trailWidth", 0.1f);
    params.trailOpacity = getFloat("trailOpacity", 0.8f);
    params.enableTrailFade = getBool("enableTrailFade", true);
    params.trailFadeSpeed = getFloat("trailFadeSpeed", 1.0f);
    
    // Parse particle properties
    params.emberCount = getInt("emberCount", 60);
    params.emberLifetime = getFloat("emberLifetime", 0.5f);
    params.emberSize = getFloat("emberSize", 0.05f);
    params.emberSpeed = getFloat("emberSpeed", 1.0f);
    params.enableEmberFade = getBool("enableEmberFade", true);
    params.emberFadeSpeed = getFloat("emberFadeSpeed", 1.0f);
    
    // Parse shader properties
    params.shaderType = getString("shaderType", "flame");
    params.shaderIntensity = getFloat("shaderIntensity", 1.0f);
    params.enableDistortion = getBool("enableDistortion", true);
    params.distortionStrength = getFloat("distortionStrength", 0.1f);
    params.enableBlur = getBool("enableBlur", false);
    params.blurStrength = getFloat("blurStrength", 0.1f);
    params.enableHeatDistortion = getBool("enableHeatDistortion", false);
    params.heatDistortionStrength = getFloat("heatDistortionStrength", 0.1f);
    
    // Parse physics properties
    params.enablePhysics = getBool("enablePhysics", true);
    params.physicsMass = getFloat("physicsMass", 0.1f);
    params.physicsDrag = getFloat("physicsDrag", 0.1f);
    params.physicsLift = getFloat("physicsLift", 0.0f);
    params.enableCollision = getBool("enableCollision", true);
    params.collisionRadius = getFloat("collisionRadius", 0.1f);
    
    // Parse performance properties
    params.enableCaching = getBool("enableCaching", true);
    params.enableHotReload = getBool("enableHotReload", true);
    params.enableParallelProcessing = getBool("enableParallelProcessing", true);
    params.lodLevel = getInt("lodLevel", 0);
    
    // Parse metadata
    params.description = getString("description");
    params.tags = getVector("tags");
    params.metadata = getMap("metadata");
    
    return params;
}

} // namespace ParamUtils

} // namespace FlameProjectiles
} // namespace MagiTech 
