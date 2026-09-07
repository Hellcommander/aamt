#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace GyroProjectiles {

using MeshHandle = uint32_t;
using SimulationHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;
using ColliderHandle = uint32_t;

enum class GyroShape { Disc, Ring, Spindle, CustomMesh };
enum class TrailType { Ribbon, Streaks, Particles };
enum class ParticleStyle { Sparks, Smoke, Sparkle };
enum class FlickerMode { None, Sinusoidal, NoiseDriven };

struct GyroParams {
    std::string id = "default_gyro";
    GyroShape shape = GyroShape::Disc;
    float radius = 0.5f;
    float thickness = 0.1f;
    bool hollow = false;
    bool dynamicTess = false;
    uint64_t hashKey() const;
};

struct FlightParams {
    float initialSpeed = 50.0f;
    float spinRateRPM = 3600.0f;
    float precessionRateDeg = 30.0f;
    float stabilityFactor = 0.9f;
    bool gravityEnabled = true;
    float gravityScale = 1.0f;
    uint64_t hashKey() const;
};

struct TrailParams {
    bool enableTrail = true;
    TrailType type = TrailType::Ribbon;
    float length = 2.0f;
    float width = 0.1f;
    glm::vec4 headColor = {1,1,1,1};
    glm::vec4 tailColor = {1,1,1,0};
    float uvScrollSpeed = 1.0f;
    uint64_t hashKey() const;
};

struct VFXParams {
    std::string shaderTemplate;
    std::vector<std::string> defines;
    float glowIntensity = 1.0f;
    float flickerSpeed = 5.0f;
    FlickerMode flickerMode = FlickerMode::None;
    uint64_t hashKey() const;
};

struct ParticleParams {
    bool enableParticles = true;
    ParticleStyle style = ParticleStyle::Sparks;
    int count = 100;
    float spawnRate = 200.0f;
    float lifeTime = 0.5f;
    glm::vec3 velocityMin = {-1,-1,-1};
    glm::vec3 velocityMax = {1,1,1};
    uint64_t hashKey() const;
};

struct AudioParams {
    bool playOnLaunch = true;
    std::string humFile;
    std::string impactFile;
    float volume = 1.0f;
    float pitchVariance = 0.0f;
    uint64_t hashKey() const;
};

struct CollisionParams {
    bool enableCollider = true;
    bool meshCollider = false;
    float radius = 0.5f;
    bool triggerOnly = false;
    bool enableCCD = true;
    uint64_t hashKey() const;
};

struct GyroAssetBundle {
    MeshHandle mesh = 0;
    SimulationHandle flightSim = 0;
    MeshHandle trailMesh = 0;
    ShaderHandle vfxShader = 0;
    ParticleHandle particleSys = 0;
    AudioHandle humAudio = 0;
    AudioHandle impactAudio = 0;
    ColliderHandle collider = 0;
};

} // namespace GyroProjectiles
} // namespace MagiTech
