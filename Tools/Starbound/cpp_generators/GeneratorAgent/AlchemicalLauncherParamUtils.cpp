// ParamUtils for the alchemical launcher family: enum <-> string conversion and
// JSON (de)serialization of AlchemicalLauncherParams / UIParams.
#include "AlchemicalLauncherTypes.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <utility>

namespace MagiTech {
namespace AlchemicalLaunchers {
namespace ParamUtils {

namespace {

std::string upper(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return c == '-' || c == ' ' ? '_' : static_cast<char>(std::toupper(c));
    });
    return s;
}

template <typename E, size_t N>
E parseEnum(const std::string& str, const std::array<std::pair<const char*, E>, N>& table, E fallback) {
    const std::string key = upper(str);
    for (const auto& [name, value] : table) {
        if (key == name) return value;
    }
    return fallback;
}

template <typename E, size_t N>
std::string enumToString(E value, const std::array<std::pair<const char*, E>, N>& table) {
    for (const auto& [name, v] : table) {
        if (v == value) return name;
    }
    return "CUSTOM";
}

const std::array<std::pair<const char*, LauncherType>, 9> kLauncherTypes{{
    {"CATAPULT", LauncherType::CATAPULT}, {"CROSSBOW", LauncherType::CROSSBOW},
    {"BALLISTA", LauncherType::BALLISTA}, {"CANNON", LauncherType::CANNON},
    {"ROCKET", LauncherType::ROCKET}, {"RAILGUN", LauncherType::RAILGUN},
    {"MAGIC_STAFF", LauncherType::MAGIC_STAFF}, {"WAND", LauncherType::WAND},
    {"CUSTOM", LauncherType::CUSTOM},
}};

const std::array<std::pair<const char*, MaterialType>, 9> kMaterialTypes{{
    {"STEEL", MaterialType::STEEL}, {"IRON", MaterialType::IRON},
    {"BRONZE", MaterialType::BRONZE}, {"WOOD", MaterialType::WOOD},
    {"STONE", MaterialType::STONE}, {"CRYSTAL", MaterialType::CRYSTAL},
    {"MAGIC", MaterialType::MAGIC}, {"ORGANIC", MaterialType::ORGANIC},
    {"CUSTOM", MaterialType::CUSTOM},
}};

const std::array<std::pair<const char*, SightType>, 6> kSightTypes{{
    {"NONE", SightType::NONE}, {"IRON_SIGHT", SightType::IRON_SIGHT},
    {"SCOPE", SightType::SCOPE}, {"MAGIC_SIGHT", SightType::MAGIC_SIGHT},
    {"THERMAL", SightType::THERMAL}, {"CUSTOM", SightType::CUSTOM},
}};

const std::array<std::pair<const char*, EngravingPattern>, 8> kEngravingPatterns{{
    {"NONE", EngravingPattern::NONE}, {"ALCHEMY_RUNES", EngravingPattern::ALCHEMY_RUNES},
    {"MAGIC_SIGILS", EngravingPattern::MAGIC_SIGILS}, {"GEOMETRIC", EngravingPattern::GEOMETRIC},
    {"FLORAL", EngravingPattern::FLORAL}, {"DRAGON", EngravingPattern::DRAGON},
    {"PHOENIX", EngravingPattern::PHOENIX}, {"CUSTOM", EngravingPattern::CUSTOM},
}};

const std::array<std::pair<const char*, BackgroundShape>, 6> kBackgroundShapes{{
    {"RECTANGLE", BackgroundShape::RECTANGLE}, {"CIRCLE", BackgroundShape::CIRCLE},
    {"HEXAGON", BackgroundShape::HEXAGON}, {"DIAMOND", BackgroundShape::DIAMOND},
    {"NONE", BackgroundShape::NONE}, {"CUSTOM", BackgroundShape::CUSTOM},
}};

nlohmann::json vec3ToJson(const glm::vec3& v) { return nlohmann::json::array({v.x, v.y, v.z}); }
nlohmann::json vec4ToJson(const glm::vec4& v) { return nlohmann::json::array({v.x, v.y, v.z, v.w}); }

glm::vec3 vec3FromJson(const nlohmann::json& j, const char* key, const glm::vec3& def) {
    if (!j.contains(key)) return def;
    const auto& a = j.at(key);
    if (!a.is_array() || a.size() < 3) return def;
    return {a[0].get<float>(), a[1].get<float>(), a[2].get<float>()};
}

glm::vec4 vec4FromJson(const nlohmann::json& j, const char* key, const glm::vec4& def) {
    if (!j.contains(key)) return def;
    const auto& a = j.at(key);
    if (!a.is_array() || a.size() < 3) return def;
    return {a[0].get<float>(), a[1].get<float>(), a[2].get<float>(), a.size() > 3 ? a[3].get<float>() : 1.0f};
}

template <typename T>
void readField(const nlohmann::json& j, const char* key, T& out) {
    if (j.contains(key) && !j.at(key).is_null()) out = j.at(key).get<T>();
}

} // namespace

LauncherType parseLauncherType(const std::string& str) {
    return parseEnum(str, kLauncherTypes, LauncherType::CUSTOM);
}
MaterialType parseMaterialType(const std::string& str) {
    return parseEnum(str, kMaterialTypes, MaterialType::CUSTOM);
}
SightType parseSightType(const std::string& str) {
    return parseEnum(str, kSightTypes, SightType::NONE);
}
EngravingPattern parseEngravingPattern(const std::string& str) {
    return parseEnum(str, kEngravingPatterns, EngravingPattern::NONE);
}
BackgroundShape parseBackgroundShape(const std::string& str) {
    return parseEnum(str, kBackgroundShapes, BackgroundShape::RECTANGLE);
}

std::string launcherTypeToString(LauncherType type) { return enumToString(type, kLauncherTypes); }
std::string materialTypeToString(MaterialType material) { return enumToString(material, kMaterialTypes); }
std::string sightTypeToString(SightType sight) { return enumToString(sight, kSightTypes); }
std::string engravingPatternToString(EngravingPattern pattern) { return enumToString(pattern, kEngravingPatterns); }
std::string backgroundShapeToString(BackgroundShape shape) { return enumToString(shape, kBackgroundShapes); }

nlohmann::json toJson(const AlchemicalLauncherParams& p) {
    nlohmann::json j;
    j["id"] = p.id;
    j["launcherType"] = launcherTypeToString(p.launcherType);
    j["materialMain"] = materialTypeToString(p.materialMain);
    j["materialSecondary"] = materialTypeToString(p.materialSecondary);
    j["sightType"] = sightTypeToString(p.sightType);
    j["engravingPattern"] = engravingPatternToString(p.engravingPattern);

    j["barrelLength"] = p.barrelLength;
    j["barrelRadius"] = p.barrelRadius;
    j["barrelThickness"] = p.barrelThickness;
    j["frameLength"] = p.frameLength;
    j["frameWidth"] = p.frameWidth;
    j["frameHeight"] = p.frameHeight;
    j["gripLength"] = p.gripLength;
    j["gripWidth"] = p.gripWidth;
    j["gripHeight"] = p.gripHeight;
    j["magazineRadius"] = p.magazineRadius;
    j["magazineHeight"] = p.magazineHeight;
    j["magazineCapacity"] = p.magazineCapacity;
    j["sightHeight"] = p.sightHeight;
    j["sightWidth"] = p.sightWidth;

    j["fireRate"] = p.fireRate;
    j["reloadTime"] = p.reloadTime;
    j["accuracy"] = p.accuracy;
    j["range"] = p.range;
    j["projectileSpeed"] = p.projectileSpeed;
    j["recoilForce"] = p.recoilForce;
    j["recoilRecovery"] = p.recoilRecovery;
    j["muzzleVelocity"] = p.muzzleVelocity;

    j["colorPrimary"] = vec3ToJson(p.colorPrimary);
    j["colorSecondary"] = vec3ToJson(p.colorSecondary);
    j["colorAccent"] = vec3ToJson(p.colorAccent);
    j["glowColor"] = vec3ToJson(p.glowColor);
    j["noiseScale"] = p.noiseScale;
    j["noiseIntensity"] = p.noiseIntensity;
    j["metallicness"] = p.metallicness;
    j["roughness"] = p.roughness;
    j["emissivePower"] = p.emissivePower;
    j["transparency"] = p.transparency;
    j["refractionIndex"] = p.refractionIndex;
    j["reflectionStrength"] = p.reflectionStrength;

    j["muzzleGlowIntensity"] = p.muzzleGlowIntensity;
    j["muzzleFlashSize"] = p.muzzleFlashSize;
    j["muzzleFlashDuration"] = p.muzzleFlashDuration;
    j["muzzleSmokeCount"] = p.muzzleSmokeCount;
    j["muzzleSmokeLifetime"] = p.muzzleSmokeLifetime;
    j["muzzleSmokeSize"] = p.muzzleSmokeSize;
    j["muzzleSmokeSpeed"] = p.muzzleSmokeSpeed;
    j["muzzleFlashColor"] = vec3ToJson(p.muzzleFlashColor);
    j["muzzleSmokeColor"] = vec3ToJson(p.muzzleSmokeColor);

    j["enableShellEjection"] = p.enableShellEjection;
    j["shellEjectionCount"] = p.shellEjectionCount;
    j["shellEjectionSpeed"] = p.shellEjectionSpeed;
    j["shellEjectionLifetime"] = p.shellEjectionLifetime;
    j["enableHeatDistortion"] = p.enableHeatDistortion;
    j["heatDistortionStrength"] = p.heatDistortionStrength;
    j["heatDistortionRadius"] = p.heatDistortionRadius;

    j["soundVolume"] = p.soundVolume;
    j["soundPitch"] = p.soundPitch;
    j["soundDuration"] = p.soundDuration;
    j["enableSpatialAudio"] = p.enableSpatialAudio;
    j["audioDistance"] = p.audioDistance;
    j["enableEcho"] = p.enableEcho;
    j["echoDelay"] = p.echoDelay;
    j["echoDecay"] = p.echoDecay;
    j["enableReverb"] = p.enableReverb;
    j["reverbIntensity"] = p.reverbIntensity;

    j["shaderType"] = p.shaderType;
    j["shaderIntensity"] = p.shaderIntensity;
    j["enableDistortion"] = p.enableDistortion;
    j["distortionStrength"] = p.distortionStrength;
    j["enableRefraction"] = p.enableRefraction;
    j["refractionStrength"] = p.refractionStrength;
    j["enableReflection"] = p.enableReflection;
    j["enableEmission"] = p.enableEmission;
    j["emissionStrength"] = p.emissionStrength;

    j["enablePhysics"] = p.enablePhysics;
    j["enableCollision"] = p.enableCollision;
    j["collisionRadius"] = p.collisionRadius;
    j["enableGravity"] = p.enableGravity;
    j["enableAirResistance"] = p.enableAirResistance;
    j["airResistanceFactor"] = p.airResistanceFactor;
    j["enableBounce"] = p.enableBounce;
    j["bounceFactor"] = p.bounceFactor;
    j["mass"] = p.mass;
    j["density"] = p.density;
    j["friction"] = p.friction;
    j["bounciness"] = p.bounciness;

    j["ornamentation"] = p.ornamentation;
    j["ornamentationScale"] = p.ornamentationScale;
    j["ornamentationIntensity"] = p.ornamentationIntensity;
    j["enableRunes"] = p.enableRunes;
    j["runeGlowIntensity"] = p.runeGlowIntensity;
    j["enableCrystals"] = p.enableCrystals;
    j["crystalGlowIntensity"] = p.crystalGlowIntensity;
    j["enableGems"] = p.enableGems;
    j["gemGlowIntensity"] = p.gemGlowIntensity;

    j["enableCaching"] = p.enableCaching;
    j["enableHotReload"] = p.enableHotReload;
    j["enableParallelProcessing"] = p.enableParallelProcessing;
    j["lodLevel"] = p.lodLevel;

    j["description"] = p.description;
    j["tags"] = p.tags;
    j["metadata"] = p.metadata;
    return j;
}

AlchemicalLauncherParams fromJson(const nlohmann::json& j) {
    AlchemicalLauncherParams p{};
    readField(j, "id", p.id);
    p.launcherType = parseLauncherType(j.value("launcherType", std::string("CATAPULT")));
    p.materialMain = parseMaterialType(j.value("materialMain", std::string("STEEL")));
    p.materialSecondary = parseMaterialType(j.value("materialSecondary", std::string("WOOD")));
    p.sightType = parseSightType(j.value("sightType", std::string("NONE")));
    p.engravingPattern = parseEngravingPattern(j.value("engravingPattern", std::string("NONE")));

    readField(j, "barrelLength", p.barrelLength);
    readField(j, "barrelRadius", p.barrelRadius);
    readField(j, "barrelThickness", p.barrelThickness);
    readField(j, "frameLength", p.frameLength);
    readField(j, "frameWidth", p.frameWidth);
    readField(j, "frameHeight", p.frameHeight);
    readField(j, "gripLength", p.gripLength);
    readField(j, "gripWidth", p.gripWidth);
    readField(j, "gripHeight", p.gripHeight);
    readField(j, "magazineRadius", p.magazineRadius);
    readField(j, "magazineHeight", p.magazineHeight);
    readField(j, "magazineCapacity", p.magazineCapacity);
    readField(j, "sightHeight", p.sightHeight);
    readField(j, "sightWidth", p.sightWidth);

    readField(j, "fireRate", p.fireRate);
    readField(j, "reloadTime", p.reloadTime);
    readField(j, "accuracy", p.accuracy);
    readField(j, "range", p.range);
    readField(j, "projectileSpeed", p.projectileSpeed);
    readField(j, "recoilForce", p.recoilForce);
    readField(j, "recoilRecovery", p.recoilRecovery);
    readField(j, "muzzleVelocity", p.muzzleVelocity);

    p.colorPrimary = vec3FromJson(j, "colorPrimary", p.colorPrimary);
    p.colorSecondary = vec3FromJson(j, "colorSecondary", p.colorSecondary);
    p.colorAccent = vec3FromJson(j, "colorAccent", p.colorAccent);
    p.glowColor = vec3FromJson(j, "glowColor", p.glowColor);
    readField(j, "noiseScale", p.noiseScale);
    readField(j, "noiseIntensity", p.noiseIntensity);
    readField(j, "metallicness", p.metallicness);
    readField(j, "roughness", p.roughness);
    readField(j, "emissivePower", p.emissivePower);
    readField(j, "transparency", p.transparency);
    readField(j, "refractionIndex", p.refractionIndex);
    readField(j, "reflectionStrength", p.reflectionStrength);

    readField(j, "muzzleGlowIntensity", p.muzzleGlowIntensity);
    readField(j, "muzzleFlashSize", p.muzzleFlashSize);
    readField(j, "muzzleFlashDuration", p.muzzleFlashDuration);
    readField(j, "muzzleSmokeCount", p.muzzleSmokeCount);
    readField(j, "muzzleSmokeLifetime", p.muzzleSmokeLifetime);
    readField(j, "muzzleSmokeSize", p.muzzleSmokeSize);
    readField(j, "muzzleSmokeSpeed", p.muzzleSmokeSpeed);
    p.muzzleFlashColor = vec3FromJson(j, "muzzleFlashColor", p.muzzleFlashColor);
    p.muzzleSmokeColor = vec3FromJson(j, "muzzleSmokeColor", p.muzzleSmokeColor);

    readField(j, "enableShellEjection", p.enableShellEjection);
    readField(j, "shellEjectionCount", p.shellEjectionCount);
    readField(j, "shellEjectionSpeed", p.shellEjectionSpeed);
    readField(j, "shellEjectionLifetime", p.shellEjectionLifetime);
    readField(j, "enableHeatDistortion", p.enableHeatDistortion);
    readField(j, "heatDistortionStrength", p.heatDistortionStrength);
    readField(j, "heatDistortionRadius", p.heatDistortionRadius);

    readField(j, "soundVolume", p.soundVolume);
    readField(j, "soundPitch", p.soundPitch);
    readField(j, "soundDuration", p.soundDuration);
    readField(j, "enableSpatialAudio", p.enableSpatialAudio);
    readField(j, "audioDistance", p.audioDistance);
    readField(j, "enableEcho", p.enableEcho);
    readField(j, "echoDelay", p.echoDelay);
    readField(j, "echoDecay", p.echoDecay);
    readField(j, "enableReverb", p.enableReverb);
    readField(j, "reverbIntensity", p.reverbIntensity);

    readField(j, "shaderType", p.shaderType);
    readField(j, "shaderIntensity", p.shaderIntensity);
    readField(j, "enableDistortion", p.enableDistortion);
    readField(j, "distortionStrength", p.distortionStrength);
    readField(j, "enableRefraction", p.enableRefraction);
    readField(j, "refractionStrength", p.refractionStrength);
    readField(j, "enableReflection", p.enableReflection);
    readField(j, "enableEmission", p.enableEmission);
    readField(j, "emissionStrength", p.emissionStrength);

    readField(j, "enablePhysics", p.enablePhysics);
    readField(j, "enableCollision", p.enableCollision);
    readField(j, "collisionRadius", p.collisionRadius);
    readField(j, "enableGravity", p.enableGravity);
    readField(j, "enableAirResistance", p.enableAirResistance);
    readField(j, "airResistanceFactor", p.airResistanceFactor);
    readField(j, "enableBounce", p.enableBounce);
    readField(j, "bounceFactor", p.bounceFactor);
    readField(j, "mass", p.mass);
    readField(j, "density", p.density);
    readField(j, "friction", p.friction);
    readField(j, "bounciness", p.bounciness);

    readField(j, "ornamentation", p.ornamentation);
    readField(j, "ornamentationScale", p.ornamentationScale);
    readField(j, "ornamentationIntensity", p.ornamentationIntensity);
    readField(j, "enableRunes", p.enableRunes);
    readField(j, "runeGlowIntensity", p.runeGlowIntensity);
    readField(j, "enableCrystals", p.enableCrystals);
    readField(j, "crystalGlowIntensity", p.crystalGlowIntensity);
    readField(j, "enableGems", p.enableGems);
    readField(j, "gemGlowIntensity", p.gemGlowIntensity);

    readField(j, "enableCaching", p.enableCaching);
    readField(j, "enableHotReload", p.enableHotReload);
    readField(j, "enableParallelProcessing", p.enableParallelProcessing);
    readField(j, "lodLevel", p.lodLevel);

    readField(j, "description", p.description);
    readField(j, "tags", p.tags);
    readField(j, "metadata", p.metadata);
    return p;
}

nlohmann::json toJson(const UIParams& u) {
    nlohmann::json j;
    j["iconSize"] = u.iconSize;
    j["borderColor"] = vec4ToJson(u.borderColor);
    j["backgroundShape"] = backgroundShapeToString(u.backgroundShape);
    j["flashOnSelect"] = u.flashOnSelect;
    j["borderThickness"] = u.borderThickness;
    j["cornerRadius"] = u.cornerRadius;
    j["enableGlow"] = u.enableGlow;
    j["glowColor"] = vec3ToJson(u.glowColor);
    j["glowIntensity"] = u.glowIntensity;
    j["enablePulse"] = u.enablePulse;
    j["pulseFrequency"] = u.pulseFrequency;
    j["pulseAmplitude"] = u.pulseAmplitude;
    j["enableHoverEffect"] = u.enableHoverEffect;
    j["hoverScale"] = u.hoverScale;
    j["hoverDuration"] = u.hoverDuration;
    j["enableClickEffect"] = u.enableClickEffect;
    j["clickScale"] = u.clickScale;
    j["clickDuration"] = u.clickDuration;
    j["label"] = u.label;
    j["enableLabel"] = u.enableLabel;
    j["labelColor"] = vec3ToJson(u.labelColor);
    j["labelSize"] = u.labelSize;
    j["labelFont"] = u.labelFont;
    j["enableCaching"] = u.enableCaching;
    j["enableHotReload"] = u.enableHotReload;
    j["lodLevel"] = u.lodLevel;
    j["description"] = u.description;
    j["tags"] = u.tags;
    j["metadata"] = u.metadata;
    return j;
}

UIParams uiParamsFromJson(const nlohmann::json& j) {
    UIParams u{};
    readField(j, "iconSize", u.iconSize);
    u.borderColor = vec4FromJson(j, "borderColor", u.borderColor);
    u.backgroundShape = parseBackgroundShape(j.value("backgroundShape", std::string("RECTANGLE")));
    readField(j, "flashOnSelect", u.flashOnSelect);
    readField(j, "borderThickness", u.borderThickness);
    readField(j, "cornerRadius", u.cornerRadius);
    readField(j, "enableGlow", u.enableGlow);
    u.glowColor = vec3FromJson(j, "glowColor", u.glowColor);
    readField(j, "glowIntensity", u.glowIntensity);
    readField(j, "enablePulse", u.enablePulse);
    readField(j, "pulseFrequency", u.pulseFrequency);
    readField(j, "pulseAmplitude", u.pulseAmplitude);
    readField(j, "enableHoverEffect", u.enableHoverEffect);
    readField(j, "hoverScale", u.hoverScale);
    readField(j, "hoverDuration", u.hoverDuration);
    readField(j, "enableClickEffect", u.enableClickEffect);
    readField(j, "clickScale", u.clickScale);
    readField(j, "clickDuration", u.clickDuration);
    readField(j, "label", u.label);
    readField(j, "enableLabel", u.enableLabel);
    u.labelColor = vec3FromJson(j, "labelColor", u.labelColor);
    readField(j, "labelSize", u.labelSize);
    readField(j, "labelFont", u.labelFont);
    readField(j, "enableCaching", u.enableCaching);
    readField(j, "enableHotReload", u.enableHotReload);
    readField(j, "lodLevel", u.lodLevel);
    readField(j, "description", u.description);
    readField(j, "tags", u.tags);
    readField(j, "metadata", u.metadata);
    return u;
}

} // namespace ParamUtils
} // namespace AlchemicalLaunchers
} // namespace MagiTech
