#pragma once

#include <string>
#include <vector>
#include <array>
#include <unordered_map>
#include <memory>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>
#include <xxhash.h>
#include "vendor/json/include/nlohmann/json.hpp"

namespace MiniJetGen {

// ---------------------------------------------------------------------------------------------
// Runtime asset data (CPU side). "Handles" own their data so they can be cached, serialized and
// uploaded by whichever renderer consumes the package.
// ---------------------------------------------------------------------------------------------

// Triangle mesh with optional skinning data (up to 4 bone influences per vertex)
struct MeshHandle {
    std::string name;
    std::vector<glm::vec3> positions;
    std::vector<glm::vec3> normals;
    std::vector<glm::vec2> uvs;
    std::vector<uint32_t> indices;
    std::vector<glm::uvec4> boneIndices;
    std::vector<glm::vec4> boneWeights;

    bool isValid() const { return !positions.empty() && !indices.empty(); }
    size_t vertexCount() const { return positions.size(); }
    size_t triangleCount() const { return indices.size() / 3; }
};

// Material: shader name plus named scalar / vector parameters
struct MaterialHandle {
    std::string name;
    std::string shader;
    std::unordered_map<std::string, float> floatParams;
    std::unordered_map<std::string, glm::vec3> vec3Params;
    float textureResolutionScale = 1.0f;   // 1 = full resolution textures
    int shaderComplexity = 3;              // 0 (cheapest) .. 3 (full feature set)

    bool isValid() const { return !name.empty(); }
};

struct Bone {
    std::string name;
    int parent = -1;                       // index into Skeleton::bones, -1 for the root
    glm::vec3 position{0.0f};              // bind position (model space)
};

struct Skeleton {
    std::vector<Bone> bones;

    bool isValid() const { return !bones.empty(); }
    int findBone(const std::string& boneName) const {
        for (size_t i = 0; i < bones.size(); ++i)
            if (bones[i].name == boneName) return static_cast<int>(i);
        return -1;
    }
};

struct Keyframe {
    float time = 0.0f;
    glm::vec3 translation{0.0f};
    glm::quat rotation{1.0f, 0.0f, 0.0f, 0.0f};
    glm::vec3 scale{1.0f};
};

struct AnimationTrack {
    std::string boneName;
    std::vector<Keyframe> keys;
};

struct Animation {
    std::string name;
    float duration = 0.0f;
    std::vector<AnimationTrack> tracks;
    Skeleton skeleton;                     // skeleton the tracks were authored for

    bool isValid() const { return !tracks.empty() && duration > 0.0f; }
    Animation clone() const { return *this; }
    const Skeleton& getSkeleton() const { return skeleton; }
    std::vector<AnimationTrack>& getTracks() { return tracks; }
    const std::vector<AnimationTrack>& getTracks() const { return tracks; }
};

struct PhysicsBody {
    enum class Shape { None, Box, Capsule, ConvexHull };
    std::string name;
    Shape shape = Shape::None;
    glm::vec3 halfExtents{0.5f};           // Box
    float radius = 0.5f;                   // Capsule
    float height = 1.0f;                   // Capsule (cylinder part)
    std::vector<glm::vec3> hullPoints;     // ConvexHull
    float mass = 0.0f;

    bool isValid() const { return shape != Shape::None; }
};

struct ThrusterNode {
    std::string name;
    float force = 0.0f;                    // Newtons at full throttle
    glm::vec3 direction{0.0f, 0.0f, -1.0f};
    float heatDistortion = 0.0f;
    glm::vec3 position{0.0f};

    bool isValid() const { return force > 0.0f; }
};

// Quality levels for LOD system
enum class Quality {
    Ultra = 0,
    High = 1,
    Medium = 2,
    Low = 3,
    COUNT
};

// Module types for the mini-jet mech
enum class ModuleType {
    Fuselage,
    Wing_Left,
    Wing_Right,
    Tailplane,
    Thruster_Main,
    Thruster_Aux,
    Cockpit,
    Weapon_Left,
    Weapon_Right,
    Energy_Core,
    COUNT
};

// Flight control surface types
enum class ControlSurfaceType {
    Aileron,
    Elevator,
    Rudder,
    Flap,
    Spoiler,
    COUNT
};

// Magitech material effect types
enum class MagitechEffectType {
    RuneGlow,
    EngineHeat,
    EnergyTrail,
    CanopyShield,
    WeaponCharge,
    COUNT
};

// Animation types for the mini-jet
enum class AnimationType {
    Takeoff,
    Hover,
    ForwardFlight,
    Banking,
    Landing,
    CockpitOpen,
    CockpitClose,
    WeaponDeploy,
    WeaponRetract,
    COUNT
};

// Module definition structure
struct ModuleDefinition {
    std::string id;
    ModuleType type = ModuleType::Fuselage;
    std::string meshPath;
    std::string attachBone;
    glm::vec3 offset = {0, 0, 0};
    glm::vec3 scale = {1, 1, 1};
    glm::quat rotation = glm::quat(1, 0, 0, 0);
    
    // Thruster-specific parameters
    float thrustForce = 0.0f;
    glm::vec3 thrustDirection = {0, 0, -1};
    float heatDistortion = 0.0f;
    
    // Control surface parameters
    ControlSurfaceType controlSurface = ControlSurfaceType::Aileron;
    float maxDeflection = 30.0f;
    
    // Weapon parameters
    std::string weaponType;
    float weaponRange = 0.0f;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, id.c_str(), id.length());
        XXH64_update(&state, &type, sizeof(type));
        XXH64_update(&state, meshPath.c_str(), meshPath.length());
        XXH64_update(&state, attachBone.c_str(), attachBone.length());
        XXH64_update(&state, &offset, sizeof(offset));
        XXH64_update(&state, &scale, sizeof(scale));
        XXH64_update(&state, &rotation, sizeof(rotation));
        XXH64_update(&state, &thrustForce, sizeof(thrustForce));
        XXH64_update(&state, &thrustDirection, sizeof(thrustDirection));
        XXH64_update(&state, &heatDistortion, sizeof(heatDistortion));
        XXH64_update(&state, &controlSurface, sizeof(controlSurface));
        XXH64_update(&state, &maxDeflection, sizeof(maxDeflection));
        XXH64_update(&state, weaponType.c_str(), weaponType.length());
        XXH64_update(&state, &weaponRange, sizeof(weaponRange));
        return XXH64_digest(&state);
    }
};

// Cockpit definition
struct CockpitDefinition {
    std::string meshPath;
    std::string attachBone;
    glm::vec3 seatPosition = {0, 0.6f, -0.2f};
    std::array<glm::vec3, 4> hudAnchors{}; // speedometer, targeting, altitude, energy
    std::string canopyMaterial;
    float canopyTransparency = 0.8f;
    bool enableHolographicHUD = true;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, meshPath.c_str(), meshPath.length());
        XXH64_update(&state, attachBone.c_str(), attachBone.length());
        XXH64_update(&state, &seatPosition, sizeof(seatPosition));
        XXH64_update(&state, hudAnchors.data(), sizeof(glm::vec3) * hudAnchors.size());
        XXH64_update(&state, canopyMaterial.c_str(), canopyMaterial.length());
        XXH64_update(&state, &canopyTransparency, sizeof(canopyTransparency));
        XXH64_update(&state, &enableHolographicHUD, sizeof(enableHolographicHUD));
        return XXH64_digest(&state);
    }
};

// Magitech material definitions
struct MagitechMaterials {
    struct RuneGlow {
        glm::vec3 emissiveColor = {0.2f, 0.8f, 1.0f};
        float pulseRate = 0.8f;
        float patternScale = 0.5f;
        float glowIntensity = 1.0f;
        
        size_t hashKey() const {
            XXH64_state_t state;
            XXH64_reset(&state, 0);
            XXH64_update(&state, &emissiveColor, sizeof(emissiveColor));
            XXH64_update(&state, &pulseRate, sizeof(pulseRate));
            XXH64_update(&state, &patternScale, sizeof(patternScale));
            XXH64_update(&state, &glowIntensity, sizeof(glowIntensity));
            return XXH64_digest(&state);
        }
    } runeGlow;
    
    struct EngineHeat {
        float distortionIntensity = 0.3f;
        float flickerRate = 10.0f;
        glm::vec3 heatColor = {1.0f, 0.3f, 0.1f};
        float maxTemperature = 1200.0f;
        
        size_t hashKey() const {
            XXH64_state_t state;
            XXH64_reset(&state, 0);
            XXH64_update(&state, &distortionIntensity, sizeof(distortionIntensity));
            XXH64_update(&state, &flickerRate, sizeof(flickerRate));
            XXH64_update(&state, &heatColor, sizeof(heatColor));
            XXH64_update(&state, &maxTemperature, sizeof(maxTemperature));
            return XXH64_digest(&state);
        }
    } engineHeat;
    
    struct EnergyTrail {
        glm::vec3 trailColor = {0.1f, 0.6f, 1.0f};
        float trailLength = 50.0f;
        float trailWidth = 2.0f;
        float fadeRate = 0.95f;
        
        size_t hashKey() const {
            XXH64_state_t state;
            XXH64_reset(&state, 0);
            XXH64_update(&state, &trailColor, sizeof(trailColor));
            XXH64_update(&state, &trailLength, sizeof(trailLength));
            XXH64_update(&state, &trailWidth, sizeof(trailWidth));
            XXH64_update(&state, &fadeRate, sizeof(fadeRate));
            return XXH64_digest(&state);
        }
    } energyTrail;
    
    size_t hashKey() const {
        return runeGlow.hashKey() ^ engineHeat.hashKey() ^ energyTrail.hashKey();
    }
};

// Flight parameters
struct FlightParameters {
    float maxSpeed = 350.0f;
    float maxAltitude = 12000.0f;
    float maxThrust = 12000.0f;
    float liftCoefficient = 1.2f;
    float dragCoefficient = 0.8f;
    float turnRate = 45.0f;
    float climbRate = 25.0f;
    
    // Control surface limits
    std::unordered_map<std::string, float> controlSurfaceLimits;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, &maxSpeed, sizeof(maxSpeed));
        XXH64_update(&state, &maxAltitude, sizeof(maxAltitude));
        XXH64_update(&state, &maxThrust, sizeof(maxThrust));
        XXH64_update(&state, &liftCoefficient, sizeof(liftCoefficient));
        XXH64_update(&state, &dragCoefficient, sizeof(dragCoefficient));
        XXH64_update(&state, &turnRate, sizeof(turnRate));
        XXH64_update(&state, &climbRate, sizeof(climbRate));
        return XXH64_digest(&state);
    }
};

// Animation definition
struct AnimationDefinition {
    std::string id;
    AnimationType type = AnimationType::Hover;
    std::string path;
    float speed = 1.0f;
    bool loop = true;
    float blendTime = 0.2f;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, id.c_str(), id.length());
        XXH64_update(&state, &type, sizeof(type));
        XXH64_update(&state, path.c_str(), path.length());
        XXH64_update(&state, &speed, sizeof(speed));
        XXH64_update(&state, &loop, sizeof(loop));
        XXH64_update(&state, &blendTime, sizeof(blendTime));
        return XXH64_digest(&state);
    }
};

// Physics definition
struct PhysicsDefinition {
    float totalMass = 800.0f;
    glm::vec3 centerOfMass = {0, 0, 0};
    
    // Per-module mass distribution
    std::unordered_map<std::string, float> moduleMass;
    
    // Joint constraints
    struct JointConstraint {
        float minAngle = -45.0f;
        float maxAngle = 45.0f;
        float damping = 0.1f;
        float stiffness = 100.0f;
    };
    std::unordered_map<std::string, JointConstraint> jointConstraints;
    
    // Collision shapes
    struct CollisionShape {
        enum class Type { Box, Capsule, ConvexHull } type = Type::Box;
        glm::vec3 size = {1, 1, 1};
        float radius = 0.5f;
        float height = 1.0f;
    };
    std::unordered_map<std::string, CollisionShape> collisionShapes;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, &totalMass, sizeof(totalMass));
        XXH64_update(&state, &centerOfMass, sizeof(centerOfMass));
        return XXH64_digest(&state);
    }
};

// LOD definition
struct LODDefinition {
    Quality quality = Quality::High;
    float meshDecimate = 0.0f;
    float materialDetail = 1.0f;
    int maxBoneInfluences = 4;
    bool enableShadows = true;
    bool enableReflections = true;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, &quality, sizeof(quality));
        XXH64_update(&state, &meshDecimate, sizeof(meshDecimate));
        XXH64_update(&state, &materialDetail, sizeof(materialDetail));
        XXH64_update(&state, &maxBoneInfluences, sizeof(maxBoneInfluences));
        XXH64_update(&state, &enableShadows, sizeof(enableShadows));
        XXH64_update(&state, &enableReflections, sizeof(enableReflections));
        return XXH64_digest(&state);
    }
};

// Main mini-jet definition
struct MiniJetDefinition {
    std::string name;
    std::string version = "1.0.0";
    
    std::vector<ModuleDefinition> modules;
    CockpitDefinition cockpit;
    MagitechMaterials magitechMaterials;
    FlightParameters flightParameters;
    std::vector<AnimationDefinition> animations;
    PhysicsDefinition physics;
    std::vector<LODDefinition> lods;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, name.c_str(), name.length());
        XXH64_update(&state, version.c_str(), version.length());
        
        for (const auto& module : modules) {
            { const size_t h = module.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        }
        
        { const size_t h = cockpit.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        { const size_t h = magitechMaterials.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        { const size_t h = flightParameters.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        
        for (const auto& anim : animations) {
            { const size_t h = anim.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        }
        
        { const size_t h = physics.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        
        for (const auto& lod : lods) {
            { const size_t h = lod.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        }
        
        return XXH64_digest(&state);
    }
};

// Runtime asset structures
struct ModuleAssets {
    std::array<MeshHandle, static_cast<size_t>(Quality::COUNT)> lodMeshes;
    std::array<MaterialHandle, static_cast<size_t>(Quality::COUNT)> lodMaterials;
    ThrusterNode thruster;
    PhysicsBody physicsBody;
};

struct MiniJetAsset {
    std::unordered_map<std::string, ModuleAssets> modules;
    Skeleton skeleton;
    std::unordered_map<std::string, Animation> animations;
    std::unordered_map<std::string, PhysicsBody> physicsBodies;
    MiniJetDefinition definition;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        { const size_t h = definition.hashKey(); XXH64_update(&state, &h, sizeof(h)); }
        return XXH64_digest(&state);
    }
};

// Package structure
struct MiniJetPackage {
    std::string name;
    std::string version;
    size_t definitionHash = 0;
    std::vector<std::string> meshFiles;
    std::vector<std::string> materialFiles;
    std::vector<std::string> animationFiles;
    std::vector<std::string> physicsFiles;
    std::string metadataFile;
    
    struct Metadata {
        MiniJetDefinition definition;
        std::unordered_map<std::string, size_t> fileHashes;
        std::string buildDate;
        std::string buildVersion;
    } metadata;
};

// Runtime instance
struct MiniJetInstance {
    std::shared_ptr<MiniJetAsset> asset;
    Quality currentLOD = Quality::High;
    std::string currentAnimation;
    float animationTime = 0.0f;
    glm::vec3 position = {0, 0, 0};
    glm::quat rotation = glm::quat(1, 0, 0, 0);
    glm::vec3 velocity = {0, 0, 0};
    float throttle = 0.0f;
    float altitude = 0.0f;
    float speed = 0.0f;
    
    glm::vec3 controlInput = {0, 0, 0};   // pitch, yaw, roll in [-1, 1]
    
    // Flight state
    bool isFlying = false;
    bool isLanding = false;
    bool isTakingOff = false;
    float flightTime = 0.0f;
    
    // Magitech effects
    float runeGlowIntensity = 1.0f;
    float engineHeatLevel = 0.0f;
    float energyTrailLength = 0.0f;
};

// Editor state
struct MiniJetEditorState {
    std::string selectedModule;
    std::string selectedAnimation;
    Quality previewLOD = Quality::High;
    float previewTime = 0.0f;
    bool showPhysics = false;
    bool showThrusters = true;
    bool showMagitechEffects = true;
    
    // Material tweaking
    glm::vec3 runeGlowColor = {0.2f, 0.8f, 1.0f};
    float runeGlowIntensity = 1.0f;
    float engineHeatDistortion = 0.3f;
    float energyTrailOpacity = 1.0f;
    
    // Flight parameters
    float maxSpeed = 350.0f;
    float maxAltitude = 12000.0f;
    float thrustForce = 12000.0f;
    
    // Module positioning
    glm::vec3 moduleOffset = {0, 0, 0};
    glm::vec3 moduleScale = {1, 1, 1};
    glm::quat moduleRotation = glm::quat(1, 0, 0, 0);
};

} // namespace MiniJetGen 
