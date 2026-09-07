#include "AdvancedProjectileFactories.hpp"
#include "core/Log.hpp"
#include "core/mesh/Mesh.hpp"
// #include "core/rendering/Primitives.hpp" // TODO: File not found
#include "core/rendering/Shaders.hpp"
#include "core/particles/ParticleSystem.hpp"
#include "core/audio/AudioSystem.hpp"
#include "core/physics/Simulation.hpp"
#include "core/physics/Collision.hpp"
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>
#include <random>

namespace MagiTech {
namespace AdvancedProjectiles {

// ============================================================================
// HASH FUNCTION IMPLEMENTATIONS
// ============================================================================

uint64_t GuidanceParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(GuidanceParams));
    return XXH64_digest(&s);
}

uint64_t PropulsionParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(PropulsionParams));
    return XXH64_digest(&s);
}

uint64_t TargetParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, targetTag.c_str(), targetTag.length());
    XXH64_update(&s, &targetPosition, sizeof(targetPosition));
    XXH64_update(&s, &homingRadius, sizeof(homingRadius));
    return XXH64_digest(&s);
}

uint64_t GrenadeParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(GrenadeParams));
    return XXH64_digest(&s);
}

uint64_t ShardParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, meshType.c_str(), meshType.length());
    XXH64_update(&s, materialType.c_str(), materialType.length());
    XXH64_update(&s, this + offsetof(ShardParams, minVelocity), 
                 sizeof(ShardParams) - offsetof(ShardParams, minVelocity));
    return XXH64_digest(&s);
}

uint64_t BeamParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(BeamParams));
    return XXH64_digest(&s);
}

uint64_t GlowParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(GlowParams));
    return XXH64_digest(&s);
}

uint64_t BoomerangParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(BoomerangParams));
    return XXH64_digest(&s);
}

uint64_t GrapnelParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(GrapnelParams));
    return XXH64_digest(&s);
}

uint64_t HookParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, meshType.c_str(), meshType.length());
    XXH64_update(&s, materialType.c_str(), materialType.length());
    XXH64_update(&s, &autoDetach, sizeof(autoDetach));
    XXH64_update(&s, &hookStrength, sizeof(hookStrength));
    return XXH64_digest(&s);
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
    
    return m_pool.enqueue([=]() {
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

namespace GuidedMissileFactory::MeshGen {
    MeshHandle buildMissileMesh(const GuidanceParams& g, const PropulsionParams& p) {
        Log::info("Building guided missile mesh");
        
        Mesh missileMesh;
        
        // Missile body (cylinder with tapered nose)
        float bodyLength = p.fuelCapacity * 0.8f;
        float bodyRadius = p.maxThrust * 0.001f;
        
        auto body = Primitives::createCylinder(bodyRadius, bodyLength, 12);
        missileMesh.append(body);
        
        // Nose cone
        auto nose = Primitives::createCone(bodyRadius * 1.2f, bodyLength * 0.3f, 12);
        glm::mat4 noseTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, bodyLength * 0.5f + bodyLength * 0.15f, 0));
        missileMesh.append(nose, noseTransform);
        
        // Fins for stability
        for (int i = 0; i < 4; ++i) {
            float angle = i * glm::pi<float>() * 0.5f;
            auto fin = Primitives::createBox(bodyLength * 0.2f, bodyRadius * 0.1f, bodyRadius * 0.8f);
            glm::mat4 finTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, -bodyLength * 0.3f, 0));
            finTransform = glm::rotate(finTransform, angle, glm::vec3(0, 1, 0));
            missileMesh.append(fin, finTransform);
        }
        
        // Engine nozzle
        auto nozzle = Primitives::createCone(bodyRadius * 0.8f, bodyLength * 0.2f, 8);
        glm::mat4 nozzleTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, -bodyLength * 0.5f - bodyLength * 0.1f, 0));
        nozzleTransform = glm::rotate(nozzleTransform, glm::pi<float>(), glm::vec3(1, 0, 0));
        missileMesh.append(nozzle, nozzleTransform);
        
        missileMesh.optimize();
        return missileMesh.upload();
    }
}

namespace GuidedMissileFactory::ShaderGen {
    ShaderHandle compileTrailShader(const PropulsionParams& p) {
        Log::info("Compiling missile trail shader");
        
        // Create shader for engine exhaust trail
        ShaderDesc desc;
        desc.vertexShader = "shaders/missile_trail.vert";
        desc.fragmentShader = "shaders/missile_trail.frag";
        desc.uniforms = {
            {"thrustIntensity", p.maxThrust / 1000.0f},
            {"fuelLevel", p.fuelCapacity},
            {"dragCoeff", p.dragCoefficient}
        };
        
        return Shaders::compile(desc);
    }
}

namespace GuidedMissileFactory::ParticleGen {
    ParticleHandle buildEngineExhaust(const PropulsionParams& p) {
        Log::info("Building engine exhaust particle system");
        
        ParticleSystemDesc desc;
        desc.maxParticles = 100;
        desc.emissionRate = p.maxThrust * 0.1f;
        desc.particleLifetime = 0.5f;
        desc.startColor = glm::vec4(1.0f, 0.5f, 0.0f, 1.0f);
        desc.endColor = glm::vec4(0.5f, 0.2f, 0.0f, 0.0f);
        desc.startSize = 0.1f;
        desc.endSize = 0.5f;
        desc.velocity = glm::vec3(0, -p.maxThrust * 0.01f, 0);
        
        return ParticleSystem::create(desc);
    }
}

namespace GuidedMissileFactory::AudioGen {
    AudioHandle loadHumAudio(const PropulsionParams& p) {
        Log::info("Loading missile hum audio");
        
        AudioDesc desc;
        desc.filename = "audio/missile_hum.wav";
        desc.volume = p.maxThrust / 1000.0f;
        desc.looping = true;
        desc.pitch = 1.0f + (p.fuelCapacity * 0.1f);
        
        return AudioSystem::load(desc);
    }
}

namespace GuidedMissileFactory::GuidanceSim {
    SimulationHandle setup(const GuidanceParams& g, const TargetParams& t) {
        Log::info("Setting up missile guidance simulation");
        
        GuidanceSimDesc desc;
        desc.enableLockOn = g.enableLockOn;
        desc.lockOnDelay = g.lockOnDelay;
        desc.turnRate = glm::radians(g.turnRateDegPerSec);
        desc.proximityFuseDist = g.proximityFuseDist;
        desc.targetTag = t.targetTag;
        desc.homingRadius = t.homingRadius;
        desc.targetPosition = t.targetPosition;
        
        return Simulation::createGuidance(desc);
    }
}

namespace GuidedMissileFactory::PropulsionSim {
    SimulationHandle setup(const PropulsionParams& p) {
        Log::info("Setting up missile propulsion simulation");
        
        PropulsionSimDesc desc;
        desc.maxThrust = p.maxThrust;
        desc.fuelCapacity = p.fuelCapacity;
        desc.dragCoefficient = p.dragCoefficient;
        desc.burnRate = p.maxThrust / p.fuelCapacity;
        
        return Simulation::createPropulsion(desc);
    }
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
    
    return m_pool.enqueue([=]() {
        ShardBundle bundle;
        bundle.bodyMesh = MeshGen::buildGrenadeBody(grenade);
        bundle.shards = FragmentGen::generateShards(shard, grenade);
        bundle.timerSim = TimerSim::setup(grenade);
        bundle.explosionVFX = VFXGen::buildBlast(grenade);
        bundle.explosionAudio = AudioGen::loadExplosionAudio(grenade);
        return bundle;
    });
}

namespace ShardGrenadeFactory::MeshGen {
    MeshHandle buildGrenadeBody(const GrenadeParams& g) {
        Log::info("Building grenade body mesh");
        
        Mesh grenadeMesh;
        
        // Main grenade body (sphere with ridges)
        float radius = g.blastRadius * 0.1f;
        auto body = Primitives::createSphere(radius, 16);
        grenadeMesh.append(body);
        
        // Safety ridges around body
        for (int i = 0; i < 8; ++i) {
            float angle = i * glm::pi<float>() * 0.25f;
            auto ridge = Primitives::createBox(radius * 0.3f, radius * 0.05f, radius * 0.1f);
            glm::mat4 ridgeTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(cos(angle) * radius * 0.8f, 0, sin(angle) * radius * 0.8f));
            ridgeTransform = glm::rotate(ridgeTransform, angle, glm::vec3(0, 1, 0));
            grenadeMesh.append(ridge, ridgeTransform);
        }
        
        // Fuse mechanism
        auto fuse = Primitives::createCylinder(radius * 0.1f, radius * 0.3f, 8);
        glm::mat4 fuseTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, radius + radius * 0.15f, 0));
        grenadeMesh.append(fuse, fuseTransform);
        
        grenadeMesh.optimize();
        return grenadeMesh.upload();
    }
}

namespace ShardGrenadeFactory::FragmentGen {
    std::vector<MeshHandle> generateShards(const ShardParams& s, const GrenadeParams& g) {
        Log::info("Generating {} shard meshes", g.shardCount);
        
        std::vector<MeshHandle> shards;
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> angleDist(0.0f, glm::two_pi<float>());
        std::uniform_real_distribution<float> heightDist(-g.spreadAngleDeg, g.spreadAngleDeg);
        
        for (int i = 0; i < g.shardCount; ++i) {
            Mesh shardMesh;
            
            // Create shard based on type
            if (s.meshType == "spike") {
                auto spike = Primitives::createCone(s.minVelocity * 0.01f, s.maxVelocity * 0.02f, 6);
                shardMesh.append(spike);
            } else if (s.meshType == "shard") {
                auto shard = Primitives::createBox(s.minVelocity * 0.01f, s.maxVelocity * 0.02f, s.minVelocity * 0.01f);
                shardMesh.append(shard);
            } else {
                auto sphere = Primitives::createSphere(s.minVelocity * 0.01f, 6);
                shardMesh.append(sphere);
            }
            
            shardMesh.optimize();
            shards.push_back(shardMesh.upload());
        }
        
        return shards;
    }
}

namespace ShardGrenadeFactory::TimerSim {
    SimulationHandle setup(const GrenadeParams& g) {
        Log::info("Setting up grenade timer simulation");
        
        TimerSimDesc desc;
        desc.fuseTime = g.fuseTime;
        desc.blastRadius = g.blastRadius;
        desc.shardCount = g.shardCount;
        desc.spreadAngle = glm::radians(g.spreadAngleDeg);
        desc.randomizeCount = g.randomizeCount;
        
        return Simulation::createTimer(desc);
    }
}

namespace ShardGrenadeFactory::VFXGen {
    ParticleHandle buildBlast(const GrenadeParams& g) {
        Log::info("Building explosion VFX");
        
        ParticleSystemDesc desc;
        desc.maxParticles = 200;
        desc.emissionRate = 1000.0f;
        desc.particleLifetime = 2.0f;
        desc.startColor = glm::vec4(1.0f, 0.8f, 0.0f, 1.0f);
        desc.endColor = glm::vec4(0.5f, 0.2f, 0.0f, 0.0f);
        desc.startSize = 0.5f;
        desc.endSize = 2.0f;
        desc.blastRadius = g.blastRadius;
        
        return ParticleSystem::create(desc);
    }
}

namespace ShardGrenadeFactory::AudioGen {
    AudioHandle loadExplosionAudio(const GrenadeParams& g) {
        Log::info("Loading explosion audio");
        
        AudioDesc desc;
        desc.filename = "audio/explosion.wav";
        desc.volume = g.blastRadius / 10.0f;
        desc.looping = false;
        desc.pitch = 1.0f;
        
        return AudioSystem::load(desc);
    }
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
    
    return m_pool.enqueue([=]() {
        BeamBundle bundle;
        bundle.beamMesh = BeamGen::createSegments(beam);
        bundle.waveSim = ArcSim::setup(beam);
        bundle.shader = ShaderGen::compileBeamShader(glow);
        bundle.crackleAudio = AudioGen::loadCrackleAudio(beam);
        return bundle;
    });
}

namespace ArcBeamFactory::BeamGen {
    MeshHandle createSegments(const BeamParams& b) {
        Log::info("Creating arc beam segments");
        
        Mesh beamMesh;
        
        // Create segmented beam with branching
        float segmentLength = b.maxRange / b.segmentCount;
        
        for (int i = 0; i < b.segmentCount; ++i) {
            auto segment = Primitives::createCylinder(b.thickness, segmentLength, 8);
            
            // Add jitter to segment position
            float jitter = (i % 3) * 0.1f;
            glm::mat4 segmentTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(i * segmentLength + jitter, 0, 0));
            
            beamMesh.append(segment, segmentTransform);
            
            // Random branching
            if (i > 0 && i < b.segmentCount - 1) {
                std::random_device rd;
                std::mt19937 gen(rd());
                std::uniform_real_distribution<float> branchDist(0.0f, 1.0f);
                
                if (branchDist(gen) < b.branchProbability) {
                    auto branch = Primitives::createCylinder(b.thickness * 0.5f, segmentLength * 0.7f, 6);
                    glm::mat4 branchTransform = glm::translate(glm::mat4(1.0f), 
                        glm::vec3(i * segmentLength, 0, 0));
                    branchTransform = glm::rotate(branchTransform, glm::pi<float>() * 0.25f, glm::vec3(0, 0, 1));
                    beamMesh.append(branch, branchTransform);
                }
            }
        }
        
        beamMesh.optimize();
        return beamMesh.upload();
    }
}

namespace ArcBeamFactory::ArcSim {
    SimulationHandle setup(const BeamParams& b) {
        Log::info("Setting up arc beam simulation");
        
        ArcSimDesc desc;
        desc.duration = b.duration;
        desc.maxRange = b.maxRange;
        desc.thickness = b.thickness;
        desc.branchProbability = b.branchProbability;
        desc.segmentCount = b.segmentCount;
        
        return Simulation::createArc(desc);
    }
}

namespace ArcBeamFactory::ShaderGen {
    ShaderHandle compileBeamShader(const GlowParams& g) {
        Log::info("Compiling beam glow shader");
        
        ShaderDesc desc;
        desc.vertexShader = "shaders/beam_glow.vert";
        desc.fragmentShader = "shaders/beam_glow.frag";
        desc.uniforms = {
            {"innerColor", g.innerColor},
            {"outerColor", g.outerColor},
            {"pulseFrequency", g.pulseFrequency},
            {"intensity", g.intensity}
        };
        
        return Shaders::compile(desc);
    }
}

namespace ArcBeamFactory::AudioGen {
    AudioHandle loadCrackleAudio(const BeamParams& b) {
        Log::info("Loading arc crackle audio");
        
        AudioDesc desc;
        desc.filename = "audio/arc_crackle.wav";
        desc.volume = b.thickness * 10.0f;
        desc.looping = true;
        desc.pitch = 1.0f + (b.branchProbability * 0.5f);
        
        return AudioSystem::load(desc);
    }
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
    return m_pool.enqueue([=]() {
        BoomerangBundle bundle;
        bundle.mesh = MeshGen::buildBoomerangBlade(params);
        bundle.flightSim = BoomerangSim::setup(params);
        bundle.whooshAudio = AudioGen::loadWhooshAudio(params);
        bundle.trailVFX = VFXGen::buildTrailVFX(params);
        return bundle;
    });
}

namespace BoomerangFactory::MeshGen {
    MeshHandle buildBoomerangBlade(const BoomerangParams& b) {
        Log::info("Building boomerang blade mesh");
        
        Mesh boomerangMesh;
        
        // Create curved boomerang blade
        float bladeLength = b.returnSpeed * 0.1f;
        float bladeWidth = bladeLength * 0.2f;
        float bladeThickness = bladeWidth * 0.1f;
        
        // Main blade (curved)
        for (int i = 0; i < 8; ++i) {
            float t = i / 7.0f;
            float curve = sin(t * glm::pi<float>()) * bladeLength * 0.3f;
            
            auto segment = Primitives::createBox(bladeLength / 8.0f, bladeThickness, bladeWidth);
            glm::mat4 segmentTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(i * bladeLength / 8.0f, curve, 0));
            segmentTransform = glm::rotate(segmentTransform, t * glm::pi<float>() * 0.5f, glm::vec3(0, 0, 1));
            boomerangMesh.append(segment, segmentTransform);
        }
        
        // Center grip
        auto grip = Primitives::createCylinder(bladeWidth * 0.3f, bladeThickness * 2.0f, 8);
        boomerangMesh.append(grip);
        
        boomerangMesh.optimize();
        return boomerangMesh.upload();
    }
}

namespace BoomerangFactory::BoomerangSim {
    SimulationHandle setup(const BoomerangParams& b) {
        Log::info("Setting up boomerang flight simulation");
        
        BoomerangSimDesc desc;
        desc.returnDelay = b.returnDelay;
        desc.returnSpeed = b.returnSpeed;
        desc.liftCoefficient = b.liftCoefficient;
        desc.dragCoefficient = b.dragCoefficient;
        desc.spinRate = b.spinRateRPM / 60.0f; // Convert to Hz
        
        return Simulation::createBoomerang(desc);
    }
}

namespace BoomerangFactory::AudioGen {
    AudioHandle loadWhooshAudio(const BoomerangParams& b) {
        Log::info("Loading boomerang whoosh audio");
        
        AudioDesc desc;
        desc.filename = "audio/boomerang_whoosh.wav";
        desc.volume = b.returnSpeed / 20.0f;
        desc.looping = true;
        desc.pitch = 1.0f + (b.spinRateRPM / 2000.0f);
        
        return AudioSystem::load(desc);
    }
}

namespace BoomerangFactory::VFXGen {
    ParticleHandle buildTrailVFX(const BoomerangParams& b) {
        Log::info("Building boomerang trail VFX");
        
        ParticleSystemDesc desc;
        desc.maxParticles = 50;
        desc.emissionRate = b.returnSpeed * 2.0f;
        desc.particleLifetime = 1.0f;
        desc.startColor = glm::vec4(0.8f, 0.8f, 0.8f, 0.8f);
        desc.endColor = glm::vec4(0.5f, 0.5f, 0.5f, 0.0f);
        desc.startSize = 0.05f;
        desc.endSize = 0.2f;
        desc.velocity = glm::vec3(0, 0, 0);
        
        return ParticleSystem::create(desc);
    }
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
    
    return m_pool.enqueue([=]() {
        GrapnelBundle bundle;
        bundle.hookMesh = MeshGen::buildGrapnelHook(hook);
        bundle.tether = TetherGen::createRope(grapnel);
        bundle.launchSim = ProjectileSim::setupLinear(grapnel);
        bundle.retractSim = ReelSim::setup(grapnel);
        bundle.reelAudio = AudioGen::loadReelAudio(grapnel);
        return bundle;
    });
}

namespace GrapnelFactory::MeshGen {
    MeshHandle buildGrapnelHook(const HookParams& h) {
        Log::info("Building grapnel hook mesh");
        
        Mesh hookMesh;
        
        // Hook body
        float hookSize = h.hookStrength * 0.001f;
        auto body = Primitives::createCylinder(hookSize * 0.3f, hookSize * 2.0f, 8);
        hookMesh.append(body);
        
        // Hook tip (curved)
        auto tip = Primitives::createTorus(hookSize * 0.8f, hookSize * 0.2f, 12, 6);
        glm::mat4 tipTransform = glm::translate(glm::mat4(1.0f), 
            glm::vec3(0, hookSize, 0));
        tipTransform = glm::rotate(tipTransform, glm::pi<float>() * 0.5f, glm::vec3(1, 0, 0));
        hookMesh.append(tip, tipTransform);
        
        // Barbs for grip
        for (int i = 0; i < 3; ++i) {
            float angle = i * glm::pi<float>() * 2.0f / 3.0f;
            auto barb = Primitives::createCone(hookSize * 0.1f, hookSize * 0.3f, 4);
            glm::mat4 barbTransform = glm::translate(glm::mat4(1.0f), 
                glm::vec3(0, hookSize * 0.5f, 0));
            barbTransform = glm::rotate(barbTransform, angle, glm::vec3(0, 1, 0));
            barbTransform = glm::rotate(barbTransform, glm::pi<float>() * 0.25f, glm::vec3(1, 0, 0));
            hookMesh.append(barb, barbTransform);
        }
        
        hookMesh.optimize();
        return hookMesh.upload();
    }
}

namespace GrapnelFactory::TetherGen {
    TetherHandle createRope(const GrapnelParams& g) {
        Log::info("Creating grapnel tether rope");
        
        TetherDesc desc;
        desc.maxRange = g.maxRange;
        desc.segmentCount = static_cast<int>(g.maxRange / 0.5f);
        desc.enableElasticity = g.enableElasticity;
        desc.springConstant = g.springConstant;
        desc.retractionSpeed = g.retractionSpeed;
        
        return Collision::createTether(desc);
    }
}

namespace GrapnelFactory::ProjectileSim {
    SimulationHandle setupLinear(const GrapnelParams& g) {
        Log::info("Setting up grapnel launch simulation");
        
        ProjectileSimDesc desc;
        desc.launchSpeed = g.launchSpeed;
        desc.maxRange = g.maxRange;
        desc.gravityInfluence = 0.3f;
        desc.dragCoefficient = 0.2f;
        
        return Simulation::createLinearProjectile(desc);
    }
}

namespace GrapnelFactory::ReelSim {
    SimulationHandle setup(const GrapnelParams& g) {
        Log::info("Setting up grapnel reel simulation");
        
        ReelSimDesc desc;
        desc.retractionSpeed = g.retractionSpeed;
        desc.enableElasticity = g.enableElasticity;
        desc.springConstant = g.springConstant;
        desc.maxRange = g.maxRange;
        
        return Simulation::createReel(desc);
    }
}

namespace GrapnelFactory::AudioGen {
    AudioHandle loadReelAudio(const GrapnelParams& g) {
        Log::info("Loading grapnel reel audio");
        
        AudioDesc desc;
        desc.filename = "audio/grapnel_reel.wav";
        desc.volume = g.retractionSpeed / 10.0f;
        desc.looping = true;
        desc.pitch = 1.0f;
        
        return AudioSystem::load(desc);
    }
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
