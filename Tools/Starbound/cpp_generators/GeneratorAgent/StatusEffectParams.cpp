#include "StatusEffectTypes.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace StatusEffects {

namespace ParamUtils {

// Convert string to enum
EffectType parseEffectType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "buff") return EffectType::BUFF;
    if (lower == "debuff") return EffectType::DEBUFF;
    if (lower == "dot") return EffectType::DOT;
    if (lower == "hot") return EffectType::HOT;
    if (lower == "shield") return EffectType::SHIELD;
    if (lower == "stun") return EffectType::STUN;
    if (lower == "slow") return EffectType::SLOW;
    if (lower == "haste") return EffectType::HASTE;
    if (lower == "invisibility") return EffectType::INVISIBILITY;
    if (lower == "poison") return EffectType::POISON;
    if (lower == "burn") return EffectType::BURN;
    if (lower == "freeze") return EffectType::FREEZE;
    if (lower == "shock") return EffectType::SHOCK;
    if (lower == "curse") return EffectType::CURSE;
    if (lower == "blessing") return EffectType::BLESSING;
    if (lower == "custom") return EffectType::CUSTOM;
    
    return EffectType::BUFF; // Default
}

ShapeType parseShapeType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "circle") return ShapeType::CIRCLE;
    if (lower == "square") return ShapeType::SQUARE;
    if (lower == "hexagon") return ShapeType::HEXAGON;
    if (lower == "star") return ShapeType::STAR;
    if (lower == "cross") return ShapeType::CROSS;
    if (lower == "diamond") return ShapeType::DIAMOND;
    if (lower == "custom_shape" || lower == "customshape") return ShapeType::CUSTOM_SHAPE;
    
    return ShapeType::CIRCLE; // Default
}

ParticleType parseParticleType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return ParticleType::NONE;
    if (lower == "sparkle") return ParticleType::SPARKLE;
    if (lower == "smoke") return ParticleType::SMOKE;
    if (lower == "fire") return ParticleType::FIRE;
    if (lower == "ice") return ParticleType::ICE;
    if (lower == "lightning") return ParticleType::LIGHTNING;
    if (lower == "poison") return ParticleType::POISON;
    if (lower == "healing") return ParticleType::HEALING;
    if (lower == "shield") return ParticleType::SHIELD;
    if (lower == "custom_particle" || lower == "customparticle") return ParticleType::CUSTOM_PARTICLE;
    
    return ParticleType::NONE; // Default
}

IconStyle parseIconStyle(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "simple") return IconStyle::SIMPLE;
    if (lower == "detailed") return IconStyle::DETAILED;
    if (lower == "animated") return IconStyle::ANIMATED;
    if (lower == "glowing") return IconStyle::GLOWING;
    if (lower == "pulsing") return IconStyle::PULSING;
    if (lower == "custom_icon" || lower == "customicon") return IconStyle::CUSTOM_ICON;
    
    return IconStyle::SIMPLE; // Default
}

EffectCategory parseEffectCategory(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "combat") return EffectCategory::COMBAT;
    if (lower == "magic") return EffectCategory::MAGIC;
    if (lower == "environmental") return EffectCategory::ENVIRONMENTAL;
    if (lower == "temporary") return EffectCategory::TEMPORARY;
    if (lower == "permanent") return EffectCategory::PERMANENT;
    if (lower == "stacking") return EffectCategory::STACKING;
    if (lower == "non_stacking" || lower == "nonstacking") return EffectCategory::NON_STACKING;
    
    return EffectCategory::COMBAT; // Default
}

// Convert enum to string
std::string effectTypeToString(EffectType type) {
    switch (type) {
        case EffectType::BUFF: return "buff";
        case EffectType::DEBUFF: return "debuff";
        case EffectType::DOT: return "dot";
        case EffectType::HOT: return "hot";
        case EffectType::SHIELD: return "shield";
        case EffectType::STUN: return "stun";
        case EffectType::SLOW: return "slow";
        case EffectType::HASTE: return "haste";
        case EffectType::INVISIBILITY: return "invisibility";
        case EffectType::POISON: return "poison";
        case EffectType::BURN: return "burn";
        case EffectType::FREEZE: return "freeze";
        case EffectType::SHOCK: return "shock";
        case EffectType::CURSE: return "curse";
        case EffectType::BLESSING: return "blessing";
        case EffectType::CUSTOM: return "custom";
        default: return "buff";
    }
}

std::string shapeTypeToString(ShapeType type) {
    switch (type) {
        case ShapeType::CIRCLE: return "circle";
        case ShapeType::SQUARE: return "square";
        case ShapeType::HEXAGON: return "hexagon";
        case ShapeType::STAR: return "star";
        case ShapeType::CROSS: return "cross";
        case ShapeType::DIAMOND: return "diamond";
        case ShapeType::CUSTOM_SHAPE: return "custom_shape";
        default: return "circle";
    }
}

std::string particleTypeToString(ParticleType type) {
    switch (type) {
        case ParticleType::NONE: return "none";
        case ParticleType::SPARKLE: return "sparkle";
        case ParticleType::SMOKE: return "smoke";
        case ParticleType::FIRE: return "fire";
        case ParticleType::ICE: return "ice";
        case ParticleType::LIGHTNING: return "lightning";
        case ParticleType::POISON: return "poison";
        case ParticleType::HEALING: return "healing";
        case ParticleType::SHIELD: return "shield";
        case ParticleType::CUSTOM_PARTICLE: return "custom_particle";
        default: return "none";
    }
}

std::string iconStyleToString(IconStyle style) {
    switch (style) {
        case IconStyle::SIMPLE: return "simple";
        case IconStyle::DETAILED: return "detailed";
        case IconStyle::ANIMATED: return "animated";
        case IconStyle::GLOWING: return "glowing";
        case IconStyle::PULSING: return "pulsing";
        case IconStyle::CUSTOM_ICON: return "custom_icon";
        default: return "simple";
    }
}

std::string effectCategoryToString(EffectCategory category) {
    switch (category) {
        case EffectCategory::COMBAT: return "combat";
        case EffectCategory::MAGIC: return "magic";
        case EffectCategory::ENVIRONMENTAL: return "environmental";
        case EffectCategory::TEMPORARY: return "temporary";
        case EffectCategory::PERMANENT: return "permanent";
        case EffectCategory::STACKING: return "stacking";
        case EffectCategory::NON_STACKING: return "non_stacking";
        default: return "combat";
    }
}

// JSON serialization for StatusEffectParams
nlohmann::json toJson(const StatusEffectParams& params) {
    nlohmann::json j;
    
    j["id"] = params.id;
    j["effectType"] = effectTypeToString(params.effectType);
    j["shapeType"] = shapeTypeToString(params.shapeType);
    j["particleType"] = particleTypeToString(params.particleType);
    j["iconStyle"] = iconStyleToString(params.iconStyle);
    j["category"] = effectCategoryToString(params.category);
    
    // Timing parameters
    j["duration"] = params.duration;
    j["intensity"] = params.intensity;
    j["fadeInTime"] = params.fadeInTime;
    j["fadeOutTime"] = params.fadeOutTime;
    j["isPermanent"] = params.isPermanent;
    j["canStack"] = params.canStack;
    j["maxStacks"] = params.maxStacks;
    
    // Visual parameters
    j["noiseScale"] = params.noiseScale;
    j["noiseSpeed"] = params.noiseSpeed;
    j["oscillationFreq"] = params.oscillationFreq;
    j["coverage"] = params.coverage;
    j["particleCount"] = params.particleCount;
    j["dissolve"] = params.dissolve;
    j["opacity"] = params.opacity;
    j["scale"] = params.scale;
    
    // Color parameters
    j["colorPrimary"] = {params.colorPrimary.x, params.colorPrimary.y, params.colorPrimary.z};
    j["colorSecondary"] = {params.colorSecondary.x, params.colorSecondary.y, params.colorSecondary.z};
    j["iconColor"] = {params.iconColor.x, params.iconColor.y, params.iconColor.z};
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    
    // Animation parameters
    j["enablePulsing"] = params.enablePulsing;
    j["pulseSpeed"] = params.pulseSpeed;
    j["pulseIntensity"] = params.pulseIntensity;
    j["enableRotation"] = params.enableRotation;
    j["rotationSpeed"] = params.rotationSpeed;
    j["enableScaling"] = params.enableScaling;
    j["scaleSpeed"] = params.scaleSpeed;
    j["scaleRange"] = params.scaleRange;
    
    // Shader parameters
    j["shaderType"] = params.shaderType;
    j["shaderIntensity"] = params.shaderIntensity;
    j["enableDistortion"] = params.enableDistortion;
    j["distortionStrength"] = params.distortionStrength;
    j["enableBlur"] = params.enableBlur;
    j["blurStrength"] = params.blurStrength;
    
    // Metadata
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    // Performance settings
    j["enableCaching"] = params.enableCaching;
    j["enableHotReload"] = params.enableHotReload;
    j["enableParallelProcessing"] = params.enableParallelProcessing;
    
    return j;
}

StatusEffectParams fromJson(const nlohmann::json& json) {
    StatusEffectParams params;
    
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
    
    // Parse parameters
    params.id = getString("id", "default_effect");
    params.effectType = parseEffectType(getString("effectType", "buff"));
    params.shapeType = parseShapeType(getString("shapeType", "circle"));
    params.particleType = parseParticleType(getString("particleType", "none"));
    params.iconStyle = parseIconStyle(getString("iconStyle", "simple"));
    params.category = parseEffectCategory(getString("category", "combat"));
    
    // Parse timing parameters
    params.duration = getFloat("duration", 10.0f);
    params.intensity = getFloat("intensity", 1.0f);
    params.fadeInTime = getFloat("fadeInTime", 0.5f);
    params.fadeOutTime = getFloat("fadeOutTime", 0.5f);
    params.isPermanent = getBool("isPermanent", false);
    params.canStack = getBool("canStack", false);
    params.maxStacks = getInt("maxStacks", 1);
    
    // Parse visual parameters
    params.noiseScale = getFloat("noiseScale", 1.0f);
    params.noiseSpeed = getFloat("noiseSpeed", 1.0f);
    params.oscillationFreq = getFloat("oscillationFreq", 1.0f);
    params.coverage = getInt("coverage", 100);
    params.particleCount = getInt("particleCount", 50);
    params.dissolve = getBool("dissolve", false);
    params.opacity = getFloat("opacity", 1.0f);
    params.scale = getFloat("scale", 1.0f);
    
    // Parse color parameters
    params.colorPrimary = getVec3("colorPrimary");
    params.colorSecondary = getVec3("colorSecondary");
    params.iconColor = getVec3("iconColor");
    params.glowColor = getVec3("glowColor");
    
    // Parse animation parameters
    params.enablePulsing = getBool("enablePulsing", false);
    params.pulseSpeed = getFloat("pulseSpeed", 1.0f);
    params.pulseIntensity = getFloat("pulseIntensity", 0.2f);
    params.enableRotation = getBool("enableRotation", false);
    params.rotationSpeed = getFloat("rotationSpeed", 1.0f);
    params.enableScaling = getBool("enableScaling", false);
    params.scaleSpeed = getFloat("scaleSpeed", 1.0f);
    params.scaleRange = getFloat("scaleRange", 0.2f);
    
    // Parse shader parameters
    params.shaderType = getString("shaderType", "standard");
    params.shaderIntensity = getFloat("shaderIntensity", 1.0f);
    params.enableDistortion = getBool("enableDistortion", false);
    params.distortionStrength = getFloat("distortionStrength", 0.1f);
    params.enableBlur = getBool("enableBlur", false);
    params.blurStrength = getFloat("blurStrength", 0.1f);
    
    // Parse metadata
    params.description = getString("description");
    params.tags = getVector("tags");
    params.metadata = getMap("metadata");
    
    // Parse performance settings
    params.enableCaching = getBool("enableCaching", true);
    params.enableHotReload = getBool("enableHotReload", true);
    params.enableParallelProcessing = getBool("enableParallelProcessing", true);
    
    return params;
}

// JSON serialization for UIParams
nlohmann::json toJson(const UIParams& params) {
    nlohmann::json j;
    
    j["iconSize"] = params.iconSize;
    j["borderColor"] = {params.borderColor.x, params.borderColor.y, params.borderColor.z, params.borderColor.w};
    j["backgroundShape"] = params.backgroundShape;
    j["flashOnApply"] = params.flashOnApply;
    
    // Additional UI parameters
    j["enableGlow"] = params.enableGlow;
    j["glowIntensity"] = params.glowIntensity;
    j["enablePulse"] = params.enablePulse;
    j["pulseSpeed"] = params.pulseSpeed;
    j["enableRotation"] = params.enableRotation;
    j["rotationSpeed"] = params.rotationSpeed;
    
    // Border parameters
    j["borderWidth"] = params.borderWidth;
    j["enableBorderGlow"] = params.enableBorderGlow;
    j["borderGlowIntensity"] = params.borderGlowIntensity;
    
    // Background parameters
    j["enableBackground"] = params.enableBackground;
    j["backgroundOpacity"] = params.backgroundOpacity;
    j["enableBackgroundBlur"] = params.enableBackgroundBlur;
    j["backgroundBlurStrength"] = params.backgroundBlurStrength;
    
    // Animation parameters
    j["enableFadeIn"] = params.enableFadeIn;
    j["fadeInDuration"] = params.fadeInDuration;
    j["enableFadeOut"] = params.enableFadeOut;
    j["fadeOutDuration"] = params.fadeOutDuration;
    j["enableScaleIn"] = params.enableScaleIn;
    j["scaleInDuration"] = params.scaleInDuration;
    j["enableScaleOut"] = params.enableScaleOut;
    j["scaleOutDuration"] = params.scaleOutDuration;
    
    // Stacking parameters
    j["showStackCount"] = params.showStackCount;
    j["stackCountStyle"] = params.stackCountStyle;
    j["stackCountColor"] = {params.stackCountColor.x, params.stackCountColor.y, params.stackCountColor.z};
    j["stackCountScale"] = params.stackCountScale;
    
    // Metadata
    j["uiName"] = params.uiName;
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    return j;
}

UIParams fromJson(const nlohmann::json& json) {
    UIParams params;
    
    // Helper functions (same as above)
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
    
    auto getVec4 = [&json](const std::string& key) -> glm::vec4 {
        if (json.contains(key) && json[key].is_array() && json[key].size() >= 4) {
            return {json[key][0].get<float>(), json[key][1].get<float>(), 
                   json[key][2].get<float>(), json[key][3].get<float>()};
        }
        return {1.0f, 1.0f, 1.0f, 1.0f}; // Default color
    };
    
    auto getVec3 = [&json](const std::string& key) -> glm::vec3 {
        if (json.contains(key) && json[key].is_array() && json[key].size() >= 3) {
            return {json[key][0].get<float>(), json[key][1].get<float>(), json[key][2].get<float>()};
        }
        return {1.0f, 1.0f, 1.0f}; // Default color
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
    
    // Parse parameters
    params.iconSize = getInt("iconSize", 32);
    params.borderColor = getVec4("borderColor");
    params.backgroundShape = getString("backgroundShape", "circle");
    params.flashOnApply = getBool("flashOnApply", true);
    
    // Parse additional UI parameters
    params.enableGlow = getBool("enableGlow", false);
    params.glowIntensity = getFloat("glowIntensity", 1.0f);
    params.enablePulse = getBool("enablePulse", false);
    params.pulseSpeed = getFloat("pulseSpeed", 1.0f);
    params.enableRotation = getBool("enableRotation", false);
    params.rotationSpeed = getFloat("rotationSpeed", 1.0f);
    
    // Parse border parameters
    params.borderWidth = getFloat("borderWidth", 2.0f);
    params.enableBorderGlow = getBool("enableBorderGlow", false);
    params.borderGlowIntensity = getFloat("borderGlowIntensity", 1.0f);
    
    // Parse background parameters
    params.enableBackground = getBool("enableBackground", true);
    params.backgroundOpacity = getFloat("backgroundOpacity", 0.8f);
    params.enableBackgroundBlur = getBool("enableBackgroundBlur", false);
    params.backgroundBlurStrength = getFloat("backgroundBlurStrength", 0.1f);
    
    // Parse animation parameters
    params.enableFadeIn = getBool("enableFadeIn", true);
    params.fadeInDuration = getFloat("fadeInDuration", 0.3f);
    params.enableFadeOut = getBool("enableFadeOut", true);
    params.fadeOutDuration = getFloat("fadeOutDuration", 0.3f);
    params.enableScaleIn = getBool("enableScaleIn", true);
    params.scaleInDuration = getFloat("scaleInDuration", 0.2f);
    params.enableScaleOut = getBool("enableScaleOut", true);
    params.scaleOutDuration = getFloat("scaleOutDuration", 0.2f);
    
    // Parse stacking parameters
    params.showStackCount = getBool("showStackCount", true);
    params.stackCountStyle = getString("stackCountStyle", "number");
    params.stackCountColor = getVec3("stackCountColor");
    params.stackCountScale = getFloat("stackCountScale", 0.8f);
    
    // Parse metadata
    params.uiName = getString("uiName");
    params.description = getString("description");
    params.tags = getVector("tags");
    params.metadata = getMap("metadata");
    
    return params;
}

} // namespace ParamUtils

} // namespace StatusEffects
} // namespace MagiTech 
