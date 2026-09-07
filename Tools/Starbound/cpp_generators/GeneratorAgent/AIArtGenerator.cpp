#include "AIArtGenerator.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <xxhash.h>

namespace MagiTech {
namespace AIArt {

// Global AI art generator instance
std::unique_ptr<AIArtGenerator> g_aiArtGenerator;

AIArtGenerator::AIArtGenerator() : isInitialized(false) {
    pool = std::make_unique<ThreadPool>(4);
}

AIArtGenerator::~AIArtGenerator() = default;

bool AIArtGenerator::initialize(const ModelConfig& config) {
    try {
        currentConfig = config;
        
        // Initialize AI model (placeholder - would integrate with actual AI backend)
        if (!loadModel(config)) {
            Log::error("Failed to load AI model: {}", config.modelPath);
            return false;
        }
        
        isInitialized = true;
        Log::info("AI Art Generator initialized successfully");
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to initialize AI Art Generator: {}", e.what());
        return false;
    }
}

void AIArtGenerator::shutdown() {
    isInitialized = false;
    Log::info("AI Art Generator shutdown");
}

std::future<AIArtGenerator::ArtOutput> AIArtGenerator::generateSpriteAsync(const ArtPrompt& prompt) {
    return pool->enqueue([this, prompt]() {
        return generateSprite(prompt);
    });
}

std::future<AIArtGenerator::ArtOutput> AIArtGenerator::generateCrossbowSpriteAsync(
    const CrossbowParams& params, const ArtPrompt& prompt) {
    return pool->enqueue([this, params, prompt]() {
        return generateCrossbowSprite(params, prompt);
    });
}

std::future<AIArtGenerator::ArtOutput> AIArtGenerator::generateBoltSpriteAsync(
    const BoltParams& params, const ArtPrompt& prompt) {
    return pool->enqueue([this, params, prompt]() {
        return generateBoltSprite(params, prompt);
    });
}

std::future<AIArtGenerator::ArtOutput> AIArtGenerator::generateArrowSpriteAsync(
    const ArrowParams& params, const ArtPrompt& prompt) {
    return pool->enqueue([this, params, prompt]() {
        return generateArrowSprite(params, prompt);
    });
}

AIArtGenerator::ArtOutput AIArtGenerator::generateSprite(const ArtPrompt& prompt) {
    ArtOutput output;
    output.success = false;
    
    if (!isInitialized) {
        output.errorMessage = "AI Art Generator not initialized";
        return output;
    }
    
    try {
        std::string promptHash = hashPrompt(prompt);
        
        // Check cache first
        if (isCached(promptHash)) {
            output = artCache[promptHash];
            Log::info("Retrieved cached art for prompt: {}", prompt.description);
            return output;
        }
        
        // Generate unique filename
        std::string baseName = sanitizeFilename(prompt.description);
        std::string outputDir = "items/active/weapons/crossbow/generated/";
        createDirectory(outputDir);
        
        std::string spritePath = outputDir + baseName + ".png";
        std::string iconPath = outputDir + baseName + "_icon.png";
        std::string framesPath = outputDir + baseName + ".frames";
        std::string metadataPath = outputDir + baseName + "_metadata.json";
        
        // Generate the sprite using AI
        if (!generateImage(prompt, spritePath)) {
            output.errorMessage = "Failed to generate sprite image";
            return output;
        }
        
        // Post-process the generated sprite
        if (!postProcessSprite(spritePath, spritePath, prompt)) {
            output.errorMessage = "Failed to post-process sprite";
            return output;
        }
        
        // Create animation frames if needed
        if (prompt.frameCount > 1) {
            if (!createAnimationFrames(spritePath, prompt)) {
                output.errorMessage = "Failed to create animation frames";
                return output;
            }
        }
        
        // Create icon
        if (!createIcon(spritePath, iconPath)) {
            output.errorMessage = "Failed to create icon";
            return output;
        }
        
        // Create metadata
        std::ostringstream metadata;
        metadata << "{\n";
        metadata << "  \"prompt\" : \"" << prompt.description << "\",\n";
        metadata << "  \"style\" : \"" << prompt.style << "\",\n";
        metadata << "  \"resolution\" : " << prompt.resolution << ",\n";
        metadata << "  \"frameCount\" : " << prompt.frameCount << ",\n";
        metadata << "  \"direction\" : \"" << prompt.direction << "\",\n";
        metadata << "  \"useAlpha\" : " << (prompt.useAlpha ? "true" : "false") << ",\n";
        metadata << "  \"specialEffects\" : [";
        for (size_t i = 0; i < prompt.specialEffects.size(); ++i) {
            metadata << "\"" << prompt.specialEffects[i] << "\"";
            if (i < prompt.specialEffects.size() - 1) metadata << ", ";
        }
        metadata << "]\n";
        metadata << "}";
        
        std::ofstream metadataFile(metadataPath);
        metadataFile << metadata.str();
        metadataFile.close();
        
        // Set output paths
        output.spriteFile = spritePath;
        output.iconFile = iconPath;
        output.framesFile = framesPath;
        output.metadataFile = metadataPath;
        output.success = true;
        
        // Cache the result
        artCache[promptHash] = output;
        
        Log::info("Generated AI art: {}", prompt.description);
        return output;
        
    } catch (const std::exception& e) {
        output.errorMessage = e.what();
        Log::error("Failed to generate sprite: {}", e.what());
        return output;
    }
}

AIArtGenerator::ArtOutput AIArtGenerator::generateCrossbowSprite(
    const CrossbowParams& params, const ArtPrompt& prompt) {
    
    // Generate crossbow-specific prompt
    ArtPrompt crossbowPrompt = generateCrossbowPrompt(params, prompt.style);
    
    // Merge with user prompt
    crossbowPrompt.description = prompt.description + " " + crossbowPrompt.description;
    crossbowPrompt.specialEffects.insert(crossbowPrompt.specialEffects.end(), 
                                       prompt.specialEffects.begin(), prompt.specialEffects.end());
    
    return generateSprite(crossbowPrompt);
}

AIArtGenerator::ArtOutput AIArtGenerator::generateBoltSprite(
    const BoltParams& params, const ArtPrompt& prompt) {
    
    // Generate bolt-specific prompt
    ArtPrompt boltPrompt = generateBoltPrompt(params, prompt.style);
    
    // Merge with user prompt
    boltPrompt.description = prompt.description + " " + boltPrompt.description;
    boltPrompt.specialEffects.insert(boltPrompt.specialEffects.end(), 
                                   prompt.specialEffects.begin(), prompt.specialEffects.end());
    
    return generateSprite(boltPrompt);
}

AIArtGenerator::ArtOutput AIArtGenerator::generateArrowSprite(
    const ArrowParams& params, const ArtPrompt& prompt) {
    
    // Generate arrow-specific prompt
    ArtPrompt arrowPrompt = generateArrowPrompt(params, prompt.style);
    
    // Merge with user prompt
    arrowPrompt.description = prompt.description + " " + arrowPrompt.description;
    arrowPrompt.specialEffects.insert(arrowPrompt.specialEffects.end(), 
                                    prompt.specialEffects.begin(), prompt.specialEffects.end());
    
    return generateSprite(arrowPrompt);
}

std::vector<AIArtGenerator::ArtOutput> AIArtGenerator::generateBatch(
    const std::vector<ArtPrompt>& prompts) {
    
    std::vector<std::future<ArtOutput>> futures;
    std::vector<ArtOutput> results;
    
    // Start all generations
    for (const auto& prompt : prompts) {
        futures.push_back(generateSpriteAsync(prompt));
    }
    
    // Collect results
    for (auto& future : futures) {
        results.push_back(future.get());
    }
    
    return results;
}

std::vector<AIArtGenerator::ArtOutput> AIArtGenerator::generateCrossbowBatch(
    const std::vector<std::pair<CrossbowParams, ArtPrompt>>& items) {
    
    std::vector<std::future<ArtOutput>> futures;
    std::vector<ArtOutput> results;
    
    // Start all generations
    for (const auto& item : items) {
        futures.push_back(generateCrossbowSpriteAsync(item.first, item.second));
    }
    
    // Collect results
    for (auto& future : futures) {
        results.push_back(future.get());
    }
    
    return results;
}

AIArtGenerator::ArtPrompt AIArtGenerator::generateCrossbowPrompt(
    const CrossbowParams& params, const std::string& style) {
    
    ArtPrompt prompt;
    prompt.description = getCrossbowPromptTemplate(params);
    prompt.style = style;
    prompt.resolution = 64;
    prompt.frameCount = 8; // 8-directional animation
    prompt.direction = "8-directional";
    prompt.useAlpha = true;
    prompt.colorPalette = "starbound";
    
    // Add special effects based on materials
    if (params.stockMaterial.find("Metal") != std::string::npos) {
        prompt.specialEffects.push_back("metallic");
    }
    if (params.limbMaterial.find("Carbon") != std::string::npos) {
        prompt.specialEffects.push_back("futuristic");
    }
    if (params.stringMaterial.find("Kevlar") != std::string::npos) {
        prompt.specialEffects.push_back("high-tech");
    }
    
    return prompt;
}

AIArtGenerator::ArtPrompt AIArtGenerator::generateBoltPrompt(
    const BoltParams& params, const std::string& style) {
    
    ArtPrompt prompt;
    prompt.description = getBoltPromptTemplate(params);
    prompt.style = style;
    prompt.resolution = 32;
    prompt.frameCount = 1; // Single frame for bolts
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.colorPalette = "starbound";
    
    // Add special effects
    if (params.barbedTip) {
        prompt.specialEffects.push_back("barbed");
    }
    if (params.useFletching) {
        prompt.specialEffects.push_back("fletched");
    }
    
    return prompt;
}

AIArtGenerator::ArtPrompt AIArtGenerator::generateArrowPrompt(
    const ArrowParams& params, const std::string& style) {
    
    ArtPrompt prompt;
    prompt.description = getArrowPromptTemplate(params);
    prompt.style = style;
    prompt.resolution = 32;
    prompt.frameCount = 1; // Single frame for arrows
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.colorPalette = "starbound";
    
    // Add special effects
    if (params.useFletching) {
        prompt.specialEffects.push_back("fletched");
        if (params.fletchStyle == "Parabolic") {
            prompt.specialEffects.push_back("parabolic");
        }
    }
    
    return prompt;
}

bool AIArtGenerator::postProcessSprite(const std::string& inputPath, const std::string& outputPath, const ArtPrompt& prompt) {
    // This would integrate with image processing libraries
    // For now, just copy the file
    try {
        std::filesystem::copy_file(inputPath, outputPath, std::filesystem::copy_options::overwrite_existing);
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to post-process sprite: {}", e.what());
        return false;
    }
}

bool AIArtGenerator::createAnimationFrames(const std::string& spritePath, const ArtPrompt& prompt) {
    // This would create animation frame definitions
    // For now, create a placeholder frames file
    std::string framesPath = spritePath.substr(0, spritePath.find_last_of('.')) + ".frames";
    
    std::ostringstream frames;
    frames << "{\n";
    frames << "  \"animation\" : {\n";
    frames << "    \"frameGrid\" : {\n";
    frames << "      \"size\" : [" << prompt.resolution << ", " << prompt.resolution << "],\n";
    frames << "      \"dimensions\" : [" << prompt.frameCount << ", 1]\n";
    frames << "    }\n";
    frames << "  }\n";
    frames << "}";
    
    std::ofstream file(framesPath);
    file << frames.str();
    file.close();
    
    return true;
}

bool AIArtGenerator::createIcon(const std::string& spritePath, const std::string& iconPath) {
    // This would resize the sprite to create an icon
    // For now, just copy the file
    try {
        std::filesystem::copy_file(spritePath, iconPath, std::filesystem::copy_options::overwrite_existing);
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to create icon: {}", e.what());
        return false;
    }
}

void AIArtGenerator::clearCache() {
    artCache.clear();
    Log::info("Cleared AI art cache");
}

size_t AIArtGenerator::getCacheSize() const {
    return artCache.size();
}

bool AIArtGenerator::isCached(const std::string& promptHash) const {
    return artCache.find(promptHash) != artCache.end();
}

bool AIArtGenerator::loadModel(const ModelConfig& config) {
    // This would load the actual AI model
    // For now, just log the attempt
    Log::info("Loading AI model: {}", config.modelPath);
    Log::info("Using LoRA: {}", config.loraPath);
    Log::info("Style tokens: {}", config.styleTokens);
    return true;
}

bool AIArtGenerator::generateImage(const ArtPrompt& prompt, const std::string& outputPath) {
    // This would call the actual AI model
    // For now, create a placeholder image
    Log::info("Generating image for prompt: {}", prompt.description);
    Log::info("Output path: {}", outputPath);
    
    // Create a simple placeholder file
    std::ofstream file(outputPath, std::ios::binary);
    if (file.is_open()) {
        // In a real implementation, this would generate the actual image
        file.close();
        return true;
    }
    return false;
}

std::string AIArtGenerator::getCrossbowPromptTemplate(const CrossbowParams& params) {
    std::ostringstream prompt;
    prompt << "pixel-art crossbow, " << params.stockMaterial << " stock, " 
           << params.limbMaterial << " limbs, " << params.stringMaterial << " string, "
           << "draw length " << params.drawLength << "m, draw weight " << params.drawWeight << "N, "
           << "clean lines, 8-directional, 64x64";
    return prompt.str();
}

std::string AIArtGenerator::getBoltPromptTemplate(const BoltParams& params) {
    std::ostringstream prompt;
    prompt << "pixel-art bolt, length " << params.length << "m, "
           << "shaft radius " << params.shaftRadius << "m, ";
    if (params.barbedTip) {
        prompt << "barbed tip, ";
    }
    if (params.useFletching) {
        prompt << params.fletchMaterial << " fletching, ";
    }
    prompt << "tip mass " << params.tipMass << "kg, clean lines, 32x32";
    return prompt.str();
}

std::string AIArtGenerator::getArrowPromptTemplate(const ArrowParams& params) {
    std::ostringstream prompt;
    prompt << "pixel-art arrow, shaft length " << params.shaftLength << "m, "
           << "shaft diameter " << params.shaftDiameter << "m, "
           << "spine rating " << params.spineRating << ", ";
    if (params.useFletching) {
        prompt << params.fletchStyle << " fletching, ";
    }
    prompt << "nock size " << params.nockSize << "m, tip mass " << params.tipMass << "kg, "
           << "clean lines, 32x64";
    return prompt.str();
}

std::string AIArtGenerator::hashPrompt(const ArtPrompt& prompt) {
    XXH64_state_t state;
    XXH64_reset(&state, 0);
    
    XXH64_update(&state, prompt.description.c_str(), prompt.description.length());
    XXH64_update(&state, prompt.style.c_str(), prompt.style.length());
    XXH64_update(&state, &prompt.resolution, sizeof(prompt.resolution));
    XXH64_update(&state, &prompt.frameCount, sizeof(prompt.frameCount));
    XXH64_update(&state, prompt.direction.c_str(), prompt.direction.length());
    XXH64_update(&state, &prompt.useAlpha, sizeof(prompt.useAlpha));
    
    for (const auto& effect : prompt.specialEffects) {
        XXH64_update(&state, effect.c_str(), effect.length());
    }
    
    return std::to_string(XXH64_digest(&state));
}

std::string AIArtGenerator::sanitizeFilename(const std::string& name) {
    std::string sanitized = name;
    std::replace(sanitized.begin(), sanitized.end(), ' ', '_');
    sanitized.erase(std::remove_if(sanitized.begin(), sanitized.end(), 
        [](char c) { return !std::isalnum(c) && c != '_' && c != '-'; }), sanitized.end());
    return sanitized;
}

bool AIArtGenerator::createDirectory(const std::string& path) {
    try {
        std::filesystem::create_directories(path);
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to create directory {}: {}", path, e.what());
        return false;
    }
}

} // namespace AIArt
} // namespace MagiTech 
