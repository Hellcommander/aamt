#pragma once
#include "IceShardTypes.hpp"
#include <vector>
#include <memory>

namespace MagiTech {
namespace IceShards {

// Enhancement: Network replication system (as mentioned in "Next Steps")
class IceShardNetworkManager {
private:
    std::vector<IceShardNetworkState> m_activeShards;
    float m_updateRate = 20.0f; // Hz
    float m_compressionThreshold = 0.01f; // minimum delta for updates

public:
    // Pack shard state for network transmission
    std::vector<uint8_t> serializeShardState(const IceShardNetworkState& state);
    
    // Unpack received network data
    IceShardNetworkState deserializeShardState(const std::vector<uint8_t>& data);
    
    // Delta compression for bandwidth optimization
    std::vector<uint8_t> createDeltaUpdate(const IceShardNetworkState& oldState, 
                                          const IceShardNetworkState& newState);
    
    // Apply delta update to existing state
    void applyDeltaUpdate(IceShardNetworkState& state, const std::vector<uint8_t>& delta);
    
    // Register a new shard for network tracking
    void registerShard(const IceShardNetworkState& state);
    
    // Remove shard from network tracking
    void unregisterShard(uint64_t shardId);
    
    // Get all active network states
    const std::vector<IceShardNetworkState>& getActiveStates() const { return m_activeShards; }
};

// Enhancement: ML-guided pattern generation (as mentioned in "Next Steps")
class IceShardMLGenerator {
private:
    std::string m_modelPath;
    bool m_modelLoaded = false;
    
public:
    // Initialize ML model (ONNX Runtime)
    bool loadModel(const std::string& modelPath);
    
    // Generate shard pattern using VAE latent space
    std::vector<glm::vec3> generateMLPattern(const IceShardMLParams& params);
    
    // Style transfer from reference image
    std::vector<glm::vec3> applyStyleTransfer(const std::vector<glm::vec3>& basePattern,
                                            const std::string& styleImagePath,
                                            float styleWeight);
    
    // Generate random latent vector for variation
    std::vector<float> generateRandomLatent(int dimensions = 128);
    
    // Interpolate between two latent vectors for smooth transitions
    std::vector<float> interpolateLatent(const std::vector<float>& a,
                                       const std::vector<float>& b,
                                       float t);
};

// Enhancement: Dynamic melting system (as mentioned in "Next Steps")
struct MeltingState {
    float meltProgress = 0.0f;    // 0.0 = solid, 1.0 = fully melted
    float temperature = 0.0f;     // current temperature
    std::vector<glm::vec3> dripPoints; // where drips form
    bool isActive = false;
};

class IceShardMeltingSystem {
private:
    std::vector<MeltingState> m_meltStates;
    float m_ambientTemperature = 20.0f; // °C
    
public:
    // Start melting process for a shard bundle
    void startMelting(uint64_t bundleId, float initialTemperature);
    
    // Update melting simulation
    void updateMelting(float deltaTime);
    
    // Get current melt state for a bundle
    const MeltingState* getMeltState(uint64_t bundleId) const;
    
    // Generate drip particles based on melt state
    std::vector<glm::vec3> generateDripParticles(const MeltingState& state);
    
    // Check if shard should be destroyed due to melting
    bool shouldDestroy(const MeltingState& state) const;
};

// Enhancement: Adaptive audio system (as mentioned in "Next Steps")
class IceShardAudioManager {
private:
    std::map<uint64_t, float> m_shardVelocities;
    
public:
    // Modulate crack pitch based on shard velocity
    float calculateCrackPitch(float velocity, float basePitch = 1.0f);
    
    // Calculate doppler effect for fast-moving shards
    float calculateDopplerShift(const glm::vec3& velocity, const glm::vec3& listenerPos);
    
    // Generate procedural whoosh audio based on shard parameters
    AudioHandle generateProceduralWhoosh(const IceShardParams& params, float velocity);
    
    // Update audio parameters in real-time
    void updateShardAudio(uint64_t shardId, const glm::vec3& position, 
                         const glm::vec3& velocity);
};

// Enhancement: Spell blending system (as mentioned in "Next Steps")
struct SpellBlendParams {
    float iceWeight = 1.0f;
    float lightningWeight = 0.0f;
    float fireWeight = 0.0f;
    float transitionTime = 0.5f;
};

class SpellBlendingSystem {
public:
    // Morph between ice shard and lightning bolt archetypes
    IceShardParams blendIceLightning(const IceShardParams& ice, 
                                   const SpellBlendParams& blend);
    
    // Create smooth transition between spell types
    std::vector<IceShardParams> createBlendSequence(const IceShardParams& start,
                                                   const IceShardParams& end,
                                                   int steps);
    
    // Real-time morphing for dynamic spell evolution
    void updateBlendState(IceShardBundle& bundle, const SpellBlendParams& blend, 
                         float deltaTime);
};

} // namespace IceShards
} // namespace MagiTech
