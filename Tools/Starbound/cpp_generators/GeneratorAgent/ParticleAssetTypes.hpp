#pragma once
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
    glm::vec3 position;
    glm::vec3 rotation;
    glm::vec3 scale;
    float rate;
    float duration;
    bool loop;
    bool burstMode;
    int burstCount;
    float burstInterval;
    bool gpuDriven;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Behavior Parameters
struct BehaviorParams {
    glm::vec3 initialVelocity;
    glm::vec3 velocityVariance;
    glm::vec3 acceleration;
    float gravity;
    float drag;
    bool collision;
    bool turbulence;
    float turbulenceStrength;
    glm::vec3 wind;
    bool attractorMode;
    glm::vec3 attractorPosition;
    float attractorStrength;
    float attractorRadius;
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
    } type;
    
    glm::vec3 dimensions;
    float angle;
    float radius;
    float innerRadius;  // For torus
    std::string meshPath;  // For custom mesh
    bool randomRotation;
    bool alignToVelocity;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Lifetime Parameters
struct LifetimeParams {
    float minLife;
    float maxLife;
    glm::vec2 sizeRange;
    bool sizeOverLife;
    bool fadeIn;
    bool fadeOut;
    float fadeInTime;
    float fadeOutTime;
    bool colorOverLife;
    glm::vec4 startColor;
    glm::vec4 endColor;
    bool velocityOverLife;
    glm::vec3 velocityStart;
    glm::vec3 velocityEnd;
    std::map<std::string, float> customParameters;
    uint64_t hashKey() const;
};

// Enhanced Render Parameters
struct RenderParams {
    std::string texturePath;
    bool animated;
    int frameCount;
    float frameRate;
    glm::vec2 frameSize;
    bool billboard;
    bool alignToCamera;
    bool softParticles;
    glm::vec4 colorOverLife[4];  // Start, middle, end, custom
    bool alphaOverLife;
    bool additive;
    bool multiply;
    bool distortion;
    float distortionStrength;
    bool glow;
    float glowIntensity;
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
    bool adaptiveLOD;
    float adaptiveThreshold;
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
    ParticleSystemHandle system;
    LODData lodData;
    TextureHandle texture;
    ShaderHandle shader;
    ComputeShaderHandle computeShader;
    std::map<std::string, std::string> metadata;
    std::chrono::system_clock::time_point creationTime;
    size_t memoryUsage;
    bool gpuAccelerated;
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
    bool enableHotReload;
    bool enableCaching;
    uint64_t hashKey() const;
};

// Particle Effect Result
struct ParticleEffectResult {
    ParticleBundle bundle;
    ParticleEffectDefinition definition;
    std::chrono::system_clock::time_point processingTime;
    bool success;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

// Particle System State
struct ParticleSystemState {
    uint32_t activeParticles;
    uint32_t totalParticles;
    float updateTime;
    float renderTime;
    float memoryUsage;
    bool isActive;
    bool isPaused;
    float currentTime;
    int currentLOD;
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
    } type;
    
    glm::vec3 position;
    glm::vec3 direction;
    float strength;
    float radius;
    float falloff;
    bool active;
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
    } type;
    
    glm::vec3 position;
    glm::vec3 dimensions;
    glm::vec3 normal;
    float restitution;
    float friction;
    bool active;
};

// Particle Trail
struct ParticleTrail {
    bool enabled;
    int maxPoints;
    float fadeTime;
    float width;
    glm::vec4 color;
    bool useTexture;
    std::string texturePath;
};

// Particle Sub-Emitter
struct ParticleSubEmitter {
    std::string effectName;
    float probability;
    glm::vec3 offset;
    bool inheritVelocity;
    bool inheritRotation;
    bool inheritColor;
    bool inheritSize;
};

// Advanced Particle Parameters
struct AdvancedParticleParams {
    bool useGPU;
    bool useInstancing;
    bool useGeometryShaders;
    int maxParticles;
    int batchSize;
    bool enableSorting;
    bool enableCulling;
    float cullDistance;
    bool enableOcclusion;
    bool enableDepthPrePass;
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
    std::string templateName;
    ParticleEffectDefinition definition;
    glm::vec3 position;
    glm::vec3 rotation;
    glm::vec3 scale;
    bool active;
    float startTime;
    float duration;
    int loopCount;
    std::map<std::string, float> parameters;
    ParticleSystemState state;
};

// Particle Manager
struct ParticleManager {
    std::map<std::string, ParticleEffectTemplate> templates;
    std::map<std::string, ParticleEffectInstance> instances;
    std::vector<ParticleForceField> globalForceFields;
    std::vector<ParticleCollision> globalCollisions;
    bool enableGlobalForces;
    bool enableGlobalCollisions;
    float globalTime;
    int maxInstances;
    size_t totalMemoryUsage;
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
    float frameTime;
    float updateTime;
    float renderTime;
    int drawCalls;
    int activeParticles;
    int totalParticles;
    size_t memoryUsage;
    float gpuTime;
    float cpuTime;
    int lodLevel;
    bool gpuAccelerated;
};

} // namespace Particles
} // namespace MagiTech
