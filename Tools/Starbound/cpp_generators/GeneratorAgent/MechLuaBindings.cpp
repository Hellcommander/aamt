#include "MechLuaBindings.hpp"
#include "MechFactory.hpp"
#include "MechTypes.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <cmath>
#include <future>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>

namespace MagiTech {
namespace Mechs {

namespace {

// ------------------------------------------------------------ factory slot --

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}

std::shared_ptr<MechFactory>& factorySlot() {
    static std::shared_ptr<MechFactory> f;
    return f;
}

// ------------------------------------------------------- spawn_mech queue ---

struct PendingMech {
    std::future<MechBundle> future;
    std::string id;
};

std::mutex& pendingMutex() {
    static std::mutex m;
    return m;
}

std::vector<PendingMech>& pendingMechs() {
    static std::vector<PendingMech> pending;
    return pending;
}

void queueSpawn(const MechParams& params) {
    auto future = MechLuaBindings::factory()->generateAsync(params);
    std::lock_guard<std::mutex> lock(pendingMutex());
    pendingMechs().push_back(PendingMech{std::move(future), params.id});
}

// ---------------------------------------------------------------- futures ---

template <typename T>
struct LuaFuture {
    std::shared_future<T> future;

    T get() const { return future.get(); }
    bool ready() const { return future.wait_for(std::chrono::seconds(0)) == std::future_status::ready; }
};

using MechBundleFuture = LuaFuture<MechBundle>;
using SegmentedBundleFuture = LuaFuture<SegmentedMechBundle>;
using CentipedeBundleFuture = LuaFuture<CentipedeMechBundle>;

// ------------------------------------------------------- table conversions --

bool isNumber(const sol::object& o) { return o.get_type() == sol::type::number; }

template <typename T>
void readNumber(const sol::table& t, const char* key, T& out) {
    sol::object o = t[key];
    if (isNumber(o)) out = static_cast<T>(o.as<double>());
}

void readBool(const sol::table& t, const char* key, bool& out) {
    sol::object o = t[key];
    if (o.get_type() == sol::type::boolean) out = o.as<bool>();
}

void readString(const sol::table& t, const char* key, std::string& out) {
    sol::object o = t[key];
    if (o.get_type() == sol::type::string) out = o.as<std::string>();
}

void readStringList(const sol::table& t, const char* key, std::vector<std::string>& out) {
    sol::object o = t[key];
    if (o.get_type() != sol::type::table) return;
    sol::table list = o.as<sol::table>();
    out.clear();
    for (size_t i = 1; i <= list.size(); ++i) {
        sol::object item = list[i];
        if (item.get_type() == sol::type::string) out.push_back(item.as<std::string>());
    }
}

template <typename T>
void readNumberList(const sol::table& t, const char* key, std::vector<T>& out) {
    sol::object o = t[key];
    if (o.get_type() != sol::type::table) return;
    sol::table list = o.as<sol::table>();
    out.clear();
    for (size_t i = 1; i <= list.size(); ++i) {
        sol::object item = list[i];
        if (isNumber(item)) out.push_back(static_cast<T>(item.as<double>()));
    }
}

void readFloatMap(const sol::table& t, const char* key, std::unordered_map<std::string, float>& out) {
    sol::object o = t[key];
    if (o.get_type() != sol::type::table) return;
    out.clear();
    for (const auto& [k, v] : o.as<sol::table>()) {
        if (k.get_type() == sol::type::string && isNumber(v)) out[k.as<std::string>()] = v.as<float>();
    }
}

// Reads {x, y, z, w} arrays or {x=, y=, z=, w=} tables component by component.
template <int N>
void readComponents(const sol::table& t, float* out) {
    static const char* names[4] = {"x", "y", "z", "w"};
    for (int i = 0; i < N; ++i) {
        sol::object o = t[i + 1];
        if (!isNumber(o)) o = t[names[i]];
        if (isNumber(o)) out[i] = o.as<float>();
    }
}

void readVec2(const sol::table& t, const char* key, glm::vec2& out) {
    sol::object o = t[key];
    if (o.get_type() == sol::type::table) readComponents<2>(o.as<sol::table>(), &out.x);
}
void readVec3(const sol::table& t, const char* key, glm::vec3& out) {
    sol::object o = t[key];
    if (o.get_type() == sol::type::table) readComponents<3>(o.as<sol::table>(), &out.x);
}
void readVec4(const sol::table& t, const char* key, glm::vec4& out) {
    sol::object o = t[key];
    if (o.get_type() == sol::type::table) readComponents<4>(o.as<sol::table>(), &out.x);
}

sol::table vecToTable(sol::state_view lua, const float* v, int n) {
    sol::table t = lua.create_table(n, 0);
    for (int i = 0; i < n; ++i) t[i + 1] = v[i];
    return t;
}

// Usertype properties exposing glm vectors as Lua arrays {x, y, z[, w]}.
template <typename S, typename V>
auto vecProperty(V S::*member) {
    constexpr int n = static_cast<int>(V::length());
    return sol::property(
        [member](const S& self, sol::this_state s) { return vecToTable(sol::state_view(s), &(self.*member).x, n); },
        [member](S& self, const sol::table& value) { readComponents<n>(value, &(self.*member).x); });
}

std::unordered_map<std::string, float> toFloatMap(const sol::table& t) {
    std::unordered_map<std::string, float> out;
    for (const auto& [k, v] : t) {
        if (k.get_type() == sol::type::string && isNumber(v)) out[k.as<std::string>()] = v.as<float>();
    }
    return out;
}

// Usertype properties exposing string->float maps as plain Lua tables (copied
// in and out, since sol's container adaptor does not support unordered_map here).
template <typename S>
auto floatMapProperty(std::unordered_map<std::string, float> S::*member) {
    return sol::property(
        [member](const S& self, sol::this_state s) {
            sol::state_view lua(s);
            sol::table t = lua.create_table();
            for (const auto& [k, v] : self.*member) t[k] = v;
            return t;
        },
        [member](S& self, const sol::table& value) { self.*member = toFloatMap(value); });
}

template <typename T>
bool fromUsertype(const sol::object& value, T& out) {
    if (value.is<T>()) {
        out = value.as<T>();
        return true;
    }
    return false;
}

[[noreturn]] void badArgument(const char* expected) {
    throw std::invalid_argument(std::string("expected a ") + expected + " or a table");
}

} // namespace

// ============================================================================
// LuaHelpers
// ============================================================================

namespace LuaHelpers {

MechParams toMechParams(const sol::object& value) {
    MechParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("MechParams");
    const sol::table t = value.as<sol::table>();
    readString(t, "id", p.id);
    readString(t, "style", p.style);
    readString(t, "pattern", p.pattern);
    readString(t, "variant", p.variant);
    readString(t, "aiBehavior", p.aiBehavior);
    readString(t, "faction", p.faction);
    readString(t, "morphCurve", p.morphCurve);
    readStringList(t, "forms", p.forms);
    readStringList(t, "weaponMounts", p.weaponMounts);
    readStringList(t, "armorTypes", p.armorTypes);
    readStringList(t, "weaponTypes", p.weaponTypes);
    readStringList(t, "abilities", p.abilities);
    readFloatMap(t, "stats", p.stats);
    readVec3(t, "colorPrimary", p.colorPrimary);
    readVec3(t, "colorAccent", p.colorAccent);
    readVec3(t, "torsoSize", p.torsoSize);
    readVec3(t, "scale", p.scale);
    readNumber(t, "limbCount", p.limbCount);
    readNumber(t, "detailLevel", p.detailLevel);
    readNumber(t, "limbLength", p.limbLength);
    readNumber(t, "mass", p.mass);
    readNumber(t, "crewCapacity", p.crewCapacity);
    readNumber(t, "maxSpeed", p.maxSpeed);
    readNumber(t, "jumpHeight", p.jumpHeight);
    readNumber(t, "noiseScale", p.noiseScale);
    readNumber(t, "patternIntensity", p.patternIntensity);
    readNumber(t, "textureResolution", p.textureResolution);
    readNumber(t, "morphDuration", p.morphDuration);
    readBool(t, "armorPlates", p.armorPlates);
    readBool(t, "pulseEmission", p.pulseEmission);
    readBool(t, "enableGlow", p.enableGlow);
    readBool(t, "enableShield", p.enableShield);
    readBool(t, "canFly", p.canFly);
    readBool(t, "canSwim", p.canSwim);
    readBool(t, "generateNormalMap", p.generateNormalMap);
    readBool(t, "generateRoughnessMap", p.generateRoughnessMap);
    readBool(t, "generateMetallicMap", p.generateMetallicMap);
    readBool(t, "enableIK", p.enableIK);
    readBool(t, "enablePhysics", p.enablePhysics);
    readNumberList(t, "lodDistances", p.lodDistances);
    readNumberList(t, "lodTriangleCounts", p.lodTriangleCounts);
    return p;
}

SegmentedMechParams toSegmentedMechParams(const sol::object& value) {
    SegmentedMechParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("SegmentedMechParams");
    const sol::table t = value.as<sol::table>();
    readString(t, "id", p.id);
    readString(t, "mechType", p.mechType);
    readNumber(t, "segmentCount", p.segmentCount);
    readNumber(t, "segmentLength", p.segmentLength);
    readNumber(t, "segmentRadius", p.segmentRadius);
    readNumber(t, "connectorGap", p.connectorGap);
    readNumber(t, "maxBendAngleDeg", p.maxBendAngleDeg);
    readNumber(t, "bendStiffness", p.bendStiffness);
    readNumber(t, "jointFlexibility", p.jointFlexibility);
    readBool(t, "enablePlating", p.enablePlating);
    readNumber(t, "platesPerSegment", p.platesPerSegment);
    readNumber(t, "plateThickness", p.plateThickness);
    readVec4(t, "platingColor", p.platingColor);
    readNumber(t, "platingDetailLevel", p.platingDetailLevel);
    readNumber(t, "stripeCount", p.stripeCount);
    readNumber(t, "stripeWidth", p.stripeWidth);
    readVec4(t, "stripeColor", p.stripeColor);
    readNumber(t, "stripeGlowIntensity", p.stripeGlowIntensity);
    readBool(t, "enableJointSparks", p.enableJointSparks);
    readNumber(t, "sparkRate", p.sparkRate);
    readNumber(t, "sparkLifetime", p.sparkLifetime);
    readVec4(t, "sparkColor", p.sparkColor);
    readNumber(t, "segmentMass", p.segmentMass);
    readNumber(t, "jointDamping", p.jointDamping);
    readNumber(t, "waveAmplitude", p.waveAmplitude);
    readNumber(t, "waveFrequency", p.waveFrequency);
    readString(t, "animationProfile", p.animationProfile);
    readString(t, "cockpitType", p.cockpitType);
    readNumber(t, "cockpitSegmentIndex", p.cockpitSegmentIndex);
    readNumber(t, "cockpitRadius", p.cockpitRadius);
    readVec3(t, "cockpitOrientation", p.cockpitOrientation);
    readString(t, "taperProfile", p.taperProfile);
    readString(t, "segmentShape", p.segmentShape);
    readNumber(t, "noiseDetail", p.noiseDetail);
    readNumber(t, "textureScale", p.textureScale);
    readVec3(t, "colorPrimary", p.colorPrimary);
    readVec3(t, "colorSecondary", p.colorSecondary);
    readString(t, "aiProfile", p.aiProfile);
    readBool(t, "rebuildOnLOD", p.rebuildOnLOD);
    readNumber(t, "lodCount", p.lodCount);
    return p;
}

CockpitParams toCockpitParams(const sol::object& value) {
    CockpitParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("CockpitParams");
    const sol::table t = value.as<sol::table>();
    readNumber(t, "seatWidth", p.seatWidth);
    readNumber(t, "seatDepth", p.seatDepth);
    readNumber(t, "seatHeight", p.seatHeight);
    readVec4(t, "seatFabricColor", p.seatFabricColor);
    readBool(t, "headrestEnabled", p.headrestEnabled);
    readNumber(t, "canopyRadius", p.canopyRadius);
    readNumber(t, "canopyHeight", p.canopyHeight);
    readNumber(t, "glassThickness", p.glassThickness);
    readVec4(t, "glassTint", p.glassTint);
    readNumber(t, "reflectivity", p.reflectivity);
    readNumber(t, "displayCount", p.displayCount);
    readVec2(t, "displayResolution", p.displayResolution);
    readNumber(t, "stickOffsetX", p.stickOffsetX);
    readNumber(t, "stickOffsetY", p.stickOffsetY);
    readBool(t, "throttleLever", p.throttleLever);
    readBool(t, "pedalControls", p.pedalControls);
    readNumber(t, "gaugeCount", p.gaugeCount);
    readNumber(t, "gaugeRadius", p.gaugeRadius);
    readVec4(t, "gaugeNeedleColor", p.gaugeNeedleColor);
    readBool(t, "holographicHUD", p.holographicHUD);
    readBool(t, "cockpitLight", p.cockpitLight);
    readVec4(t, "lightColor", p.lightColor);
    readNumber(t, "lightIntensity", p.lightIntensity);
    readBool(t, "canopyAnimEnabled", p.canopyAnimEnabled);
    readNumber(t, "canopyOpenAngleDeg", p.canopyOpenAngleDeg);
    readNumber(t, "canopyOpenDuration", p.canopyOpenDuration);
    readVec3(t, "mountOffset", p.mountOffset);
    sol::object rotation = t["mountRotation"];
    if (rotation.get_type() == sol::type::table) {
        // {w, x, y, z}
        float q[4] = {p.mountRotation.w, p.mountRotation.x, p.mountRotation.y, p.mountRotation.z};
        const sol::table r = rotation.as<sol::table>();
        for (int i = 0; i < 4; ++i) {
            sol::object c = r[i + 1];
            if (isNumber(c)) q[i] = c.as<float>();
        }
        p.mountRotation = glm::normalize(glm::quat(q[0], q[1], q[2], q[3]));
    }
    return p;
}

UIParams toUIParams(const sol::object& value) {
    UIParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("UIParams");
    const sol::table t = value.as<sol::table>();
    readNumber(t, "iconSize", p.iconSize);
    readVec4(t, "borderColor", p.borderColor);
    readString(t, "backgroundShape", p.backgroundShape);
    readBool(t, "flashOnSelect", p.flashOnSelect);
    return p;
}

CentipedeMechParams toCentipedeMechParams(const sol::object& value) {
    CentipedeMechParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("CentipedeMechParams");
    const sol::table t = value.as<sol::table>();
    readString(t, "id", p.id);
    readNumber(t, "segmentCount", p.segmentCount);
    readNumber(t, "segmentLength", p.segmentLength);
    readNumber(t, "segmentRadius", p.segmentRadius);
    readVec4(t, "baseColor", p.baseColor);
    readBool(t, "seamlessJoints", p.seamlessJoints);
    readNumber(t, "legsPerSegment", p.legsPerSegment);
    readNumber(t, "upperLegLength", p.upperLegLength);
    readNumber(t, "lowerLegLength", p.lowerLegLength);
    readNumber(t, "jointRadius", p.jointRadius);
    readBool(t, "armorPlates", p.armorPlates);
    readString(t, "footType", p.footType);
    readBool(t, "hasCockpit", p.hasCockpit);
    readVec3(t, "cockpitPosition", p.cockpitPosition);
    readNumber(t, "cockpitWidth", p.cockpitWidth);
    readNumber(t, "cockpitHeight", p.cockpitHeight);
    readNumber(t, "cockpitDepth", p.cockpitDepth);
    readBool(t, "enableDisplays", p.enableDisplays);
    readNumber(t, "displayCount", p.displayCount);
    readString(t, "seatMaterial", p.seatMaterial);
    readString(t, "controlStyle", p.controlStyle);
    readNumber(t, "missileTubes", p.missileTubes);
    readNumber(t, "autocannonSlots", p.autocannonSlots);
    readBool(t, "enableTurret", p.enableTurret);
    readBool(t, "enableRadarArray", p.enableRadarArray);
    readNumber(t, "radarRange", p.radarRange);
    return p;
}

ProceduralParams toProceduralParams(const sol::object& value) {
    ProceduralParams p;
    if (fromUsertype(value, p) || value.get_type() == sol::type::lua_nil) return p;
    if (value.get_type() != sol::type::table) badArgument("ProceduralParams");
    const sol::table t = value.as<sol::table>();
    readNumber(t, "frequency", p.frequency);
    readNumber(t, "amplitude", p.amplitude);
    readNumber(t, "octaves", p.octaves);
    readNumber(t, "persistence", p.persistence);
    readNumber(t, "lacunarity", p.lacunarity);
    readString(t, "patternType", p.patternType);
    readNumber(t, "patternScale", p.patternScale);
    readNumber(t, "patternRotation", p.patternRotation);
    readVec3(t, "patternColor", p.patternColor);
    readNumber(t, "roughness", p.roughness);
    readNumber(t, "metallic", p.metallic);
    readNumber(t, "emissive", p.emissive);
    readNumber(t, "normalStrength", p.normalStrength);
    return p;
}

sol::table proceduralParamsToTable(sol::state_view lua, const ProceduralParams& p) {
    sol::table t = lua.create_table();
    t["frequency"] = p.frequency;
    t["amplitude"] = p.amplitude;
    t["octaves"] = p.octaves;
    t["persistence"] = p.persistence;
    t["lacunarity"] = p.lacunarity;
    t["patternType"] = p.patternType;
    t["patternScale"] = p.patternScale;
    t["patternRotation"] = p.patternRotation;
    t["patternColor"] = vecToTable(lua, &p.patternColor.x, 3);
    t["roughness"] = p.roughness;
    t["metallic"] = p.metallic;
    t["emissive"] = p.emissive;
    t["normalStrength"] = p.normalStrength;
    return t;
}

sol::table performanceMetricsToTable(sol::state_view lua, const MechPerformanceMetrics& m) {
    sol::table t = lua.create_table();
    t["totalGenerations"] = m.totalGenerations.load();
    t["cacheHits"] = m.cacheHits.load();
    t["cacheMisses"] = m.cacheMisses.load();
    t["cacheHitRate"] = m.getCacheHitRate();
    t["totalGenerationTime"] = m.totalGenerationTime.load();
    t["averageGenerationTime"] = m.getAverageGenerationTime();
    t["peakMemoryUsage"] = m.peakMemoryUsage.load();
    t["activeInstances"] = m.activeInstances.load();
    t["morphingInstances"] = m.morphingInstances.load();
    return t;
}

sol::table stringListToTable(sol::state_view lua, const std::vector<std::string>& values) {
    sol::table t = lua.create_table(static_cast<int>(values.size()), 0);
    for (size_t i = 0; i < values.size(); ++i) t[i + 1] = values[i];
    return t;
}

bool setMechProperty(MechInstanceState& s, const std::string& property, float value) {
    if (property == "positionX") s.position.x = value;
    else if (property == "positionY") s.position.y = value;
    else if (property == "positionZ") s.position.z = value;
    else if (property == "velocityX") s.velocity.x = value;
    else if (property == "velocityY") s.velocity.y = value;
    else if (property == "velocityZ") s.velocity.z = value;
    else if (property == "accelerationX") s.acceleration.x = value;
    else if (property == "accelerationY") s.acceleration.y = value;
    else if (property == "accelerationZ") s.acceleration.z = value;
    else if (property == "animationTime") s.animationTime = value;
    else if (property == "scale") s.scale = glm::vec3(value);
    else if (property == "maxSpeed") s.params.maxSpeed = value;
    else if (property == "jumpHeight") s.params.jumpHeight = value;
    else return false;
    return true;
}

bool getMechProperty(const MechInstanceState& s, const std::string& property, float& value) {
    if (property == "positionX") value = s.position.x;
    else if (property == "positionY") value = s.position.y;
    else if (property == "positionZ") value = s.position.z;
    else if (property == "velocityX") value = s.velocity.x;
    else if (property == "velocityY") value = s.velocity.y;
    else if (property == "velocityZ") value = s.velocity.z;
    else if (property == "accelerationX") value = s.acceleration.x;
    else if (property == "accelerationY") value = s.acceleration.y;
    else if (property == "accelerationZ") value = s.acceleration.z;
    else if (property == "animationTime") value = s.animationTime;
    else if (property == "scale") value = s.scale.x;
    else if (property == "maxSpeed") value = s.params.maxSpeed;
    else if (property == "jumpHeight") value = s.params.jumpHeight;
    else if (property == "morphProgress") value = s.morphProgress;
    else if (property == "mass") value = s.bundle.mass;
    else return false;
    return true;
}

bool setSegmentedMechProperty(SegmentedMechInstanceState& s, const std::string& property, float value) {
    if (property == "positionX") s.position.x = value;
    else if (property == "positionY") s.position.y = value;
    else if (property == "positionZ") s.position.z = value;
    else if (property == "velocityX") s.velocity.x = value;
    else if (property == "velocityY") s.velocity.y = value;
    else if (property == "velocityZ") s.velocity.z = value;
    else if (property == "accelerationX") s.acceleration.x = value;
    else if (property == "accelerationY") s.acceleration.y = value;
    else if (property == "accelerationZ") s.acceleration.z = value;
    else if (property == "animationTime") s.animationTime = value;
    else if (property == "scale") s.scale = glm::vec3(value);
    else return false;
    return true;
}

bool getSegmentedMechProperty(const SegmentedMechInstanceState& s, const std::string& property, float& value) {
    if (property == "positionX") value = s.position.x;
    else if (property == "positionY") value = s.position.y;
    else if (property == "positionZ") value = s.position.z;
    else if (property == "velocityX") value = s.velocity.x;
    else if (property == "velocityY") value = s.velocity.y;
    else if (property == "velocityZ") value = s.velocity.z;
    else if (property == "accelerationX") value = s.acceleration.x;
    else if (property == "accelerationY") value = s.acceleration.y;
    else if (property == "accelerationZ") value = s.acceleration.z;
    else if (property == "animationTime") value = s.animationTime;
    else if (property == "scale") value = s.scale.x;
    else if (property == "segmentCount") value = static_cast<float>(s.currentSegmentCount);
    else if (property == "segmentRadius") value = s.params.segmentRadius;
    else if (property == "segmentLength") value = s.params.segmentLength;
    else return false;
    return true;
}

std::string describeMech(const MechInstanceState& s) {
    std::ostringstream out;
    out << "Mech '" << s.id << "' (" << s.params.style << ", " << s.params.variant << "): form '" << s.currentForm << "'";
    if (s.isMorphing) {
        out << " morphing to '" << s.targetForm << "' " << static_cast<int>(s.morphProgress * 100.0f) << "%"
            << (s.morphPaused ? " (paused)" : "");
    }
    out << ", " << s.params.limbCount << " limbs, mass " << s.bundle.mass << ", position (" << s.position.x << ", "
        << s.position.y << ", " << s.position.z << ")";
    return out.str();
}

std::string describeSegmentedMech(const SegmentedMechInstanceState& s) {
    std::ostringstream out;
    out << "Segmented mech '" << s.id << "' (" << s.params.mechType << "): " << s.currentSegmentCount << " segments, "
        << "cockpit " << (s.cockpitAttached ? s.params.cockpitType : std::string("detached")) << ", animation '"
        << s.currentAnimation << "'" << (s.animationPaused ? " (paused)" : "") << ", position (" << s.position.x
        << ", " << s.position.y << ", " << s.position.z << ")";
    return out.str();
}

} // namespace LuaHelpers

// ============================================================================
// MechLuaBindings
// ============================================================================

void MechLuaBindings::setFactory(std::shared_ptr<MechFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<MechFactory> MechLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<MechFactory>();
        slot->initialize(64, 4);
    }
    return slot;
}

void registerMechLuaBindings(lua_State* L) {
    MechLuaBindings::bind(sol::state_view(L));
}

void MechLuaBindings::bind(sol::state_view lua) {
    using namespace LuaHelpers;
    sol::table mt = lua["mt_mech"].get_or_create<sol::table>();

    // ---------------------------------------------------------- usertypes --
    auto params = mt.new_usertype<MechParams>("MechParams", sol::constructors<MechParams()>());
    params["id"] = &MechParams::id;
    params["style"] = &MechParams::style;
    params["pattern"] = &MechParams::pattern;
    params["forms"] = &MechParams::forms;
    params["weaponMounts"] = &MechParams::weaponMounts;
    params["colorPrimary"] = vecProperty(&MechParams::colorPrimary);
    params["colorAccent"] = vecProperty(&MechParams::colorAccent);
    params["limbCount"] = &MechParams::limbCount;
    params["detailLevel"] = &MechParams::detailLevel;
    params["torsoSize"] = vecProperty(&MechParams::torsoSize);
    params["limbLength"] = &MechParams::limbLength;
    params["armorPlates"] = &MechParams::armorPlates;
    params["pulseEmission"] = &MechParams::pulseEmission;
    params["variant"] = &MechParams::variant;
    params["armorTypes"] = &MechParams::armorTypes;
    params["weaponTypes"] = &MechParams::weaponTypes;
    params["scale"] = vecProperty(&MechParams::scale);
    params["mass"] = &MechParams::mass;
    params["enableGlow"] = &MechParams::enableGlow;
    params["enableShield"] = &MechParams::enableShield;
    params["aiBehavior"] = &MechParams::aiBehavior;
    params["crewCapacity"] = &MechParams::crewCapacity;
    params["maxSpeed"] = &MechParams::maxSpeed;
    params["jumpHeight"] = &MechParams::jumpHeight;
    params["canFly"] = &MechParams::canFly;
    params["canSwim"] = &MechParams::canSwim;
    params["faction"] = &MechParams::faction;
    params["abilities"] = &MechParams::abilities;
    params["stats"] = floatMapProperty(&MechParams::stats);
    params["noiseScale"] = &MechParams::noiseScale;
    params["patternIntensity"] = &MechParams::patternIntensity;
    params["textureResolution"] = &MechParams::textureResolution;
    params["generateNormalMap"] = &MechParams::generateNormalMap;
    params["generateRoughnessMap"] = &MechParams::generateRoughnessMap;
    params["generateMetallicMap"] = &MechParams::generateMetallicMap;
    params["morphDuration"] = &MechParams::morphDuration;
    params["morphCurve"] = &MechParams::morphCurve;
    params["enableIK"] = &MechParams::enableIK;
    params["enablePhysics"] = &MechParams::enablePhysics;
    params["lodDistances"] = &MechParams::lodDistances;
    params["lodTriangleCounts"] = &MechParams::lodTriangleCounts;

    auto segParams = mt.new_usertype<SegmentedMechParams>("SegmentedMechParams", sol::constructors<SegmentedMechParams()>());
    segParams["id"] = &SegmentedMechParams::id;
    segParams["mechType"] = &SegmentedMechParams::mechType;
    segParams["segmentCount"] = &SegmentedMechParams::segmentCount;
    segParams["segmentLength"] = &SegmentedMechParams::segmentLength;
    segParams["segmentRadius"] = &SegmentedMechParams::segmentRadius;
    segParams["connectorGap"] = &SegmentedMechParams::connectorGap;
    segParams["maxBendAngleDeg"] = &SegmentedMechParams::maxBendAngleDeg;
    segParams["bendStiffness"] = &SegmentedMechParams::bendStiffness;
    segParams["jointFlexibility"] = &SegmentedMechParams::jointFlexibility;
    segParams["enablePlating"] = &SegmentedMechParams::enablePlating;
    segParams["platesPerSegment"] = &SegmentedMechParams::platesPerSegment;
    segParams["plateThickness"] = &SegmentedMechParams::plateThickness;
    segParams["platingColor"] = vecProperty(&SegmentedMechParams::platingColor);
    segParams["platingDetailLevel"] = &SegmentedMechParams::platingDetailLevel;
    segParams["stripeCount"] = &SegmentedMechParams::stripeCount;
    segParams["stripeWidth"] = &SegmentedMechParams::stripeWidth;
    segParams["stripeColor"] = vecProperty(&SegmentedMechParams::stripeColor);
    segParams["stripeGlowIntensity"] = &SegmentedMechParams::stripeGlowIntensity;
    segParams["enableJointSparks"] = &SegmentedMechParams::enableJointSparks;
    segParams["sparkRate"] = &SegmentedMechParams::sparkRate;
    segParams["sparkLifetime"] = &SegmentedMechParams::sparkLifetime;
    segParams["sparkColor"] = vecProperty(&SegmentedMechParams::sparkColor);
    segParams["segmentMass"] = &SegmentedMechParams::segmentMass;
    segParams["jointDamping"] = &SegmentedMechParams::jointDamping;
    segParams["waveAmplitude"] = &SegmentedMechParams::waveAmplitude;
    segParams["waveFrequency"] = &SegmentedMechParams::waveFrequency;
    segParams["animationProfile"] = &SegmentedMechParams::animationProfile;
    segParams["cockpitType"] = &SegmentedMechParams::cockpitType;
    segParams["cockpitSegmentIndex"] = &SegmentedMechParams::cockpitSegmentIndex;
    segParams["cockpitRadius"] = &SegmentedMechParams::cockpitRadius;
    segParams["cockpitOrientation"] = vecProperty(&SegmentedMechParams::cockpitOrientation);
    segParams["taperProfile"] = &SegmentedMechParams::taperProfile;
    segParams["segmentShape"] = &SegmentedMechParams::segmentShape;
    segParams["noiseDetail"] = &SegmentedMechParams::noiseDetail;
    segParams["textureScale"] = &SegmentedMechParams::textureScale;
    segParams["colorPrimary"] = vecProperty(&SegmentedMechParams::colorPrimary);
    segParams["colorSecondary"] = vecProperty(&SegmentedMechParams::colorSecondary);
    segParams["aiProfile"] = &SegmentedMechParams::aiProfile;
    segParams["rebuildOnLOD"] = &SegmentedMechParams::rebuildOnLOD;
    segParams["lodCount"] = &SegmentedMechParams::lodCount;

    auto cockpit = mt.new_usertype<CockpitParams>("CockpitParams", sol::constructors<CockpitParams()>());
    cockpit["seatWidth"] = &CockpitParams::seatWidth;
    cockpit["seatDepth"] = &CockpitParams::seatDepth;
    cockpit["seatHeight"] = &CockpitParams::seatHeight;
    cockpit["seatFabricColor"] = vecProperty(&CockpitParams::seatFabricColor);
    cockpit["headrestEnabled"] = &CockpitParams::headrestEnabled;
    cockpit["canopyRadius"] = &CockpitParams::canopyRadius;
    cockpit["canopyHeight"] = &CockpitParams::canopyHeight;
    cockpit["glassThickness"] = &CockpitParams::glassThickness;
    cockpit["glassTint"] = vecProperty(&CockpitParams::glassTint);
    cockpit["reflectivity"] = &CockpitParams::reflectivity;
    cockpit["displayCount"] = &CockpitParams::displayCount;
    cockpit["displayResolution"] = vecProperty(&CockpitParams::displayResolution);
    cockpit["stickOffsetX"] = &CockpitParams::stickOffsetX;
    cockpit["stickOffsetY"] = &CockpitParams::stickOffsetY;
    cockpit["throttleLever"] = &CockpitParams::throttleLever;
    cockpit["pedalControls"] = &CockpitParams::pedalControls;
    cockpit["gaugeCount"] = &CockpitParams::gaugeCount;
    cockpit["gaugeRadius"] = &CockpitParams::gaugeRadius;
    cockpit["gaugeNeedleColor"] = vecProperty(&CockpitParams::gaugeNeedleColor);
    cockpit["holographicHUD"] = &CockpitParams::holographicHUD;
    cockpit["cockpitLight"] = &CockpitParams::cockpitLight;
    cockpit["lightColor"] = vecProperty(&CockpitParams::lightColor);
    cockpit["lightIntensity"] = &CockpitParams::lightIntensity;
    cockpit["canopyAnimEnabled"] = &CockpitParams::canopyAnimEnabled;
    cockpit["canopyOpenAngleDeg"] = &CockpitParams::canopyOpenAngleDeg;
    cockpit["canopyOpenDuration"] = &CockpitParams::canopyOpenDuration;
    cockpit["mountOffset"] = vecProperty(&CockpitParams::mountOffset);

    auto ui = mt.new_usertype<UIParams>("UIParams", sol::constructors<UIParams()>());
    ui["iconSize"] = &UIParams::iconSize;
    ui["borderColor"] = vecProperty(&UIParams::borderColor);
    ui["backgroundShape"] = &UIParams::backgroundShape;
    ui["flashOnSelect"] = &UIParams::flashOnSelect;

    auto centipede = mt.new_usertype<CentipedeMechParams>("CentipedeMechParams", sol::constructors<CentipedeMechParams()>());
    centipede["id"] = &CentipedeMechParams::id;
    centipede["segmentCount"] = &CentipedeMechParams::segmentCount;
    centipede["segmentLength"] = &CentipedeMechParams::segmentLength;
    centipede["segmentRadius"] = &CentipedeMechParams::segmentRadius;
    centipede["baseColor"] = vecProperty(&CentipedeMechParams::baseColor);
    centipede["seamlessJoints"] = &CentipedeMechParams::seamlessJoints;
    centipede["legsPerSegment"] = &CentipedeMechParams::legsPerSegment;
    centipede["upperLegLength"] = &CentipedeMechParams::upperLegLength;
    centipede["lowerLegLength"] = &CentipedeMechParams::lowerLegLength;
    centipede["jointRadius"] = &CentipedeMechParams::jointRadius;
    centipede["armorPlates"] = &CentipedeMechParams::armorPlates;
    centipede["footType"] = &CentipedeMechParams::footType;
    centipede["hasCockpit"] = &CentipedeMechParams::hasCockpit;
    centipede["cockpitPosition"] = vecProperty(&CentipedeMechParams::cockpitPosition);
    centipede["cockpitWidth"] = &CentipedeMechParams::cockpitWidth;
    centipede["cockpitHeight"] = &CentipedeMechParams::cockpitHeight;
    centipede["cockpitDepth"] = &CentipedeMechParams::cockpitDepth;
    centipede["enableDisplays"] = &CentipedeMechParams::enableDisplays;
    centipede["displayCount"] = &CentipedeMechParams::displayCount;
    centipede["seatMaterial"] = &CentipedeMechParams::seatMaterial;
    centipede["controlStyle"] = &CentipedeMechParams::controlStyle;
    centipede["missileTubes"] = &CentipedeMechParams::missileTubes;
    centipede["autocannonSlots"] = &CentipedeMechParams::autocannonSlots;
    centipede["enableTurret"] = &CentipedeMechParams::enableTurret;
    centipede["enableRadarArray"] = &CentipedeMechParams::enableRadarArray;
    centipede["radarRange"] = &CentipedeMechParams::radarRange;

    auto bundle = mt.new_usertype<MechBundle>("MechBundle", sol::no_constructor);
    bundle["mesh"] = sol::readonly(&MechBundle::mesh);
    bundle["tex"] = sol::readonly(&MechBundle::tex);
    bundle["skeleton"] = sol::readonly(&MechBundle::skeleton);
    bundle["animation"] = sol::readonly(&MechBundle::animation);
    bundle["material"] = sol::readonly(&MechBundle::material);
    bundle["normalMap"] = sol::readonly(&MechBundle::normalMap);
    bundle["roughnessMap"] = sol::readonly(&MechBundle::roughnessMap);
    bundle["metallicMap"] = sol::readonly(&MechBundle::metallicMap);
    bundle["emissiveMap"] = sol::readonly(&MechBundle::emissiveMap);
    bundle["mass"] = sol::readonly(&MechBundle::mass);
    bundle["centerOfMass"] = vecProperty(&MechBundle::centerOfMass);
    bundle["animationClips"] = sol::readonly(&MechBundle::animationClips);
    bundle["morphWeights"] = floatMapProperty(&MechBundle::morphWeights);
    bundle["generationTime"] = sol::readonly(&MechBundle::generationTime);
    bundle["memoryUsage"] = sol::readonly(&MechBundle::memoryUsage);
    bundle["gpuAccelerated"] = sol::readonly(&MechBundle::gpuAccelerated);

    auto segBundle = mt.new_usertype<SegmentedMechBundle>("SegmentedMechBundle", sol::no_constructor);
    segBundle["segmentMesh"] = sol::readonly(&SegmentedMechBundle::segmentMesh);
    segBundle["skeleton"] = sol::readonly(&SegmentedMechBundle::skeleton);
    segBundle["proceduralAnimation"] = sol::readonly(&SegmentedMechBundle::proceduralAnimation);
    segBundle["materialShader"] = sol::readonly(&SegmentedMechBundle::materialShader);
    segBundle["sparkParticles"] = sol::readonly(&SegmentedMechBundle::sparkParticles);
    segBundle["physicsAsset"] = sol::readonly(&SegmentedMechBundle::physicsAsset);
    segBundle["cockpitMesh"] = sol::readonly(&SegmentedMechBundle::cockpitMesh);
    segBundle["cockpitTexture"] = sol::readonly(&SegmentedMechBundle::cockpitTexture);
    segBundle["cockpitMaterial"] = sol::readonly(&SegmentedMechBundle::cockpitMaterial);
    segBundle["icon"] = sol::readonly(&SegmentedMechBundle::icon);
    segBundle["generationTime"] = sol::readonly(&SegmentedMechBundle::generationTime);
    segBundle["memoryUsage"] = sol::readonly(&SegmentedMechBundle::memoryUsage);
    segBundle["gpuAccelerated"] = sol::readonly(&SegmentedMechBundle::gpuAccelerated);

    auto centBundle = mt.new_usertype<CentipedeMechBundle>("CentipedeMechBundle", sol::no_constructor);
    centBundle["segments"] = sol::readonly(&CentipedeMechBundle::segments);
    centBundle["joints"] = sol::readonly(&CentipedeMechBundle::joints);
    centBundle["legs"] = sol::readonly(&CentipedeMechBundle::legs);
    centBundle["cockpit"] = sol::readonly(&CentipedeMechBundle::cockpit);
    centBundle["weapons"] = sol::readonly(&CentipedeMechBundle::weapons);
    centBundle["sensorArray"] = sol::readonly(&CentipedeMechBundle::sensorArray);
    centBundle["materials"] = sol::readonly(&CentipedeMechBundle::materials);
    centBundle["vfx"] = sol::readonly(&CentipedeMechBundle::vfx);
    centBundle["audio"] = sol::readonly(&CentipedeMechBundle::audio);
    centBundle["collider"] = sol::readonly(&CentipedeMechBundle::collider);
    centBundle["generationTime"] = sol::readonly(&CentipedeMechBundle::generationTime);
    centBundle["memoryUsage"] = sol::readonly(&CentipedeMechBundle::memoryUsage);

    auto inst = mt.new_usertype<MechInstanceState>("MechInstance", sol::no_constructor);
    inst["id"] = sol::readonly(&MechInstanceState::id);
    inst["params"] = &MechInstanceState::params;
    inst["bundle"] = &MechInstanceState::bundle;
    inst["currentForm"] = sol::readonly(&MechInstanceState::currentForm);
    inst["targetForm"] = sol::readonly(&MechInstanceState::targetForm);
    inst["morphProgress"] = sol::readonly(&MechInstanceState::morphProgress);
    inst["isMorphing"] = sol::readonly(&MechInstanceState::isMorphing);
    inst["morphPaused"] = sol::readonly(&MechInstanceState::morphPaused);
    inst["isActive"] = &MechInstanceState::isActive;
    inst["position"] = vecProperty(&MechInstanceState::position);
    inst["scale"] = vecProperty(&MechInstanceState::scale);
    inst["velocity"] = vecProperty(&MechInstanceState::velocity);
    inst["angularVelocity"] = vecProperty(&MechInstanceState::angularVelocity);
    inst["acceleration"] = vecProperty(&MechInstanceState::acceleration);
    inst["animationTime"] = &MechInstanceState::animationTime;
    inst["currentAnimation"] = sol::readonly(&MechInstanceState::currentAnimation);
    inst["animationLooping"] = &MechInstanceState::animationLooping;
    inst["frameCount"] = sol::readonly(&MechInstanceState::frameCount);

    auto segInst = mt.new_usertype<SegmentedMechInstanceState>("SegmentedMechInstance", sol::no_constructor);
    segInst["id"] = sol::readonly(&SegmentedMechInstanceState::id);
    segInst["params"] = &SegmentedMechInstanceState::params;
    segInst["bundle"] = &SegmentedMechInstanceState::bundle;
    segInst["cockpitParams"] = sol::readonly(&SegmentedMechInstanceState::cockpitParams);
    segInst["cockpitAttached"] = sol::readonly(&SegmentedMechInstanceState::cockpitAttached);
    segInst["segments"] = sol::readonly(&SegmentedMechInstanceState::segments);
    segInst["currentSegmentCount"] = sol::readonly(&SegmentedMechInstanceState::currentSegmentCount);
    segInst["isActive"] = &SegmentedMechInstanceState::isActive;
    segInst["position"] = vecProperty(&SegmentedMechInstanceState::position);
    segInst["scale"] = vecProperty(&SegmentedMechInstanceState::scale);
    segInst["velocity"] = vecProperty(&SegmentedMechInstanceState::velocity);
    segInst["angularVelocity"] = vecProperty(&SegmentedMechInstanceState::angularVelocity);
    segInst["acceleration"] = vecProperty(&SegmentedMechInstanceState::acceleration);
    segInst["animationTime"] = &SegmentedMechInstanceState::animationTime;
    segInst["currentAnimation"] = sol::readonly(&SegmentedMechInstanceState::currentAnimation);
    segInst["animationPaused"] = sol::readonly(&SegmentedMechInstanceState::animationPaused);
    segInst["frameCount"] = sol::readonly(&SegmentedMechInstanceState::frameCount);

    auto centInst = mt.new_usertype<CentipedeMechInstanceState>("CentipedeMechInstance", sol::no_constructor);
    centInst["id"] = sol::readonly(&CentipedeMechInstanceState::id);
    centInst["params"] = &CentipedeMechInstanceState::params;
    centInst["bundle"] = &CentipedeMechInstanceState::bundle;
    centInst["segmentLegCounts"] = sol::readonly(&CentipedeMechInstanceState::segmentLegCounts);
    centInst["isActive"] = &CentipedeMechInstanceState::isActive;
    centInst["position"] = vecProperty(&CentipedeMechInstanceState::position);
    centInst["scale"] = vecProperty(&CentipedeMechInstanceState::scale);
    centInst["velocity"] = vecProperty(&CentipedeMechInstanceState::velocity);
    centInst["angularVelocity"] = vecProperty(&CentipedeMechInstanceState::angularVelocity);
    centInst["acceleration"] = vecProperty(&CentipedeMechInstanceState::acceleration);
    centInst["animationTime"] = &CentipedeMechInstanceState::animationTime;
    centInst["currentAnimation"] = sol::readonly(&CentipedeMechInstanceState::currentAnimation);
    centInst["animationPaused"] = sol::readonly(&CentipedeMechInstanceState::animationPaused);
    centInst["frameCount"] = sol::readonly(&CentipedeMechInstanceState::frameCount);

    mt.new_usertype<MechBundleFuture>("MechBundleFuture", sol::no_constructor,
        "get", &MechBundleFuture::get, "ready", &MechBundleFuture::ready);
    mt.new_usertype<SegmentedBundleFuture>("SegmentedMechBundleFuture", sol::no_constructor,
        "get", &SegmentedBundleFuture::get, "ready", &SegmentedBundleFuture::ready);
    mt.new_usertype<CentipedeBundleFuture>("CentipedeMechBundleFuture", sol::no_constructor,
        "get", &CentipedeBundleFuture::get, "ready", &CentipedeBundleFuture::ready);

    // ------------------------------------------------- global spawn helper --
    lua.set_function("spawn_mech", [](const sol::object& p) { queueSpawn(toMechParams(p)); });

    // ----------------------------------------------------- core generation --
    mt.set_function("generateAsync", [](const sol::object& p) {
        return MechBundleFuture{factory()->generateAsync(toMechParams(p)).share()};
    });
    mt.set_function("generateSync", [](const sol::object& p) { return factory()->generateSync(toMechParams(p)); });
    mt.set_function("createInstance", [](const sol::object& p) { return factory()->createInstance(toMechParams(p)); });
    mt.set_function("destroyInstance", [](const MechInstanceState& s) { return factory()->destroyInstance(s); });
    mt.set_function("updateInstance", [](MechInstanceState& s, float dt) { return factory()->updateInstance(s, dt); });

    mt.set_function("startMorph", [](MechInstanceState& s, const std::string& form) { return factory()->startMorph(s, form); });
    mt.set_function("setMorphProgress", [](MechInstanceState& s, float progress) { return factory()->setMorphProgress(s, progress); });
    mt.set_function("pauseMorph", [](MechInstanceState& s) { return factory()->pauseMorph(s); });
    mt.set_function("resumeMorph", [](MechInstanceState& s) { return factory()->resumeMorph(s); });

    mt.set_function("generateBatch", [](const sol::table& list, sol::this_state ts) {
        sol::state_view state(ts);
        sol::table out = state.create_table();
        for (size_t i = 1; i <= list.size(); ++i) {
            sol::object item = list[i];
            out[i] = MechBundleFuture{factory()->generateAsync(toMechParams(item)).share()};
        }
        return out;
    });
    mt.set_function("generateBatchSync", [](const sol::table& list, sol::this_state ts) {
        std::vector<MechParams> params;
        for (size_t i = 1; i <= list.size(); ++i) {
            sol::object item = list[i];
            params.push_back(toMechParams(item));
        }
        std::vector<MechBundle> bundles;
        factory()->generateBatchSync(params, bundles);
        sol::state_view state(ts);
        sol::table out = state.create_table(static_cast<int>(bundles.size()), 0);
        for (size_t i = 0; i < bundles.size(); ++i) out[i + 1] = bundles[i];
        return out;
    });

    mt.set_function("clearCache", [] { factory()->clearCache(); });
    mt.set_function("getCacheSize", [] { return factory()->getCacheSize(); });
    mt.set_function("isCached", [](const sol::object& p) { return factory()->isCached(toMechParams(p)); });
    mt.set_function("setCacheSize", [](size_t size) { factory()->setCacheSize(size); });

    mt.set_function("getPerformanceMetrics", [](sol::this_state ts) {
        return performanceMetricsToTable(sol::state_view(ts), factory()->getPerformanceMetrics());
    });
    mt.set_function("resetPerformanceMetrics", [] { factory()->resetPerformanceMetrics(); });
    mt.set_function("setGPUAcceleration", [](bool enabled) { factory()->setGPUAcceleration(enabled); });
    mt.set_function("isGPUAccelerationEnabled", [] { return factory()->isGPUAccelerationEnabled(); });

    mt.set_function("setDefinitionDirectory", [](const std::string& dir) { factory()->setDefinitionDirectory(dir); });
    mt.set_function("watchDefinition", [](const std::string& id) { factory()->watchDefinition(id); });
    mt.set_function("unwatchDefinition", [](const std::string& id) { factory()->unwatchDefinition(id); });
    mt.set_function("processHotReloads", [] { factory()->processHotReloads(); });

    mt.set_function("setProceduralParams", [](const sol::object& p) { factory()->setProceduralParams(toProceduralParams(p)); });
    mt.set_function("getProceduralParams", [](sol::this_state ts) {
        return proceduralParamsToTable(sol::state_view(ts), factory()->getProceduralParams());
    });

    mt.set_function("createFromTemplate", [](const std::string& name) { return factory()->createFromTemplate(name); });
    mt.set_function("registerTemplate", [](const std::string& name, const sol::object& p) {
        factory()->registerTemplate(name, toMechParams(p));
    });
    mt.set_function("getAvailableTemplates", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getAvailableTemplates());
    });
    mt.set_function("validateParams", [](const sol::object& p) { return factory()->validateParams(toMechParams(p)); });
    mt.set_function("getValidationErrors", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getValidationErrors());
    });

    mt.set_function("spawnMech", [](const sol::object& p) { queueSpawn(toMechParams(p)); });
    mt.set_function("createMechParams", [] { return MechParams{}; });
    mt.set_function("getMechInfo", [](const MechInstanceState& s) { return describeMech(s); });
    mt.set_function("setMechProperty", [](MechInstanceState& s, const std::string& name, float value) {
        return setMechProperty(s, name, value);
    });
    mt.set_function("getMechProperty", [](const MechInstanceState& s, const std::string& name) -> std::optional<float> {
        float value = 0.0f;
        if (getMechProperty(s, name, value)) return value;
        return std::nullopt;
    });

    // ------------------------------------------------------ segmented mechs --
    mt.set_function("generateSegmentedAsync", [](const sol::object& p, const sol::object& c, const sol::object& u) {
        return SegmentedBundleFuture{
            factory()->generateSegmentedAsync(toSegmentedMechParams(p), toCockpitParams(c), toUIParams(u)).share()};
    });
    mt.set_function("generateSegmentedSync", [](const sol::object& p, const sol::object& c, const sol::object& u) {
        return factory()->generateSegmentedSync(toSegmentedMechParams(p), toCockpitParams(c), toUIParams(u));
    });
    mt.set_function("createSegmentedInstance", [](const sol::object& p, const sol::object& c) {
        return factory()->createSegmentedInstance(toSegmentedMechParams(p), toCockpitParams(c));
    });
    mt.set_function("destroySegmentedInstance", [](const SegmentedMechInstanceState& s) {
        return factory()->destroySegmentedInstance(s);
    });
    mt.set_function("updateSegmentedInstance", [](SegmentedMechInstanceState& s, float dt) {
        return factory()->updateSegmentedInstance(s, dt);
    });
    mt.set_function("addSegment", [](SegmentedMechInstanceState& s, int index) { return factory()->addSegment(s, index); });
    mt.set_function("removeSegment", [](SegmentedMechInstanceState& s, int index) { return factory()->removeSegment(s, index); });
    mt.set_function("setSegmentCount", [](SegmentedMechInstanceState& s, int count) { return factory()->setSegmentCount(s, count); });
    mt.set_function("updateSegmentProperties", [](SegmentedMechInstanceState& s, int index, const sol::table& props) {
        return factory()->updateSegmentProperties(s, index, toFloatMap(props));
    });
    mt.set_function("startSegmentedAnimation", [](SegmentedMechInstanceState& s, const std::string& name) {
        return factory()->startSegmentedAnimation(s, name);
    });
    mt.set_function("setSegmentedAnimationProgress", [](SegmentedMechInstanceState& s, float progress) {
        return factory()->setSegmentedAnimationProgress(s, progress);
    });
    mt.set_function("pauseSegmentedAnimation", [](SegmentedMechInstanceState& s) { return factory()->pauseSegmentedAnimation(s); });
    mt.set_function("resumeSegmentedAnimation", [](SegmentedMechInstanceState& s) { return factory()->resumeSegmentedAnimation(s); });
    mt.set_function("attachCockpit", [](SegmentedMechInstanceState& s, const sol::object& c) {
        return factory()->attachCockpit(s, toCockpitParams(c));
    });
    mt.set_function("detachCockpit", [](SegmentedMechInstanceState& s) { return factory()->detachCockpit(s); });
    mt.set_function("updateCockpitParams", [](SegmentedMechInstanceState& s, const sol::object& c) {
        return factory()->updateCockpitParams(s, toCockpitParams(c));
    });
    mt.set_function("generateSegmentedBatch", [](const sol::table& list, sol::this_state ts) {
        // Each entry is {params, cockpit} or {params = ..., cockpit = ...}
        std::vector<std::pair<SegmentedMechParams, CockpitParams>> configs;
        for (size_t i = 1; i <= list.size(); ++i) {
            sol::object entry = list[i];
            if (entry.get_type() != sol::type::table) throw std::invalid_argument("generateSegmentedBatch expects a list of tables");
            const sol::table e = entry.as<sol::table>();
            sol::object mech = e[1];
            sol::object cockpitConfig = e[2];
            if (mech.get_type() == sol::type::lua_nil) mech = e["params"];
            if (cockpitConfig.get_type() == sol::type::lua_nil) cockpitConfig = e["cockpit"];
            configs.emplace_back(toSegmentedMechParams(mech), toCockpitParams(cockpitConfig));
        }
        auto futures = factory()->generateSegmentedBatch(configs);
        sol::state_view state(ts);
        sol::table out = state.create_table(static_cast<int>(futures.size()), 0);
        for (size_t i = 0; i < futures.size(); ++i) out[i + 1] = SegmentedBundleFuture{futures[i].share()};
        return out;
    });
    mt.set_function("clearSegmentedCache", [] { factory()->clearSegmentedCache(); });
    mt.set_function("getSegmentedCacheSize", [] { return factory()->getSegmentedCacheSize(); });
    mt.set_function("isSegmentedCached", [](const sol::object& p) { return factory()->isSegmentedCached(toSegmentedMechParams(p)); });
    mt.set_function("validateSegmentedParams", [](const sol::object& p) {
        return factory()->validateSegmentedParams(toSegmentedMechParams(p));
    });
    mt.set_function("validateCockpitParams", [](const sol::object& c) { return factory()->validateCockpitParams(toCockpitParams(c)); });
    mt.set_function("getSegmentedValidationErrors", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getSegmentedValidationErrors());
    });
    mt.set_function("createSegmentedFromTemplate", [](const std::string& name) { return factory()->createSegmentedFromTemplate(name); });
    mt.set_function("registerSegmentedTemplate", [](const std::string& name, const sol::object& p) {
        factory()->registerSegmentedTemplate(name, toSegmentedMechParams(p));
    });
    mt.set_function("getAvailableSegmentedTemplates", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getAvailableSegmentedTemplates());
    });
    mt.set_function("createCockpitFromTemplate", [](const std::string& name) { return factory()->createCockpitFromTemplate(name); });
    mt.set_function("registerCockpitTemplate", [](const std::string& name, const sol::object& c) {
        factory()->registerCockpitTemplate(name, toCockpitParams(c));
    });
    mt.set_function("getAvailableCockpitTemplates", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getAvailableCockpitTemplates());
    });
    mt.set_function("spawnSegmentedMech", [](const sol::object& p, const sol::object& c) {
        return factory()->createSegmentedInstance(toSegmentedMechParams(p), toCockpitParams(c));
    });
    mt.set_function("createSegmentedMechParams", [] { return SegmentedMechParams{}; });
    mt.set_function("createCockpitParams", [] { return CockpitParams{}; });
    mt.set_function("createUIParams", [] { return UIParams{}; });
    mt.set_function("getSegmentedMechInfo", [](const SegmentedMechInstanceState& s) { return describeSegmentedMech(s); });
    mt.set_function("setSegmentedMechProperty", [](SegmentedMechInstanceState& s, const std::string& name, float value) {
        return setSegmentedMechProperty(s, name, value);
    });
    mt.set_function("getSegmentedMechProperty", [](const SegmentedMechInstanceState& s, const std::string& name) -> std::optional<float> {
        float value = 0.0f;
        if (getSegmentedMechProperty(s, name, value)) return value;
        return std::nullopt;
    });

    // ------------------------------------------------------ centipede mechs --
    mt.set_function("generateCentipedeAsync", [](const sol::object& p) {
        return CentipedeBundleFuture{factory()->generateCentipedeAsync(toCentipedeMechParams(p)).share()};
    });
    mt.set_function("generateCentipedeSync", [](const sol::object& p) {
        return factory()->generateCentipedeSync(toCentipedeMechParams(p));
    });
    mt.set_function("createCentipedeInstance", [](const sol::object& p) {
        return factory()->createCentipedeInstance(toCentipedeMechParams(p));
    });
    mt.set_function("destroyCentipedeInstance", [](const CentipedeMechInstanceState& s) {
        return factory()->destroyCentipedeInstance(s);
    });
    mt.set_function("updateCentipedeInstance", [](CentipedeMechInstanceState& s, float dt) {
        return factory()->updateCentipedeInstance(s, dt);
    });
    mt.set_function("addCentipedeSegment", [](CentipedeMechInstanceState& s, int index) {
        return factory()->addCentipedeSegment(s, index);
    });
    mt.set_function("removeCentipedeSegment", [](CentipedeMechInstanceState& s, int index) {
        return factory()->removeCentipedeSegment(s, index);
    });
    mt.set_function("setCentipedeSegmentCount", [](CentipedeMechInstanceState& s, int count) {
        return factory()->setCentipedeSegmentCount(s, count);
    });
    mt.set_function("updateCentipedeSegmentProperties", [](CentipedeMechInstanceState& s, int index, const sol::table& props) {
        return factory()->updateCentipedeSegmentProperties(s, index, toFloatMap(props));
    });
    mt.set_function("addCentipedeLeg", [](CentipedeMechInstanceState& s, int segment, int leg) {
        return factory()->addCentipedeLeg(s, segment, leg);
    });
    mt.set_function("removeCentipedeLeg", [](CentipedeMechInstanceState& s, int segment, int leg) {
        return factory()->removeCentipedeLeg(s, segment, leg);
    });
    mt.set_function("updateCentipedeLegProperties", [](CentipedeMechInstanceState& s, int segment, int leg, const sol::table& props) {
        return factory()->updateCentipedeLegProperties(s, segment, leg, toFloatMap(props));
    });
    mt.set_function("startCentipedeAnimation", [](CentipedeMechInstanceState& s, const std::string& name) {
        return factory()->startCentipedeAnimation(s, name);
    });
    mt.set_function("setCentipedeAnimationProgress", [](CentipedeMechInstanceState& s, float progress) {
        return factory()->setCentipedeAnimationProgress(s, progress);
    });
    mt.set_function("pauseCentipedeAnimation", [](CentipedeMechInstanceState& s) { return factory()->pauseCentipedeAnimation(s); });
    mt.set_function("resumeCentipedeAnimation", [](CentipedeMechInstanceState& s) { return factory()->resumeCentipedeAnimation(s); });
    mt.set_function("attachCentipedeCockpit", [](CentipedeMechInstanceState& s, const sol::object& c) {
        return factory()->attachCentipedeCockpit(s, toCockpitParams(c));
    });
    mt.set_function("detachCentipedeCockpit", [](CentipedeMechInstanceState& s) { return factory()->detachCentipedeCockpit(s); });
    mt.set_function("updateCentipedeCockpitParams", [](CentipedeMechInstanceState& s, const sol::object& c) {
        return factory()->updateCentipedeCockpitParams(s, toCockpitParams(c));
    });
    mt.set_function("addCentipedeWeapon", [](CentipedeMechInstanceState& s, const std::string& type, int hardpoint) {
        return factory()->addCentipedeWeapon(s, type, hardpoint);
    });
    mt.set_function("removeCentipedeWeapon", [](CentipedeMechInstanceState& s, int hardpoint) {
        return factory()->removeCentipedeWeapon(s, hardpoint);
    });
    mt.set_function("updateCentipedeSensorArray", [](CentipedeMechInstanceState& s, const std::string& type) {
        return factory()->updateCentipedeSensorArray(s, type);
    });
    mt.set_function("generateCentipedeBatch", [](const sol::table& list, sol::this_state ts) {
        std::vector<CentipedeMechParams> params;
        for (size_t i = 1; i <= list.size(); ++i) {
            sol::object item = list[i];
            params.push_back(toCentipedeMechParams(item));
        }
        auto futures = factory()->generateCentipedeBatch(params);
        sol::state_view state(ts);
        sol::table out = state.create_table(static_cast<int>(futures.size()), 0);
        for (size_t i = 0; i < futures.size(); ++i) out[i + 1] = CentipedeBundleFuture{futures[i].share()};
        return out;
    });
    mt.set_function("clearCentipedeCache", [] { factory()->clearCentipedeCache(); });
    mt.set_function("getCentipedeCacheSize", [] { return factory()->getCentipedeCacheSize(); });
    mt.set_function("isCentipedeCached", [](const sol::object& p) { return factory()->isCentipedeCached(toCentipedeMechParams(p)); });
    mt.set_function("validateCentipedeParams", [](const sol::object& p) {
        return factory()->validateCentipedeParams(toCentipedeMechParams(p));
    });
    mt.set_function("getCentipedeValidationErrors", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getCentipedeValidationErrors());
    });
    mt.set_function("createCentipedeFromTemplate", [](const std::string& name) { return factory()->createCentipedeFromTemplate(name); });
    mt.set_function("registerCentipedeTemplate", [](const std::string& name, const sol::object& p) {
        factory()->registerCentipedeTemplate(name, toCentipedeMechParams(p));
    });
    mt.set_function("getAvailableCentipedeTemplates", [](sol::this_state ts) {
        return stringListToTable(sol::state_view(ts), factory()->getAvailableCentipedeTemplates());
    });
    mt.set_function("spawnCentipedeMech", [](const sol::object& p) { return factory()->spawnCentipedeMech(toCentipedeMechParams(p)); });
    mt.set_function("createCentipedeMechParams", [] { return factory()->createCentipedeMechParams(); });
    mt.set_function("getCentipedeMechInfo", [](const CentipedeMechInstanceState& s) { return factory()->getCentipedeMechInfo(s); });
    mt.set_function("setCentipedeMechProperty", [](CentipedeMechInstanceState& s, const std::string& name, float value) {
        return factory()->setCentipedeMechProperty(s, name, value);
    });
    mt.set_function("getCentipedeMechProperty", [](const CentipedeMechInstanceState& s, const std::string& name) -> std::optional<float> {
        const float value = factory()->getCentipedeMechProperty(s, name);
        if (std::isnan(value)) return std::nullopt;
        return value;
    });
}

void MechLuaBindings::poll_assets(sol::state_view lua) {
    std::vector<PendingMech> finished;
    {
        std::lock_guard<std::mutex> lock(pendingMutex());
        auto& pending = pendingMechs();
        for (auto it = pending.begin(); it != pending.end();) {
            if (it->future.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                finished.push_back(std::move(*it));
                it = pending.erase(it);
            } else {
                ++it;
            }
        }
    }
    for (auto& mech : finished) {
        try {
            const MechBundle bundle = mech.future.get();
            Log::info("Mech", "Mech ready: {} (mesh {}, texture {}, skeleton {})", mech.id, bundle.mesh, bundle.tex,
                      bundle.skeleton);
            sol::protected_function onReady = lua["on_mech_ready"];
            if (onReady.valid()) {
                auto result = onReady(mech.id, bundle);
                if (!result.valid()) {
                    sol::error err = result;
                    Log::error("Mech", "on_mech_ready failed for {}: {}", mech.id, err.what());
                }
            } else {
                lua["print"]("Mech ready: " + mech.id);
            }
        } catch (const std::exception& e) {
            Log::error("Mech", "Mech asset {} failed: {}", mech.id, e.what());
        }
    }
}

} // namespace Mechs
} // namespace MagiTech
