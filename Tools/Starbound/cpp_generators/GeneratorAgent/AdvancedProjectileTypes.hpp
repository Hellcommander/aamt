#pragma once

#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace AdvancedProjectiles {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using AudioHandle = uint32_t;
using SimulationHandle = uint32_t;
using TetherHandle = uint32_t;

// ============================================================================
// GUIDED MISSILE SYSTEM
// ============================================================================

struct GuidanceParams {
    bool enableLockOn = true;
    float lockOnDelay = 0.5f;         // seconds before acquiring target
    float turnRateDegPerSec = 180.0f; // maximum steering angular speed
    float proximityFuseDist = 2.0f;   // detonation distance threshold
    uint64_t hashKey() const;
};

struct PropulsionParams {
    float maxThrust = 500.0f;         // force magnitude
    float fuelCapacity = 5.0f;        // total burn time
    float dragCoefficient = 0.3f;     // aerodynamic drag
    uint64_t hashKey() const;
};

struct TargetParams {
    std::string targetTag;             // actor identifier
    float homingRadius = 50.0f;       // search sphere radius
    glm::vec3 targetPosition;         // current target position
    uint64_t hashKey() const;
};

struct MissileBundle {
    MeshHandle mesh = 0;
    ShaderHandle vfxShader = 0;
    ParticleHandle particleSys = 0;
    AudioHandle humAudio = 0;
    SimulationHandle guidanceSim = 0;
    SimulationHandle thrustSim = 0;
};

// ============================================================================
// SHARD-BURST GRENADE SYSTEM
// ============================================================================

struct GrenadeParams {
    float fuseTime = 3.0f;            // seconds until detonation
    float blastRadius = 8.0f;
    int shardCount = 12;
    float spreadAngleDeg = 45.0f;     // cone half-angle
    bool randomizeCount = true;
    uint64_t hashKey() const;
};

struct ShardParams {
    std::string meshType = "spike";
    std::string materialType = "metal";
    float minVelocity = 10.0f;
    float maxVelocity = 25.0f;
    float lifeTime = 2.0f;
    uint64_t hashKey() const;
};

struct ShardBundle {
    MeshHandle bodyMesh = 0;
    std::vector<MeshHandle> shards;
    SimulationHandle timerSim = 0;
    ParticleHandle explosionVFX = 0;
    AudioHandle explosionAudio = 0;
};

// ============================================================================
// ARC BEAM SYSTEM
// ============================================================================

struct BeamParams {
    float duration = 2.0f;            // seconds
    float maxRange = 20.0f;
    float thickness = 0.1f;
    float branchProbability = 0.3f;   // 0–1 chance per segment
    int segmentCount = 50;
    uint64_t hashKey() const;
};

struct GlowParams {
    glm::vec3 innerColor = glm::vec3(0.8f, 0.9f, 1.0f);
    glm::vec3 outerColor = glm::vec3(0.2f, 0.4f, 0.8f);
    float pulseFrequency = 10.0f;     // Hz
    float intensity = 1.0f;
    uint64_t hashKey() const;
};

struct BeamBundle {
    MeshHandle beamMesh = 0;
    SimulationHandle waveSim = 0;
    ShaderHandle shader = 0;
    AudioHandle crackleAudio = 0;
};

// ============================================================================
// BOOMERANG DISC SYSTEM
// ============================================================================

struct BoomerangParams {
    float returnDelay = 1.5f;         // time before return phase
    float returnSpeed = 15.0f;
    float liftCoefficient = 0.8f;
    float dragCoefficient = 0.4f;
    float spinRateRPM = 1200.0f;
    uint64_t hashKey() const;
};

struct BoomerangBundle {
    MeshHandle mesh = 0;
    SimulationHandle flightSim = 0;
    AudioHandle whooshAudio = 0;
    ParticleHandle trailVFX = 0;
};

// ============================================================================
// GRAPNEL HOOK SYSTEM
// ============================================================================

struct GrapnelParams {
    float maxRange = 30.0f;
    float launchSpeed = 25.0f;
    float retractionSpeed = 8.0f;
    bool enableElasticity = true;
    float springConstant = 100.0f;    // for elastic tether
    uint64_t hashKey() const;
};

struct HookParams {
    std::string meshType = "hook";
    std::string materialType = "metal";
    bool autoDetach = false;
    float hookStrength = 1000.0f;
    uint64_t hashKey() const;
};

struct GrapnelBundle {
    MeshHandle hookMesh = 0;
    TetherHandle tether = 0;
    SimulationHandle launchSim = 0;
    SimulationHandle retractSim = 0;
    AudioHandle reelAudio = 0;
};

// ============================================================================
// FACTORY INTERFACES
// ============================================================================

class GuidedMissileFactory;
class ShardGrenadeFactory;
class ArcBeamFactory;
class BoomerangFactory;
class GrapnelFactory;

} // namespace AdvancedProjectiles
} // namespace MagiTech 
