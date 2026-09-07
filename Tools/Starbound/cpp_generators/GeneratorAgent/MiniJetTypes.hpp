#pragma once

#include <string>
#include <vector>
#include <array>
#include <unordered_map>
#include <memory>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>
#include <xxhash.h>
#include <yaml-cpp/yaml.h>

namespace MiniJetGen {

// Forward declarations
struct MeshHandle;
struct MaterialHandle;
struct Skeleton;
struct Animation;
struct PhysicsBody;
struct ThrusterNode;

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
    ModuleType type;
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
    glm::vec3 hudAnchors[4]; // speedometer, targeting, altitude, energy
    std::string canopyMaterial;
    float canopyTransparency = 0.8f;
    bool enableHolographicHUD = true;
    
    size_t hashKey() const {
        XXH64_state_t state;
        XXH64_reset(&state, 0);
        XXH64_update(&state, meshPath.c_str(), meshPath.length());
        XXH64_update(&state, attachBone.c_str(), attachBone.length());
        XXH64_update(&state, &seatPosition, sizeof(seatPosition));
        XXH64_update(&state, hudAnchors, sizeof(hudAnchors));
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
    AnimationType type;
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
        enum class Type { Box, Capsule, ConvexHull } type;
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
    Quality quality;
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
            XXH64_update(&state, &module.hashKey(), sizeof(size_t));
        }
        
        XXH64_update(&state, &cockpit.hashKey(), sizeof(size_t));
        XXH64_update(&state, &magitechMaterials.hashKey(), sizeof(size_t));
        XXH64_update(&state, &flightParameters.hashKey(), sizeof(size_t));
        
        for (const auto& anim : animations) {
            XXH64_update(&state, &anim.hashKey(), sizeof(size_t));
        }
        
        XXH64_update(&state, &physics.hashKey(), sizeof(size_t));
        
        for (const auto& lod : lods) {
            XXH64_update(&state, &lod.hashKey(), sizeof(size_t));
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
        XXH64_update(&state, &definition.hashKey(), sizeof(size_t));
        return XXH64_digest(&state);
    }
};

// Package structure
struct MiniJetPackage {
    std::string name;
    std::string version;
    size_t definitionHash;
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
