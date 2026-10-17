#pragma once
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Particles {

using ParticleSystemHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ComputeShaderHandle = uint32_t;

// Enhanced Emitter Parameters
struct EmitterParams {
    std::string id;
    glm::vec3 position{0.0f};
    glm::vec3 rotation{0.0f};
    glm::vec3 scale{1.0f};
    float rate = 10.0f;
    float duration = 1.0f;          // < 0 means infinite
    bool loop = false;
    bool burstMode = false;
    int burstCount = 0;
    float burstInterval = 0.0f;
    bool gpuDriven = false;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Behavior Parameters
struct BehaviorParams {
    glm::vec3 initialVelocity{0.0f};
    glm::vec3 velocityVariance{0.0f};
    glm::vec3 acceleration{0.0f};
    float gravity = 0.0f;
    float drag = 0.0f;
    bool collision = false;
    bool turbulence = false;
    float turbulenceStrength = 0.0f;
    glm::vec3 wind{0.0f};
    bool attractorMode = false;
    glm::vec3 attractorPosition{0.0f};
    float attractorStrength = 0.0f;
    float attractorRadius = 0.0f;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Shape Parameters
struct ShapeParams {
    enum ShapeType {
        Point,
        Sphere,
        Box,
        Cone,
        Circle,
        Cylinder,
        Torus,
        CustomMesh
    } type = Point;

    glm::vec3 dimensions{0.0f};
    float angle = 0.0f;              // Cone half-angle in degrees
    float radius = 0.0f;
    float innerRadius = 0.0f;        // For torus
    std::string meshPath;            // For custom mesh
    bool randomRotation = false;
    bool alignToVelocity = false;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Lifetime Parameters
struct LifetimeParams {
    float minLife = 1.0f;
    float maxLife = 1.0f;
    glm::vec2 sizeRange{1.0f, 1.0f};
    bool sizeOverLife = false;
    bool fadeIn = false;
    bool fadeOut = false;
    float fadeInTime = 0.0f;
    float fadeOutTime = 0.0f;
    bool colorOverLife = false;
    glm::vec4 startColor{1.0f};
    glm::vec4 endColor{1.0f};
    bool velocityOverLife = false;
    glm::vec3 velocityStart{0.0f};
    glm::vec3 velocityEnd{0.0f};
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Render Parameters
struct RenderParams {
    std::string texturePath;
    bool animated = false;
    int frameCount = 1;
    float frameRate = 0.0f;
    glm::vec2 frameSize{1.0f, 1.0f};
    bool billboard = true;
    bool alignToCamera = false;
    bool softParticles = false;
    glm::vec4 colorOverLife[4] = {glm::vec4(1.0f), glm::vec4(1.0f), glm::vec4(1.0f), glm::vec4(1.0f)};  // Start, middle, end, custom
    bool alphaOverLife = false;
    bool additive = false;
    bool multiply = false;
    bool distortion = false;
    float distortionStrength = 0.0f;
    bool glow = false;
    float glowIntensity = 0.0f;
    std::string normalMapPath;
    std::string emissionMapPath;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced LOD Parameters
struct LODParams {
    std::vector<float> screenSizes;
    std::vector<float> rateScales;
    std::vector<float> qualityScales;
    bool adaptiveLOD = false;
    float adaptiveThreshold = 0.0f;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced LOD Data
struct LODData {
    std::vector<float> screenSizes;
    std::vector<float> rateScales;
    std::vector<float> qualityScales;
    std::vector<int> maxParticles;
    std::vector<float> cullDistances;
};

// Enhanced Particle Bundle
struct ParticleBundle {
    ParticleSystemHandle system = 0;
    LODData lodData;
    TextureHandle texture = 0;
    ShaderHandle shader = 0;
    ComputeShaderHandle computeShader = 0;
    std::map<std::string, std::string> metadata;
    std::chrono::system_clock::time_point creationTime{};
    size_t memoryUsage = 0;
    bool gpuAccelerated = false;
};

// Particle Effect Definition
struct ParticleEffectDefinition {
    std::string name;
    std::string description;
    std::string category;
    EmitterParams emitter;
    BehaviorParams behavior;
    ShapeParams shape;
    LifetimeParams lifetime;
    RenderParams render;
    LODParams lod;
    std::vector<std::string> tags;
    std::map<std::string, std::string> metadata;
    bool enableHotReload = false;
    bool enableCaching = true;
    uint64_t hashKey() const;
};

// Particle Effect Result
struct ParticleEffectResult {
    ParticleBundle bundle;
    ParticleEffectDefinition definition;
    std::chrono::system_clock::time_point processingTime{};
    bool success = false;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

// Particle System State
struct ParticleSystemState {
    uint32_t activeParticles = 0;
    uint32_t totalParticles = 0;
    float updateTime = 0.0f;
    float renderTime = 0.0f;
    float memoryUsage = 0.0f;
    bool isActive = false;
    bool isPaused = false;
    float currentTime = 0.0f;
    int currentLOD = 0;
};

// Particle Data Structure
struct Particle {
    glm::vec3 position;
    glm::vec3 velocity;
    glm::vec3 acceleration;
    glm::vec4 color;
    float size;
    float age;
    float lifetime;
    float rotation;
    float rotationSpeed;
    glm::vec2 uvOffset;
    bool active;

    Particle() : position(0), velocity(0), acceleration(0), color(1),
                 size(1), age(0), lifetime(1), rotation(0), rotationSpeed(0),
                 uvOffset(0), active(true) {}
};

// Particle Force Field
struct ParticleForceField {
    enum FieldType {
        Gravity,
        Wind,
        Turbulence,
        Attractor,
        Repulsor,
        Vortex,
        Custom
    } type = Gravity;

    std::string id;                  // Used to remove a field again
    glm::vec3 position{0.0f};
    glm::vec3 direction{0.0f, -1.0f, 0.0f};  // Wind direction / vortex axis
    float strength = 0.0f;
    float radius = 0.0f;             // <= 0 means unbounded
    float falloff = 1.0f;
    bool active = true;
    std::function<glm::vec3(const glm::vec3&, float)> customForce;
};

// Particle Collision
struct ParticleCollision {
    enum CollisionType {
        None,
        Sphere,
        Box,
        Plane,
        Mesh
    } type = None;

    std::string id;                  // Used to remove a collider again
    glm::vec3 position{0.0f};
    glm::vec3 dimensions{0.0f};      // Box extents; x = radius for spheres
    glm::vec3 normal{0.0f, 1.0f, 0.0f};
    float restitution = 0.5f;
    float friction = 0.0f;
    bool active = true;
    std::string meshPath;            // For mesh colliders
};

// Particle Trail
struct ParticleTrail {
    bool enabled = false;
    int maxPoints = 16;
    float fadeTime = 1.0f;
    float width = 0.1f;
    glm::vec4 color{1.0f};
    bool useTexture = false;
    std::string texturePath;
};

// Particle Sub-Emitter
struct ParticleSubEmitter {
    std::string effectName;
    float probability = 1.0f;        // Spawn chance per second of parent life
    glm::vec3 offset{0.0f};
    bool inheritVelocity = false;
    bool inheritRotation = false;
    bool inheritColor = false;
    bool inheritSize = false;
};

// Advanced Particle Parameters
struct AdvancedParticleParams {
    bool useGPU = false;
    bool useInstancing = false;
    bool useGeometryShaders = false;
    int maxParticles = 1000;
    int batchSize = 256;
    bool enableSorting = false;
    bool enableCulling = true;
    float cullDistance = 100.0f;
    bool enableOcclusion = false;
    bool enableDepthPrePass = false;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Particle Effect Template
struct ParticleEffectTemplate {
    std::string name;
    std::string description;
    std::vector<std::string> tags;
    ParticleEffectDefinition baseDefinition;
    std::vector<ParticleSubEmitter> subEmitters;
    std::vector<ParticleForceField> forceFields;
    std::vector<ParticleCollision> collisions;
    ParticleTrail trail;
    AdvancedParticleParams advanced;
    std::map<std::string, std::string> metadata;
    uint64_t hashKey() const;
};

// Particle Effect Instance
struct ParticleEffectInstance {
    std::string id;                  // Unique instance id (key for destroy/update)
    std::string templateName;
    ParticleEffectDefinition definition;
    glm::vec3 position{0.0f};
    glm::vec3 rotation{0.0f};
    glm::vec3 scale{1.0f};
    bool active = false;
    float startTime = 0.0f;
    float duration = 0.0f;
    int loopCount = 0;
    std::map<std::string, float> parameters;
    ParticleSystemState state;
};

// Particle Manager
struct ParticleManager {
    std::map<std::string, ParticleEffectTemplate> templates;
    std::map<std::string, ParticleEffectInstance> instances;
    std::vector<ParticleForceField> globalForceFields;
    std::vector<ParticleCollision> globalCollisions;
    bool enableGlobalForces = true;
    bool enableGlobalCollisions = true;
    float globalTime = 0.0f;
    int maxInstances = 256;
    size_t totalMemoryUsage = 0;
};

// Quality Settings
enum class ParticleQuality {
    Low,
    Medium,
    High,
    Ultra
};

// Performance Metrics
struct ParticlePerformanceMetrics {
    float frameTime = 0.0f;
    float updateTime = 0.0f;
    float renderTime = 0.0f;
    int drawCalls = 0;
    int activeParticles = 0;
    int totalParticles = 0;
    size_t memoryUsage = 0;
    float gpuTime = 0.0f;
    float cpuTime = 0.0f;
    int lodLevel = 0;
    bool gpuAccelerated = false;
};

} // namespace Particles
} // namespace MagiTech
