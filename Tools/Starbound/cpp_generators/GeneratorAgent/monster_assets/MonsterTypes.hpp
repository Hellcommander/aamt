#pragma once

#include <string>
#include <vector>
#include <array>
#include <glm/glm.hpp>
#include "xxhash.h"

namespace MagiTech {
namespace Monsters {

// Monster body types
enum class BodyType : uint8_t {
    HUMANOID = 0,
    QUADRUPED = 1,
    INSECTOID = 2,
    AMORPHOUS = 3,
    AVIAN = 4,
    AQUATIC = 5,
    REPTILIAN = 6,
    ARACHNID = 7,
    CEPHALOPOD = 8,
    CRYSTALLINE = 9
};

// Monster complexity levels
enum class ComplexityLevel : uint8_t {
    LOW_POLY = 0,      // 0-500 vertices
    MEDIUM = 1,         // 500-2000 vertices
    HIGH = 2,           // 2000-8000 vertices
    ULTRA = 3           // 8000+ vertices
};

// Horn types
enum class HornType : uint8_t {
    NONE = 0,
    SPIKE = 1,
    CURVED = 2,
    ANTLER = 3,
    CRYSTAL = 4,
    TENTACLE = 5,
    SPIRAL = 6
};

// Tail types
enum class TailType : uint8_t {
    NONE = 0,
    TAIL = 1,
    MULTIPLE_TAILS = 2,
    SPINE = 3,
    TENTACLE = 4,
    CRYSTAL = 5,
    FLAME = 6
};

// Pattern types
enum class PatternType : uint8_t {
    NONE = 0,
    STRIPES = 1,
    SPOTS = 2,
    SCALES = 3,
    SKIN = 4,
    CRYSTAL = 5,
    GLOW = 6,
    CAMOUFLAGE = 7
};

// Animation profiles
enum class AnimationProfile : uint8_t {
    BEAST_BASIC = 0,
    PREDATOR = 1,
    PACK_HUNTER = 2,
    HORROR_FLOAT = 3,
    INSECT_SCUTTLE = 4,
    AQUATIC_SWIM = 5,
    AVIAN_FLY = 6,
    CRYSTAL_PULSE = 7
};

// AI profiles
enum class AIProfile : uint8_t {
    PASSIVE = 0,
    NEUTRAL = 1,
    PREDATOR = 2,
    PACK_HUNTER = 3,
    BOSS = 4,
    MINION = 5,
    GUARDIAN = 6,
    WANDERER = 7
};

// Enhanced MonsterParams with C++23 features
struct MonsterParams {
    // Basic identification
    std::string id;
    std::string name;
    std::string description;
    
    // Body configuration
    BodyType bodyType = BodyType::HUMANOID;
    float size = 2.0f;                    // Height in meters
    ComplexityLevel complexity = ComplexityLevel::MEDIUM;
    
    // Limb configuration
    int limbCount = 4;                     // Total arms/legs
    int headCount = 1;                     // Number of heads/eye clusters
    int eyeCount = 2;                      // Eyes per head
    int wingCount = 0;                     // Wings (for avian/aquatic)
    int tentacleCount = 0;                 // Tentacles (for cephalopods)
    
    // Appendages
    HornType hornType = HornType::NONE;
    TailType tailType = TailType::NONE;
    int hornCount = 0;
    int tailCount = 1;
    
    // Visual appearance
    PatternType patternType = PatternType::NONE;
    glm::vec3 colorPrimary = {0.6f, 0.1f, 0.2f};
    glm::vec3 colorSecondary = {0.2f, 0.2f, 0.2f};
    glm::vec3 colorAccent = {0.8f, 0.8f, 0.8f};
    float colorVariation = 0.1f;          // Random color variation
    
    // Texture and material
    float noiseDetail = 0.8f;             // Vertex noise intensity
    float textureScale = 1.5f;            // UV tiling factor
    float materialRoughness = 0.7f;       // PBR roughness
    float materialMetallic = 0.0f;        // PBR metallic
    float materialEmissive = 0.0f;        // Glow intensity
    float materialTransparency = 0.0f;    // Transparency factor
    
    // Animation and behavior
    AnimationProfile animationProfile = AnimationProfile::BEAST_BASIC;
    AIProfile aiProfile = AIProfile::PREDATOR;
    
    // Physics properties
    float mass = 100.0f;                  // Mass in kg
    float density = 1.0f;                 // Material density
    float friction = 0.5f;                // Surface friction
    float restitution = 0.3f;             // Bounce factor
    
    // Advanced features
    bool gpuAccelerated = true;           // Use GPU for generation
    bool simdEnabled = true;              // Use SIMD optimizations
    bool adaptiveLOD = true;              // Adaptive level of detail
    bool proceduralVariation = true;      // Add random variations
    
    // Generation settings
    uint32_t seed = 0;                    // Random seed (0 = auto)
    float generationQuality = 1.0f;       // Quality multiplier
    bool cacheEnabled = true;             // Enable asset caching
    
    // C++23 Modern hash function
    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, seed);
        
        // Hash basic parameters
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, &bodyType, sizeof(bodyType));
        XXH64_update(&hash_state, &size, sizeof(size));
        XXH64_update(&hash_state, &complexity, sizeof(complexity));
        XXH64_update(&hash_state, &limbCount, sizeof(limbCount));
        XXH64_update(&hash_state, &headCount, sizeof(headCount));
        XXH64_update(&hash_state, &eyeCount, sizeof(eyeCount));
        
        // Hash visual parameters
        XXH64_update(&hash_state, &hornType, sizeof(hornType));
        XXH64_update(&hash_state, &tailType, sizeof(tailType));
        XXH64_update(&hash_state, &patternType, sizeof(patternType));
        XXH64_update(&hash_state, &colorPrimary, sizeof(colorPrimary));
        XXH64_update(&hash_state, &colorSecondary, sizeof(colorSecondary));
        XXH64_update(&hash_state, &colorAccent, sizeof(colorAccent));
        
        // Hash material parameters
        XXH64_update(&hash_state, &noiseDetail, sizeof(noiseDetail));
        XXH64_update(&hash_state, &textureScale, sizeof(textureScale));
        XXH64_update(&hash_state, &materialRoughness, sizeof(materialRoughness));
        XXH64_update(&hash_state, &materialMetallic, sizeof(materialMetallic));
        XXH64_update(&hash_state, &materialEmissive, sizeof(materialEmissive));
        
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
               size > 0.0f && 
               limbCount >= 0 && 
               headCount > 0 && 
               eyeCount > 0 &&
               generationQuality > 0.0f &&
               generationQuality <= 2.0f;
    }
    
    // C++23 Modern serialization helpers
    std::string toString() const {
        return "MonsterParams{id='" + id + "', bodyType=" + std::to_string(static_cast<int>(bodyType)) + 
               ", size=" + std::to_string(size) + ", complexity=" + std::to_string(static_cast<int>(complexity)) + "}";
    }
};

// Monster generation result
struct MonsterGenerationResult {
    bool success = false;
    std::string errorMessage;
    float generationTime = 0.0f;
    size_t memoryUsage = 0;
    uint32_t vertexCount = 0;
    uint32_t triangleCount = 0;
    uint32_t textureSize = 0;
    uint32_t animationFrameCount = 0;
    
    // C++23 Modern result type
    explicit operator bool() const { return success; }
};

// Monster asset bundle with enhanced metadata
struct MonsterAssetBundle {
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
    MonsterGenerationResult result;
    MonsterParams params;
    std::string assetPath;
    std::chrono::system_clock::time_point creationTime;
    
    // C++23 Modern asset validation
    bool isValid() const {
        return mesh != 0 && texture != 0 && skeleton != 0 && anim != 0 && ai != 0;
    }
    
    // C++23 Modern asset info
    std::string getInfo() const {
        return "MonsterAssetBundle{mesh=" + std::to_string(mesh) + 
               ", texture=" + std::to_string(texture) + 
               ", skeleton=" + std::to_string(skeleton) + 
               ", anim=" + std::to_string(anim) + 
               ", ai=" + std::to_string(ai) + "}";
    }
};

} // namespace Monsters
} // namespace MagiTech
