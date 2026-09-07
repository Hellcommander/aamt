#pragma once

#include "CrossbowAssetFactory.hpp"
#include "AIArtGenerator.hpp"
#include "core/Log.hpp"
#include <string>
#include <vector>
#include <memory>
#include <fstream>

namespace MagiTech {
namespace Crossbows {

// OpenStarbound Asset Generator for Crossbows with AI Art Integration
class CrossbowAssetGenerator {
public:
    struct AssetOutput {
        std::string itemFile;      // .activeitem JSON
        std::string framesFile;    // .frames JSON
        std::string spriteFile;    // .png sprite (AI-generated)
        std::string iconFile;      // .png icon (AI-generated)
        std::string projectileFile; // .projectile JSON for bolts/arrows
        std::string behaviorFile;  // .lua behavior script
        std::string effectFile;    // .json effect configuration
        std::string metadataFile;  // .json AI generation metadata
    };

    struct ItemConfig {
        std::string itemName;
        std::string description;
        std::string rarity;
        std::string category;
        std::string level;
        std::string damageType;
        float damage;
        float fireRate;
        std::string abilityType;
        std::vector<std::string> projectileTypes;
        
        // Integration with existing systems
        std::string behaviorSystem;     // "lua", "cpp", "hybrid"
        std::string effectSystem;       // "spell", "projectile", "custom"
        std::vector<std::string> specialEffects; // ["explosive", "piercing", "elemental"]
        std::string materialSystem;     // "vanilla", "magitech", "custom"
        
        // AI Art generation settings
        bool useAIArt;                  // Enable AI art generation
        std::string artStyle;           // "pixel-art", "realistic", "cartoon"
        std::string colorPalette;       // "starbound", "neon", "earth-tone"
        std::vector<std::string> artEffects; // ["metallic", "glowing", "weathered"]
    };

    CrossbowAssetGenerator();
    ~CrossbowAssetGenerator() = default;

    // Initialize with AI art generator
    void initialize(std::shared_ptr<AIArt::AIArtGenerator> aiGenerator);

    // Generate complete OpenStarbound assets with AI art
    AssetOutput generateCrossbowAssets(const CrossbowParams& params, const ItemConfig& config);
    AssetOutput generateBoltAssets(const BoltParams& params, const ItemConfig& config);
    AssetOutput generateArrowAssets(const ArrowParams& params, const ItemConfig& config);

    // Asset file generation helpers
    std::string generateActiveItemJSON(const CrossbowParams& params, const ItemConfig& config);
    std::string generateProjectileJSON(const BoltParams& params, const ItemConfig& config);
    std::string generateProjectileJSON(const ArrowParams& params, const ItemConfig& config);
    std::string generateFramesJSON(const std::string& spriteName, int frameCount);
    std::string generateBehaviorScript(const CrossbowParams& params, const ItemConfig& config);
    std::string generateEffectConfig(const CrossbowParams& params, const ItemConfig& config);
    
    // AI Art integration
    AIArt::ArtOutput generateCrossbowArt(const CrossbowParams& params, const ItemConfig& config);
    AIArt::ArtOutput generateBoltArt(const BoltParams& params, const ItemConfig& config);
    AIArt::ArtOutput generateArrowArt(const ArrowParams& params, const ItemConfig& config);
    
    // Fallback sprite generation (if AI art fails)
    bool generateFallbackSprite(const std::string& outputPath, const CrossbowParams& params);
    bool generateFallbackSprite(const std::string& outputPath, const BoltParams& params);
    bool generateFallbackSprite(const std::string& outputPath, const ArrowParams& params);
    bool generateFallbackIcon(const std::string& outputPath, const std::string& itemName);

    // File system helpers
    bool createDirectory(const std::string& path);
    bool writeFile(const std::string& path, const std::string& content);
    std::string sanitizeFilename(const std::string& name);

private:
    std::string outputBasePath;
    std::shared_ptr<AIArt::AIArtGenerator> aiGenerator;
    
    // Template helpers
    std::string getCrossbowItemTemplate();
    std::string getProjectileTemplate();
    std::string getFramesTemplate();
    std::string getBehaviorTemplate();
    std::string getEffectTemplate();
    
    // Asset naming
    std::string generateAssetName(const std::string& baseName, const std::string& suffix);
    std::string generateDescription(const CrossbowParams& params);
    std::string generateDescription(const BoltParams& params);
    std::string generateDescription(const ArrowParams& params);
    
    // Integration helpers
    std::string integrateWithBehaviorSystem(const ItemConfig& config);
    std::string integrateWithEffectSystem(const ItemConfig& config);
    std::string integrateWithMaterialSystem(const ItemConfig& config);
    
    // AI Art prompt generation
    AIArt::ArtPrompt createCrossbowArtPrompt(const CrossbowParams& params, const ItemConfig& config);
    AIArt::ArtPrompt createBoltArtPrompt(const BoltParams& params, const ItemConfig& config);
    AIArt::ArtPrompt createArrowArtPrompt(const ArrowParams& params, const ItemConfig& config);
};

// Global asset generator instance
extern std::unique_ptr<CrossbowAssetGenerator> g_assetGenerator;

} // namespace Crossbows
} // namespace MagiTech 
