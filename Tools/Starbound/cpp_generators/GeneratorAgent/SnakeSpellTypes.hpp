#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace SnakeSpells {

using MeshHandle = uint32_t;
using SimulationHandle = uint32_t;
using MaterialSetup = uint32_t;
using ParticleHandle = uint32_t;
using AudioBundle = uint32_t;
using ColliderHandle = uint32_t;

// Body & Geometry
struct SnakeBodyParams {
    int segmentCount = 12;
    float totalLength = 4.0f;
    float segmentRadius = 0.2f;
    std::string scaleMaterial;
    bool dynamicMorph = true;
    uint64_t hashKey() const;
};

// Flight & Motion
struct MotionParams {
    bool curlEnabled = true;
    float curlFrequency = 2.0f;
    float curlAmplitude = 0.5f;
    bool homing = true;
    float homingTurnRate = 60.0f;
    uint64_t hashKey() const;
};

// Scale Visual Effects
struct ScaleVFXParams {
    bool enableGlow = true;
    glm::vec4 glowColor = {0,1,0,1};
    float glowIntensity = 1.5f;
    bool pulsate = true;
    float pulsateSpeed = 3.0f;
    uint64_t hashKey() const;
};

// Particle Effects
struct ParticleParams {
    bool venomDrip = true;
    float dripRate = 5.0f;
    glm::vec4 venomColor = {0,0.8,0,1};
    bool smokeTrail = true;
    float smokeDensity = 10.0f;
    uint64_t hashKey() const;
};

// Audio Effects
struct AudioParams {
    bool hissOnLaunch = true;
    std::string hissFile;
    float hissVolume = 0.7f;
    bool rattleOnImpact = true;
    std::string rattleFile;
    uint64_t hashKey() const;
};

// Collision
struct CollisionParams {
    int capsuleSegments = 12;
    float capsuleRadius = 0.2f;
    bool enableCCD = true;
    uint64_t hashKey() const;
};

// Asset Bundle
struct SnakeBundle {
    MeshHandle mesh = 0;
    SimulationHandle motionSim = 0;
    MaterialSetup vfx = 0;
    ParticleHandle particles = 0;
    AudioBundle audio = 0;
    ColliderHandle collider = 0;
};

} // namespace SnakeSpells
} // namespace MagiTech
