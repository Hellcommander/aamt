#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace IceShards {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using LightHandle = uint32_t;
using AudioHandle = uint32_t;
using ColliderHandle = uint32_t;

enum class ShardDistribution { RadialBurst, StreamLine, RandomScatter };

struct IceShardParams {
    std::string id = "default_ice_shard";
    float coreRadius = 0.2f;
    int shardCount = 8;
    float shardLength = 1.0f;
    float shardVariance = 0.2f;
    ShardDistribution distribution = ShardDistribution::RadialBurst;
    bool dynamicTess = false;
    
    // Enhancement: Seeded randomness for reproducible patterns
    uint32_t randomSeed = 0; // 0 = use current time
    
    // Enhancement: LOD system
    float lodDistance = 50.0f;  // distance at which to reduce detail
    int minShardCount = 4;      // minimum shards for distant LODs
    
    // Enhancement: Advanced crystal properties
    float shardTaper = 0.8f;    // how much shards narrow toward tip [0-1]
    float roughnessScale = 0.1f; // surface irregularity for more organic look
    
    uint64_t hashKey() const;
};

struct FrostTrailParams {
    bool enableTrail = true;
    float trailLength = 2.0f;
    float width = 0.1f;
    glm::vec4 tipColor = {1,1,1,1};
    glm::vec4 baseColor = {0.5f, 0.7f, 1.0f, 0.5f};
    float uvScrollSpeed = 1.0f;
    uint64_t hashKey() const;
};

struct FrostVFXParams {
    std::string shaderTemplate;
    std::vector<std::string> defines;
    float noiseIntensity = 0.5f;
    float rimPower = 3.0f;
    
    // Enhancement: Dynamic melting effects
    bool enableMelting = false;
    float meltSpeed = 1.0f;       // rate of melt progression
    float meltTemperature = 0.0f; // external temperature influence
    
    // Enhancement: Refraction and caustics
    float refractionIndex = 1.31f; // ice refraction (~1.31)
    bool enableCaustics = false;
    float causticsIntensity = 0.3f;
    
    // Enhancement: Crack propagation
    float crackPropagationSpeed = 2.0f;
    glm::vec3 crackOrigin = {0.0f, 0.0f, 0.0f};
    
    uint64_t hashKey() const;
};

struct FrostParticleParams {
    bool enableParticles = true;
    int burstCount = 50;
    float spawnRate = 100.0f;
    float lifeTime = 0.5f;
    glm::vec3 initialVelocity = {0,0,5};
    float spreadAngle = 30.0f;
    
    // Enhancement: Multi-layered particle effects
    bool enableIceDust = true;     // fine ice dust particles
    bool enableSparkles = false;   // light-catching ice crystals
    bool enableVapor = false;      // sublimation vapor trails
    
    // Enhancement: Physics simulation
    float gravity = 9.81f;         // downward acceleration
    float airResistance = 0.1f;    // drag coefficient
    bool enableCollisions = false; // particle-world collision
    
    // Enhancement: Temperature effects
    float freezeThreshold = 0.0f;  // temperature below which particles persist
    float sublimationRate = 0.2f;  // rate of ice -> vapor transition
    
    uint64_t hashKey() const;
};

struct FrostLightParams {
    bool enableLight = true;
    glm::vec4 color = {0.6f, 0.8f, 1.0f, 1.0f};
    float intensity = 2.0f;
    float flickerFreq = 5.0f;
    uint64_t hashKey() const;
};

struct FrostAudioParams {
    bool playOnCast = true;
    std::string whooshFile;
    std::string crackFile;
    float volume = 0.8f;
    uint64_t hashKey() const;
};

struct FrostCollisionParams {
    bool enableCollider = true;
    float radius = 0.2f;
    bool convexHull = true;
    bool triggerOnly = false;
    
    // Enhancement: Advanced collision features
    bool enableCCD = true;         // Continuous Collision Detection for high-speed
    float bounceElasticity = 0.1f; // how much energy retained on bounce
    int maxBounces = 3;            // maximum number of bounces before destruction
    bool shatterOnImpact = true;   // break into smaller fragments
    float impactThreshold = 5.0f;  // minimum velocity for shattering
    
    uint64_t hashKey() const;
};

struct IceShardBundle {
    std::vector<MeshHandle> shardMeshes;
    MeshHandle trailMesh = 0;
    ShaderHandle vfxShader = 0;
    ParticleHandle particleSys = 0;
    LightHandle light = 0;
    AudioHandle audioWhoosh = 0;
    AudioHandle audioCrack = 0;
    ColliderHandle collider = 0;
    
    // Enhancement: Advanced shader variants
    ShaderHandle meltShader = 0;       // for dynamic melting effects
    ShaderHandle refractShader = 0;    // for caustics and refraction
    
    // Enhancement: LOD mesh variants
    std::vector<MeshHandle> lodMeshes; // different detail levels
    
    // Enhancement: Network sync data
    uint64_t bundleId = 0;             // unique identifier for networking
    uint32_t version = 1;              // for delta compression
};

// Enhancement: Network replication state (as mentioned in "Next Steps")
struct IceShardNetworkState {
    uint64_t shardId;
    glm::vec3 position;
    glm::quat rotation;
    glm::vec3 velocity;
    float timeAlive;
    uint8_t shardIntegrity; // 0-255, for damage/melting state
    bool isActive;
    
    // Compression helpers for bandwidth optimization
    glm::vec3 compressedPos;    // quantized position
    uint16_t compressedRot;     // compressed quaternion
};

// Enhancement: ML-guided pattern generation (as mentioned in "Next Steps") 
struct IceShardMLParams {
    std::string modelPath = "models/ice_shard_vae.onnx";
    std::vector<float> latentVector;   // VAE latent space coordinates
    float styleWeight = 1.0f;          // how much to apply ML styling
    bool enableStyleTransfer = false;  // use style transfer from reference image
    std::string styleImagePath;
};

} // namespace IceShards
} // namespace MagiTech
