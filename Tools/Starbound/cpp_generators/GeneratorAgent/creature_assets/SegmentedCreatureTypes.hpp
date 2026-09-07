#pragma once

#include <string>
#include <vector>
#include <array>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace SegmentedCreatures {

// Taper profile types
enum class TaperProfile : uint8_t {
    NONE = 0,
    LINEAR = 1,
    EXPONENTIAL = 2,
    CUSTOM_CURVE = 3,
    BELL_CURVE = 4,
    STEPPED = 5,
    IRREGULAR = 6
};

// Segment types
enum class SegmentType : uint8_t {
    CYLINDER = 0,
    BOX = 1,
    HEXAGON = 2,
    CUSTOM_MESH = 3,
    SPHERE = 4,
    CAPSULE = 5,
    PRISM = 6,
    IRREGULAR = 7
};

// Head types
enum class HeadType : uint8_t {
    SIMPLE = 0,
    MANDIBLE = 1,
    MULTI_EYE = 2,
    HORNED = 3,
    FANGED = 4,
    TENTACLED = 5,
    CRYSTAL = 6,
    MECHANICAL = 7
};

// Tail types
enum class TailType : uint8_t {
    NONE = 0,
    SPIKE = 1,
    FLARED = 2,
    TENTACLE = 3,
    CRYSTAL = 4,
    MECHANICAL = 5,
    BIOLUMINESCENT = 6,
    VENOMOUS = 7
};

// Animation profiles
enum class AnimationProfile : uint8_t {
    WAVE_SLITHER = 0,
    CRAWL = 1,
    COIL = 2,
    BURROW = 3,
    SWIM = 4,
    FLY = 5,
    CLIMB = 6,
    CUSTOM = 7
};

// AI profiles
enum class AIProfile : uint8_t {
    PASSIVE = 0,
    NEUTRAL = 1,
    PREDATOR = 2,
    SWARM = 3,
    BURROWER = 4,
    CLIMBER = 5,
    AMBUSHER = 6,
    GUARDIAN = 7
};

// Enhanced SegmentedCreatureParams with C++23 features
struct SegmentedCreatureParams {
    // Basic identification
    std::string id;
    std::string name;
    std::string description;
    
    // Segment configuration
    int segmentCount = 20;                 // Total number of repeating modules
    float segmentLength = 0.5f;            // World units per segment
    float segmentRadius = 0.2f;            // Base radius
    TaperProfile taperProfile = TaperProfile::LINEAR;
    SegmentType segmentType = SegmentType::CYLINDER;
    
    // Head and tail configuration
    HeadType headType = HeadType::MANDIBLE;
    TailType tailType = TailType::SPIKE;
    float headScale = 1.2f;                // Head size multiplier
    float tailScale = 0.8f;                // Tail size multiplier
    int headSegmentCount = 1;              // Number of head segments
    int tailSegmentCount = 1;              // Number of tail segments
    
    // Articulation and physics
    float articulationStiffness = 0.7f;    // 0-1 how rigid the joints are
    float jointLimit = 45.0f;              // Maximum joint angle in degrees
    float segmentMass = 1.0f;              // Mass per segment
    float segmentDensity = 1.0f;           // Material density
    float segmentFriction = 0.5f;          // Surface friction
    float segmentRestitution = 0.3f;       // Bounce factor
    
    // Visual appearance
    glm::vec3 colorPrimary = {0.3f, 0.3f, 0.35f};
    glm::vec3 colorSecondary = {0.1f, 0.1f, 0.1f};
    glm::vec3 colorAccent = {0.8f, 0.8f, 0.8f};
    float colorVariation = 0.1f;           // Random color variation
    
    // Texture and material
    float noiseDetail = 0.4f;              // Surface noise intensity
    float materialRoughness = 0.6f;        // PBR roughness
    float materialMetallic = 0.8f;         // PBR metallic
    float materialEmissive = 0.0f;         // Glow intensity
    float materialTransparency = 0.0f;     // Transparency factor
    
    // Armor and plating
    bool armorPlates = true;               // Enable segment armor overlay
    int plateDetailLevel = 2;              // 0=none,1=low,2=med,3=high
    float plateThickness = 0.02f;          // Armor plate thickness
    float plateSpacing = 0.1f;             // Distance between plates
    bool plateOverlap = false;             // Allow plates to overlap
    
    // Animation and behavior
    AnimationProfile animationProfile = AnimationProfile::WAVE_SLITHER;
    AIProfile aiProfile = AIProfile::BURROWER;
    
    // Advanced features
    bool gpuAccelerated = true;            // Use GPU for generation
    bool simdEnabled = true;               // Use SIMD optimizations
    bool adaptiveLOD = true;               // Adaptive level of detail
    bool proceduralVariation = true;       // Add random variations
    bool dynamicSegments = false;          // Allow segment count changes
    bool damageableSegments = false;       // Individual segment damage
    
    // Generation settings
    uint32_t seed = 0;                     // Random seed (0 = auto)
    float generationQuality = 1.0f;        // Quality multiplier
    bool cacheEnabled = true;              // Enable asset caching
    
    // C++23 Modern hash function
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, seed);
        
        // Hash basic parameters
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &segmentCount, sizeof(segmentCount));
        XXH64_update(&hash_state, &segmentLength, sizeof(segmentLength));
        XXH64_update(&hash_state, &segmentRadius, sizeof(segmentRadius));
        XXH64_update(&hash_state, &taperProfile, sizeof(taperProfile));
        XXH64_update(&hash_state, &segmentType, sizeof(segmentType));
        
        // Hash head and tail parameters
        XXH64_update(&hash_state, &headType, sizeof(headType));
        XXH64_update(&hash_state, &tailType, sizeof(tailType));
        XXH64_update(&hash_state, &headScale, sizeof(headScale));
        XXH64_update(&hash_state, &tailScale, sizeof(tailScale));
        
        // Hash articulation parameters
        XXH64_update(&hash_state, &articulationStiffness, sizeof(articulationStiffness));
        XXH64_update(&hash_state, &jointLimit, sizeof(jointLimit));
        XXH64_update(&hash_state, &segmentMass, sizeof(segmentMass));
        XXH64_update(&hash_state, &segmentDensity, sizeof(segmentDensity));
        
        // Hash visual parameters
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorSecondary, sizeof(colorSecondary));
        XXH64_update(&hash_state, &colorAccent, sizeof(colorAccent));
        XXH64_update(&hash_state, &colorVariation, sizeof(colorVariation));
        
        // Hash material parameters
        XXH64_update(&hash_state, &noiseDetail, sizeof(noiseDetail));
        XXH64_update(&hash_state, &materialRoughness, sizeof(materialRoughness));
        XXH64_update(&hash_state, &materialMetallic, sizeof(materialMetallic));
        XXH64_update(&hash_state, &materialEmissive, sizeof(materialEmissive));
        
        // Hash armor parameters
        XXH64_update(&hash_state, &armorPlates, sizeof(armorPlates));
        XXH64_update(&hash_state, &plateDetailLevel, sizeof(plateDetailLevel));
        XXH64_update(&hash_state, &plateThickness, sizeof(plateThickness));
        XXH64_update(&hash_state, &plateSpacing, sizeof(plateSpacing));
        
        // Hash behavior parameters
        XXH64_update(&hash_state, &animationProfile, sizeof(animationProfile));
        XXH64_update(&hash_state, &aiProfile, sizeof(aiProfile));
        
        // Hash generation settings
        XXH64_update(&hash_state, &seed, sizeof(seed));
        XXH64_update(&hash_state, &generationQuality, sizeof(generationQuality));
        
        return XXH64_digest(&hash_state);
    }
    
    // C++23 Modern validation
    bool isValid() const {
        return !id.empty() && 
               segmentCount > 0 && segmentCount <= 1000 &&
               segmentLength > 0.0f && segmentLength <= 10.0f &&
               segmentRadius > 0.0f && segmentRadius <= 5.0f &&
               articulationStiffness >= 0.0f && articulationStiffness <= 1.0f &&
               generationQuality > 0.0f && generationQuality <= 2.0f;
    }
    
    // C++23 Modern serialization helpers
    std::string toString() const {
        return "SegmentedCreatureParams{id='" + id + "', segmentCount=" + std::to_string(segmentCount) + 
               ", segmentLength=" + std::to_string(segmentLength) + ", segmentRadius=" + std::to_string(segmentRadius) + "}";
    }
};

// Segmented creature generation result
struct SegmentedCreatureGenerationResult {
    bool success = false;
    std::string errorMessage;
    float generationTime = 0.0f;
    size_t memoryUsage = 0;
    uint32_t vertexCount = 0;
    uint32_t triangleCount = 0;
    uint32_t textureSize = 0;
    uint32_t animationFrameCount = 0;
    uint32_t segmentCount = 0;
    uint32_t boneCount = 0;
    
    // C++23 Modern result type
    explicit operator bool() const { return success; }
};

// Segmented creature asset bundle with enhanced metadata
struct SegmentedCreatureAssetBundle {
    // Core assets
    MeshHandle mesh = 0;
    TextureHandle texture = 0;
    SkeletonHandle skeleton = 0;
    AnimationHandle anim = 0;
    AIHandle ai = 0;
    
    // Additional assets
    TextureHandle normalMap = 0;
    TextureHandle roughnessMap = 0;
    TextureHandle metallicMap = 0;
    TextureHandle emissiveMap = 0;
    TextureHandle aoMap = 0;
    
    // Metadata
    SegmentedCreatureGenerationResult result;
    SegmentedCreatureParams params;
    std::string assetPath;
    std::chrono::system_clock::time_point creationTime;
    
    // C++23 Modern asset validation
    bool isValid() const {
        return mesh != 0 && texture != 0 && skeleton != 0 && anim != 0 && ai != 0;
    }
    
    // C++23 Modern asset info
    std::string getInfo() const {
        return "SegmentedCreatureAssetBundle{mesh=" + std::to_string(mesh) + 
               ", texture=" + std::to_string(texture) + 
               ", skeleton=" + std::to_string(skeleton) + 
               ", anim=" + std::to_string(anim) + 
               ", ai=" + std::to_string(ai) + "}";
    }
};

} // namespace SegmentedCreatures
} // namespace MagiTech
