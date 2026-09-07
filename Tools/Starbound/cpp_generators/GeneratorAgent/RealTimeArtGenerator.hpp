#pragma once

#include "AIArtGenerator.hpp"
#include "core/Log.hpp"
#include "core/threading/ThreadPool.hpp"
#include "core/graphics/Texture.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <functional>
#include <unordered_map>

namespace MagiTech {
namespace RealTimeArt {

// Real-Time In-Game AI Art Generation Pipeline
class RealTimeArtGenerator {
public:
    struct GenDef {
        std::string prompt;
        int outW, outH;        // e.g. 64×64
        int directions;         // 1, 4, 8
        int seed;
        std::string style;     // "pixel-art", "realistic", "cartoon"
        std::string palette;   // "starbound", "neon", "earth-tone"
        std::vector<std::string> effects; // ["metallic", "glowing", "weathered"]
    };

    struct DamageParams {
        uint32_t baseTexId;
        float impactX, impactY;  // UV coordinates
        float intensity;          // 0–1
        uint32_t seed;
        bool useAI;
        std::string prompt;
        std::string damageType;  // "bullet_hole", "crack", "burn", "rust"
    };

    struct TextureHandle {
        uint32_t id;
        int width, height;
        bool isValid;
    };

    struct Task {
        GenDef def;
        std::function<void(TextureHandle)> callback;
        uint64_t requestId;
    };

    struct Result {
        TextureHandle texture;
        std::function<void(TextureHandle)> callback;
        uint64_t requestId;
    };

    struct DamageTask {
        DamageParams params;
        std::function<void(TextureHandle)> callback;
        uint64_t requestId;
    };

    RealTimeArtGenerator();
    ~RealTimeArtGenerator() = default;

    // Initialize the real-time pipeline
    bool initialize(const AIArt::ModelConfig& aiConfig);
    void shutdown();

    // Main generation API
    void generate(const GenDef& def, std::function<void(TextureHandle)> callback);
    void generateCrossbow(const CrossbowParams& params, const GenDef& def, 
                         std::function<void(TextureHandle)> callback);
    void generateBolt(const BoltParams& params, const GenDef& def, 
                     std::function<void(TextureHandle)> callback);
    void generateArrow(const ArrowParams& params, const GenDef& def, 
                      std::function<void(TextureHandle)> callback);

    // Damage editing API
    void editDamage(const DamageParams& params, std::function<void(TextureHandle)> callback);
    void addBulletHole(uint32_t baseTexId, float x, float y, float intensity, 
                       std::function<void(TextureHandle)> callback);
    void addCrack(uint32_t baseTexId, float x, float y, float intensity, 
                  std::function<void(TextureHandle)> callback);
    void addBurn(uint32_t baseTexId, float x, float y, float intensity, 
                 std::function<void(TextureHandle)> callback);

    // Batch operations
    void generateBatch(const std::vector<GenDef>& defs, 
                      std::function<void(std::vector<TextureHandle>)> callback);
    void generateCrossbowBatch(const std::vector<std::pair<CrossbowParams, GenDef>>& items,
                              std::function<void(std::vector<TextureHandle>)> callback);

    // Update loop - must be called per frame
    void update();

    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    bool isCached(const std::string& key) const;

    // Performance monitoring
    struct Stats {
        uint64_t totalRequests;
        uint64_t cacheHits;
        uint64_t aiGenerations;
        uint64_t shaderEdits;
        float averageGenerationTime;
        float averageDamageEditTime;
    };
    Stats getStats() const;

private:
    std::unique_ptr<ThreadPool> pool;
    std::shared_ptr<AIArt::AIArtGenerator> aiGenerator;
    
    // Task queues
    moodycamel::ConcurrentQueue<Task> tasks_;
    moodycamel::ConcurrentQueue<DamageTask> damageTasks_;
    moodycamel::ConcurrentQueue<Result> results_;
    
    // Cache
    std::unordered_map<std::string, TextureHandle> textureCache;
    std::unordered_map<std::string, TextureHandle> damageCache;
    
    // Stats
    mutable Stats stats_;
    mutable std::mutex statsMutex_;
    
    // Worker threads
    std::vector<std::thread> workers_;
    std::atomic<bool> shutdown_;
    
    // Internal methods
    void workerThread();
    void damageWorkerThread();
    
    // Generation helpers
    TextureHandle runModel(const GenDef& def);
    TextureHandle runDamageModel(const DamageParams& params);
    TextureHandle runShaderDamage(const DamageParams& params);
    
    // Post-processing
    TextureHandle postProcessSprite(const std::vector<uint8_t>& rgbaData, const GenDef& def);
    TextureHandle packDirections(const std::vector<TextureHandle>& directions, const GenDef& def);
    TextureHandle createTexture2D(const std::vector<uint8_t>& data, int width, int height);
    
    // Utility functions
    std::string hashGenDef(const GenDef& def);
    std::string hashDamageParams(const DamageParams& params);
    std::string generatePrompt(const CrossbowParams& params, const GenDef& def);
    std::string generatePrompt(const BoltParams& params, const GenDef& def);
    std::string generatePrompt(const ArrowParams& params, const GenDef& def);
    
    // Shader damage effects
    std::vector<uint8_t> generateBulletHoleShader(const DamageParams& params);
    std::vector<uint8_t> generateCrackShader(const DamageParams& params);
    std::vector<uint8_t> generateBurnShader(const DamageParams& params);
    
    // AI integration
    AIArt::ArtPrompt createArtPrompt(const GenDef& def);
    AIArt::ArtPrompt createDamagePrompt(const DamageParams& params);
};

// Global real-time art generator instance
extern std::unique_ptr<RealTimeArtGenerator> g_realTimeArtGenerator;

} // namespace RealTimeArt
} // namespace MagiTech 
