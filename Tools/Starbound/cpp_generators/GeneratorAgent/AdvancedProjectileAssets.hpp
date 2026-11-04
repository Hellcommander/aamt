#pragma once

/**
 * Asset and simulation registry for the advanced projectile family.
 *
 * Each create/load call allocates a shared GeneratorAgent asset handle
 * (MagiTech::nextAssetHandle) and records the descriptor under it, so a handle
 * returned in a MissileBundle / ShardBundle / ... can later be resolved back to
 * the parameters it was generated from (for export to OpenStarbound configs).
 */

#include "AdvancedProjectileTypes.hpp"
#include "core/rendering/Shaders.hpp"
#include <glm/glm.hpp>
#include <map>
#include <optional>
#include <string>
#include <variant>

namespace MagiTech {
namespace AdvancedProjectiles {

// ============================================================================
// SIMULATION DESCRIPTORS
// ============================================================================

struct GuidanceSimDesc {
    bool enableLockOn = true;
    float lockOnDelay = 0.5f;          // seconds
    float turnRate = 3.14159265f;      // radians per second
    float proximityFuseDist = 2.0f;
    std::string targetTag;
    float homingRadius = 50.0f;
    glm::vec3 targetPosition{0.0f};
};

struct PropulsionSimDesc {
    float maxThrust = 500.0f;
    float fuelCapacity = 5.0f;         // seconds of burn
    float dragCoefficient = 0.3f;
    float burnRate = 100.0f;           // thrust units consumed per second
};

struct TimerSimDesc {
    float fuseTime = 3.0f;
    float blastRadius = 8.0f;
    int shardCount = 12;
    float spreadAngle = 0.785398f;     // radians (cone half-angle)
    bool randomizeCount = true;
};

struct ArcSimDesc {
    float duration = 2.0f;
    float maxRange = 20.0f;
    float thickness = 0.1f;
    float branchProbability = 0.3f;
    int segmentCount = 50;
};

struct BoomerangSimDesc {
    float returnDelay = 1.5f;
    float returnSpeed = 15.0f;
    float liftCoefficient = 0.8f;
    float dragCoefficient = 0.4f;
    float spinRate = 20.0f;            // revolutions per second
};

struct ProjectileSimDesc {
    float launchSpeed = 25.0f;
    float maxRange = 30.0f;
    float gravityInfluence = 1.0f;
    float dragCoefficient = 0.3f;
};

struct ReelSimDesc {
    float retractionSpeed = 8.0f;
    bool enableElasticity = true;
    float springConstant = 100.0f;
    float maxRange = 30.0f;
};

using SimulationDesc = std::variant<GuidanceSimDesc, PropulsionSimDesc, TimerSimDesc, ArcSimDesc,
                                    BoomerangSimDesc, ProjectileSimDesc, ReelSimDesc>;

// ============================================================================
// TETHER / AUDIO / SHADER DESCRIPTORS
// ============================================================================

struct TetherDesc {
    float maxRange = 30.0f;
    int segmentCount = 60;
    bool enableElasticity = true;
    float springConstant = 100.0f;
    float retractionSpeed = 8.0f;
};

struct ProjectileAudioDesc {
    std::string filename;
    float volume = 1.0f;
    float pitch = 1.0f;
    bool looping = false;
};

struct ShaderProgramDesc {
    std::string name;                  // asset identifier, e.g. "shaders/missile_trail"
    std::string vertexSource;          // GLSL
    std::string fragmentSource;        // GLSL
    std::map<std::string, ShaderUniformValue> uniforms;
};

// ============================================================================
// REGISTRY API (thread-safe; called from factory worker threads)
// ============================================================================

namespace Assets {

SimulationHandle createGuidanceSim(const GuidanceSimDesc& desc);
SimulationHandle createPropulsionSim(const PropulsionSimDesc& desc);
SimulationHandle createTimerSim(const TimerSimDesc& desc);
SimulationHandle createArcSim(const ArcSimDesc& desc);
SimulationHandle createBoomerangSim(const BoomerangSimDesc& desc);
/** Linear ballistic flight; the handle comes from MagiTech::Simulation::createLinearProjectile. */
SimulationHandle createLinearProjectileSim(const ProjectileSimDesc& desc);
SimulationHandle createReelSim(const ReelSimDesc& desc);
std::optional<SimulationDesc> getSimulationDesc(SimulationHandle handle);

TetherHandle createTether(const TetherDesc& desc);
std::optional<TetherDesc> getTetherDesc(TetherHandle handle);

/** Returns 0 when desc.filename is empty (same contract as MagiTech::AudioSystem::load). */
AudioHandle loadAudio(const ProjectileAudioDesc& desc);
std::optional<ProjectileAudioDesc> getAudioDesc(AudioHandle handle);

/** Returns 0 when both sources are empty (same contract as MagiTech::Shaders::compile). */
ShaderHandle compileShaderProgram(const ShaderProgramDesc& desc);
std::optional<ShaderProgramDesc> getShaderProgramDesc(ShaderHandle handle);

void clearAll();

} // namespace Assets

} // namespace AdvancedProjectiles
} // namespace MagiTech
