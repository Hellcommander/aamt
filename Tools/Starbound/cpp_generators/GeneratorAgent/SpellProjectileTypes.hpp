#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace SpellProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using LightHandle = uint32_t;
using AudioHandle = uint32_t;
using ColliderHandle = uint32_t;

enum class SpellShape { Sphere, Cone, Torus, Ribbon, CustomMesh };
enum class TrailMode { Ribbon, Particles, SDFRibbon };
enum class ParticleStyle { Sparks, Smoke, Ember, Cosmic };
enum class LightFlicker { None, Sinusoidal, NoiseDriven, Pulse };

struct SpellParams {
    std::string id = "default_spell";
    SpellShape shape = SpellShape::Sphere;
    float baseRadius = 0.5f;
    float length = 1.0f;
    bool dynamicTess = false;
    uint64_t hashKey() const;
};

struct TrailParams {
    bool enableTrail = false;
    TrailMode mode = TrailMode::Ribbon;
    float trailLength = 5.0f;
    float width = 0.2f;
    float uptime = 2.0f;
    glm::vec4 headColor = {1,1,1,1};
    glm::vec4 tailColor = {1,1,1,0};
    uint64_t hashKey() const;
};

struct VFXParams {
    std::string shaderTemplate;
    std::vector<std::string> defines;
    float noiseIntensity = 0.1f;
    float pulseFreq = 1.0f;
    uint64_t hashKey() const;
};

struct ParticleParams {
    bool enableParticles = false;
    ParticleStyle style = ParticleStyle::Sparks;
    int maxCount = 100;
    float spawnRate = 50.0f;
    float lifeTime = 1.0f;
    glm::vec3 initialVelocity = {0,0,1};
    float spreadAngle = 15.0f;
    uint64_t hashKey() const;
};

struct LightParams {
    bool enableLight = false;
    glm::vec4 color = {1,1,1,1};
    float intensity = 1.0f;
    LightFlicker flickerMode = LightFlicker::None;
    float flickerSpeed = 1.0f;
    uint64_t hashKey() const;
};

struct AudioParams {
    bool playOnCast = false;
    std::string sfxFile;
    float volume = 1.0f;
    bool loop = false;
    uint64_t hashKey() const;
};

struct CollisionParams {
    bool enableCollider = false;
    float radius = 0.5f;
    bool meshCollider = false;
    bool triggerOnly = true;
    uint64_t hashKey() const;
};

struct SpellAssetBundle {
    MeshHandle geometry = 0;
    MeshHandle trailMesh = 0;
    ShaderHandle vfxShader = 0;
    ParticleHandle particleSystem = 0;
    LightHandle dynamicLight = 0;
    AudioHandle audioCue = 0;
    ColliderHandle collider = 0;
};

} // namespace SpellProjectiles
} // namespace MagiTech
