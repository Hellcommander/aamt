#include "MechFactory.hpp"
#include "MechGenerators.hpp"
#include "MechFamilyAssetStore.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iterator>
#include <limits>
#include <numbers>
#include <sstream>
#include <stdexcept>

namespace MagiTech {
namespace Mechs {

namespace {

using SteadyClock = std::chrono::steady_clock;
constexpr float kPi = std::numbers::pi_v<float>;
constexpr int kMaxSegments = 256;
constexpr int kMaxCentipedeSegments = 64;
constexpr int kMaxLegsPerSegment = 8;
constexpr int kMaxHardpoints = 16;

uint64_t elapsedMs(SteadyClock::time_point start) {
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(SteadyClock::now() - start).count());
}

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

std::string joinErrors(const std::vector<std::string>& errors) {
    std::string out;
    for (const auto& e : errors) {
        if (!out.empty()) out += "; ";
        out += e;
    }
    return out;
}

template <typename T>
std::future<T> readyFuture(T value) {
    std::promise<T> promise;
    promise.set_value(std::move(value));
    return promise.get_future();
}

template <typename Map>
std::vector<std::string> sortedKeys(const Map& map) {
    std::vector<std::string> keys;
    keys.reserve(map.size());
    for (const auto& [name, value] : map) keys.push_back(name);
    std::sort(keys.begin(), keys.end());
    return keys;
}

// Writes the caller's copy of an instance back into the factory's registry.
template <typename State>
void syncInstance(std::unordered_map<std::string, State>& map, std::mutex& mutex, const State& instance) {
    std::lock_guard<std::mutex> lock(mutex);
    auto it = map.find(instance.id);
    if (it != map.end()) it->second = instance;
}

uint64_t assetMemory(uint32_t handle) {
    if (handle == 0) return 0;
    auto& store = MechFamilyAssetStore::instance();
    if (auto mesh = store.get<mt::Mesh>(handle)) return mesh->getMemoryUsage();
    if (auto tex = store.get<MechTextureData>(handle)) return tex->rgba.size();
    if (auto rig = store.get<MechSkeletonData>(handle)) return rig->bones.size() * sizeof(MechBone);
    if (auto anim = store.get<MechAnimationData>(handle)) {
        uint64_t bytes = 0;
        for (const auto& key : anim->keys) {
            bytes += key.boneRotations.size() * sizeof(glm::quat) + key.boneOffsets.size() * sizeof(glm::vec3);
        }
        return bytes;
    }
    if (auto physics = store.get<MechPhysicsData>(handle)) return physics->shapes.size() * sizeof(MechColliderShape);
    if (auto fx = store.get<MechParticleData>(handle)) return sizeof(MechParticleData) + fx->emitterPositions.size() * sizeof(glm::vec3);
    if (store.get<MechMaterialData>(handle)) return sizeof(MechMaterialData);
    if (store.get<MechAudioData>(handle)) return sizeof(MechAudioData);
    return 0;
}

uint64_t assetMemory(const std::vector<uint32_t>& handles) {
    uint64_t total = 0;
    for (uint32_t h : handles) total += assetMemory(h);
    return total;
}

float animationDuration(AnimationHandle handle, float fallback) {
    if (auto anim = MechFamilyAssetStore::instance().get<MechAnimationData>(handle)) return std::max(0.001f, anim->duration);
    return std::max(0.001f, fallback);
}

// ------------------------------------------------- instance-owned assets ----

bool isOwned(const std::vector<uint32_t>& owned, uint32_t handle) {
    return handle != 0 && std::find(owned.begin(), owned.end(), handle) != owned.end();
}

void releaseIfOwned(std::vector<uint32_t>& owned, uint32_t handle) {
    if (!isOwned(owned, handle)) return;   // shared (cached) bundle assets are never released here
    owned.erase(std::find(owned.begin(), owned.end(), handle));
    MechFamilyAssetStore::instance().release(handle);
}

void replaceOwned(std::vector<uint32_t>& owned, uint32_t& slot, uint32_t fresh) {
    releaseIfOwned(owned, slot);
    slot = fresh;
    if (fresh != 0) owned.push_back(fresh);
}

void replaceOwnedList(std::vector<uint32_t>& owned, std::vector<uint32_t>& slots, std::vector<uint32_t> fresh) {
    for (uint32_t old : slots) releaseIfOwned(owned, old);
    slots = std::move(fresh);
    for (uint32_t h : slots) {
        if (h != 0) owned.push_back(h);
    }
}

void releaseAllOwned(std::vector<uint32_t>& owned) {
    for (uint32_t h : owned) MechFamilyAssetStore::instance().release(h);
    owned.clear();
}

// ---------------------------------------------------------------- morphs ----

float easeCurve(const std::string& curve, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    const std::string c = lower(curve);
    if (c == "linear") return t;
    if (c == "easein") return t * t;
    if (c == "easeout") return 1.0f - (1.0f - t) * (1.0f - t);
    return t * t * (3.0f - 2.0f * t);
}

void applyMorphWeights(MechInstanceState& s) {
    const float w = easeCurve(s.params.morphCurve, s.morphProgress);
    for (auto& [form, weight] : s.bundle.morphWeights) {
        if (form == s.targetForm && form == s.currentForm) weight = 1.0f;
        else if (form == s.targetForm) weight = w;
        else if (form == s.currentForm) weight = 1.0f - w;
        else weight = 0.0f;
    }
}

void finishMorph(MechInstanceState& s) {
    s.currentForm = s.targetForm;
    s.morphProgress = 0.0f;
    s.isMorphing = false;
    s.morphPaused = false;
    s.currentAnimation = "idle";
    s.animationTime = 0.0f;
    applyMorphWeights(s);
}

void integrateRotation(glm::quat& rotation, const glm::vec3& angularVelocity, float dt) {
    if (glm::dot(angularVelocity, angularVelocity) <= 0.0f) return;
    const glm::quat spin(0.0f, angularVelocity.x, angularVelocity.y, angularVelocity.z);
    rotation = glm::normalize(rotation + (spin * rotation) * (0.5f * dt));
}

void updateFrameStats(uint64_t& frameCount, float& averageFrameTime, float dt) {
    ++frameCount;
    averageFrameTime += (dt - averageFrameTime) / static_cast<float>(std::min<uint64_t>(frameCount, 120));
}

// -------------------------------------------------------- segmented helpers -

bool applySegmentProperty(SegmentedMechParams& p, const std::string& key, float value) {
    if (key == "segmentRadius") p.segmentRadius = value;
    else if (key == "segmentLength") p.segmentLength = value;
    else if (key == "connectorGap") p.connectorGap = value;
    else if (key == "maxBendAngleDeg") p.maxBendAngleDeg = value;
    else if (key == "bendStiffness") p.bendStiffness = value;
    else if (key == "jointFlexibility") p.jointFlexibility = value;
    else if (key == "plateThickness") p.plateThickness = value;
    else if (key == "platesPerSegment") p.platesPerSegment = static_cast<int>(value);
    else if (key == "stripeCount") p.stripeCount = static_cast<int>(value);
    else if (key == "stripeWidth") p.stripeWidth = value;
    else if (key == "stripeGlowIntensity") p.stripeGlowIntensity = value;
    else if (key == "segmentMass") p.segmentMass = value;
    else if (key == "jointDamping") p.jointDamping = value;
    else if (key == "noiseDetail") p.noiseDetail = value;
    else return false;
    return true;
}

SegmentedMechParams paramsForSegment(const SegmentedMechInstanceState& s, int index) {
    SegmentedMechParams p = s.params;
    if (index >= 0 && index < static_cast<int>(s.segmentOverrides.size())) {
        for (const auto& [key, value] : s.segmentOverrides[index]) applySegmentProperty(p, key, value);
    }
    return p;
}

std::vector<std::string> collectSegmentedErrors(const SegmentedMechParams& p) {
    std::vector<std::string> e;
    if (p.id.empty()) e.emplace_back("id must not be empty");
    if (p.segmentCount < 1 || p.segmentCount > kMaxSegments) e.emplace_back("segmentCount must be in [1, 256]");
    if (p.segmentLength <= 0.0f) e.emplace_back("segmentLength must be positive");
    if (p.segmentRadius <= 0.0f) e.emplace_back("segmentRadius must be positive");
    if (p.connectorGap < 0.0f) e.emplace_back("connectorGap must not be negative");
    if (p.maxBendAngleDeg <= 0.0f || p.maxBendAngleDeg > 180.0f) e.emplace_back("maxBendAngleDeg must be in (0, 180]");
    if (p.bendStiffness < 0.0f) e.emplace_back("bendStiffness must not be negative");
    if (p.jointFlexibility < 0.0f || p.jointFlexibility > 1.0f) e.emplace_back("jointFlexibility must be in [0, 1]");
    if (p.platesPerSegment < 0) e.emplace_back("platesPerSegment must not be negative");
    if (p.plateThickness < 0.0f) e.emplace_back("plateThickness must not be negative");
    if (p.stripeCount < 0) e.emplace_back("stripeCount must not be negative");
    if (p.stripeWidth < 0.0f) e.emplace_back("stripeWidth must not be negative");
    if (p.enableJointSparks && (p.sparkRate < 0.0f || p.sparkLifetime <= 0.0f)) {
        e.emplace_back("sparkRate must not be negative and sparkLifetime must be positive");
    }
    if (p.segmentMass <= 0.0f) e.emplace_back("segmentMass must be positive");
    if (p.jointDamping < 0.0f) e.emplace_back("jointDamping must not be negative");
    if (p.waveFrequency <= 0.0f) e.emplace_back("waveFrequency must be positive");
    if (lower(p.cockpitType) != "none") {
        if (p.cockpitSegmentIndex < 0 || p.cockpitSegmentIndex >= p.segmentCount) {
            e.emplace_back("cockpitSegmentIndex must reference an existing segment");
        }
        if (p.cockpitRadius <= 0.0f) e.emplace_back("cockpitRadius must be positive");
    }
    if (p.lodCount < 1) e.emplace_back("lodCount must be at least 1");
    return e;
}

std::vector<std::string> collectCockpitErrors(const CockpitParams& c) {
    std::vector<std::string> e;
    if (c.seatWidth <= 0.0f || c.seatDepth <= 0.0f || c.seatHeight <= 0.0f) e.emplace_back("seat dimensions must be positive");
    if (c.canopyRadius <= 0.0f || c.canopyHeight <= 0.0f) e.emplace_back("canopy dimensions must be positive");
    if (c.glassThickness < 0.0f) e.emplace_back("glassThickness must not be negative");
    if (c.reflectivity < 0.0f || c.reflectivity > 1.0f) e.emplace_back("reflectivity must be in [0, 1]");
    if (c.displayCount < 0 || c.gaugeCount < 0) e.emplace_back("displayCount and gaugeCount must not be negative");
    if (c.gaugeRadius <= 0.0f) e.emplace_back("gaugeRadius must be positive");
    if (c.lightIntensity < 0.0f) e.emplace_back("lightIntensity must not be negative");
    if (c.canopyAnimEnabled) {
        if (c.canopyOpenAngleDeg < 0.0f || c.canopyOpenAngleDeg > 180.0f) e.emplace_back("canopyOpenAngleDeg must be in [0, 180]");
        if (c.canopyOpenDuration <= 0.0f) e.emplace_back("canopyOpenDuration must be positive");
    }
    return e;
}

std::vector<std::string> collectCentipedeErrors(const CentipedeMechParams& p) {
    std::vector<std::string> e;
    if (p.id.empty()) e.emplace_back("id must not be empty");
    if (p.segmentCount < 1 || p.segmentCount > kMaxCentipedeSegments) e.emplace_back("segmentCount must be in [1, 64]");
    if (p.segmentLength <= 0.0f || p.segmentRadius <= 0.0f) e.emplace_back("segment dimensions must be positive");
    if (p.legsPerSegment < 0 || p.legsPerSegment > kMaxLegsPerSegment) e.emplace_back("legsPerSegment must be in [0, 8]");
    if (p.upperLegLength <= 0.0f || p.lowerLegLength <= 0.0f) e.emplace_back("leg lengths must be positive");
    if (p.jointRadius <= 0.0f) e.emplace_back("jointRadius must be positive");
    const std::string foot = lower(p.footType);
    if (foot != "claw" && foot != "pad" && foot != "spike") e.emplace_back("footType must be Claw, Pad or Spike");
    if (p.hasCockpit && (p.cockpitWidth <= 0.0f || p.cockpitHeight <= 0.0f || p.cockpitDepth <= 0.0f)) {
        e.emplace_back("cockpit dimensions must be positive");
    }
    if (p.displayCount < 0) e.emplace_back("displayCount must not be negative");
    if (p.missileTubes < 0 || p.autocannonSlots < 0) e.emplace_back("weapon counts must not be negative");
    if (p.enableRadarArray && p.radarRange <= 0.0f) e.emplace_back("radarRange must be positive");
    return e;
}

std::vector<std::string> collectMechErrors(const MechParams& p) {
    std::vector<std::string> e;
    if (p.id.empty()) e.emplace_back("id must not be empty");
    if (p.limbCount < 0 || p.limbCount > 16) e.emplace_back("limbCount must be in [0, 16]");
    if (p.detailLevel < 0 || p.detailLevel > 3) e.emplace_back("detailLevel must be in [0, 3]");
    if (p.torsoSize.x <= 0.0f || p.torsoSize.y <= 0.0f || p.torsoSize.z <= 0.0f) e.emplace_back("torsoSize must be positive");
    if (p.limbCount > 0 && p.limbLength <= 0.0f) e.emplace_back("limbLength must be positive when the mech has limbs");
    if (p.scale.x <= 0.0f || p.scale.y <= 0.0f || p.scale.z <= 0.0f) e.emplace_back("scale must be positive");
    if (p.mass <= 0.0f) e.emplace_back("mass must be positive");
    if (p.textureResolution < 16 || p.textureResolution > 4096) e.emplace_back("textureResolution must be in [16, 4096]");
    if (p.morphDuration <= 0.0f) e.emplace_back("morphDuration must be positive");
    if (p.maxSpeed < 0.0f || p.jumpHeight < 0.0f) e.emplace_back("maxSpeed and jumpHeight must not be negative");
    if (p.crewCapacity < 0) e.emplace_back("crewCapacity must not be negative");
    if (p.patternIntensity < 0.0f || p.patternIntensity > 1.0f) e.emplace_back("patternIntensity must be in [0, 1]");
    if (p.lodDistances.size() != p.lodTriangleCounts.size()) {
        e.emplace_back("lodDistances and lodTriangleCounts must have the same length");
    } else {
        for (size_t i = 1; i < p.lodDistances.size(); ++i) {
            if (p.lodDistances[i] <= p.lodDistances[i - 1]) e.emplace_back("lodDistances must be ascending");
            if (p.lodTriangleCounts[i] > p.lodTriangleCounts[i - 1]) e.emplace_back("lodTriangleCounts must be descending");
        }
    }
    return e;
}

// ---------------------------------------------------------- centipede layout -

glm::vec3 centipedeLocalHip(const CentipedeMechParams& p, int legIndex, int legCount) {
    const int perSide = std::max(1, (legCount + 1) / 2);
    const float side = (legIndex % 2 == 0) ? -1.0f : 1.0f;
    const int row = legIndex / 2;
    const float z = perSide > 1 ? (static_cast<float>(row) / (perSide - 1) - 0.5f) * p.segmentLength * 0.6f : 0.0f;
    return glm::vec3(side * p.segmentRadius, 0.0f, z);
}

glm::quat lookRotation(const glm::vec3& forward) {
    // Orientation whose local +Z axis (the head direction; segments trail along -Z) points along `forward`.
    const glm::vec3 from(0.0f, 0.0f, 1.0f);
    const float len = glm::length(forward);
    if (len < 1e-6f) return glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    const glm::vec3 to = forward / len;
    const float d = glm::dot(from, to);
    if (d > 0.9999f) return glm::quat(1.0f, 0.0f, 0.0f, 0.0f);
    if (d < -0.9999f) return glm::angleAxis(kPi, glm::vec3(0.0f, 1.0f, 0.0f));
    const glm::vec3 axis = glm::cross(from, to);
    return glm::normalize(glm::quat(1.0f + d, axis.x, axis.y, axis.z));
}

std::vector<MeshHandle> buildCentipedeLegs(const CentipedeMechParams& p, const std::vector<int>& legCounts) {
    std::vector<MeshHandle> legs;
    for (size_t s = 0; s < legCounts.size(); ++s) {
        CentipedeMechParams segParams = p;
        segParams.legsPerSegment = legCounts[s];
        for (int l = 0; l < legCounts[s]; ++l) {
            legs.push_back(CentipedeLegGenerator::buildSingleLeg(segParams, static_cast<int>(s), l));
        }
    }
    return legs;
}

// Regenerates every geometry asset that depends on the segment / leg layout.
void rebuildCentipedeGeometry(CentipedeMechInstanceState& s) {
    s.params.segmentCount = static_cast<int>(s.segmentLegCounts.size());
    replaceOwnedList(s.ownedAssets, s.bundle.segments, CentipedeSegmentGenerator::buildSegments(s.params));
    replaceOwnedList(s.ownedAssets, s.bundle.joints, CentipedeJointGenerator::buildJoints(s.params));
    replaceOwnedList(s.ownedAssets, s.bundle.legs, buildCentipedeLegs(s.params, s.segmentLegCounts));
    replaceOwned(s.ownedAssets, s.bundle.collider, CentipedeCollisionGenerator::buildMechCollider(s.params));
}

int legFlatIndex(const CentipedeMechInstanceState& s, int segmentIndex, int legIndex) {
    int index = 0;
    for (int i = 0; i < segmentIndex; ++i) index += s.segmentLegCounts[i];
    return index + legIndex;
}

float centipedeGaitDuration(const std::string& animation) {
    const std::string a = lower(animation);
    if (a == "run") return 0.5f;
    if (a == "walk" || a == "crawl") return 1.0f;
    return 2.0f;
}

bool isLocomotion(const std::string& animation) {
    const std::string a = lower(animation);
    return a == "walk" || a == "crawl" || a == "run";
}

// ------------------------------------------------------------- JSON input ---

void readVec3(const nlohmann::json& j, const char* key, glm::vec3& out) {
    auto it = j.find(key);
    if (it == j.end() || it->is_null()) return;
    if (!it->is_array() || it->size() != 3) throw std::invalid_argument(std::string(key) + " must be an array of 3 numbers");
    out = glm::vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
}

template <typename T>
void readField(const nlohmann::json& j, const char* key, T& out) {
    auto it = j.find(key);
    if (it != j.end() && !it->is_null()) out = it->template get<T>();
}

void applyMechJson(MechParams& p, const nlohmann::json& j) {
    readField(j, "id", p.id);
    readField(j, "style", p.style);
    readField(j, "pattern", p.pattern);
    readField(j, "variant", p.variant);
    readField(j, "aiBehavior", p.aiBehavior);
    readField(j, "faction", p.faction);
    readField(j, "morphCurve", p.morphCurve);
    readField(j, "forms", p.forms);
    readField(j, "weaponMounts", p.weaponMounts);
    readField(j, "armorTypes", p.armorTypes);
    readField(j, "weaponTypes", p.weaponTypes);
    readField(j, "abilities", p.abilities);
    readField(j, "stats", p.stats);
    readVec3(j, "colorPrimary", p.colorPrimary);
    readVec3(j, "colorAccent", p.colorAccent);
    readVec3(j, "torsoSize", p.torsoSize);
    readVec3(j, "scale", p.scale);
    readField(j, "limbCount", p.limbCount);
    readField(j, "detailLevel", p.detailLevel);
    readField(j, "crewCapacity", p.crewCapacity);
    readField(j, "textureResolution", p.textureResolution);
    readField(j, "limbLength", p.limbLength);
    readField(j, "mass", p.mass);
    readField(j, "maxSpeed", p.maxSpeed);
    readField(j, "jumpHeight", p.jumpHeight);
    readField(j, "noiseScale", p.noiseScale);
    readField(j, "patternIntensity", p.patternIntensity);
    readField(j, "morphDuration", p.morphDuration);
    readField(j, "armorPlates", p.armorPlates);
    readField(j, "pulseEmission", p.pulseEmission);
    readField(j, "enableGlow", p.enableGlow);
    readField(j, "enableShield", p.enableShield);
    readField(j, "canFly", p.canFly);
    readField(j, "canSwim", p.canSwim);
    readField(j, "generateNormalMap", p.generateNormalMap);
    readField(j, "generateRoughnessMap", p.generateRoughnessMap);
    readField(j, "generateMetallicMap", p.generateMetallicMap);
    readField(j, "enableIK", p.enableIK);
    readField(j, "enablePhysics", p.enablePhysics);
    readField(j, "lodDistances", p.lodDistances);
    readField(j, "lodTriangleCounts", p.lodTriangleCounts);
}

} // namespace

// ============================================================================
// Lifecycle
// ============================================================================

MechFactory::MechFactory() {
    registerBuiltinTemplates();
}

MechFactory::~MechFactory() {
    shutdown();
}

void MechFactory::initialize(size_t cache_size, size_t num_threads) {
    std::lock_guard<std::mutex> lock(lifecycleMutex_);
    if (m_initialized) return;
    m_cache.set_capacity(cache_size);
    m_segmentedCache.set_capacity(cache_size);
    m_centipedeCache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
    Log::info("Mech", "MechFactory initialized (cache {}, threads {})", cache_size, m_pool.size());
}

void MechFactory::shutdown() {
    std::lock_guard<std::mutex> lock(lifecycleMutex_);
    if (!m_initialized) return;
    m_pool.stop();   // drains queued generation tasks before returning
    m_initialized = false;
}

void MechFactory::registerBuiltinTemplates() {
    MechParams scout;
    scout.id = "scout";
    scout.style = "scout";
    scout.forms = {"mobile", "stealth"};
    scout.limbCount = 2;
    scout.torsoSize = glm::vec3(1.0f, 1.2f, 0.6f);
    scout.limbLength = 0.8f;
    scout.armorPlates = true;
    scout.weaponMounts = {"shoulder", "arm"};
    scout.pattern = "hexCamouflage";
    scout.detailLevel = 2;
    scout.pulseEmission = true;
    scout.mass = 800.0f;
    scout.maxSpeed = 15.0f;
    scout.jumpHeight = 3.0f;
    scout.canSwim = true;

    MechParams heavy;
    heavy.id = "heavy";
    heavy.style = "heavy";
    heavy.forms = {"drive", "tower", "siege"};
    heavy.limbCount = 0;
    heavy.torsoSize = glm::vec3(1.5f, 0.8f, 1.2f);
    heavy.armorPlates = true;
    heavy.weaponMounts = {"top", "sides"};
    heavy.pattern = "techDamaged";
    heavy.detailLevel = 2;
    heavy.mass = 2500.0f;
    heavy.maxSpeed = 8.0f;
    heavy.jumpHeight = 1.0f;

    MechParams support;
    support.id = "support";
    support.style = "support";
    support.forms = {"mobile", "turret", "repair"};
    support.limbCount = 2;
    support.torsoSize = glm::vec3(1.2f, 1.0f, 0.8f);
    support.limbLength = 0.9f;
    support.armorPlates = true;
    support.weaponMounts = {"back", "arm"};
    support.pattern = "techClean";
    support.detailLevel = 2;
    support.pulseEmission = true;
    support.maxSpeed = 12.0f;
    support.canSwim = true;
    {
        std::lock_guard<std::mutex> lock(templateMutex_);
        mechTemplates_["scout"] = scout;
        mechTemplates_["heavy"] = heavy;
        mechTemplates_["support"] = support;
    }

    SegmentedMechParams snake;
    snake.id = "snake";
    snake.mechType = "snake";
    SegmentedMechParams worm;
    worm.id = "worm";
    worm.mechType = "worm";
    worm.segmentCount = 25;
    worm.segmentLength = 1.2f;
    worm.segmentRadius = 0.5f;
    worm.cockpitType = "external";
    worm.enableJointSparks = false;
    SegmentedMechParams serpent;
    serpent.id = "serpent";
    serpent.mechType = "serpent";
    serpent.segmentCount = 18;
    serpent.segmentLength = 1.2f;
    serpent.taperProfile = "exponential";
    serpent.animationProfile = "undulate";
    serpent.waveFrequency = 1.5f;

    CockpitParams internalCockpit;
    CockpitParams externalCockpit;
    externalCockpit.seatWidth = 1.0f;
    externalCockpit.seatDepth = 1.5f;
    externalCockpit.seatHeight = 0.6f;
    externalCockpit.canopyRadius = 1.2f;
    externalCockpit.canopyHeight = 1.0f;
    externalCockpit.displayCount = 4;
    externalCockpit.gaugeCount = 8;
    CockpitParams moduleCockpit;
    moduleCockpit.seatWidth = 0.7f;
    moduleCockpit.canopyRadius = 0.8f;
    moduleCockpit.canopyHeight = 0.6f;
    moduleCockpit.displayCount = 2;
    moduleCockpit.holographicHUD = false;
    moduleCockpit.canopyAnimEnabled = false;
    {
        std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
        segmentedMechTemplates_["snake"] = snake;
        segmentedMechTemplates_["worm"] = worm;
        segmentedMechTemplates_["serpent"] = serpent;
        cockpitTemplates_["internal"] = internalCockpit;
        cockpitTemplates_["external"] = externalCockpit;
        cockpitTemplates_["module"] = moduleCockpit;
    }

    CentipedeMechParams standard;
    standard.id = "standard";
    CentipedeMechParams assault = standard;
    assault.id = "assault";
    assault.segmentCount = 12;
    assault.missileTubes = 4;
    assault.autocannonSlots = 2;
    CentipedeMechParams recon = standard;
    recon.id = "recon";
    recon.segmentCount = 6;
    recon.legsPerSegment = 2;
    recon.missileTubes = 0;
    recon.enableTurret = false;
    recon.radarRange = 600.0f;
    {
        std::lock_guard<std::mutex> lock(centipedeTemplateMutex_);
        centipedeMechTemplates_["standard"] = standard;
        centipedeMechTemplates_["assault"] = assault;
        centipedeMechTemplates_["recon"] = recon;
    }
}

std::string MechFactory::makeInstanceId(const std::string& baseId) {
    return (baseId.empty() ? std::string("mech") : baseId) + "#" + std::to_string(nextInstanceId_++);
}

void MechFactory::updateMetrics(uint64_t generationTime, uint64_t memoryUsage) {
    metrics_.totalGenerations++;
    metrics_.totalGenerationTime += generationTime;
    uint64_t peak = metrics_.peakMemoryUsage.load();
    while (memoryUsage > peak && !metrics_.peakMemoryUsage.compare_exchange_weak(peak, memoryUsage)) {
    }
}

void MechFactory::trackInstanceCount() {
    uint64_t active = 0;
    uint64_t morphing = 0;
    {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        active += activeInstances_.size();
        for (const auto& [id, inst] : activeInstances_) {
            if (inst.isMorphing) ++morphing;
        }
    }
    {
        std::lock_guard<std::mutex> lock(segmentedInstanceMutex_);
        active += activeSegmentedInstances_.size();
    }
    {
        std::lock_guard<std::mutex> lock(centipedeInstanceMutex_);
        active += activeCentipedeInstances_.size();
    }
    metrics_.activeInstances = active;
    metrics_.morphingInstances = morphing;
}

// ============================================================================
// Mech generation
// ============================================================================

void MechFactory::setProceduralParams(const ProceduralParams& params) {
    std::lock_guard<std::mutex> lock(proceduralMutex_);
    proceduralParams_ = params;
}

ProceduralParams MechFactory::getProceduralParams() const {
    std::lock_guard<std::mutex> lock(proceduralMutex_);
    return proceduralParams_;
}

uint64_t MechFactory::mechCacheKey(const MechParams& params) const {
    return MechHash::hashFields(params.hashKey(), getProceduralParams().hashKey());
}

MechBundle MechFactory::generateMechBundle(const MechParams& params) {
    if (!validateParams(params)) {
        throw std::invalid_argument("Invalid mech params '" + params.id + "': " + joinErrors(getValidationErrors()));
    }
    const auto start = SteadyClock::now();
    ProceduralParams proc = getProceduralParams();
    proc.frequency *= std::max(0.01f, params.noiseScale);

    MechBundle b;
    b.mesh = MeshGenerator::buildMechMesh(params);
    b.tex = TextureGenerator::buildProceduralSkin(params, proc);
    b.skeleton = SkeletonGenerator::buildRig(params);
    b.animation = SkeletonGenerator::createIdleAnimation(params);
    if (params.generateNormalMap) b.normalMap = TextureGenerator::buildNormalMap(params);
    if (params.generateRoughnessMap) b.roughnessMap = TextureGenerator::buildRoughnessMap(params);
    if (params.generateMetallicMap) b.metallicMap = TextureGenerator::buildMetallicMap(params);
    if (params.pulseEmission || params.enableGlow) b.emissiveMap = TextureGenerator::buildEmissiveMap(params);
    b.material = MaterialGenerator::createMaterialFromTextures(params, b.tex, b.normalMap, b.roughnessMap,
                                                               b.metallicMap, b.emissiveMap);
    if (params.enablePhysics) {
        PhysicsGenerator::generateCollisionMesh(params, b.collisionVertices, b.collisionIndices);
        glm::mat3 inertia(1.0f);
        PhysicsGenerator::generateRigidBody(params, b.mass, b.centerOfMass, inertia);
    } else {
        b.mass = params.mass;
    }

    b.animationClips.push_back("idle");
    for (size_t i = 0; i < params.forms.size(); ++i) {
        b.animationClips.push_back("form_" + params.forms[i]);
        b.morphWeights[params.forms[i]] = i == 0 ? 1.0f : 0.0f;
    }
    if (params.canFly) b.animationClips.push_back("flight");
    if (params.canSwim) b.animationClips.push_back("swim");

    b.creationTime = std::chrono::system_clock::now();
    b.generationTime = elapsedMs(start);
    b.memoryUsage = assetMemory({b.mesh, b.tex, b.skeleton, b.animation, b.material, b.normalMap, b.roughnessMap,
                                 b.metallicMap, b.emissiveMap}) +
                    b.collisionVertices.size() * sizeof(glm::vec3) + b.collisionIndices.size() * sizeof(uint32_t);
    b.gpuAccelerated = gpuAccelerationEnabled_;
    updateMetrics(b.generationTime, b.memoryUsage);
    Log::info("Mech", "Generated mech '{}' in {} ms", params.id, b.generationTime);
    return b;
}

std::future<MechBundle> MechFactory::generateAsync(MechParams p) {
    const uint64_t key = mechCacheKey(p);
    if (auto hit = m_cache.find(key)) {
        metrics_.cacheHits++;
        return readyFuture(std::move(*hit));
    }
    metrics_.cacheMisses++;
    return m_pool.enqueue([this, p = std::move(p), key] {
        MechBundle b = generateMechBundle(p);
        m_cache.insert(key, b);
        return b;
    });
}

MechBundle MechFactory::generateSync(MechParams p) {
    const uint64_t key = mechCacheKey(p);
    if (auto hit = m_cache.find(key)) {
        metrics_.cacheHits++;
        return *hit;
    }
    metrics_.cacheMisses++;
    MechBundle b = generateMechBundle(p);
    m_cache.insert(key, b);
    return b;
}

std::vector<std::future<MechBundle>> MechFactory::generateBatch(const std::vector<MechParams>& params) {
    std::vector<std::future<MechBundle>> futures;
    futures.reserve(params.size());
    for (const auto& p : params) futures.push_back(generateAsync(p));
    return futures;
}

void MechFactory::generateBatchSync(const std::vector<MechParams>& params, std::vector<MechBundle>& results) {
    auto futures = generateBatch(params);
    results.clear();
    results.reserve(futures.size());
    for (auto& f : futures) results.push_back(f.get());
}

void MechFactory::clearCache() { m_cache.clear(); }
size_t MechFactory::getCacheSize() const { return m_cache.size(); }
bool MechFactory::isCached(const MechParams& params) const { return m_cache.contains(mechCacheKey(params)); }
void MechFactory::setCacheSize(size_t size) { m_cache.set_capacity(size); }

// ============================================================================
// Mech instances and morphing
// ============================================================================

MechInstanceState MechFactory::createInstance(const MechParams& params) {
    MechInstanceState s;
    s.bundle = generateSync(params);
    s.id = makeInstanceId(params.id);
    s.params = params;
    s.currentForm = params.forms.empty() ? std::string("default") : params.forms.front();
    s.targetForm = s.currentForm;
    s.scale = params.scale;
    s.lastUpdate = std::chrono::system_clock::now();
    {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        activeInstances_[s.id] = s;
    }
    trackInstanceCount();
    return s;
}

bool MechFactory::destroyInstance(const MechInstanceState& instance) {
    bool erased = false;
    {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        erased = activeInstances_.erase(instance.id) > 0;
    }
    trackInstanceCount();
    return erased;
}

bool MechFactory::updateInstance(MechInstanceState& instance, float deltaTime) {
    if (!instance.isActive || deltaTime < 0.0f) return false;

    if (instance.isMorphing && !instance.morphPaused) {
        instance.morphProgress += deltaTime / std::max(0.01f, instance.params.morphDuration);
        if (instance.morphProgress >= 1.0f) finishMorph(instance);
        else applyMorphWeights(instance);
    }

    if (instance.params.enablePhysics) {
        instance.velocity += instance.acceleration * deltaTime;
        glm::vec2 horizontal(instance.velocity.x, instance.velocity.z);
        const float speed = glm::length(horizontal);
        if (speed > instance.params.maxSpeed && speed > 0.0f) {
            horizontal *= instance.params.maxSpeed / speed;
            instance.velocity.x = horizontal.x;
            instance.velocity.z = horizontal.y;
        }
        if (!instance.params.canFly && instance.position.y > 0.0f) instance.velocity.y -= 9.81f * deltaTime;
        instance.position += instance.velocity * deltaTime;
        if (!instance.params.canFly && instance.position.y < 0.0f) {
            instance.position.y = 0.0f;
            instance.velocity.y = std::max(0.0f, instance.velocity.y);
        }
        integrateRotation(instance.rotation, instance.angularVelocity, deltaTime);
    }

    const float duration = instance.isMorphing ? std::max(0.01f, instance.params.morphDuration)
                                               : animationDuration(instance.bundle.animation, 1.0f);
    instance.animationTime += deltaTime;
    if (instance.animationTime > duration) {
        instance.animationTime = instance.animationLooping ? std::fmod(instance.animationTime, duration) : duration;
    }

    updateFrameStats(instance.frameCount, instance.averageFrameTime, deltaTime);
    instance.lastUpdate = std::chrono::system_clock::now();
    syncInstance(activeInstances_, instanceMutex_, instance);
    trackInstanceCount();
    return true;
}

bool MechFactory::startMorph(MechInstanceState& instance, const std::string& formName) {
    const auto& forms = instance.params.forms;
    const bool known = formName == "default" ? forms.empty()
                                             : std::find(forms.begin(), forms.end(), formName) != forms.end();
    if (!known) {
        Log::warn("Mech", "Mech '{}' has no form '{}'", instance.id, formName);
        return false;
    }
    if (formName == instance.currentForm && !instance.isMorphing) return true;   // already in that form
    instance.targetForm = formName;
    instance.morphProgress = 0.0f;
    instance.isMorphing = true;
    instance.morphPaused = false;
    instance.currentAnimation = "morph_" + formName;
    instance.animationTime = 0.0f;
    applyMorphWeights(instance);
    syncInstance(activeInstances_, instanceMutex_, instance);
    trackInstanceCount();
    return true;
}

bool MechFactory::setMorphProgress(MechInstanceState& instance, float progress) {
    if (!instance.isMorphing) return false;
    instance.morphProgress = std::clamp(progress, 0.0f, 1.0f);
    if (instance.morphProgress >= 1.0f) finishMorph(instance);
    else applyMorphWeights(instance);
    syncInstance(activeInstances_, instanceMutex_, instance);
    trackInstanceCount();
    return true;
}

bool MechFactory::pauseMorph(MechInstanceState& instance) {
    if (!instance.isMorphing || instance.morphPaused) return false;
    instance.morphPaused = true;
    syncInstance(activeInstances_, instanceMutex_, instance);
    return true;
}

bool MechFactory::resumeMorph(MechInstanceState& instance) {
    if (!instance.isMorphing || !instance.morphPaused) return false;
    instance.morphPaused = false;
    syncInstance(activeInstances_, instanceMutex_, instance);
    return true;
}

// ============================================================================
// Hot reload
// ============================================================================

void MechFactory::setDefinitionDirectory(const std::filesystem::path& directory) {
    std::lock_guard<std::mutex> lock(watcherMutex_);
    definitionDirectory_ = directory;
    for (auto& watcher : fileWatchers_) watcher.filePath = definitionPathFor(watcher.mechId);
}

std::filesystem::path MechFactory::getDefinitionDirectory() const {
    std::lock_guard<std::mutex> lock(watcherMutex_);
    return definitionDirectory_;
}

// Caller must hold watcherMutex_.
std::string MechFactory::definitionPathFor(const std::string& mechId) const {
    return (definitionDirectory_ / (mechId + ".json")).string();
}

uint64_t MechFactory::computeFileHash(const std::string& filePath) const {
    std::ifstream in(filePath, std::ios::binary);
    if (!in) return 0;
    const std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    return MechHash::hashFields(content);
}

void MechFactory::watchDefinition(const std::string& mechId) {
    std::lock_guard<std::mutex> lock(watcherMutex_);
    for (const auto& w : fileWatchers_) {
        if (w.mechId == mechId) return;
    }
    FileWatcher watcher;
    watcher.mechId = mechId;
    watcher.filePath = definitionPathFor(mechId);
    std::error_code ec;
    if (std::filesystem::exists(watcher.filePath, ec)) {
        watcher.lastModified = std::filesystem::last_write_time(watcher.filePath, ec);
        watcher.lastHash = computeFileHash(watcher.filePath);
    }
    Log::info("Mech", "Watching mech definition '{}' at {}", mechId, watcher.filePath);
    fileWatchers_.push_back(std::move(watcher));
}

void MechFactory::unwatchDefinition(const std::string& mechId) {
    std::lock_guard<std::mutex> lock(watcherMutex_);
    std::erase_if(fileWatchers_, [&](const FileWatcher& w) { return w.mechId == mechId; });
}

void MechFactory::processHotReloads() {
    checkFileChanges();
}

void MechFactory::checkFileChanges() {
    std::vector<std::string> changed;
    {
        std::lock_guard<std::mutex> lock(watcherMutex_);
        for (auto& w : fileWatchers_) {
            std::error_code ec;
            if (!std::filesystem::exists(w.filePath, ec)) continue;
            const auto modified = std::filesystem::last_write_time(w.filePath, ec);
            if (ec || modified == w.lastModified) continue;
            w.lastModified = modified;
            const uint64_t hash = computeFileHash(w.filePath);
            if (hash != w.lastHash) {
                w.lastHash = hash;
                changed.push_back(w.mechId);
            }
        }
    }
    for (const auto& id : changed) rebuildFromFile(id);
}

bool MechFactory::rebuildFromFile(const std::string& mechId) {
    std::string path;
    {
        std::lock_guard<std::mutex> lock(watcherMutex_);
        path = definitionPathFor(mechId);
    }
    MechParams params;
    {
        std::lock_guard<std::mutex> lock(templateMutex_);
        auto it = mechTemplates_.find(mechId);
        if (it != mechTemplates_.end()) params = it->second;
    }
    params.id = mechId;
    try {
        std::ifstream in(path);
        if (!in) {
            Log::error("Mech", "Cannot open mech definition {}", path);
            return false;
        }
        applyMechJson(params, nlohmann::json::parse(in));
    } catch (const std::exception& e) {
        Log::error("Mech", "Failed to parse mech definition {}: {}", path, e.what());
        return false;
    }
    if (!validateParams(params)) {
        Log::error("Mech", "Mech definition {} is invalid: {}", path, joinErrors(getValidationErrors()));
        return false;
    }
    registerTemplate(mechId, params);
    MechBundle bundle;
    try {
        bundle = generateSync(params);
    } catch (const std::exception& e) {
        Log::error("Mech", "Failed to rebuild mech '{}': {}", mechId, e.what());
        return false;
    }
    {
        std::lock_guard<std::mutex> lock(instanceMutex_);
        for (auto& [id, inst] : activeInstances_) {
            if (inst.params.id != mechId) continue;
            inst.params = params;
            inst.bundle = bundle;
        }
    }
    Log::info("Mech", "Hot-reloaded mech definition '{}'", mechId);
    return true;
}

// ============================================================================
// Templates and validation
// ============================================================================

MechParams MechFactory::createFromTemplate(const std::string& templateName) {
    std::lock_guard<std::mutex> lock(templateMutex_);
    auto it = mechTemplates_.find(templateName);
    if (it == mechTemplates_.end()) throw std::out_of_range("Unknown mech template '" + templateName + "'");
    return it->second;
}

void MechFactory::registerTemplate(const std::string& name, const MechParams& template_) {
    std::lock_guard<std::mutex> lock(templateMutex_);
    mechTemplates_[name] = template_;
}

std::vector<std::string> MechFactory::getAvailableTemplates() const {
    std::lock_guard<std::mutex> lock(templateMutex_);
    return sortedKeys(mechTemplates_);
}

bool MechFactory::validateParams(const MechParams& params) {
    auto errors = collectMechErrors(params);
    const bool ok = errors.empty();
    std::lock_guard<std::mutex> lock(validationMutex_);
    validationErrors_ = std::move(errors);
    return ok;
}

std::vector<std::string> MechFactory::getValidationErrors() const {
    std::lock_guard<std::mutex> lock(validationMutex_);
    return validationErrors_;
}

// ============================================================================
// Segmented mechs
// ============================================================================

uint64_t MechFactory::segmentedCacheKey(const SegmentedMechParams& params, const CockpitParams& cockpitParams,
                                        const UIParams& uiParams) {
    return MechHash::hashFields(params.hashKey(), cockpitParams.hashKey(), uiParams.hashKey());
}

bool MechFactory::generateCockpitMesh(const CockpitParams& params, MeshHandle& mesh) {
    mesh = CockpitGenerator::buildCockpit(params);
    return mesh != 0;
}

bool MechFactory::generateCockpitTexture(const CockpitParams& params, TextureHandle& texture) {
    texture = CockpitGenerator::buildCockpitTexture(params);
    return texture != 0;
}

bool MechFactory::generateUIIcon(const SegmentedMechParams& params, const UIParams& uiParams, TextureHandle& icon) {
    icon = UIIconGenerator::buildMechIcon(params, uiParams);
    return icon != 0;
}

bool MechFactory::generateSegmentMesh(const SegmentedMechParams& params, int index, MeshHandle& mesh) {
    mesh = SegmentedMeshGenerator::createSegment(params, index);
    return mesh != 0;
}

bool MechFactory::generateSegmentPhysics(const SegmentedMechParams& params, int index, PhysicsHandle& physics) {
    physics = SegmentedPhysicsGenerator::createSegmentPhysics(params, index);
    return physics != 0;
}

SegmentHandle MechFactory::createSegment(const SegmentedMechParams& params, int index) {
    MeshHandle mesh = 0;
    return generateSegmentMesh(params, index, mesh) ? mesh : 0;
}

bool MechFactory::destroySegment(SegmentHandle handle) {
    return handle != 0 && MechFamilyAssetStore::instance().release(handle);
}

SegmentedMechBundle MechFactory::generateSegmentedBundle(const SegmentedMechParams& params,
                                                         const CockpitParams& cockpitParams,
                                                         const UIParams& uiParams) {
    auto errors = collectSegmentedErrors(params);
    const auto cockpitErrors = collectCockpitErrors(cockpitParams);
    errors.insert(errors.end(), cockpitErrors.begin(), cockpitErrors.end());
    if (!errors.empty()) {
        const std::string message = joinErrors(errors);
        {
            std::lock_guard<std::mutex> lock(validationMutex_);
            segmentedValidationErrors_ = std::move(errors);
        }
        throw std::invalid_argument("Invalid segmented mech params '" + params.id + "': " + message);
    }
    const auto start = SteadyClock::now();
    SegmentedMechBundle b;
    b.segmentMesh = SegmentedMeshGenerator::buildSegmentedMech(params);
    b.skeleton = SegmentedSkeletonGenerator::buildSegmentedRig(params);
    b.proceduralAnimation = SegmentedSkeletonGenerator::createCustomAnimation(params, params.animationProfile);
    b.materialShader = MaterialGenerator::buildSegmentedMaterial(params);
    b.sparkParticles = SegmentedParticleGenerator::buildJointSparks(params);
    b.physicsAsset = SegmentedPhysicsGenerator::buildSegmentedPhysics(params);
    if (lower(params.cockpitType) != "none") {
        generateCockpitMesh(cockpitParams, b.cockpitMesh);
        generateCockpitTexture(cockpitParams, b.cockpitTexture);
        b.cockpitMaterial = CockpitGenerator::buildCockpitMaterial(cockpitParams);
    }
    generateUIIcon(params, uiParams, b.icon);
    b.creationTime = std::chrono::system_clock::now();
    b.generationTime = elapsedMs(start);
    b.memoryUsage = assetMemory({b.segmentMesh, b.skeleton, b.proceduralAnimation, b.materialShader, b.sparkParticles,
                                 b.physicsAsset, b.cockpitMesh, b.cockpitTexture, b.cockpitMaterial, b.icon});
    b.gpuAccelerated = gpuAccelerationEnabled_;
    updateMetrics(b.generationTime, b.memoryUsage);
    Log::info("Mech", "Generated segmented mech '{}' ({} segments) in {} ms", params.id, params.segmentCount,
              b.generationTime);
    return b;
}

std::future<SegmentedMechBundle> MechFactory::generateSegmentedAsync(const SegmentedMechParams& params,
                                                                     const CockpitParams& cockpitParams,
                                                                     const UIParams& uiParams) {
    const uint64_t key = segmentedCacheKey(params, cockpitParams, uiParams);
    if (auto hit = m_segmentedCache.find(key)) {
        metrics_.cacheHits++;
        return readyFuture(std::move(*hit));
    }
    metrics_.cacheMisses++;
    return m_pool.enqueue([this, params, cockpitParams, uiParams, key] {
        SegmentedMechBundle b = generateSegmentedBundle(params, cockpitParams, uiParams);
        m_segmentedCache.insert(key, b);
        return b;
    });
}

SegmentedMechBundle MechFactory::generateSegmentedSync(const SegmentedMechParams& params,
                                                       const CockpitParams& cockpitParams,
                                                       const UIParams& uiParams) {
    const uint64_t key = segmentedCacheKey(params, cockpitParams, uiParams);
    if (auto hit = m_segmentedCache.find(key)) {
        metrics_.cacheHits++;
        return *hit;
    }
    metrics_.cacheMisses++;
    SegmentedMechBundle b = generateSegmentedBundle(params, cockpitParams, uiParams);
    m_segmentedCache.insert(key, b);
    return b;
}

void MechFactory::storeSegmentedInstance(const SegmentedMechInstanceState& instance) {
    syncInstance(activeSegmentedInstances_, segmentedInstanceMutex_, instance);
}

SegmentedMechInstanceState MechFactory::createSegmentedInstance(const SegmentedMechParams& params,
                                                                const CockpitParams& cockpitParams) {
    SegmentedMechInstanceState s;
    s.bundle = generateSegmentedSync(params, cockpitParams);
    s.id = makeInstanceId(params.id);
    s.params = params;
    s.cockpitParams = cockpitParams;
    s.cockpitAttached = lower(params.cockpitType) != "none";
    s.currentAnimation = params.animationProfile;
    for (int i = 0; i < params.segmentCount; ++i) {
        s.segments.push_back(createSegment(params, i));
        s.segmentOverrides.emplace_back();
    }
    s.currentSegmentCount = params.segmentCount;
    s.lastUpdate = std::chrono::system_clock::now();
    {
        std::lock_guard<std::mutex> lock(segmentedInstanceMutex_);
        activeSegmentedInstances_[s.id] = s;
    }
    trackInstanceCount();
    return s;
}

bool MechFactory::destroySegmentedInstance(const SegmentedMechInstanceState& instance) {
    SegmentedMechInstanceState stored;
    {
        std::lock_guard<std::mutex> lock(segmentedInstanceMutex_);
        auto it = activeSegmentedInstances_.find(instance.id);
        if (it == activeSegmentedInstances_.end()) return false;
        stored = std::move(it->second);
        activeSegmentedInstances_.erase(it);
    }
    for (SegmentHandle h : stored.segments) destroySegment(h);
    releaseAllOwned(stored.ownedAssets);
    trackInstanceCount();
    return true;
}

bool MechFactory::updateSegmentedInstance(SegmentedMechInstanceState& instance, float deltaTime) {
    if (!instance.isActive || deltaTime < 0.0f) return false;
    if (!instance.animationPaused) {
        const float duration = animationDuration(instance.bundle.proceduralAnimation,
                                                 1.0f / std::max(0.01f, instance.params.waveFrequency));
        instance.animationTime += deltaTime;
        if (instance.animationTime > duration) {
            instance.animationTime = instance.animationLooping ? std::fmod(instance.animationTime, duration) : duration;
        }
    }
    instance.velocity += instance.acceleration * deltaTime;
    instance.position += instance.velocity * deltaTime;
    integrateRotation(instance.rotation, instance.angularVelocity, deltaTime);
    updateFrameStats(instance.frameCount, instance.averageFrameTime, deltaTime);
    instance.lastUpdate = std::chrono::system_clock::now();
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::updateSegmentSkeleton(SegmentedMechInstanceState& instance) {
    instance.params.segmentCount = instance.currentSegmentCount;
    if (instance.params.cockpitSegmentIndex >= instance.currentSegmentCount) {
        instance.params.cockpitSegmentIndex = instance.currentSegmentCount - 1;
    }
    auto& owned = instance.ownedAssets;
    replaceOwned(owned, instance.bundle.skeleton, SegmentedSkeletonGenerator::buildSegmentedRig(instance.params));
    replaceOwned(owned, instance.bundle.segmentMesh, SegmentedMeshGenerator::buildSegmentedMech(instance.params));
    replaceOwned(owned, instance.bundle.physicsAsset, SegmentedPhysicsGenerator::buildSegmentedPhysics(instance.params));
    replaceOwned(owned, instance.bundle.proceduralAnimation,
                 SegmentedSkeletonGenerator::createCustomAnimation(instance.params, instance.currentAnimation));
    replaceOwned(owned, instance.bundle.sparkParticles, SegmentedParticleGenerator::buildJointSparks(instance.params));
    return instance.bundle.skeleton != 0;
}

bool MechFactory::addSegment(SegmentedMechInstanceState& instance, int index) {
    if (instance.currentSegmentCount >= kMaxSegments) return false;
    index = std::clamp(index, 0, instance.currentSegmentCount);
    instance.segmentOverrides.insert(instance.segmentOverrides.begin() + index, std::unordered_map<std::string, float>{});
    instance.segments.insert(instance.segments.begin() + index, SegmentHandle{0});
    instance.currentSegmentCount++;
    instance.params.segmentCount = instance.currentSegmentCount;
    // Segment meshes are positioned by index, so everything from `index` on is rebuilt.
    for (int i = index; i < instance.currentSegmentCount; ++i) {
        destroySegment(instance.segments[i]);
        instance.segments[i] = createSegment(paramsForSegment(instance, i), i);
    }
    updateSegmentSkeleton(instance);
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::removeSegment(SegmentedMechInstanceState& instance, int index) {
    if (instance.currentSegmentCount <= 1 || index < 0 || index >= instance.currentSegmentCount) return false;
    destroySegment(instance.segments[index]);
    instance.segments.erase(instance.segments.begin() + index);
    instance.segmentOverrides.erase(instance.segmentOverrides.begin() + index);
    instance.currentSegmentCount--;
    instance.params.segmentCount = instance.currentSegmentCount;
    for (int i = index; i < instance.currentSegmentCount; ++i) {
        destroySegment(instance.segments[i]);
        instance.segments[i] = createSegment(paramsForSegment(instance, i), i);
    }
    updateSegmentSkeleton(instance);
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::setSegmentCount(SegmentedMechInstanceState& instance, int count) {
    if (count < 1 || count > kMaxSegments) return false;
    while (instance.currentSegmentCount < count) {
        if (!addSegment(instance, instance.currentSegmentCount)) return false;
    }
    while (instance.currentSegmentCount > count) {
        if (!removeSegment(instance, instance.currentSegmentCount - 1)) return false;
    }
    return true;
}

bool MechFactory::updateSegmentProperties(SegmentedMechInstanceState& instance, int segmentIndex,
                                          const std::unordered_map<std::string, float>& properties) {
    if (segmentIndex < 0 || segmentIndex >= instance.currentSegmentCount) return false;
    const auto previous = instance.segmentOverrides[segmentIndex];
    auto overrides = previous;
    SegmentedMechParams probe = instance.params;
    bool applied = false;
    for (const auto& [key, value] : properties) {
        if (applySegmentProperty(probe, key, value)) {
            overrides[key] = value;
            applied = true;
        } else {
            Log::warn("Mech", "Unknown segment property '{}'", key);
        }
    }
    if (!applied) return false;
    instance.segmentOverrides[segmentIndex] = std::move(overrides);
    const SegmentedMechParams segmentParams = paramsForSegment(instance, segmentIndex);
    const auto errors = collectSegmentedErrors(segmentParams);
    if (!errors.empty()) {
        Log::warn("Mech", "Segment {} properties rejected: {}", segmentIndex, joinErrors(errors));
        instance.segmentOverrides[segmentIndex] = previous;
        return false;
    }
    destroySegment(instance.segments[segmentIndex]);
    instance.segments[segmentIndex] = createSegment(segmentParams, segmentIndex);
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::startSegmentedAnimation(SegmentedMechInstanceState& instance, const std::string& animationName) {
    if (animationName.empty()) return false;
    replaceOwned(instance.ownedAssets, instance.bundle.proceduralAnimation,
                 SegmentedSkeletonGenerator::createCustomAnimation(instance.params, animationName));
    instance.currentAnimation = animationName;
    instance.animationTime = 0.0f;
    instance.animationPaused = false;
    storeSegmentedInstance(instance);
    return instance.bundle.proceduralAnimation != 0;
}

bool MechFactory::setSegmentedAnimationProgress(SegmentedMechInstanceState& instance, float progress) {
    const float duration = animationDuration(instance.bundle.proceduralAnimation,
                                             1.0f / std::max(0.01f, instance.params.waveFrequency));
    instance.animationTime = std::clamp(progress, 0.0f, 1.0f) * duration;
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::pauseSegmentedAnimation(SegmentedMechInstanceState& instance) {
    if (instance.animationPaused) return false;
    instance.animationPaused = true;
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::resumeSegmentedAnimation(SegmentedMechInstanceState& instance) {
    if (!instance.animationPaused) return false;
    instance.animationPaused = false;
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::attachCockpit(SegmentedMechInstanceState& instance, const CockpitParams& cockpitParams) {
    if (!validateCockpitParams(cockpitParams)) return false;
    MeshHandle mesh = 0;
    TextureHandle texture = 0;
    if (!generateCockpitMesh(cockpitParams, mesh) || !generateCockpitTexture(cockpitParams, texture)) return false;
    auto& owned = instance.ownedAssets;
    replaceOwned(owned, instance.bundle.cockpitMesh, mesh);
    replaceOwned(owned, instance.bundle.cockpitTexture, texture);
    replaceOwned(owned, instance.bundle.cockpitMaterial, CockpitGenerator::buildCockpitMaterial(cockpitParams));
    instance.cockpitParams = cockpitParams;
    instance.cockpitAttached = true;
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::detachCockpit(SegmentedMechInstanceState& instance) {
    if (!instance.cockpitAttached) return false;
    auto& owned = instance.ownedAssets;
    replaceOwned(owned, instance.bundle.cockpitMesh, 0);
    replaceOwned(owned, instance.bundle.cockpitTexture, 0);
    replaceOwned(owned, instance.bundle.cockpitMaterial, 0);
    instance.cockpitAttached = false;
    storeSegmentedInstance(instance);
    return true;
}

bool MechFactory::updateCockpitParams(SegmentedMechInstanceState& instance, const CockpitParams& cockpitParams) {
    if (!instance.cockpitAttached) return false;
    return attachCockpit(instance, cockpitParams);
}

std::vector<std::future<SegmentedMechBundle>> MechFactory::generateSegmentedBatch(
    const std::vector<std::pair<SegmentedMechParams, CockpitParams>>& params) {
    std::vector<std::future<SegmentedMechBundle>> futures;
    futures.reserve(params.size());
    for (const auto& [mech, cockpit] : params) futures.push_back(generateSegmentedAsync(mech, cockpit));
    return futures;
}

void MechFactory::clearSegmentedCache() { m_segmentedCache.clear(); }
size_t MechFactory::getSegmentedCacheSize() const { return m_segmentedCache.size(); }
bool MechFactory::isSegmentedCached(const SegmentedMechParams& params) const {
    return m_segmentedCache.contains(segmentedCacheKey(params, CockpitParams{}, UIParams{}));
}

bool MechFactory::validateSegmentedParams(const SegmentedMechParams& params) {
    auto errors = collectSegmentedErrors(params);
    const bool ok = errors.empty();
    std::lock_guard<std::mutex> lock(validationMutex_);
    segmentedValidationErrors_ = std::move(errors);
    return ok;
}

bool MechFactory::validateCockpitParams(const CockpitParams& params) {
    auto errors = collectCockpitErrors(params);
    const bool ok = errors.empty();
    std::lock_guard<std::mutex> lock(validationMutex_);
    segmentedValidationErrors_ = std::move(errors);
    return ok;
}

std::vector<std::string> MechFactory::getSegmentedValidationErrors() const {
    std::lock_guard<std::mutex> lock(validationMutex_);
    return segmentedValidationErrors_;
}

SegmentedMechParams MechFactory::createSegmentedFromTemplate(const std::string& templateName) {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    auto it = segmentedMechTemplates_.find(templateName);
    if (it == segmentedMechTemplates_.end()) throw std::out_of_range("Unknown segmented mech template '" + templateName + "'");
    return it->second;
}

void MechFactory::registerSegmentedTemplate(const std::string& name, const SegmentedMechParams& template_) {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    segmentedMechTemplates_[name] = template_;
}

std::vector<std::string> MechFactory::getAvailableSegmentedTemplates() const {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    return sortedKeys(segmentedMechTemplates_);
}

CockpitParams MechFactory::createCockpitFromTemplate(const std::string& templateName) {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    auto it = cockpitTemplates_.find(templateName);
    if (it == cockpitTemplates_.end()) throw std::out_of_range("Unknown cockpit template '" + templateName + "'");
    return it->second;
}

void MechFactory::registerCockpitTemplate(const std::string& name, const CockpitParams& template_) {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    cockpitTemplates_[name] = template_;
}

std::vector<std::string> MechFactory::getAvailableCockpitTemplates() const {
    std::lock_guard<std::mutex> lock(segmentedTemplateMutex_);
    return sortedKeys(cockpitTemplates_);
}

// ============================================================================
// Centipede mechs
// ============================================================================

MeshHandle MechFactory::createCentipedeSegment(const CentipedeMechParams& params, int segmentIndex) {
    return CentipedeSegmentGenerator::createSegment(params, segmentIndex);
}
MeshHandle MechFactory::createCentipedeJoint(const CentipedeMechParams& params, int jointIndex) {
    return CentipedeJointGenerator::createJoint(params, jointIndex);
}
MeshHandle MechFactory::createCentipedeLeg(const CentipedeMechParams& params, int segmentIndex, int legIndex) {
    return CentipedeLegGenerator::buildSingleLeg(params, segmentIndex, legIndex);
}
MeshHandle MechFactory::createCentipedeCockpit(const CentipedeMechParams& params) {
    return CentipedeCockpitGenerator::buildCockpit(params);
}
std::vector<MeshHandle> MechFactory::createCentipedeWeapons(const CentipedeMechParams& params) {
    return CentipedeWeaponGenerator::buildWeapons(params);
}
MeshHandle MechFactory::createCentipedeSensorArray(const CentipedeMechParams& params) {
    return CentipedeSensorGenerator::buildSensorArray(params);
}
PhysicsHandle MechFactory::createCentipedeCollider(const CentipedeMechParams& params) {
    return CentipedeCollisionGenerator::buildMechCollider(params);
}
std::vector<MaterialHandle> MechFactory::createCentipedeMaterials(const CentipedeMechParams& params) {
    return CentipedeMaterialGenerator::assignMechMaterials(params);
}
std::vector<ParticleHandle> MechFactory::createCentipedeVFX(const CentipedeMechParams& params) {
    return CentipedeVFXGenerator::buildDamageAndThrusterFX(params);
}
std::vector<AudioHandle> MechFactory::createCentipedeAudio(const CentipedeMechParams& params) {
    return CentipedeAudioGenerator::buildMechSounds(params);
}

CentipedeMechBundle MechFactory::generateCentipedeBundle(const CentipedeMechParams& params) {
    if (!validateCentipedeParams(params)) {
        throw std::invalid_argument("Invalid centipede mech params '" + params.id + "': " +
                                    joinErrors(getCentipedeValidationErrors()));
    }
    const auto start = SteadyClock::now();
    CentipedeMechBundle b;
    for (int s = 0; s < params.segmentCount; ++s) b.segments.push_back(createCentipedeSegment(params, s));
    for (int j = 0; j + 1 < params.segmentCount; ++j) b.joints.push_back(createCentipedeJoint(params, j));
    for (int s = 0; s < params.segmentCount; ++s) {
        for (int l = 0; l < params.legsPerSegment; ++l) b.legs.push_back(createCentipedeLeg(params, s, l));
    }
    if (params.hasCockpit) b.cockpit = createCentipedeCockpit(params);
    b.weapons = createCentipedeWeapons(params);
    b.sensorArray = createCentipedeSensorArray(params);
    b.materials = createCentipedeMaterials(params);
    b.vfx = createCentipedeVFX(params);
    b.audio = createCentipedeAudio(params);
    b.collider = createCentipedeCollider(params);
    b.creationTime = std::chrono::system_clock::now();
    b.generationTime = elapsedMs(start);
    b.memoryUsage = assetMemory(b.segments) + assetMemory(b.joints) + assetMemory(b.legs) + assetMemory(b.weapons) +
                    assetMemory(b.materials) + assetMemory(b.vfx) + assetMemory(b.audio) +
                    assetMemory(std::vector<uint32_t>{b.cockpit, b.sensorArray, b.collider});
    b.gpuAccelerated = gpuAccelerationEnabled_;
    updateMetrics(b.generationTime, b.memoryUsage);
    Log::info("Mech", "Generated centipede mech '{}' ({} segments, {} legs) in {} ms", params.id, params.segmentCount,
              b.legs.size(), b.generationTime);
    return b;
}

std::future<CentipedeMechBundle> MechFactory::generateCentipedeAsync(const CentipedeMechParams& params) {
    const uint64_t key = params.hashKey();
    if (auto hit = m_centipedeCache.find(key)) {
        metrics_.cacheHits++;
        return readyFuture(std::move(*hit));
    }
    metrics_.cacheMisses++;
    return m_pool.enqueue([this, params, key] {
        CentipedeMechBundle b = generateCentipedeBundle(params);
        m_centipedeCache.insert(key, b);
        return b;
    });
}

CentipedeMechBundle MechFactory::generateCentipedeSync(const CentipedeMechParams& params) {
    const uint64_t key = params.hashKey();
    if (auto hit = m_centipedeCache.find(key)) {
        metrics_.cacheHits++;
        return *hit;
    }
    metrics_.cacheMisses++;
    CentipedeMechBundle b = generateCentipedeBundle(params);
    m_centipedeCache.insert(key, b);
    return b;
}

void MechFactory::storeCentipedeInstance(const CentipedeMechInstanceState& instance) {
    syncInstance(activeCentipedeInstances_, centipedeInstanceMutex_, instance);
}

void MechFactory::rebuildCentipedeLayout(CentipedeMechInstanceState& instance) {
    const auto& p = instance.params;
    const size_t segments = instance.segmentLegCounts.size();
    instance.segmentPositions.resize(segments);
    instance.segmentRotations.resize(segments, instance.rotation);
    for (size_t s = 0; s < segments; ++s) {
        instance.segmentPositions[s] = instance.position +
            instance.rotation * glm::vec3(0.0f, 0.0f, -static_cast<float>(s) * p.segmentLength);
        instance.segmentRotations[s] = instance.rotation;
    }
    size_t legCount = 0;
    for (int c : instance.segmentLegCounts) legCount += static_cast<size_t>(c);
    instance.legPositions.assign(legCount, glm::vec3(0.0f));
    instance.legRotations.assign(legCount, instance.rotation);
    updateCentipedeLegIK(instance);
}

CentipedeMechInstanceState MechFactory::createCentipedeInstance(const CentipedeMechParams& params) {
    CentipedeMechInstanceState s;
    s.bundle = generateCentipedeSync(params);
    s.id = makeInstanceId(params.id);
    s.params = params;
    s.segmentLegCounts.assign(static_cast<size_t>(params.segmentCount), params.legsPerSegment);
    rebuildCentipedeLayout(s);
    s.lastUpdate = std::chrono::system_clock::now();
    {
        std::lock_guard<std::mutex> lock(centipedeInstanceMutex_);
        activeCentipedeInstances_[s.id] = s;
    }
    trackInstanceCount();
    return s;
}

bool MechFactory::destroyCentipedeInstance(const CentipedeMechInstanceState& instance) {
    CentipedeMechInstanceState stored;
    {
        std::lock_guard<std::mutex> lock(centipedeInstanceMutex_);
        auto it = activeCentipedeInstances_.find(instance.id);
        if (it == activeCentipedeInstances_.end()) return false;
        stored = std::move(it->second);
        activeCentipedeInstances_.erase(it);
    }
    releaseAllOwned(stored.ownedAssets);
    trackInstanceCount();
    return true;
}

bool MechFactory::updateCentipedeInstance(CentipedeMechInstanceState& instance, float deltaTime) {
    if (!instance.isActive || deltaTime < 0.0f) return false;
    updateCentipedePhysics(instance, deltaTime);
    updateCentipedeSegmentPositions(instance);
    updateCentipedeAnimation(instance, deltaTime);
    updateCentipedeLegIK(instance);
    updateFrameStats(instance.frameCount, instance.averageFrameTime, deltaTime);
    instance.lastUpdate = std::chrono::system_clock::now();
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::updateCentipedePhysics(CentipedeMechInstanceState& instance, float deltaTime) {
    instance.velocity += instance.acceleration * deltaTime;
    instance.position += instance.velocity * deltaTime;
    integrateRotation(instance.rotation, instance.angularVelocity, deltaTime);
    return true;
}

bool MechFactory::updateCentipedeSegmentPositions(CentipedeMechInstanceState& instance) {
    const size_t segments = instance.segmentLegCounts.size();
    if (instance.segmentPositions.size() != segments) rebuildCentipedeLayout(instance);
    if (segments == 0) return false;
    // Follow-the-leader: the head tracks the body position, each segment trails the previous one.
    instance.segmentPositions[0] = instance.position;
    instance.segmentRotations[0] = instance.rotation;
    const float spacing = instance.params.segmentLength;
    for (size_t s = 1; s < segments; ++s) {
        const glm::vec3 toPrev = instance.segmentPositions[s - 1] - instance.segmentPositions[s];
        const float dist = glm::length(toPrev);
        if (dist > 1e-5f) {
            instance.segmentPositions[s] = instance.segmentPositions[s - 1] - toPrev / dist * spacing;
            instance.segmentRotations[s] = lookRotation(toPrev);
        } else {
            instance.segmentPositions[s] = instance.segmentPositions[s - 1] +
                instance.segmentRotations[s - 1] * glm::vec3(0.0f, 0.0f, -spacing);
            instance.segmentRotations[s] = instance.segmentRotations[s - 1];
        }
    }
    return true;
}

bool MechFactory::updateCentipedeLegIK(CentipedeMechInstanceState& instance) {
    const auto& p = instance.params;
    const float upper = p.upperLegLength;
    const float lower = p.lowerLegLength;
    const bool moving = isLocomotion(instance.currentAnimation);
    const float cycle = centipedeGaitDuration(instance.currentAnimation);
    size_t leg = 0;
    for (size_t s = 0; s < instance.segmentLegCounts.size() && s < instance.segmentPositions.size(); ++s) {
        const int count = instance.segmentLegCounts[s];
        for (int l = 0; l < count && leg < instance.legPositions.size(); ++l, ++leg) {
            const glm::quat segRot = instance.segmentRotations[s];
            const glm::vec3 hip = instance.segmentPositions[s] + segRot * centipedeLocalHip(p, l, count);
            const float side = (l % 2 == 0) ? -1.0f : 1.0f;
            // Metachronal gait: neighbouring segments and opposite legs are out of phase.
            const float phase = 2.0f * kPi * instance.animationTime / cycle + static_cast<float>(s) * kPi * 0.5f +
                                (side > 0.0f ? kPi : 0.0f);
            const float lift = moving ? std::max(0.0f, std::sin(phase)) * 0.25f * lower : 0.0f;
            const float stride = moving ? std::cos(phase) * 0.2f * upper : 0.0f;
            glm::vec3 foot = hip + segRot * glm::vec3(side * upper * 0.9f, -lower + lift, stride);
            // Two-bone IK: clamp the reach and derive the knee bend (law of cosines).
            const glm::vec3 reach = foot - hip;
            const float maxReach = (upper + lower) * 0.999f;
            float dist = glm::length(reach);
            if (dist > maxReach) {
                foot = hip + reach / dist * maxReach;
                dist = maxReach;
            }
            const float cosKnee = std::clamp((upper * upper + lower * lower - dist * dist) / (2.0f * upper * lower), -1.0f, 1.0f);
            const float kneeBend = kPi - std::acos(cosKnee);
            instance.legPositions[leg] = foot;
            instance.legRotations[leg] = segRot * glm::angleAxis(side * kneeBend, glm::vec3(0.0f, 0.0f, 1.0f));
        }
    }
    return true;
}

bool MechFactory::updateCentipedeAnimation(CentipedeMechInstanceState& instance, float deltaTime) {
    if (instance.animationPaused) return false;
    const float duration = centipedeGaitDuration(instance.currentAnimation);
    instance.animationTime += deltaTime;
    if (instance.animationTime > duration) {
        instance.animationTime = instance.animationLooping ? std::fmod(instance.animationTime, duration) : duration;
    }
    return true;
}

bool MechFactory::addCentipedeSegment(CentipedeMechInstanceState& instance, int index) {
    if (static_cast<int>(instance.segmentLegCounts.size()) >= kMaxCentipedeSegments) return false;
    index = std::clamp(index, 0, static_cast<int>(instance.segmentLegCounts.size()));
    instance.segmentLegCounts.insert(instance.segmentLegCounts.begin() + index, instance.params.legsPerSegment);
    rebuildCentipedeGeometry(instance);
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::removeCentipedeSegment(CentipedeMechInstanceState& instance, int index) {
    if (instance.segmentLegCounts.size() <= 1 || index < 0 || index >= static_cast<int>(instance.segmentLegCounts.size())) {
        return false;
    }
    instance.segmentLegCounts.erase(instance.segmentLegCounts.begin() + index);
    rebuildCentipedeGeometry(instance);
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::setCentipedeSegmentCount(CentipedeMechInstanceState& instance, int count) {
    if (count < 1 || count > kMaxCentipedeSegments) return false;
    instance.segmentLegCounts.resize(static_cast<size_t>(count), instance.params.legsPerSegment);
    rebuildCentipedeGeometry(instance);
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::updateCentipedeSegmentProperties(CentipedeMechInstanceState& instance, int segmentIndex,
                                                   const std::unordered_map<std::string, float>& properties) {
    if (segmentIndex < 0 || segmentIndex >= static_cast<int>(instance.segmentLegCounts.size())) return false;
    CentipedeMechParams updated = instance.params;
    std::vector<int> legCounts = instance.segmentLegCounts;
    bool applied = false;
    for (const auto& [key, value] : properties) {
        // Body dimensions are shared by all segments; the leg count is per segment.
        if (key == "segmentLength") updated.segmentLength = value;
        else if (key == "segmentRadius") updated.segmentRadius = value;
        else if (key == "jointRadius") updated.jointRadius = value;
        else if (key == "upperLegLength") updated.upperLegLength = value;
        else if (key == "lowerLegLength") updated.lowerLegLength = value;
        else if (key == "legsPerSegment") legCounts[segmentIndex] = std::clamp(static_cast<int>(value), 0, kMaxLegsPerSegment);
        else {
            Log::warn("Mech", "Unknown centipede segment property '{}'", key);
            continue;
        }
        applied = true;
    }
    if (!applied) return false;
    const auto errors = collectCentipedeErrors(updated);
    if (!errors.empty()) {
        Log::warn("Mech", "Centipede segment properties rejected: {}", joinErrors(errors));
        return false;
    }
    instance.params = updated;
    instance.segmentLegCounts = std::move(legCounts);
    rebuildCentipedeGeometry(instance);
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::addCentipedeLeg(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex) {
    if (segmentIndex < 0 || segmentIndex >= static_cast<int>(instance.segmentLegCounts.size())) return false;
    int& count = instance.segmentLegCounts[segmentIndex];
    if (count >= kMaxLegsPerSegment || legIndex < 0 || legIndex > count) return false;
    ++count;
    replaceOwnedList(instance.ownedAssets, instance.bundle.legs, buildCentipedeLegs(instance.params, instance.segmentLegCounts));
    replaceOwned(instance.ownedAssets, instance.bundle.collider, CentipedeCollisionGenerator::buildMechCollider(instance.params));
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::removeCentipedeLeg(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex) {
    if (segmentIndex < 0 || segmentIndex >= static_cast<int>(instance.segmentLegCounts.size())) return false;
    int& count = instance.segmentLegCounts[segmentIndex];
    if (legIndex < 0 || legIndex >= count) return false;
    --count;
    replaceOwnedList(instance.ownedAssets, instance.bundle.legs, buildCentipedeLegs(instance.params, instance.segmentLegCounts));
    rebuildCentipedeLayout(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::updateCentipedeLegProperties(CentipedeMechInstanceState& instance, int segmentIndex, int legIndex,
                                               const std::unordered_map<std::string, float>& properties) {
    if (segmentIndex < 0 || segmentIndex >= static_cast<int>(instance.segmentLegCounts.size())) return false;
    if (legIndex < 0 || legIndex >= instance.segmentLegCounts[segmentIndex]) return false;
    CentipedeMechParams legParams = instance.params;
    legParams.legsPerSegment = instance.segmentLegCounts[segmentIndex];
    bool applied = false;
    for (const auto& [key, value] : properties) {
        if (key == "upperLegLength") legParams.upperLegLength = value;
        else if (key == "lowerLegLength") legParams.lowerLegLength = value;
        else if (key == "jointRadius") legParams.jointRadius = value;
        else {
            Log::warn("Mech", "Unknown centipede leg property '{}'", key);
            continue;
        }
        applied = true;
    }
    if (!applied || legParams.upperLegLength <= 0.0f || legParams.lowerLegLength <= 0.0f || legParams.jointRadius <= 0.0f) {
        return false;
    }
    const int flat = legFlatIndex(instance, segmentIndex, legIndex);
    if (flat < 0 || flat >= static_cast<int>(instance.bundle.legs.size())) return false;
    replaceOwned(instance.ownedAssets, instance.bundle.legs[flat], createCentipedeLeg(legParams, segmentIndex, legIndex));
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::startCentipedeAnimation(CentipedeMechInstanceState& instance, const std::string& animationName) {
    if (animationName.empty()) return false;
    instance.currentAnimation = animationName;
    instance.animationTime = 0.0f;
    instance.animationPaused = false;
    instance.animationLooping = lower(animationName) != "attack";
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::setCentipedeAnimationProgress(CentipedeMechInstanceState& instance, float progress) {
    instance.animationTime = std::clamp(progress, 0.0f, 1.0f) * centipedeGaitDuration(instance.currentAnimation);
    updateCentipedeLegIK(instance);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::pauseCentipedeAnimation(CentipedeMechInstanceState& instance) {
    if (instance.animationPaused) return false;
    instance.animationPaused = true;
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::resumeCentipedeAnimation(CentipedeMechInstanceState& instance) {
    if (!instance.animationPaused) return false;
    instance.animationPaused = false;
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::attachCentipedeCockpit(CentipedeMechInstanceState& instance, const CockpitParams& cockpitParams) {
    if (!validateCockpitParams(cockpitParams)) return false;
    auto& p = instance.params;
    p.hasCockpit = true;
    p.cockpitWidth = cockpitParams.canopyRadius * 2.0f;
    p.cockpitHeight = cockpitParams.canopyHeight + cockpitParams.seatHeight;
    p.cockpitDepth = cockpitParams.seatDepth;
    p.displayCount = cockpitParams.displayCount;
    p.enableDisplays = cockpitParams.displayCount > 0;
    p.controlStyle = cockpitParams.holographicHUD ? "Holographic" : "Analog";
    p.cockpitPosition = cockpitParams.mountOffset;
    replaceOwned(instance.ownedAssets, instance.bundle.cockpit, createCentipedeCockpit(p));
    storeCentipedeInstance(instance);
    return instance.bundle.cockpit != 0;
}

bool MechFactory::detachCentipedeCockpit(CentipedeMechInstanceState& instance) {
    if (!instance.params.hasCockpit) return false;
    instance.params.hasCockpit = false;
    replaceOwned(instance.ownedAssets, instance.bundle.cockpit, 0);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::updateCentipedeCockpitParams(CentipedeMechInstanceState& instance, const CockpitParams& cockpitParams) {
    if (!instance.params.hasCockpit) return false;
    return attachCentipedeCockpit(instance, cockpitParams);
}

bool MechFactory::addCentipedeWeapon(CentipedeMechInstanceState& instance, const std::string& weaponType,
                                     int hardpointIndex) {
    if (hardpointIndex < 0 || hardpointIndex >= kMaxHardpoints || weaponType.empty()) return false;
    auto& weapons = instance.bundle.weapons;
    if (static_cast<int>(weapons.size()) <= hardpointIndex) weapons.resize(static_cast<size_t>(hardpointIndex) + 1, 0);
    if (weapons[hardpointIndex] != 0) return false;   // hardpoint occupied
    replaceOwned(instance.ownedAssets, weapons[hardpointIndex],
                 CentipedeWeaponGenerator::createWeaponBarrel(instance.params, weaponType));
    storeCentipedeInstance(instance);
    return weapons[hardpointIndex] != 0;
}

bool MechFactory::removeCentipedeWeapon(CentipedeMechInstanceState& instance, int hardpointIndex) {
    auto& weapons = instance.bundle.weapons;
    if (hardpointIndex < 0 || hardpointIndex >= static_cast<int>(weapons.size()) || weapons[hardpointIndex] == 0) return false;
    replaceOwned(instance.ownedAssets, weapons[hardpointIndex], 0);
    storeCentipedeInstance(instance);
    return true;
}

bool MechFactory::updateCentipedeSensorArray(CentipedeMechInstanceState& instance, const std::string& sensorType) {
    const std::string type = lower(sensorType);
    MeshHandle sensor = 0;
    if (type == "radar") sensor = CentipedeSensorGenerator::createRadarArray(instance.params);
    else if (type == "dish") sensor = CentipedeSensorGenerator::createSensorDish(instance.params);
    else if (type == "antenna") sensor = CentipedeSensorGenerator::createSensorAntenna(instance.params);
    else return false;
    instance.params.enableRadarArray = type == "radar";
    replaceOwned(instance.ownedAssets, instance.bundle.sensorArray, sensor);
    storeCentipedeInstance(instance);
    return true;
}

std::vector<std::future<CentipedeMechBundle>> MechFactory::generateCentipedeBatch(const std::vector<CentipedeMechParams>& params) {
    std::vector<std::future<CentipedeMechBundle>> futures;
    futures.reserve(params.size());
    for (const auto& p : params) futures.push_back(generateCentipedeAsync(p));
    return futures;
}

void MechFactory::clearCentipedeCache() { m_centipedeCache.clear(); }
size_t MechFactory::getCentipedeCacheSize() const { return m_centipedeCache.size(); }
bool MechFactory::isCentipedeCached(const CentipedeMechParams& params) const {
    return m_centipedeCache.contains(params.hashKey());
}

bool MechFactory::validateCentipedeParams(const CentipedeMechParams& params) {
    auto errors = collectCentipedeErrors(params);
    const bool ok = errors.empty();
    std::lock_guard<std::mutex> lock(validationMutex_);
    centipedeValidationErrors_ = std::move(errors);
    return ok;
}

std::vector<std::string> MechFactory::getCentipedeValidationErrors() const {
    std::lock_guard<std::mutex> lock(validationMutex_);
    return centipedeValidationErrors_;
}

CentipedeMechParams MechFactory::createCentipedeFromTemplate(const std::string& templateName) {
    std::lock_guard<std::mutex> lock(centipedeTemplateMutex_);
    auto it = centipedeMechTemplates_.find(templateName);
    if (it == centipedeMechTemplates_.end()) throw std::out_of_range("Unknown centipede template '" + templateName + "'");
    return it->second;
}

void MechFactory::registerCentipedeTemplate(const std::string& name, const CentipedeMechParams& template_) {
    std::lock_guard<std::mutex> lock(centipedeTemplateMutex_);
    centipedeMechTemplates_[name] = template_;
}

std::vector<std::string> MechFactory::getAvailableCentipedeTemplates() const {
    std::lock_guard<std::mutex> lock(centipedeTemplateMutex_);
    return sortedKeys(centipedeMechTemplates_);
}

bool MechFactory::spawnCentipedeMech(const CentipedeMechParams& params) {
    try {
        const auto instance = createCentipedeInstance(params);
        Log::info("Mech", "Spawned centipede mech instance '{}'", instance.id);
        return true;
    } catch (const std::exception& e) {
        Log::error("Mech", "Failed to spawn centipede mech '{}': {}", params.id, e.what());
        return false;
    }
}

CentipedeMechParams MechFactory::createCentipedeMechParams() {
    return CentipedeMechParams{};
}

std::string MechFactory::getCentipedeMechInfo(const CentipedeMechInstanceState& instance) {
    size_t legs = 0;
    for (int c : instance.segmentLegCounts) legs += static_cast<size_t>(c);
    size_t weapons = 0;
    for (auto w : instance.bundle.weapons) weapons += w != 0 ? 1 : 0;
    std::ostringstream out;
    out << "Centipede mech '" << instance.id << "' (" << instance.params.id << "): "
        << instance.segmentLegCounts.size() << " segments, " << legs << " legs, " << weapons << " weapons, "
        << "cockpit " << (instance.params.hasCockpit ? "attached" : "none") << ", "
        << "animation '" << instance.currentAnimation << "'" << (instance.animationPaused ? " (paused)" : "")
        << ", position (" << instance.position.x << ", " << instance.position.y << ", " << instance.position.z << ")";
    return out.str();
}

bool MechFactory::setCentipedeMechProperty(CentipedeMechInstanceState& instance, const std::string& property, float value) {
    auto& p = instance.params;
    bool geometry = false;
    if (property == "segmentLength") { p.segmentLength = value; geometry = true; }
    else if (property == "segmentRadius") { p.segmentRadius = value; geometry = true; }
    else if (property == "upperLegLength") { p.upperLegLength = value; geometry = true; }
    else if (property == "lowerLegLength") { p.lowerLegLength = value; geometry = true; }
    else if (property == "jointRadius") { p.jointRadius = value; geometry = true; }
    else if (property == "radarRange") {
        p.radarRange = value;
        replaceOwned(instance.ownedAssets, instance.bundle.sensorArray, CentipedeSensorGenerator::buildSensorArray(p));
    }
    else if (property == "positionX") instance.position.x = value;
    else if (property == "positionY") instance.position.y = value;
    else if (property == "positionZ") instance.position.z = value;
    else if (property == "velocityX") instance.velocity.x = value;
    else if (property == "velocityY") instance.velocity.y = value;
    else if (property == "velocityZ") instance.velocity.z = value;
    else if (property == "scale") instance.scale = glm::vec3(value);
    else if (property == "animationTime") instance.animationTime = value;
    else {
        Log::warn("Mech", "Unknown centipede property '{}'", property);
        return false;
    }
    if (geometry) {
        const auto errors = collectCentipedeErrors(p);
        if (!errors.empty()) {
            Log::warn("Mech", "Centipede property '{}' rejected: {}", property, joinErrors(errors));
            return false;
        }
        rebuildCentipedeGeometry(instance);
        rebuildCentipedeLayout(instance);
    }
    storeCentipedeInstance(instance);
    return true;
}

float MechFactory::getCentipedeMechProperty(const CentipedeMechInstanceState& instance, const std::string& property) {
    const auto& p = instance.params;
    if (property == "segmentLength") return p.segmentLength;
    if (property == "segmentRadius") return p.segmentRadius;
    if (property == "upperLegLength") return p.upperLegLength;
    if (property == "lowerLegLength") return p.lowerLegLength;
    if (property == "jointRadius") return p.jointRadius;
    if (property == "radarRange") return p.radarRange;
    if (property == "segmentCount") return static_cast<float>(instance.segmentLegCounts.size());
    if (property == "positionX") return instance.position.x;
    if (property == "positionY") return instance.position.y;
    if (property == "positionZ") return instance.position.z;
    if (property == "velocityX") return instance.velocity.x;
    if (property == "velocityY") return instance.velocity.y;
    if (property == "velocityZ") return instance.velocity.z;
    if (property == "scale") return instance.scale.x;
    if (property == "animationTime") return instance.animationTime;
    Log::warn("Mech", "Unknown centipede property '{}'", property);
    return std::numeric_limits<float>::quiet_NaN();
}

} // namespace Mechs
} // namespace MagiTech
