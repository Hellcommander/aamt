#include "LightningProjectileTypes.hpp"
#include "core/Log.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace LightningProjectiles {

namespace ParamUtils {

// String to enum conversions
LightningType parseLightningType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "bolt" || lower == "lightning_bolt") return LightningType::BOLT;
    if (lower == "arc" || lower == "electric_arc") return LightningType::ARC;
    if (lower == "chain" || lower == "chain_lightning") return LightningType::CHAIN;
    if (lower == "fork" || lower == "forked_lightning") return LightningType::FORK;
    if (lower == "storm" || lower == "storm_lightning") return LightningType::STORM;
    if (lower == "plasma" || lower == "plasma_bolt") return LightningType::PLASMA;
    if (lower == "magic" || lower == "magic_lightning") return LightningType::MAGIC;
    if (lower == "custom") return LightningType::CUSTOM;
    
    Log::warn("Unknown lightning type: {}, defaulting to BOLT", str);
    return LightningType::BOLT;
}

TrailType parseTrailType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none" || lower == "no_trail") return TrailType::NONE;
    if (lower == "electric_tail" || lower == "electric") return TrailType::ELECTRIC_TAIL;
    if (lower == "plasma_streak" || lower == "plasma") return TrailType::PLASMA_STREAK;
    if (lower == "magic_trail" || lower == "magic") return TrailType::MAGIC_TRAIL;
    if (lower == "custom") return TrailType::CUSTOM;
    
    Log::warn("Unknown trail type: {}, defaulting to ELECTRIC_TAIL", str);
    return TrailType::ELECTRIC_TAIL;
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

AudioType parseAudioType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "crackle" || lower == "electric_crackle") return AudioType::CRACKLE;
    if (lower == "zap" || lower == "electric_zap") return AudioType::ZAP;
    if (lower == "thunder" || lower == "thunder_clap") return AudioType::THUNDER;
    if (lower == "electric" || lower == "electric_sound") return AudioType::ELECTRIC;
    if (lower == "custom") return AudioType::CUSTOM;
    
    Log::warn("Unknown audio type: {}, defaulting to CRACKLE", str);
    return AudioType::CRACKLE;
}

// Enum to string conversions
std::string lightningTypeToString(LightningType type) {
    switch (type) {
        case LightningType::BOLT: return "bolt";
        case LightningType::ARC: return "arc";
        case LightningType::CHAIN: return "chain";
        case LightningType::FORK: return "fork";
        case LightningType::STORM: return "storm";
        case LightningType::PLASMA: return "plasma";
        case LightningType::MAGIC: return "magic";
        case LightningType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

std::string trailTypeToString(TrailType type) {
    switch (type) {
        case TrailType::NONE: return "none";
        case TrailType::ELECTRIC_TAIL: return "electric_tail";
        case TrailType::PLASMA_STREAK: return "plasma_streak";
        case TrailType::MAGIC_TRAIL: return "magic_trail";
        case TrailType::CUSTOM: return "custom";
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

std::string audioTypeToString(AudioType type) {
    switch (type) {
        case AudioType::CRACKLE: return "crackle";
        case AudioType::ZAP: return "zap";
        case AudioType::THUNDER: return "thunder";
        case AudioType::ELECTRIC: return "electric";
        case AudioType::CUSTOM: return "custom";
        default: return "unknown";
    }
}

// JSON serialization/deserialization
nlohmann::json toJson(const LightningProjectileParams& params) {
    nlohmann::json j;
    
    // Basic properties
    j["id"] = params.id;
    j["lightningType"] = lightningTypeToString(params.lightningType);
    j["trailType"] = trailTypeToString(params.trailType);
    j["noiseType"] = noiseTypeToString(params.noiseType);
    j["blendMode"] = blendModeToString(params.blendMode);
    j["audioType"] = audioTypeToString(params.audioType);
    
    // Physical properties
    j["length"] = params.length;
    j["thickness"] = params.thickness;
    j["speed"] = params.speed;
    j["mass"] = params.mass;
    j["charge"] = params.charge;
    j["conductivity"] = params.conductivity;
    
    // Color properties
    j["mainColor"] = {params.mainColor.x, params.mainColor.y, params.mainColor.z};
    j["glowColor"] = {params.glowColor.x, params.glowColor.y, params.glowColor.z};
    j["coreColor"] = {params.coreColor.x, params.coreColor.y, params.coreColor.z};
    j["sparkColor"] = {params.sparkColor.x, params.sparkColor.y, params.sparkColor.z};
    j["trailColor"] = {params.trailColor.x, params.trailColor.y, params.trailColor.z, params.trailColor.w};
    
    // Visual properties
    j["noiseIntensity"] = params.noiseIntensity;
    j["noiseScale"] = params.noiseScale;
    j["flickerSpeed"] = params.flickerSpeed;
    j["pulseFrequency"] = params.pulseFrequency;
    j["glowIntensity"] = params.glowIntensity;
    j["emissivePower"] = params.emissivePower;
    j["coreOpacity"] = params.coreOpacity;
    j["trailOpacity"] = params.trailOpacity;
    j["enableCoreGlow"] = params.enableCoreGlow;
    j["enableTrailGlow"] = params.enableTrailGlow;
    
    // Branch properties
    j["branchCount"] = params.branchCount;
    j["branchLengthFactor"] = params.branchLengthFactor;
    j["branchSpread"] = params.branchSpread;
    j["branchAngle"] = params.branchAngle;
    j["enableBranching"] = params.enableBranching;
    j["enableBranchPhysics"] = params.enableBranchPhysics;
    
    // Jitter properties
    j["jitterAmplitude"] = params.jitterAmplitude;
    j["jitterFrequency"] = params.jitterFrequency;
    j["jitterPhase"] = params.jitterPhase;
    j["enableJitter"] = params.enableJitter;
    j["enableRandomJitter"] = params.enableRandomJitter;
    
    // Arc properties
    j["arcWidthVariation"] = params.arcWidthVariation;
    j["arcSegments"] = params.arcSegments;
    j["arcSmoothness"] = params.arcSmoothness;
    j["enableArcPhysics"] = params.enableArcPhysics;
    j["arcStiffness"] = params.arcStiffness;
    
    // Trail properties
    j["trailLength"] = params.trailLength;
    j["trailWidth"] = params.trailWidth;
    j["trailFadeSpeed"] = params.trailFadeSpeed;
    j["enableTrailFade"] = params.enableTrailFade;
    j["enableTrailDistortion"] = params.enableTrailDistortion;
    j["trailDistortionStrength"] = params.trailDistortionStrength;
    
    // Particle properties
    j["sparkCount"] = params.sparkCount;
    j["sparkLifetime"] = params.sparkLifetime;
    j["sparkSize"] = params.sparkSize;
    j["sparkSpeed"] = params.sparkSpeed;
    j["enableSparkFade"] = params.enableSparkFade;
    j["sparkFadeSpeed"] = params.sparkFadeSpeed;
    j["enableSparkPhysics"] = params.enableSparkPhysics;
    j["sparkGravity"] = params.sparkGravity;
    
    // Audio properties
    j["soundPitch"] = params.soundPitch;
    j["soundVolume"] = params.soundVolume;
    j["soundDuration"] = params.soundDuration;
    j["enableAudio"] = params.enableAudio;
    j["enableSpatialAudio"] = params.enableSpatialAudio;
    j["audioDistance"] = params.audioDistance;
    
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

LightningProjectileParams fromJson(const nlohmann::json& json) {
    LightningProjectileParams params;
    
    try {
        // Basic properties
        params.id = json.value("id", "unnamed_lightning");
        params.lightningType = parseLightningType(json.value("lightningType", "bolt"));
        params.trailType = parseTrailType(json.value("trailType", "electric_tail"));
        params.noiseType = parseNoiseType(json.value("noiseType", "perlin"));
        params.blendMode = parseBlendMode(json.value("blendMode", "additive"));
        params.audioType = parseAudioType(json.value("audioType", "crackle"));
        
        // Physical properties
        params.length = json.value("length", 8.0f);
        params.thickness = json.value("thickness", 0.05f);
        params.speed = json.value("speed", 30.0f);
        params.mass = json.value("mass", 1.0f);
        params.charge = json.value("charge", 1.0f);
        params.conductivity = json.value("conductivity", 1.0f);
        
        // Color properties
        if (json.contains("mainColor") && json["mainColor"].is_array()) {
            auto& main = json["mainColor"];
            params.mainColor = {main[0], main[1], main[2]};
        } else {
            params.mainColor = {0.8f, 1.0f, 1.0f};
        }
        
        if (json.contains("glowColor") && json["glowColor"].is_array()) {
            auto& glow = json["glowColor"];
            params.glowColor = {glow[0], glow[1], glow[2]};
        } else {
            params.glowColor = {0.2f, 0.6f, 1.0f};
        }
        
        if (json.contains("coreColor") && json["coreColor"].is_array()) {
            auto& core = json["coreColor"];
            params.coreColor = {core[0], core[1], core[2]};
        } else {
            params.coreColor = {1.0f, 1.0f, 1.0f};
        }
        
        if (json.contains("sparkColor") && json["sparkColor"].is_array()) {
            auto& spark = json["sparkColor"];
            params.sparkColor = {spark[0], spark[1], spark[2]};
        } else {
            params.sparkColor = {1.0f, 0.8f, 0.5f};
        }
        
        if (json.contains("trailColor") && json["trailColor"].is_array()) {
            auto& trail = json["trailColor"];
            params.trailColor = {trail[0], trail[1], trail[2], trail[3]};
        } else {
            params.trailColor = {0.5f, 0.8f, 1.0f, 0.6f};
        }
        
        // Visual properties
        params.noiseIntensity = json.value("noiseIntensity", 0.5f);
        params.noiseScale = json.value("noiseScale", 4.0f);
        params.flickerSpeed = json.value("flickerSpeed", 25.0f);
        params.pulseFrequency = json.value("pulseFrequency", 2.0f);
        params.glowIntensity = json.value("glowIntensity", 1.0f);
        params.emissivePower = json.value("emissivePower", 1.0f);
        params.coreOpacity = json.value("coreOpacity", 1.0f);
        params.trailOpacity = json.value("trailOpacity", 0.8f);
        params.enableCoreGlow = json.value("enableCoreGlow", true);
        params.enableTrailGlow = json.value("enableTrailGlow", true);
        
        // Branch properties
        params.branchCount = json.value("branchCount", 3);
        params.branchLengthFactor = json.value("branchLengthFactor", 0.5f);
        params.branchSpread = json.value("branchSpread", 1.0f);
        params.branchAngle = json.value("branchAngle", 0.5f);
        params.enableBranching = json.value("enableBranching", true);
        params.enableBranchPhysics = json.value("enableBranchPhysics", true);
        
        // Jitter properties
        params.jitterAmplitude = json.value("jitterAmplitude", 0.1f);
        params.jitterFrequency = json.value("jitterFrequency", 30.0f);
        params.jitterPhase = json.value("jitterPhase", 0.0f);
        params.enableJitter = json.value("enableJitter", true);
        params.enableRandomJitter = json.value("enableRandomJitter", true);
        
        // Arc properties
        params.arcWidthVariation = json.value("arcWidthVariation", 0.3f);
        params.arcSegments = json.value("arcSegments", 16.0f);
        params.arcSmoothness = json.value("arcSmoothness", 0.5f);
        params.enableArcPhysics = json.value("enableArcPhysics", true);
        params.arcStiffness = json.value("arcStiffness", 1.0f);
        
        // Trail properties
        params.trailLength = json.value("trailLength", 0.5f);
        params.trailWidth = json.value("trailWidth", 0.1f);
        params.trailFadeSpeed = json.value("trailFadeSpeed", 1.0f);
        params.enableTrailFade = json.value("enableTrailFade", true);
        params.enableTrailDistortion = json.value("enableTrailDistortion", true);
        params.trailDistortionStrength = json.value("trailDistortionStrength", 0.1f);
        
        // Particle properties
        params.sparkCount = json.value("sparkCount", 60);
        params.sparkLifetime = json.value("sparkLifetime", 0.3f);
        params.sparkSize = json.value("sparkSize", 0.02f);
        params.sparkSpeed = json.value("sparkSpeed", 1.0f);
        params.enableSparkFade = json.value("enableSparkFade", true);
        params.sparkFadeSpeed = json.value("sparkFadeSpeed", 1.0f);
        params.enableSparkPhysics = json.value("enableSparkPhysics", true);
        params.sparkGravity = json.value("sparkGravity", 0.5f);
        
        // Audio properties
        params.soundPitch = json.value("soundPitch", 1.0f);
        params.soundVolume = json.value("soundVolume", 1.0f);
        params.soundDuration = json.value("soundDuration", 1.0f);
        params.enableAudio = json.value("enableAudio", true);
        params.enableSpatialAudio = json.value("enableSpatialAudio", true);
        params.audioDistance = json.value("audioDistance", 10.0f);
        
        // Shader properties
        params.shaderType = json.value("shaderType", "lightning");
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
        params.collisionRadius = json.value("collisionRadius", 0.1f);
        params.enableGravity = json.value("enableGravity", false);
        params.enableAirResistance = json.value("enableAirResistance", true);
        params.airResistanceFactor = json.value("airResistanceFactor", 0.1f);
        
        // Performance properties
        params.enableCaching = json.value("enableCaching", true);
        params.enableHotReload = json.value("enableHotReload", true);
        params.enableParallelProcessing = json.value("enableParallelProcessing", true);
        params.lodLevel = json.value("lodLevel", 0);
        
        // Metadata
        params.description = json.value("description", "Generated lightning projectile");
        if (json.contains("tags") && json["tags"].is_array()) {
            params.tags = json["tags"].get<std::vector<std::string>>();
        } else {
            params.tags = {"lightning", "projectile"};
        }
        
        if (json.contains("metadata") && json["metadata"].is_object()) {
            params.metadata = json["metadata"].get<std::map<std::string, std::string>>();
        } else {
            params.metadata = {{"source", "json"}};
        }
        
    } catch (const std::exception& e) {
        Log::error("Error parsing lightning projectile JSON: {}", e.what());
        // Return default parameters on error
        params.id = "error_loading";
        params.lightningType = LightningType::BOLT;
        params.trailType = TrailType::ELECTRIC_TAIL;
        params.noiseType = NoiseType::PERLIN;
        params.blendMode = BlendMode::ADDITIVE;
        params.audioType = AudioType::CRACKLE;
        params.length = 8.0f;
        params.thickness = 0.05f;
        params.speed = 30.0f;
        params.mass = 1.0f;
        params.charge = 1.0f;
        params.conductivity = 1.0f;
        params.mainColor = {0.8f, 1.0f, 1.0f};
        params.glowColor = {0.2f, 0.6f, 1.0f};
        params.coreColor = {1.0f, 1.0f, 1.0f};
        params.sparkColor = {1.0f, 0.8f, 0.5f};
        params.trailColor = {0.5f, 0.8f, 1.0f, 0.6f};
        params.noiseIntensity = 0.5f;
        params.noiseScale = 4.0f;
        params.flickerSpeed = 25.0f;
        params.pulseFrequency = 2.0f;
        params.glowIntensity = 1.0f;
        params.emissivePower = 1.0f;
        params.coreOpacity = 1.0f;
        params.trailOpacity = 0.8f;
        params.enableCoreGlow = true;
        params.enableTrailGlow = true;
        params.branchCount = 3;
        params.branchLengthFactor = 0.5f;
        params.branchSpread = 1.0f;
        params.branchAngle = 0.5f;
        params.enableBranching = true;
        params.enableBranchPhysics = true;
        params.jitterAmplitude = 0.1f;
        params.jitterFrequency = 30.0f;
        params.jitterPhase = 0.0f;
        params.enableJitter = true;
        params.enableRandomJitter = true;
        params.arcWidthVariation = 0.3f;
        params.arcSegments = 16.0f;
        params.arcSmoothness = 0.5f;
        params.enableArcPhysics = true;
        params.arcStiffness = 1.0f;
        params.trailLength = 0.5f;
        params.trailWidth = 0.1f;
        params.trailFadeSpeed = 1.0f;
        params.enableTrailFade = true;
        params.enableTrailDistortion = true;
        params.trailDistortionStrength = 0.1f;
        params.sparkCount = 60;
        params.sparkLifetime = 0.3f;
        params.sparkSize = 0.02f;
        params.sparkSpeed = 1.0f;
        params.enableSparkFade = true;
        params.sparkFadeSpeed = 1.0f;
        params.enableSparkPhysics = true;
        params.sparkGravity = 0.5f;
        params.soundPitch = 1.0f;
        params.soundVolume = 1.0f;
        params.soundDuration = 1.0f;
        params.enableAudio = true;
        params.enableSpatialAudio = true;
        params.audioDistance = 10.0f;
        params.shaderType = "lightning";
        params.shaderIntensity = 1.0f;
        params.enableDistortion = true;
        params.distortionStrength = 0.1f;
        params.enableBlur = false;
        params.blurStrength = 0.1f;
        params.enableHeatDistortion = false;
        params.heatDistortionStrength = 0.1f;
        params.enablePhysics = true;
        params.enableCollision = true;
        params.collisionRadius = 0.1f;
        params.enableGravity = false;
        params.enableAirResistance = true;
        params.airResistanceFactor = 0.1f;
        params.enableCaching = true;
        params.enableHotReload = true;
        params.enableParallelProcessing = true;
        params.lodLevel = 0;
        params.description = "Error loading lightning projectile";
        params.tags = {"error", "lightning", "projectile"};
        params.metadata = {{"error", "json_parse_failed"}};
    }
    
    return params;
}

} // namespace ParamUtils

} // namespace LightningProjectiles
} // namespace MagiTech 
