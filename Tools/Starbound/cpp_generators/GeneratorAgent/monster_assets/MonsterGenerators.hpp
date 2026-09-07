#pragma once

#include "MonsterTypes.hpp"
#include <glm/glm.hpp>
#include <vector>
#include <memory>
#include <future>

namespace MagiTech {
namespace Monsters {

// Forward declarations
class Mesh;
class Texture;
class Skeleton;
class Animation;
class AI;

// Mesh generation namespace
namespace MeshGen {
    // Base shape generation
    class BaseShape {
    public:
        static std::unique_ptr<Mesh> create(BodyType bodyType, float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createHumanoid(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createQuadruped(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createInsectoid(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createAmorphous(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createAvian(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createAquatic(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createReptilian(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createArachnid(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createCephalopod(float size, ComplexityLevel complexity);
        static std::unique_ptr<Mesh> createCrystalline(float size, ComplexityLevel complexity);
    };
    
    // Limb generation
    class LimbGenerator {
    public:
        static void addLimbs(std::unique_ptr<Mesh>& mesh, int limbCount, BodyType bodyType, float size);
        static void addArms(std::unique_ptr<Mesh>& mesh, int armCount, float size);
        static void addLegs(std::unique_ptr<Mesh>& mesh, int legCount, float size);
        static void addWings(std::unique_ptr<Mesh>& mesh, int wingCount, float size);
        static void addTentacles(std::unique_ptr<Mesh>& mesh, int tentacleCount, float size);
    };
    
    // Appendage generation
    class AppendageGenerator {
    public:
        static void addHeads(std::unique_ptr<Mesh>& mesh, int headCount, int eyeCount, float size);
        static void addHorns(std::unique_ptr<Mesh>& mesh, HornType hornType, int hornCount, float size);
        static void addTails(std::unique_ptr<Mesh>& mesh, TailType tailType, int tailCount, float size);
        static void addEyes(std::unique_ptr<Mesh>& mesh, int eyeCount, float size);
    };
    
    // Noise and displacement
    class NoiseGenerator {
    public:
        static void applyNoise(std::unique_ptr<Mesh>& mesh, float noiseDetail, uint32_t seed);
        static void applyVertexDisplacement(std::unique_ptr<Mesh>& mesh, float intensity, uint32_t seed);
        static void applySurfaceDetail(std::unique_ptr<Mesh>& mesh, float detail, uint32_t seed);
    };
    
    // Main mesh generation function
    MeshHandle build(const MonsterParams& params);
}

// Texture generation namespace
namespace TextureGen {
    // Base texture generation
    class BaseTexture {
    public:
        static std::unique_ptr<Texture> generate2D(float scale, float detail, uint32_t seed);
        static std::unique_ptr<Texture> generatePerlin(float scale, float detail, uint32_t seed);
        static std::unique_ptr<Texture> generateCellular(float scale, float detail, uint32_t seed);
        static std::unique_ptr<Texture> generateWorley(float scale, float detail, uint32_t seed);
    };
    
    // Pattern generation
    class PatternGenerator {
    public:
        static std::unique_ptr<Texture> overlayPattern(std::unique_ptr<Texture>& base, 
                                                     PatternType patternType, 
                                                     const glm::vec3& color, 
                                                     float intensity);
        static std::unique_ptr<Texture> generateStripes(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateSpots(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateScales(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateSkin(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateCrystal(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateGlow(float scale, const glm::vec3& color, uint32_t seed);
        static std::unique_ptr<Texture> generateCamouflage(float scale, const glm::vec3& color, uint32_t seed);
    };
    
    // Material map generation
    class MaterialGenerator {
    public:
        static std::unique_ptr<Texture> generateNormalMap(const std::unique_ptr<Texture>& heightMap);
        static std::unique_ptr<Texture> generateRoughnessMap(float roughness, float variation);
        static std::unique_ptr<Texture> generateMetallicMap(float metallic, float variation);
        static std::unique_ptr<Texture> generateEmissiveMap(float emissive, const glm::vec3& color);
        static std::unique_ptr<Texture> generateAOMap(const std::unique_ptr<Texture>& heightMap);
    };
    
    // Main texture generation function
    TextureHandle build(const MonsterParams& params);
}

// Skeleton generation namespace
namespace RigGen {
    // Bone hierarchy generation
    class SkeletonBuilder {
    public:
        SkeletonBuilder& addRootBone(const std::string& name);
        SkeletonBuilder& addLimbChains(int limbCount, BodyType bodyType);
        SkeletonBuilder& addHeadBones(int headCount);
        SkeletonBuilder& addWingBones(int wingCount);
        SkeletonBuilder& addTailBones(int tailCount);
        SkeletonBuilder& addHornBones(int hornCount);
        SkeletonHandle finalize();
    };
    
    // Bone positioning
    class BonePositioner {
    public:
        static void positionHumanoidBones(std::unique_ptr<Skeleton>& skeleton, float size);
        static void positionQuadrupedBones(std::unique_ptr<Skeleton>& skeleton, float size);
        static void positionInsectoidBones(std::unique_ptr<Skeleton>& skeleton, float size);
        static void positionAmorphousBones(std::unique_ptr<Skeleton>& skeleton, float size);
    };
    
    // Main skeleton generation function
    SkeletonHandle build(const MonsterParams& params);
}

// Animation generation namespace
namespace AnimGen {
    // Animation profile generation
    class AnimationProfile {
    public:
        static std::unique_ptr<Animation> createBeastBasic(int limbCount, float size);
        static std::unique_ptr<Animation> createPredator(int limbCount, float size);
        static std::unique_ptr<Animation> createPackHunter(int limbCount, float size);
        static std::unique_ptr<Animation> createHorrorFloat(int limbCount, float size);
        static std::unique_ptr<Animation> createInsectScuttle(int limbCount, float size);
        static std::unique_ptr<Animation> createAquaticSwim(int limbCount, float size);
        static std::unique_ptr<Animation> createAvianFly(int limbCount, float size);
        static std::unique_ptr<Animation> createCrystalPulse(int limbCount, float size);
    };
    
    // Keyframe generation
    class KeyframeGenerator {
    public:
        static void generateIdleAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size);
        static void generateWalkAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size);
        static void generateRunAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size);
        static void generateAttackAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size);
        static void generateDeathAnimation(std::unique_ptr<Animation>& anim, int limbCount, float size);
    };
    
    // Main animation generation function
    AnimationHandle build(const MonsterParams& params);
}

// AI generation namespace
namespace AIGen {
    // Behavior tree generation
    class BehaviorTreeBuilder {
    public:
        static std::unique_ptr<AI> createPassiveAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createNeutralAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createPredatorAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createPackHunterAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createBossAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createMinionAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createGuardianAI(const BehaviorParams& params);
        static std::unique_ptr<AI> createWandererAI(const BehaviorParams& params);
    };
    
    // State machine generation
    class StateMachineBuilder {
    public:
        static void addPatrolState(std::unique_ptr<AI>& ai, const BehaviorParams& params);
        static void addCombatState(std::unique_ptr<AI>& ai, const BehaviorParams& params);
        static void addSocialState(std::unique_ptr<AI>& ai, const BehaviorParams& params);
        static void addEnvironmentalState(std::unique_ptr<AI>& ai, const BehaviorParams& params);
    };
    
    // Main AI generation function
    AIHandle build(const BehaviorParams& params);
}

// Main monster generation orchestrator
class MonsterGenerator {
public:
    MonsterGenerator();
    ~MonsterGenerator();
    
    // Initialize the generator
    void initialize(size_t cacheSize = 1000, size_t numThreads = 4);
    void shutdown();
    
    // Generate monster assets
    std::future<MonsterAssetBundle> generateAsync(const MonsterParams& params);
    MonsterAssetBundle generate(const MonsterParams& params);
    
    // Generate individual components
    MeshHandle generateMesh(const MonsterParams& params);
    TextureHandle generateTexture(const MonsterParams& params);
    SkeletonHandle generateSkeleton(const MonsterParams& params);
    AnimationHandle generateAnimation(const MonsterParams& params);
    AIHandle generateAI(const BehaviorParams& params);
    
    // Utility functions
    void clearCache();
    size_t getCacheSize() const;
    size_t getCacheHits() const;
    size_t getCacheMisses() const;
    float getGenerationTime() const;
    
    // C++23 Modern features
    bool isInitialized() const { return m_initialized; }
    bool isGenerating() const { return m_generating; }
    float getProgress() const { return m_progress; }
    
private:
    // Internal state
    bool m_initialized = false;
    bool m_generating = false;
    float m_progress = 0.0f;
    float m_generationTime = 0.0f;
    
    // Cache and threading
    std::unique_ptr<ConcurrentLRUCache<uint64_t, MonsterAssetBundle>> m_cache;
    std::unique_ptr<ThreadPool> m_threadPool;
    
    // Generation statistics
    size_t m_cacheHits = 0;
    size_t m_cacheMisses = 0;
    size_t m_totalGenerations = 0;
    
    // Internal generation methods
    MonsterAssetBundle generateMonsterAssets(const MonsterParams& params);
    void updateProgress(float progress);
    void logGenerationStats(const MonsterParams& params, const MonsterAssetBundle& bundle);
};

} // namespace Monsters
} // namespace MagiTech
