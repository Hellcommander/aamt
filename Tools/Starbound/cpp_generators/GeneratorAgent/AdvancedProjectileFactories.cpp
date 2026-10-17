#include "AdvancedProjectileFactories.hpp"
#include "AdvancedProjectileAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/particles/ParticleSystem.hpp"
#include "vendor/xxhash/xxhash.h"
#include <glm/gtc/constants.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <algorithm>
#include <cmath>
#include <random>
#include <string>
#include <type_traits>
#include <vector>

namespace MagiTech {
namespace AdvancedProjectiles {

namespace {

constexpr const char* kLogCategory = "AdvancedProjectile";

/**
 * Serializes fields one by one before hashing, so struct padding (bools next
 * to floats) and std::string internals never leak into the cache key.
 */
class KeyHasher {
public:
    template <typename T>
        requires std::is_trivially_copyable_v<T>
    KeyHasher& add(const T& value) {
        const auto* bytes = reinterpret_cast<const unsigned char*>(&value);
        m_bytes.insert(m_bytes.end(), bytes, bytes + sizeof(T));
        return *this;
    }

    KeyHasher& add(const std::string& value) {
        add(static_cast<uint64_t>(value.size()));
        m_bytes.insert(m_bytes.end(), value.begin(), value.end());
        return *this;
    }

    uint64_t digest() const { return XXH64(m_bytes.data(), m_bytes.size(), 0); }

private:
    std::vector<unsigned char> m_bytes;
};

// Shared vertex stage for the projectile effect shaders.
constexpr const char* kEffectVertexShader = R"(#version 330 core
layout(location = 0) in vec3 inPosition;
layout(location = 2) in vec2 inUV;
uniform mat4 uModelViewProjection;
out vec2 vUV;
void main() {
    vUV = inUV;
    gl_Position = uModelViewProjection * vec4(inPosition, 1.0);
}
)";

constexpr const char* kMissileTrailFragmentShader = R"(#version 330 core
in vec2 vUV;
out vec4 fragColor;
uniform float thrustIntensity;
uniform float fuelLevel;
uniform float dragCoeff;
void main() {
    float core = 1.0 - abs(vUV.x * 2.0 - 1.0);
    float fade = 1.0 - vUV.y;
    float heat = clamp(thrustIntensity, 0.0, 2.0);
    vec3 color = mix(vec3(0.5, 0.2, 0.0), vec3(1.0, 0.8, 0.3), clamp(core * heat, 0.0, 1.0));
    float alpha = core * fade * clamp(fuelLevel, 0.0, 1.0) / (1.0 + dragCoeff);
    fragColor = vec4(color, alpha);
}
)";

constexpr const char* kBeamGlowFragmentShader = R"(#version 330 core
in vec2 vUV;
out vec4 fragColor;
uniform vec3 innerColor;
uniform vec3 outerColor;
uniform float pulseFrequency;
uniform float intensity;
uniform float uTime;
void main() {
    float d = abs(vUV.y * 2.0 - 1.0);
    float glow = pow(1.0 - d, 3.0);
    float pulse = 0.75 + 0.25 * sin(uTime * pulseFrequency * 6.2831853);
    vec3 color = mix(outerColor, innerColor, glow);
    fragColor = vec4(color * intensity * pulse, glow * pulse);
}
)";

} // namespace

// ============================================================================
// HASH FUNCTION IMPLEMENTATIONS
// ============================================================================

uint64_t GuidanceParams::hashKey() const {
    return KeyHasher().add(enableLockOn).add(lockOnDelay).add(turnRateDegPerSec).add(proximityFuseDist).digest();
}

uint64_t PropulsionParams::hashKey() const {
    return KeyHasher().add(maxThrust).add(fuelCapacity).add(dragCoefficient).digest();
}

uint64_t TargetParams::hashKey() const {
    return KeyHasher().add(targetTag).add(targetPosition).add(homingRadius).digest();
}

uint64_t GrenadeParams::hashKey() const {
    return KeyHasher().add(fuseTime).add(blastRadius).add(shardCount).add(spreadAngleDeg).add(randomizeCount).digest();
}

uint64_t ShardParams::hashKey() const {
    return KeyHasher()
        .add(meshType)
        .add(materialType)
        .add(minVelocity)
        .add(maxVelocity)
        .add(lifeTime)
        .digest();
}

uint64_t BeamParams::hashKey() const {
    return KeyHasher().add(duration).add(maxRange).add(thickness).add(branchProbability).add(segmentCount).digest();
}

uint64_t GlowParams::hashKey() const {
    return KeyHasher().add(innerColor).add(outerColor).add(pulseFrequency).add(intensity).digest();
}

uint64_t BoomerangParams::hashKey() const {
    return KeyHasher()
        .add(returnDelay)
        .add(returnSpeed)
        .add(liftCoefficient)
        .add(dragCoefficient)
        .add(spinRateRPM)
        .digest();
}

uint64_t GrapnelParams::hashKey() const {
    return KeyHasher()
        .add(maxRange)
        .add(launchSpeed)
        .add(retractionSpeed)
        .add(enableElasticity)
        .add(springConstant)
        .digest();
}

uint64_t HookParams::hashKey() const {
    return KeyHasher().add(meshType).add(materialType).add(autoDetach).add(hookStrength).digest();
}

// ============================================================================
// GUIDED MISSILE FACTORY IMPLEMENTATION
// ============================================================================

void GuidedMissileFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void GuidedMissileFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<MissileBundle> GuidedMissileFactory::generateAsync(
    const GuidanceParams& guidance,
    const PropulsionParams& propulsion,
    const TargetParams& target) {

    return m_pool.enqueue([guidance, propulsion, target]() {
        MissileBundle bundle;
        bundle.mesh = MeshGen::buildMissileMesh(guidance, propulsion);
        bundle.vfxShader = ShaderGen::compileTrailShader(propulsion);
        bundle.particleSys = ParticleGen::buildEngineExhaust(propulsion);
        bundle.humAudio = AudioGen::loadHumAudio(propulsion);
        bundle.guidanceSim = GuidanceSim::setup(guidance, target);
        bundle.thrustSim = PropulsionSim::setup(propulsion);
        return bundle;
    });
}

MeshHandle GuidedMissileFactory::MeshGen::buildMissileMesh(const GuidanceParams& g, const PropulsionParams& p) {
    Log::info(kLogCategory, "Building guided missile mesh");

    Mesh missileMesh;

    // Missile body (cylinder with tapered nose)
    const float bodyLength = p.fuelCapacity * 0.8f;
    const float bodyRadius = p.maxThrust * 0.001f;

    missileMesh.append(Primitives::createCylinder(bodyRadius, bodyLength, 12));

    // Nose cone
    const Mesh nose = Primitives::createCone(bodyRadius * 1.2f, bodyLength * 0.3f, 12);
    const glm::mat4 noseTransform = glm::translate(glm::mat4(1.0f),
        glm::vec3(0, bodyLength * 0.5f + bodyLength * 0.15f, 0));
    missileMesh.append(nose, noseTransform);

    // Lock-on seeker: a sensor dome on the nose tip for missiles that acquire targets
    if (g.enableLockOn) {
        const Mesh seeker = Primitives::createSphere(bodyRadius * 0.5f, 8);
        const glm::mat4 seekerTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(0, bodyLength * 0.5f + bodyLength * 0.3f, 0));
        missileMesh.append(seeker, seekerTransform);
    }

    // Fins for stability
    for (int i = 0; i < 4; ++i) {
        const float angle = i * glm::pi<float>() * 0.5f;
        const Mesh fin = Primitives::createBox(bodyLength * 0.2f, bodyRadius * 0.1f, bodyRadius * 0.8f);
        glm::mat4 finTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(0, -bodyLength * 0.3f, 0));
        finTransform = glm::rotate(finTransform, angle, glm::vec3(0, 1, 0));
        missileMesh.append(fin, finTransform);
    }

    // Engine nozzle
    const Mesh nozzle = Primitives::createCone(bodyRadius * 0.8f, bodyLength * 0.2f, 8);
    glm::mat4 nozzleTransform = glm::translate(glm::mat4(1.0f),
        glm::vec3(0, -bodyLength * 0.5f - bodyLength * 0.1f, 0));
    nozzleTransform = glm::rotate(nozzleTransform, glm::pi<float>(), glm::vec3(1, 0, 0));
    missileMesh.append(nozzle, nozzleTransform);

    missileMesh.optimize();
    return missileMesh.upload();
}

ShaderHandle GuidedMissileFactory::ShaderGen::compileTrailShader(const PropulsionParams& p) {
    Log::info(kLogCategory, "Compiling missile trail shader");

    // Shader for the engine exhaust trail
    ShaderProgramDesc desc;
    desc.name = "shaders/missile_trail";
    desc.vertexSource = kEffectVertexShader;
    desc.fragmentSource = kMissileTrailFragmentShader;
    desc.uniforms = {
        {"thrustIntensity", p.maxThrust / 1000.0f},
        {"fuelLevel", p.fuelCapacity},
        {"dragCoeff", p.dragCoefficient}
    };

    return Assets::compileShaderProgram(desc);
}

ParticleHandle GuidedMissileFactory::ParticleGen::buildEngineExhaust(const PropulsionParams& p) {
    Log::info(kLogCategory, "Building engine exhaust particle system");

    ParticleSystemDesc desc;
    desc.maxParticles = 100;
    desc.emissionRate = p.maxThrust * 0.1f;
    desc.particleLifetime = 0.5f;
    desc.startColor = glm::vec4(1.0f, 0.5f, 0.0f, 1.0f);
    desc.endColor = glm::vec4(0.5f, 0.2f, 0.0f, 0.0f);
    desc.startSize = 0.1f;
    desc.endSize = 0.5f;
    const glm::vec3 exhaustVelocity(0, -p.maxThrust * 0.01f, 0);
    desc.velocityMin = exhaustVelocity;
    desc.velocityMax = exhaustVelocity;

    return ParticleSystem::create(desc);
}

AudioHandle GuidedMissileFactory::AudioGen::loadHumAudio(const PropulsionParams& p) {
    Log::info(kLogCategory, "Loading missile hum audio");

    ProjectileAudioDesc desc;
    desc.filename = "audio/missile_hum.wav";
    desc.volume = p.maxThrust / 1000.0f;
    desc.looping = true;
    desc.pitch = 1.0f + (p.fuelCapacity * 0.1f);

    return Assets::loadAudio(desc);
}

SimulationHandle GuidedMissileFactory::GuidanceSim::setup(const GuidanceParams& g, const TargetParams& t) {
    Log::info(kLogCategory, "Setting up missile guidance simulation");

    GuidanceSimDesc desc;
    desc.enableLockOn = g.enableLockOn;
    desc.lockOnDelay = g.lockOnDelay;
    desc.turnRate = glm::radians(g.turnRateDegPerSec);
    desc.proximityFuseDist = g.proximityFuseDist;
    desc.targetTag = t.targetTag;
    desc.homingRadius = t.homingRadius;
    desc.targetPosition = t.targetPosition;

    return Assets::createGuidanceSim(desc);
}

SimulationHandle GuidedMissileFactory::PropulsionSim::setup(const PropulsionParams& p) {
    Log::info(kLogCategory, "Setting up missile propulsion simulation");

    PropulsionSimDesc desc;
    desc.maxThrust = p.maxThrust;
    desc.fuelCapacity = p.fuelCapacity;
    desc.dragCoefficient = p.dragCoefficient;
    // A zero-capacity tank burns nothing (avoids dividing by zero).
    desc.burnRate = p.fuelCapacity > 0.0f ? p.maxThrust / p.fuelCapacity : 0.0f;

    return Assets::createPropulsionSim(desc);
}

// ============================================================================
// SHARD-BURST GRENADE FACTORY IMPLEMENTATION
// ============================================================================

void ShardGrenadeFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void ShardGrenadeFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<ShardBundle> ShardGrenadeFactory::generateAsync(
    const GrenadeParams& grenade,
    const ShardParams& shard) {

    return m_pool.enqueue([grenade, shard]() {
        ShardBundle bundle;
        bundle.bodyMesh = MeshGen::buildGrenadeBody(grenade);
        bundle.shards = FragmentGen::generateShards(shard, grenade);
        bundle.timerSim = TimerSim::setup(grenade);
        bundle.explosionVFX = VFXGen::buildBlast(grenade);
        bundle.explosionAudio = AudioGen::loadExplosionAudio(grenade);
        return bundle;
    });
}

MeshHandle ShardGrenadeFactory::MeshGen::buildGrenadeBody(const GrenadeParams& g) {
    Log::info(kLogCategory, "Building grenade body mesh");

    Mesh grenadeMesh;

    // Main grenade body (sphere with ridges)
    const float radius = g.blastRadius * 0.1f;
    grenadeMesh.append(Primitives::createSphere(radius, 16));

    // Safety ridges around body
    for (int i = 0; i < 8; ++i) {
        const float angle = i * glm::pi<float>() * 0.25f;
        const Mesh ridge = Primitives::createBox(radius * 0.3f, radius * 0.05f, radius * 0.1f);
        glm::mat4 ridgeTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(std::cos(angle) * radius * 0.8f, 0, std::sin(angle) * radius * 0.8f));
        ridgeTransform = glm::rotate(ridgeTransform, angle, glm::vec3(0, 1, 0));
        grenadeMesh.append(ridge, ridgeTransform);
    }

    // Fuse mechanism
    const Mesh fuse = Primitives::createCylinder(radius * 0.1f, radius * 0.3f, 8);
    const glm::mat4 fuseTransform = glm::translate(glm::mat4(1.0f),
        glm::vec3(0, radius + radius * 0.15f, 0));
    grenadeMesh.append(fuse, fuseTransform);

    grenadeMesh.optimize();
    return grenadeMesh.upload();
}

std::vector<MeshHandle> ShardGrenadeFactory::MeshGen::generateShards(const ShardParams& s, int count, float spreadAngleDeg) {
    std::vector<MeshHandle> shards;
    if (count <= 0) return shards;
    shards.reserve(static_cast<size_t>(count));

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> angleDist(0.0f, glm::two_pi<float>());
    std::uniform_real_distribution<float> heightDist(-spreadAngleDeg, spreadAngleDeg);

    for (int i = 0; i < count; ++i) {
        // Create shard geometry based on type
        Mesh shardGeometry;
        if (s.meshType == "spike") {
            shardGeometry = Primitives::createCone(s.minVelocity * 0.01f, s.maxVelocity * 0.02f, 6);
        } else if (s.meshType == "shard") {
            shardGeometry = Primitives::createBox(s.minVelocity * 0.01f, s.maxVelocity * 0.02f, s.minVelocity * 0.01f);
        } else {
            shardGeometry = Primitives::createSphere(s.minVelocity * 0.01f, 6);
        }

        // Orient the shard along a random direction inside the spread cone
        glm::mat4 orientation = glm::rotate(glm::mat4(1.0f), angleDist(gen), glm::vec3(0, 1, 0));
        orientation = glm::rotate(orientation, glm::radians(heightDist(gen)), glm::vec3(1, 0, 0));

        Mesh shardMesh;
        shardMesh.append(shardGeometry, orientation);
        shardMesh.optimize();
        shards.push_back(shardMesh.upload());
    }

    return shards;
}

std::vector<MeshHandle> ShardGrenadeFactory::FragmentGen::generateShards(const ShardParams& s, const GrenadeParams& g) {
    Log::info(kLogCategory, "Generating {} shard meshes", g.shardCount);
    return MeshGen::generateShards(s, g.shardCount, g.spreadAngleDeg);
}

SimulationHandle ShardGrenadeFactory::TimerSim::setup(const GrenadeParams& g) {
    Log::info(kLogCategory, "Setting up grenade timer simulation");

    TimerSimDesc desc;
    desc.fuseTime = g.fuseTime;
    desc.blastRadius = g.blastRadius;
    desc.shardCount = g.shardCount;
    desc.spreadAngle = glm::radians(g.spreadAngleDeg);
    desc.randomizeCount = g.randomizeCount;

    return Assets::createTimerSim(desc);
}

ParticleHandle ShardGrenadeFactory::VFXGen::buildBlast(const GrenadeParams& g) {
    Log::info(kLogCategory, "Building explosion VFX");

    ParticleSystemDesc desc;
    desc.maxParticles = 200;
    desc.emissionRate = 1000.0f;
    desc.particleLifetime = 2.0f;
    desc.startColor = glm::vec4(1.0f, 0.8f, 0.0f, 1.0f);
    desc.endColor = glm::vec4(0.5f, 0.2f, 0.0f, 0.0f);
    desc.startSize = 0.5f;
    desc.endSize = 2.0f;
    // Radial burst: particles reach the blast radius by the end of their life
    const float blastSpeed = g.blastRadius / desc.particleLifetime;
    desc.velocityMin = glm::vec3(-blastSpeed);
    desc.velocityMax = glm::vec3(blastSpeed);

    return ParticleSystem::create(desc);
}

AudioHandle ShardGrenadeFactory::AudioGen::loadExplosionAudio(const GrenadeParams& g) {
    Log::info(kLogCategory, "Loading explosion audio");

    ProjectileAudioDesc desc;
    desc.filename = "audio/explosion.wav";
    desc.volume = g.blastRadius / 10.0f;
    desc.looping = false;
    desc.pitch = 1.0f;

    return Assets::loadAudio(desc);
}

// ============================================================================
// ARC BEAM FACTORY IMPLEMENTATION
// ============================================================================

void ArcBeamFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void ArcBeamFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<BeamBundle> ArcBeamFactory::generateAsync(
    const BeamParams& beam,
    const GlowParams& glow) {

    return m_pool.enqueue([beam, glow]() {
        BeamBundle bundle;
        bundle.beamMesh = BeamGen::createSegments(beam);
        bundle.waveSim = ArcSim::setup(beam);
        bundle.shader = ShaderGen::compileBeamShader(glow);
        bundle.crackleAudio = AudioGen::loadCrackleAudio(beam);
        return bundle;
    });
}

MeshHandle ArcBeamFactory::BeamGen::createSegments(const BeamParams& b) {
    Log::info(kLogCategory, "Creating arc beam segments");

    Mesh beamMesh;
    if (b.segmentCount <= 0) return beamMesh.upload();

    // Create segmented beam with branching
    const float segmentLength = b.maxRange / static_cast<float>(b.segmentCount);

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> branchDist(0.0f, 1.0f);

    for (int i = 0; i < b.segmentCount; ++i) {
        const Mesh segment = Primitives::createCylinder(b.thickness, segmentLength, 8);

        // Add jitter to segment position
        const float jitter = (i % 3) * 0.1f;
        const glm::mat4 segmentTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(i * segmentLength + jitter, 0, 0));

        beamMesh.append(segment, segmentTransform);

        // Random branching
        if (i > 0 && i < b.segmentCount - 1 && branchDist(gen) < b.branchProbability) {
            const Mesh branch = Primitives::createCylinder(b.thickness * 0.5f, segmentLength * 0.7f, 6);
            glm::mat4 branchTransform = glm::translate(glm::mat4(1.0f),
                glm::vec3(i * segmentLength, 0, 0));
            branchTransform = glm::rotate(branchTransform, glm::pi<float>() * 0.25f, glm::vec3(0, 0, 1));
            beamMesh.append(branch, branchTransform);
        }
    }

    beamMesh.optimize();
    return beamMesh.upload();
}

SimulationHandle ArcBeamFactory::ArcSim::setup(const BeamParams& b) {
    Log::info(kLogCategory, "Setting up arc beam simulation");

    ArcSimDesc desc;
    desc.duration = b.duration;
    desc.maxRange = b.maxRange;
    desc.thickness = b.thickness;
    desc.branchProbability = b.branchProbability;
    desc.segmentCount = b.segmentCount;

    return Assets::createArcSim(desc);
}

ShaderHandle ArcBeamFactory::ShaderGen::compileBeamShader(const GlowParams& g) {
    Log::info(kLogCategory, "Compiling beam glow shader");

    ShaderProgramDesc desc;
    desc.name = "shaders/beam_glow";
    desc.vertexSource = kEffectVertexShader;
    desc.fragmentSource = kBeamGlowFragmentShader;
    desc.uniforms = {
        {"innerColor", g.innerColor},
        {"outerColor", g.outerColor},
        {"pulseFrequency", g.pulseFrequency},
        {"intensity", g.intensity},
        {"uTime", 0.0f}
    };

    return Assets::compileShaderProgram(desc);
}

AudioHandle ArcBeamFactory::AudioGen::loadCrackleAudio(const BeamParams& b) {
    Log::info(kLogCategory, "Loading arc crackle audio");

    ProjectileAudioDesc desc;
    desc.filename = "audio/arc_crackle.wav";
    desc.volume = b.thickness * 10.0f;
    desc.looping = true;
    desc.pitch = 1.0f + (b.branchProbability * 0.5f);

    return Assets::loadAudio(desc);
}

// ============================================================================
// BOOMERANG FACTORY IMPLEMENTATION
// ============================================================================

void BoomerangFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void BoomerangFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<BoomerangBundle> BoomerangFactory::generateAsync(const BoomerangParams& params) {
    return m_pool.enqueue([params]() {
        BoomerangBundle bundle;
        bundle.mesh = MeshGen::buildBoomerangBlade(params);
        bundle.flightSim = BoomerangSim::setup(params);
        bundle.whooshAudio = AudioGen::loadWhooshAudio(params);
        bundle.trailVFX = VFXGen::buildTrailVFX(params);
        return bundle;
    });
}

MeshHandle BoomerangFactory::MeshGen::buildBoomerangBlade(const BoomerangParams& b) {
    Log::info(kLogCategory, "Building boomerang blade mesh");

    Mesh boomerangMesh;

    // Create curved boomerang blade
    const float bladeLength = b.returnSpeed * 0.1f;
    const float bladeWidth = bladeLength * 0.2f;
    const float bladeThickness = bladeWidth * 0.1f;

    // Main blade (curved)
    for (int i = 0; i < 8; ++i) {
        const float t = i / 7.0f;
        const float curve = std::sin(t * glm::pi<float>()) * bladeLength * 0.3f;

        const Mesh segment = Primitives::createBox(bladeLength / 8.0f, bladeThickness, bladeWidth);
        glm::mat4 segmentTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(i * bladeLength / 8.0f, curve, 0));
        segmentTransform = glm::rotate(segmentTransform, t * glm::pi<float>() * 0.5f, glm::vec3(0, 0, 1));
        boomerangMesh.append(segment, segmentTransform);
    }

    // Center grip
    boomerangMesh.append(Primitives::createCylinder(bladeWidth * 0.3f, bladeThickness * 2.0f, 8));

    boomerangMesh.optimize();
    return boomerangMesh.upload();
}

SimulationHandle BoomerangFactory::BoomerangSim::setup(const BoomerangParams& b) {
    Log::info(kLogCategory, "Setting up boomerang flight simulation");

    BoomerangSimDesc desc;
    desc.returnDelay = b.returnDelay;
    desc.returnSpeed = b.returnSpeed;
    desc.liftCoefficient = b.liftCoefficient;
    desc.dragCoefficient = b.dragCoefficient;
    desc.spinRate = b.spinRateRPM / 60.0f; // Convert to Hz

    return Assets::createBoomerangSim(desc);
}

AudioHandle BoomerangFactory::AudioGen::loadWhooshAudio(const BoomerangParams& b) {
    Log::info(kLogCategory, "Loading boomerang whoosh audio");

    ProjectileAudioDesc desc;
    desc.filename = "audio/boomerang_whoosh.wav";
    desc.volume = b.returnSpeed / 20.0f;
    desc.looping = true;
    desc.pitch = 1.0f + (b.spinRateRPM / 2000.0f);

    return Assets::loadAudio(desc);
}

ParticleHandle BoomerangFactory::VFXGen::buildTrailVFX(const BoomerangParams& b) {
    Log::info(kLogCategory, "Building boomerang trail VFX");

    ParticleSystemDesc desc;
    desc.maxParticles = 50;
    desc.emissionRate = b.returnSpeed * 2.0f;
    desc.particleLifetime = 1.0f;
    desc.startColor = glm::vec4(0.8f, 0.8f, 0.8f, 0.8f);
    desc.endColor = glm::vec4(0.5f, 0.5f, 0.5f, 0.0f);
    desc.startSize = 0.05f;
    desc.endSize = 0.2f;
    // Trail particles stay where they were emitted
    desc.velocityMin = glm::vec3(0.0f);
    desc.velocityMax = glm::vec3(0.0f);

    return ParticleSystem::create(desc);
}

// ============================================================================
// GRAPNEL FACTORY IMPLEMENTATION
// ============================================================================

void GrapnelFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool.start(num_threads);
    m_initialized = true;
}

void GrapnelFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.stop();
    m_initialized = false;
}

std::future<GrapnelBundle> GrapnelFactory::generateAsync(
    const GrapnelParams& grapnel,
    const HookParams& hook) {

    return m_pool.enqueue([grapnel, hook]() {
        GrapnelBundle bundle;
        bundle.hookMesh = MeshGen::buildGrapnelHook(hook);
        bundle.tether = TetherGen::createRope(grapnel);
        bundle.launchSim = ProjectileSim::setupLinear(grapnel);
        bundle.retractSim = ReelSim::setup(grapnel);
        bundle.reelAudio = AudioGen::loadReelAudio(grapnel);
        return bundle;
    });
}

MeshHandle GrapnelFactory::MeshGen::buildGrapnelHook(const HookParams& h) {
    Log::info(kLogCategory, "Building grapnel hook mesh");

    Mesh hookMesh;

    // Hook body
    const float hookSize = h.hookStrength * 0.001f;
    hookMesh.append(Primitives::createCylinder(hookSize * 0.3f, hookSize * 2.0f, 8));

    // Hook tip (curved)
    const Mesh tip = Primitives::createTorus(hookSize * 0.8f, hookSize * 0.2f, 12, 6);
    glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f),
        glm::vec3(0, hookSize, 0));
    tipTransform = glm::rotate(tipTransform, glm::pi<float>() * 0.5f, glm::vec3(1, 0, 0));
    hookMesh.append(tip, tipTransform);

    // Barbs for grip
    for (int i = 0; i < 3; ++i) {
        const float angle = i * glm::pi<float>() * 2.0f / 3.0f;
        const Mesh barb = Primitives::createCone(hookSize * 0.1f, hookSize * 0.3f, 4);
        glm::mat4 barbTransform = glm::translate(glm::mat4(1.0f),
            glm::vec3(0, hookSize * 0.5f, 0));
        barbTransform = glm::rotate(barbTransform, angle, glm::vec3(0, 1, 0));
        barbTransform = glm::rotate(barbTransform, glm::pi<float>() * 0.25f, glm::vec3(1, 0, 0));
        hookMesh.append(barb, barbTransform);
    }

    hookMesh.optimize();
    return hookMesh.upload();
}

TetherHandle GrapnelFactory::TetherGen::createRope(const GrapnelParams& g) {
    Log::info(kLogCategory, "Creating grapnel tether rope");

    TetherDesc desc;
    desc.maxRange = g.maxRange;
    desc.segmentCount = std::max(1, static_cast<int>(g.maxRange / 0.5f));
    desc.enableElasticity = g.enableElasticity;
    desc.springConstant = g.springConstant;
    desc.retractionSpeed = g.retractionSpeed;

    return Assets::createTether(desc);
}

SimulationHandle GrapnelFactory::ProjectileSim::setupLinear(const GrapnelParams& g) {
    Log::info(kLogCategory, "Setting up grapnel launch simulation");

    ProjectileSimDesc desc;
    desc.launchSpeed = g.launchSpeed;
    desc.maxRange = g.maxRange;
    desc.gravityInfluence = 0.3f;
    desc.dragCoefficient = 0.2f;

    return Assets::createLinearProjectileSim(desc);
}

SimulationHandle GrapnelFactory::ReelSim::setup(const GrapnelParams& g) {
    Log::info(kLogCategory, "Setting up grapnel reel simulation");

    ReelSimDesc desc;
    desc.retractionSpeed = g.retractionSpeed;
    desc.enableElasticity = g.enableElasticity;
    desc.springConstant = g.springConstant;
    desc.maxRange = g.maxRange;

    return Assets::createReelSim(desc);
}

AudioHandle GrapnelFactory::AudioGen::loadReelAudio(const GrapnelParams& g) {
    Log::info(kLogCategory, "Loading grapnel reel audio");

    ProjectileAudioDesc desc;
    desc.filename = "audio/grapnel_reel.wav";
    desc.volume = g.retractionSpeed / 10.0f;
    desc.looping = true;
    desc.pitch = 1.0f;

    return Assets::loadAudio(desc);
}

// ============================================================================
// ADVANCED PROJECTILE MANAGER IMPLEMENTATION
// ============================================================================

AdvancedProjectileManager::AdvancedProjectileManager() {
    m_missileFactory = std::make_unique<GuidedMissileFactory>();
    m_grenadeFactory = std::make_unique<ShardGrenadeFactory>();
    m_beamFactory = std::make_unique<ArcBeamFactory>();
    m_boomerangFactory = std::make_unique<BoomerangFactory>();
    m_grapnelFactory = std::make_unique<GrapnelFactory>();
}

AdvancedProjectileManager::~AdvancedProjectileManager() {
    shutdown();
}

void AdvancedProjectileManager::initialize(size_t num_threads) {
    m_missileFactory->initialize(num_threads);
    m_grenadeFactory->initialize(num_threads);
    m_beamFactory->initialize(num_threads);
    m_boomerangFactory->initialize(num_threads);
    m_grapnelFactory->initialize(num_threads);
}

void AdvancedProjectileManager::shutdown() {
    m_missileFactory->shutdown();
    m_grenadeFactory->shutdown();
    m_beamFactory->shutdown();
    m_boomerangFactory->shutdown();
    m_grapnelFactory->shutdown();
}

} // namespace AdvancedProjectiles
} // namespace MagiTech
