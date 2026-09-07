#include "SegmentedWeaponTypes.hpp"
#include <algorithm>
#include <stdexcept>

namespace MagiTech {
namespace SegmentedWeapons {

namespace ParamUtils {

// Convert string to enum
WeaponType parseWeaponType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "whip") return WeaponType::WHIP;
    if (lower == "chain") return WeaponType::CHAIN;
    if (lower == "flail") return WeaponType::FLAIL;
    if (lower == "nunchaku") return WeaponType::NUNCHAKU;
    if (lower == "rope") return WeaponType::ROPE;
    
    return WeaponType::WHIP; // Default
}

SegmentShape parseSegmentShape(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "cylinder") return SegmentShape::CYLINDER;
    if (lower == "box") return SegmentShape::BOX;
    if (lower == "sphere") return SegmentShape::SPHERE;
    if (lower == "custom_mesh" || lower == "custommesh") return SegmentShape::CUSTOM_MESH;
    
    return SegmentShape::CYLINDER; // Default
}

TaperProfile parseTaperProfile(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return TaperProfile::NONE;
    if (lower == "linear") return TaperProfile::LINEAR;
    if (lower == "exponential") return TaperProfile::EXPONENTIAL;
    if (lower == "custom_curve" || lower == "customcurve") return TaperProfile::CUSTOM_CURVE;
    
    return TaperProfile::NONE; // Default
}

MaterialType parseMaterialType(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "leather") return MaterialType::LEATHER;
    if (lower == "steel") return MaterialType::STEEL;
    if (lower == "rope") return MaterialType::ROPE;
    if (lower == "chain_metal" || lower == "chainmetal") return MaterialType::CHAIN_METAL;
    
    return MaterialType::LEATHER; // Default
}

EndAttachment parseEndAttachment(const std::string& str) {
    std::string lower = str;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower == "none") return EndAttachment::NONE;
    if (lower == "weight") return EndAttachment::WEIGHT;
    if (lower == "spike") return EndAttachment::SPIKE;
    if (lower == "hook") return EndAttachment::HOOK;
    if (lower == "blade") return EndAttachment::BLADE;
    
    return EndAttachment::BLADE; // Default
}

// Convert enum to string
std::string weaponTypeToString(WeaponType type) {
    switch (type) {
        case WeaponType::WHIP: return "whip";
        case WeaponType::CHAIN: return "chain";
        case WeaponType::FLAIL: return "flail";
        case WeaponType::NUNCHAKU: return "nunchaku";
        case WeaponType::ROPE: return "rope";
        default: return "whip";
    }
}

std::string segmentShapeToString(SegmentShape shape) {
    switch (shape) {
        case SegmentShape::CYLINDER: return "cylinder";
        case SegmentShape::BOX: return "box";
        case SegmentShape::SPHERE: return "sphere";
        case SegmentShape::CUSTOM_MESH: return "custom_mesh";
        default: return "cylinder";
    }
}

std::string taperProfileToString(TaperProfile profile) {
    switch (profile) {
        case TaperProfile::NONE: return "none";
        case TaperProfile::LINEAR: return "linear";
        case TaperProfile::EXPONENTIAL: return "exponential";
        case TaperProfile::CUSTOM_CURVE: return "custom_curve";
        default: return "none";
    }
}

std::string materialTypeToString(MaterialType type) {
    switch (type) {
        case MaterialType::LEATHER: return "leather";
        case MaterialType::STEEL: return "steel";
        case MaterialType::ROPE: return "rope";
        case MaterialType::CHAIN_METAL: return "chain_metal";
        default: return "leather";
    }
}

std::string endAttachmentToString(EndAttachment attachment) {
    switch (attachment) {
        case EndAttachment::NONE: return "none";
        case EndAttachment::WEIGHT: return "weight";
        case EndAttachment::SPIKE: return "spike";
        case EndAttachment::HOOK: return "hook";
        case EndAttachment::BLADE: return "blade";
        default: return "blade";
    }
}

// JSON serialization for SegmentedWeaponParams
nlohmann::json toJson(const SegmentedWeaponParams& params) {
    nlohmann::json j;
    
    j["id"] = params.id;
    j["weaponType"] = weaponTypeToString(params.weaponType);
    j["segmentCount"] = params.segmentCount;
    j["segmentLength"] = params.segmentLength;
    j["segmentRadius"] = params.segmentRadius;
    j["segmentShape"] = segmentShapeToString(params.segmentShape);
    j["taperProfile"] = taperProfileToString(params.taperProfile);
    j["jointFlexibility"] = params.jointFlexibility;
    j["articulationLimits"] = {
        {"twist", params.articulationLimits.twist},
        {"swing", params.articulationLimits.swing}
    };
    j["materialType"] = materialTypeToString(params.materialType);
    j["colorPrimary"] = {params.colorPrimary.x, params.colorPrimary.y, params.colorPrimary.z};
    j["colorSecondary"] = {params.colorSecondary.x, params.colorSecondary.y, params.colorSecondary.z};
    j["noiseDetail"] = params.noiseDetail;
    j["textureScale"] = params.textureScale;
    j["ornamentation"] = params.ornamentation;
    j["endAttachment"] = endAttachmentToString(params.endAttachment);
    j["segmentSpacing"] = params.segmentSpacing;
    j["enableJoints"] = params.enableJoints;
    j["jointDamping"] = params.jointDamping;
    j["enableCollision"] = params.enableCollision;
    j["collisionRadius"] = params.collisionRadius;
    j["enablePhysics"] = params.enablePhysics;
    j["physicsMass"] = params.physicsMass;
    j["customTaperCurve"] = params.customTaperCurve;
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    j["enableCaching"] = params.enableCaching;
    j["enableHotReload"] = params.enableHotReload;
    j["enableParallelProcessing"] = params.enableParallelProcessing;
    
    return j;
}

SegmentedWeaponParams fromJson(const nlohmann::json& json) {
    SegmentedWeaponParams params;
    
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
        return {0.15f, 0.05f, 0.02f}; // Default color
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
    params.id = getString("id", "default_whip");
    params.weaponType = parseWeaponType(getString("weaponType", "whip"));
    params.segmentCount = getInt("segmentCount", 16);
    params.segmentLength = getFloat("segmentLength", 0.3f);
    params.segmentRadius = getFloat("segmentRadius", 0.02f);
    params.segmentShape = parseSegmentShape(getString("segmentShape", "cylinder"));
    params.taperProfile = parseTaperProfile(getString("taperProfile", "none"));
    params.jointFlexibility = getFloat("jointFlexibility", 0.9f);
    
    // Parse articulation limits
    if (json.contains("articulationLimits") && json["articulationLimits"].is_object()) {
        params.articulationLimits.twist = getFloat("articulationLimits.twist", 45.0f);
        params.articulationLimits.swing = getFloat("articulationLimits.swing", 60.0f);
    }
    
    params.materialType = parseMaterialType(getString("materialType", "leather"));
    params.colorPrimary = getVec3("colorPrimary");
    params.colorSecondary = getVec3("colorSecondary");
    params.noiseDetail = getFloat("noiseDetail", 0.3f);
    params.textureScale = getFloat("textureScale", 2.0f);
    params.ornamentation = getBool("ornamentation", true);
    params.endAttachment = parseEndAttachment(getString("endAttachment", "blade"));
    
    // Parse additional parameters
    params.segmentSpacing = getFloat("segmentSpacing", 0.05f);
    params.enableJoints = getBool("enableJoints", true);
    params.jointDamping = getFloat("jointDamping", 0.2f);
    params.enableCollision = getBool("enableCollision", true);
    params.collisionRadius = getFloat("collisionRadius", 0.025f);
    params.enablePhysics = getBool("enablePhysics", true);
    params.physicsMass = getFloat("physicsMass", 0.1f);
    
    // Parse custom taper curve
    if (json.contains("customTaperCurve") && json["customTaperCurve"].is_array()) {
        params.customTaperCurve = json["customTaperCurve"].get<std::vector<float>>();
    }
    
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

// JSON serialization for PhysicsParams
nlohmann::json toJson(const PhysicsParams& params) {
    nlohmann::json j;
    
    j["massPerSegment"] = params.massPerSegment;
    j["damping"] = params.damping;
    j["restitution"] = params.restitution;
    j["collisionRadius"] = params.collisionRadius;
    j["solverIterations"] = params.solverIterations;
    j["gravityInfluence"] = params.gravityInfluence;
    j["friction"] = params.friction;
    j["rollingFriction"] = params.rollingFriction;
    j["spinningFriction"] = params.spinningFriction;
    j["enableGravity"] = params.enableGravity;
    j["enableCollisionDetection"] = params.enableCollisionDetection;
    j["maxLinearVelocity"] = params.maxLinearVelocity;
    j["maxAngularVelocity"] = params.maxAngularVelocity;
    j["jointDamping"] = params.jointDamping;
    j["jointFriction"] = params.jointFriction;
    j["enableJointLimits"] = params.enableJointLimits;
    j["jointLimitSoftness"] = params.jointLimitSoftness;
    j["jointLimitBias"] = params.jointLimitBias;
    j["jointLimitRelaxation"] = params.jointLimitRelaxation;
    j["physicsName"] = params.physicsName;
    j["description"] = params.description;
    j["tags"] = params.tags;
    j["metadata"] = params.metadata;
    
    return j;
}

PhysicsParams fromJson(const nlohmann::json& json) {
    PhysicsParams params;
    
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
    params.massPerSegment = getFloat("massPerSegment", 0.1f);
    params.damping = getFloat("damping", 0.2f);
    params.restitution = getFloat("restitution", 0.1f);
    params.collisionRadius = getFloat("collisionRadius", 0.025f);
    params.solverIterations = getInt("solverIterations", 8);
    params.gravityInfluence = getFloat("gravityInfluence", 1.0f);
    params.friction = getFloat("friction", 0.5f);
    params.rollingFriction = getFloat("rollingFriction", 0.1f);
    params.spinningFriction = getFloat("spinningFriction", 0.1f);
    params.enableGravity = getBool("enableGravity", true);
    params.enableCollisionDetection = getBool("enableCollisionDetection", true);
    params.maxLinearVelocity = getFloat("maxLinearVelocity", 100.0f);
    params.maxAngularVelocity = getFloat("maxAngularVelocity", 10.0f);
    params.jointDamping = getFloat("jointDamping", 0.2f);
    params.jointFriction = getFloat("jointFriction", 0.1f);
    params.enableJointLimits = getBool("enableJointLimits", true);
    params.jointLimitSoftness = getFloat("jointLimitSoftness", 0.5f);
    params.jointLimitBias = getFloat("jointLimitBias", 0.3f);
    params.jointLimitRelaxation = getFloat("jointLimitRelaxation", 1.0f);
    params.physicsName = getString("physicsName");
    params.description = getString("description");
    params.tags = getVector("tags");
    params.metadata = getMap("metadata");
    
    return params;
}

} // namespace ParamUtils

} // namespace SegmentedWeapons
} // namespace MagiTech 
