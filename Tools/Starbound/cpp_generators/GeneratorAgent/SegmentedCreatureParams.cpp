#include "SegmentedCreatureParams.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace SegmentedCreatures {

namespace ParamUtils {

// Convert string to enum
TaperProfile parseTaperProfile(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return TaperProfile::NONE;
    if (lower == "linear") return TaperProfile::LINEAR;
    if (lower == "exponential") return TaperProfile::EXPONENTIAL;
    if (lower == "custom_curve" || lower == "customcurve") return TaperProfile::CUSTOM_CURVE;
    
    return TaperProfile::LINEAR; // Default
}

SegmentType parseSegmentType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "cylinder") return SegmentType::CYLINDER;
    if (lower == "box") return SegmentType::BOX;
    if (lower == "hexagon") return SegmentType::HEXAGON;
    if (lower == "custom_mesh" || lower == "custommesh") return SegmentType::CUSTOM_MESH;
    
    return SegmentType::CYLINDER; // Default
}

HeadType parseHeadType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "simple") return HeadType::SIMPLE;
    if (lower == "mandible") return HeadType::MANDIBLE;
    if (lower == "multi_eye" || lower == "multieye") return HeadType::MULTI_EYE;
    if (lower == "horned") return HeadType::HORNED;
    
    return HeadType::MANDIBLE; // Default
}

TailType parseTailType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return TailType::NONE;
    if (lower == "spike") return TailType::SPIKE;
    if (lower == "flared") return TailType::FLARED;
    
    return TailType::SPIKE; // Default
}

AnimationProfile parseAnimationProfile(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "slither") return AnimationProfile::SLITHER;
    if (lower == "crawl") return AnimationProfile::CRAWL;
    if (lower == "coil") return AnimationProfile::COIL;
    if (lower == "custom") return AnimationProfile::CUSTOM;
    
    return AnimationProfile::SLITHER; // Default
}

AIProfile parseAIProfile(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "passive") return AIProfile::PASSIVE;
    if (lower == "neutral") return AIProfile::NEUTRAL;
    if (lower == "predator") return AIProfile::PREDATOR;
    if (lower == "swarm") return AIProfile::SWARM;
    
    return AIProfile::PREDATOR; // Default
}

// Convert enum to string
std::string taperProfileToString(TaperProfile profile) {
    switch (profile) {
        case TaperProfile::NONE: return "none";
        case TaperProfile::LINEAR: return "linear";
        case TaperProfile::EXPONENTIAL: return "exponential";
        case TaperProfile::CUSTOM_CURVE: return "custom_curve";
        default: return "linear";
    }
}

std::string segmentTypeToString(SegmentType type) {
    switch (type) {
        case SegmentType::CYLINDER: return "cylinder";
        case SegmentType::BOX: return "box";
        case SegmentType::HEXAGON: return "hexagon";
        case SegmentType::CUSTOM_MESH: return "custom_mesh";
        default: return "cylinder";
    }
}

std::string headTypeToString(HeadType type) {
    switch (type) {
        case HeadType::SIMPLE: return "simple";
        case HeadType::MANDIBLE: return "mandible";
        case HeadType::MULTI_EYE: return "multi_eye";
        case HeadType::HORNED: return "horned";
        default: return "mandible";
    }
}

std::string tailTypeToString(TailType type) {
    switch (type) {
        case TailType::NONE: return "none";
        case TailType::SPIKE: return "spike";
        case TailType::FLARED: return "flared";
        default: return "spike";
    }
}

std::string animationProfileToString(AnimationProfile profile) {
    switch (profile) {
        case AnimationProfile::SLITHER: return "slither";
        case AnimationProfile::CRAWL: return "crawl";
        case AnimationProfile::COIL: return "coil";
        case AnimationProfile::CUSTOM: return "custom";
        default: return "slither";
    }
}

std::string aiProfileToString(AIProfile profile) {
    switch (profile) {
        case AIProfile::PASSIVE: return "passive";
        case AIProfile::NEUTRAL: return "neutral";
        case AIProfile::PREDATOR: return "predator";
        case AIProfile::SWARM: return "swarm";
        default: return "predator";
    }
}

// JSON serialization for SegmentedCreatureParams
nlohmann::json toJson(const SegmentedCreatureParams& params) {
    nlohmann::json j;
    
    j["id"] = params.id;
    j["segmentCount"] = params.segmentCount;
    j["segmentLength"] = params.segmentLength;
    j["taperProfile"] = taperProfileToString(params.taperProfile);
    j["segmentRadius"] = params.segmentRadius;
    j["segmentType"] = segmentTypeToString(params.segmentType);
    j["headType"] = headTypeToString(params.headType);
    j["tailType"] = tailTypeToString(params.tailType);
    j["articulationStiffness"] = params.articulationStiffness;
    j["noiseDetail"] = params.noiseDetail;
    j["armorPlates"] = params.armorPlates;
    j["plateDetailLevel"] = params.plateDetailLevel;
    j["colorPrimary"] = params.colorPrimary;
    j["colorSecondary"] = params.colorSecondary;
    j["materialRoughness"] = params.materialRoughness;
    j["materialMetallic"] = params.materialMetallic;
    j["animationProfile"] = animationProfileToString(params.animationProfile);
    j["aiProfile"] = aiProfileToString(params.aiProfile);
    j["customTaperCurve"] = params.customTaperCurve;
    j["segmentSpacing"] = params.segmentSpacing;
    j["enableJoints"] = params.enableJoints;
    j["jointFlexibility"] = params.jointFlexibility;
    j["enableArmor"] = params.enableArmor;
    j["armorThickness"] = params.armorThickness;
    j["enableSpikes"] = params.enableSpikes;
    j["spikeCount"] = params.spikeCount;
    j["spikeLength"] = params.spikeLength;
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    j["enableCaching"] = params.enableCaching;
    j["enableHotReload"] = params.enableHotReload;
    j["enableParallelProcessing"] = params.enableParallelProcessing;
    
    return j;
}

SegmentedCreatureParams fromJson(const nlohmann::json& json) {
    SegmentedCreatureParams params;
    
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
    
    auto getArray = [&json](const std::string& key) -> std::array<float, 3> {
        if (json.contains(key) && json[key].is_array() && json[key].size() >= 3) {
            return {json[key][0].get<float>(), json[key][1].get<float>(), json[key][2].get<float>()};
        }
        return {0.3f, 0.3f, 0.35f}; // Default color
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
    params.id = getString("id", "default_creature");
    params.segmentCount = getInt("segmentCount", 20);
    params.segmentLength = getFloat("segmentLength", 0.5f);
    params.taperProfile = parseTaperProfile(getString("taperProfile", "linear"));
    params.segmentRadius = getFloat("segmentRadius", 0.2f);
    params.segmentType = parseSegmentType(getString("segmentType", "cylinder"));
    params.headType = parseHeadType(getString("headType", "mandible"));
    params.tailType = parseTailType(getString("tailType", "spike"));
    params.articulationStiffness = getFloat("articulationStiffness", 0.7f);
    params.noiseDetail = getFloat("noiseDetail", 0.4f);
    params.armorPlates = getBool("armorPlates", true);
    params.plateDetailLevel = getInt("plateDetailLevel", 2);
    params.colorPrimary = getArray("colorPrimary");
    params.colorSecondary = getArray("colorSecondary");
    params.materialRoughness = getFloat("materialRoughness", 0.6f);
    params.materialMetallic = getFloat("materialMetallic", 0.8f);
    params.animationProfile = parseAnimationProfile(getString("animationProfile", "slither"));
    params.aiProfile = parseAIProfile(getString("aiProfile", "predator"));
    
    // Parse custom taper curve
    if (json.contains("customTaperCurve") && json["customTaperCurve"].is_array()) {
        params.customTaperCurve = json["customTaperCurve"].get<std::vector<float>>();
    }
    
    // Parse additional parameters
    params.segmentSpacing = getFloat("segmentSpacing", 0.1f);
    params.enableJoints = getBool("enableJoints", true);
    params.jointFlexibility = getFloat("jointFlexibility", 0.5f);
    params.enableArmor = getBool("enableArmor", true);
    params.armorThickness = getFloat("armorThickness", 0.05f);
    params.enableSpikes = getBool("enableSpikes", false);
    params.spikeCount = getInt("spikeCount", 0);
    params.spikeLength = getFloat("spikeLength", 0.1f);
    
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

// JSON serialization for BehaviorParams
nlohmann::json toJson(const BehaviorParams& params) {
    nlohmann::json j;
    
    j["speed"] = params.speed;
    j["detectionRange"] = params.detectionRange;
    j["attackRange"] = params.attackRange;
    j["aggression"] = params.aggression;
    j["packSize"] = params.packSize;
    j["burrowDepth"] = params.burrowDepth;
    j["climbAbility"] = params.climbAbility;
    j["patrolRadius"] = params.patrolRadius;
    j["idleTime"] = params.idleTime;
    j["chaseSpeed"] = params.chaseSpeed;
    j["retreatHealth"] = params.retreatHealth;
    j["canSwim"] = params.canSwim;
    j["canFly"] = params.canFly;
    j["nocturnal"] = params.nocturnal;
    j["territorial"] = params.territorial;
    j["territorySize"] = params.territorySize;
    j["attackDamage"] = params.attackDamage;
    j["attackCooldown"] = params.attackCooldown;
    j["canRangedAttack"] = params.canRangedAttack;
    j["rangedAttackRange"] = params.rangedAttackRange;
    j["canUseAbilities"] = params.canUseAbilities;
    j["abilities"] = params.abilities;
    j["packHunting"] = params.packHunting;
    j["packCohesion"] = params.packCohesion;
    j["hierarchical"] = params.hierarchical;
    j["dominanceRank"] = params.dominanceRank;
    j["burrower"] = params.burrower;
    j["climber"] = params.climber;
    j["swimmer"] = params.swimmer;
    j["flyer"] = params.flyer;
    j["preferredTemperature"] = params.preferredTemperature;
    j["temperatureTolerance"] = params.temperatureTolerance;
    j["behaviorName"] = params.behaviorName;
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    return j;
}

BehaviorParams fromJson(const nlohmann::json& json) {
    BehaviorParams params;
    
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
    params.speed = getFloat("speed", 1.0f);
    params.detectionRange = getFloat("detectionRange", 15.0f);
    params.attackRange = getFloat("attackRange", 1.5f);
    params.aggression = getFloat("aggression", 0.6f);
    params.packSize = getInt("packSize", 1);
    params.burrowDepth = getFloat("burrowDepth", 2.0f);
    params.climbAbility = getBool("climbAbility", true);
    params.patrolRadius = getFloat("patrolRadius", 10.0f);
    params.idleTime = getFloat("idleTime", 2.0f);
    params.chaseSpeed = getFloat("chaseSpeed", 1.5f);
    params.retreatHealth = getFloat("retreatHealth", 0.3f);
    params.canSwim = getBool("canSwim", false);
    params.canFly = getBool("canFly", false);
    params.nocturnal = getBool("nocturnal", false);
    params.territorial = getBool("territorial", false);
    params.territorySize = getFloat("territorySize", 20.0f);
    params.attackDamage = getFloat("attackDamage", 10.0f);
    params.attackCooldown = getFloat("attackCooldown", 1.0f);
    params.canRangedAttack = getBool("canRangedAttack", false);
    params.rangedAttackRange = getFloat("rangedAttackRange", 5.0f);
    params.canUseAbilities = getBool("canUseAbilities", false);
    params.abilities = getVector("abilities");
    params.packHunting = getBool("packHunting", false);
    params.packCohesion = getFloat("packCohesion", 0.8f);
    params.hierarchical = getBool("hierarchical", false);
    params.dominanceRank = getInt("dominanceRank", 0);
    params.burrower = getBool("burrower", false);
    params.climber = getBool("climber", false);
    params.swimmer = getBool("swimmer", false);
    params.flyer = getBool("flyer", false);
    params.preferredTemperature = getFloat("preferredTemperature", 20.0f);
    params.temperatureTolerance = getFloat("temperatureTolerance", 10.0f);
    params.behaviorName = getString("behaviorName");
    params.description = getString("description");
    params.tags = getVector("tags");
    params.metadata = getMap("metadata");
    
    return params;
}

} // namespace ParamUtils

} // namespace SegmentedCreatures
} // namespace MagiTech 
