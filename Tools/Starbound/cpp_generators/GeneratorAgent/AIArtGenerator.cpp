#include "AIArtGenerator.hpp"
#include "GeneratorConcurrency.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <cctype>
#include "vendor/json/include/nlohmann/json.hpp"
#include <xxhash.h>
#include <stb_image_write.h>
#include <cmath>

namespace MagiTech {
namespace AIArt {

// Global AI art generator instance
std::unique_ptr<AIArtGenerator> g_aiArtGenerator;

AIArtGenerator::AIArtGenerator() : isInitialized(false) {
    pool = std::make_unique<GeneratorTaskPool>(4);
}

bool AIArtGenerator::initialize(const ModelConfig& config) {
    try {
        currentConfig = config;
        
        // Initialize AI model (placeholder - would integrate with actual AI backend)
        if (!loadModel(config)) {
            Log::error("AIArt", "Failed to load AI model: {}", config.modelPath);
            return false;
        }
        
        isInitialized = true;
        Log::info("AI Art Generator initialized successfully");
        return true;
    } catch (const std::exception& e) {
        Log::error("AIArt", "Failed to initialize AI Art Generator: {}", e.what());
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
        if (auto cached = findCached(promptHash)) {
            output = *cached;
            Log::info("AIArt", "Retrieved cached art for prompt: {}", prompt.description);
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
        nlohmann::json metadata = {
            {"prompt", prompt.description},
            {"style", prompt.style},
            {"colorPalette", prompt.colorPalette},
            {"resolution", prompt.resolution},
            {"frameCount", prompt.frameCount},
            {"direction", prompt.direction},
            {"useAlpha", prompt.useAlpha},
            {"specialEffects", prompt.specialEffects}
        };

        std::ofstream metadataFile(metadataPath);
        metadataFile << metadata.dump(2);
        metadataFile.close();
        
        // Set output paths
        output.spriteFile = spritePath;
        output.iconFile = iconPath;
        output.framesFile = framesPath;
        output.metadataFile = metadataPath;
        output.success = true;
        
        // Cache the result
        {
            std::lock_guard<std::mutex> lock(cacheMutex);
            artCache[promptHash] = output;
        }
        
        Log::info("AIArt", "Generated AI art: {}", prompt.description);
        return output;
        
    } catch (const std::exception& e) {
        output.errorMessage = e.what();
        Log::error("AIArt", "Failed to generate sprite: {}", e.what());
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
        if (!std::filesystem::exists(inputPath)) {
            Log::error("AIArt", "Sprite to post-process does not exist: {}", inputPath);
            return false;
        }
        // In-place processing: nothing to copy
        if (std::filesystem::path(inputPath).lexically_normal() != std::filesystem::path(outputPath).lexically_normal()) {
            std::filesystem::copy_file(inputPath, outputPath, std::filesystem::copy_options::overwrite_existing);
        }
        return true;
    } catch (const std::exception& e) {
        Log::error("AIArt", "Failed to post-process sprite: {}", e.what());
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
        Log::error("AIArt", "Failed to create icon: {}", e.what());
        return false;
    }
}

void AIArtGenerator::clearCache() {
    std::lock_guard<std::mutex> lock(cacheMutex);
    artCache.clear();
    Log::info("Cleared AI art cache");
}

size_t AIArtGenerator::getCacheSize() const {
    std::lock_guard<std::mutex> lock(cacheMutex);
    return artCache.size();
}

bool AIArtGenerator::isCached(const std::string& promptHash) const {
    std::lock_guard<std::mutex> lock(cacheMutex);
    return artCache.find(promptHash) != artCache.end();
}

std::optional<AIArtGenerator::ArtOutput> AIArtGenerator::findCached(const std::string& promptHash) const {
    std::lock_guard<std::mutex> lock(cacheMutex);
    auto it = artCache.find(promptHash);
    if (it == artCache.end()) return std::nullopt;
    return it->second;
}

bool AIArtGenerator::loadModel(const ModelConfig& config) {
    // This would load the actual AI model
    // For now, just log the attempt
    Log::info("AIArt", "Loading AI model: {}", config.modelPath);
    Log::info("AIArt", "Using LoRA: {}", config.loraPath);
    Log::info("AIArt", "Style tokens: {}", config.styleTokens);
    return true;
}

bool AIArtGenerator::generateImage(const ArtPrompt& prompt, const std::string& outputPath) {
    // No diffusion backend is linked into the backend; render a deterministic
    // procedural sprite from the prompt instead, so the rest of the pipeline
    // (post-processing, frames, icons, real-time loading) works on real PNGs.
    Log::info("AIArt", "Generating image for prompt: {}", prompt.description);
    Log::info("AIArt", "Output path: {}", outputPath);

    const int size = std::clamp(prompt.resolution > 0 ? prompt.resolution : 32, 8, 512);
    const int frames = std::clamp(prompt.frameCount > 0 ? prompt.frameCount : 1, 1, 16);
    const int width = size * frames;
    std::vector<uint8_t> rgba(static_cast<size_t>(width) * size * 4, 0);

    // Palette: base hue from the prompt hash, tinted by the requested palette name
    const uint64_t seed = XXH64(prompt.description.data(), prompt.description.size(), 0);
    float r = ((seed >> 0) & 0xFF) / 255.0f, g = ((seed >> 8) & 0xFF) / 255.0f, b = ((seed >> 16) & 0xFF) / 255.0f;
    if (prompt.colorPalette == "neon") { r = std::max(r, 0.3f); g = std::max(g, 0.8f); b = 1.0f; }
    else if (prompt.colorPalette == "earth-tone") { r = 0.45f + r * 0.2f; g = 0.35f + g * 0.15f; b = 0.2f + b * 0.1f; }
    const bool metallic = std::find(prompt.specialEffects.begin(), prompt.specialEffects.end(), "metallic") != prompt.specialEffects.end();
    const bool glowing = std::find(prompt.specialEffects.begin(), prompt.specialEffects.end(), "glowing") != prompt.specialEffects.end();

    for (int f = 0; f < frames; ++f) {
        const float phase = frames > 1 ? static_cast<float>(f) / frames : 0.0f;
        for (int y = 0; y < size; ++y) {
            for (int x = 0; x < size; ++x) {
                // Diamond silhouette that "breathes" over the frames
                const float nx = (x + 0.5f) / size - 0.5f;
                const float ny = (y + 0.5f) / size - 0.5f;
                const float extent = 0.38f + 0.04f * std::sin(phase * 6.2831853f);
                const float d = std::abs(nx) + std::abs(ny) * 1.3f;
                if (d > extent) continue;
                float shade = 1.0f - d / extent * 0.6f;          // lighter centre
                if (metallic) shade *= 0.85f + 0.15f * ((x + y) % 4 == 0);
                if (glowing && d > extent * 0.8f) shade = 1.0f;  // bright rim
                const bool outline = d > extent - 1.5f / size;
                uint8_t* p = &rgba[(static_cast<size_t>(y) * width + f * size + x) * 4];
                p[0] = outline ? 20 : static_cast<uint8_t>(std::clamp(r * shade, 0.0f, 1.0f) * 255);
                p[1] = outline ? 20 : static_cast<uint8_t>(std::clamp(g * shade, 0.0f, 1.0f) * 255);
                p[2] = outline ? 28 : static_cast<uint8_t>(std::clamp(b * shade, 0.0f, 1.0f) * 255);
                p[3] = 255;
            }
        }
    }

    if (!stbi_write_png(outputPath.c_str(), width, size, 4, rgba.data(), width * 4)) {
        Log::error("AIArt", "Failed to write image: {}", outputPath);
        return false;
    }
    return true;
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
        [](char c) { return !std::isalnum(static_cast<unsigned char>(c)) && c != '_' && c != '-'; }), sanitized.end());
    return sanitized;
}

bool AIArtGenerator::createDirectory(const std::string& path) {
    try {
        std::filesystem::create_directories(path);
        return true;
    } catch (const std::exception& e) {
        Log::error("AIArt", "Failed to create directory {}: {}", path, e.what());
        return false;
    }
}

} // namespace AIArt
} // namespace MagiTech 
