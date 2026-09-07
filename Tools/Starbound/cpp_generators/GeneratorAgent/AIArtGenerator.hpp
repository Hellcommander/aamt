#pragma once

#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include "core/threading/ThreadPool.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>

namespace MagiTech {
namespace AIArt {

// AI-Driven Art Generation Pipeline
class AIArtGenerator {
public:
    struct ArtPrompt {
        std::string description;
        std::string style;
        std::string colorPalette;
        int resolution;
        int frameCount;
        std::string direction; // "8-directional", "4-directional", "single"
        bool useAlpha;
        std::vector<std::string> specialEffects;
    };

    struct ArtOutput {
        std::string spriteFile;
        std::string iconFile;
        std::string framesFile;
        std::string metadataFile;
        bool success;
        std::string errorMessage;
    };

    struct ModelConfig {
        std::string modelPath;
        std::string loraPath;
        std::string styleTokens;
        int maxSteps;
        float guidanceScale;
        bool useHalfPrecision;
        bool useTensorRT;
        int batchSize;
    };

    AIArtGenerator();
    ~AIArtGenerator() = default;

    // Initialize the AI pipeline
    bool initialize(const ModelConfig& config);
    void shutdown();

    // Generate art assets
    std::future<ArtOutput> generateSpriteAsync(const ArtPrompt& prompt);
    std::future<ArtOutput> generateCrossbowSpriteAsync(const CrossbowParams& params, const ArtPrompt& prompt);
    std::future<ArtOutput> generateBoltSpriteAsync(const BoltParams& params, const ArtPrompt& prompt);
    std::future<ArtOutput> generateArrowSpriteAsync(const ArrowParams& params, const ArtPrompt& prompt);

    // Synchronous versions
    ArtOutput generateSprite(const ArtPrompt& prompt);
    ArtOutput generateCrossbowSprite(const CrossbowParams& params, const ArtPrompt& prompt);
    ArtOutput generateBoltSprite(const BoltParams& params, const ArtPrompt& prompt);
    ArtOutput generateArrowSprite(const ArrowParams& params, const ArtPrompt& prompt);

    // Batch generation
    std::vector<ArtOutput> generateBatch(const std::vector<ArtPrompt>& prompts);
    std::vector<ArtOutput> generateCrossbowBatch(const std::vector<std::pair<CrossbowParams, ArtPrompt>>& items);

    // Prompt generation helpers
    ArtPrompt generateCrossbowPrompt(const CrossbowParams& params, const std::string& style = "pixel-art");
    ArtPrompt generateBoltPrompt(const BoltParams& params, const std::string& style = "pixel-art");
    ArtPrompt generateArrowPrompt(const ArrowParams& params, const std::string& style = "pixel-art");

    // Post-processing
    bool postProcessSprite(const std::string& inputPath, const std::string& outputPath, const ArtPrompt& prompt);
    bool createAnimationFrames(const std::string& spritePath, const ArtPrompt& prompt);
    bool createIcon(const std::string& spritePath, const std::string& iconPath);

    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    bool isCached(const std::string& promptHash) const;

private:
    std::unique_ptr<ThreadPool> pool;
    std::unordered_map<std::string, ArtOutput> artCache;
    ModelConfig currentConfig;
    bool isInitialized;

    // AI model interface (would integrate with Python/C++ wrapper)
    bool loadModel(const ModelConfig& config);
    bool generateImage(const ArtPrompt& prompt, const std::string& outputPath);
    
    // Prompt templates
    std::string getCrossbowPromptTemplate(const CrossbowParams& params);
    std::string getBoltPromptTemplate(const BoltParams& params);
    std::string getArrowPromptTemplate(const ArrowParams& params);
    
    // Utility functions
    std::string hashPrompt(const ArtPrompt& prompt);
    std::string sanitizeFilename(const std::string& name);
    bool createDirectory(const std::string& path);
};

// Global AI art generator instance
extern std::unique_ptr<AIArtGenerator> g_aiArtGenerator;

} // namespace AIArt
} // namespace MagiTech 
