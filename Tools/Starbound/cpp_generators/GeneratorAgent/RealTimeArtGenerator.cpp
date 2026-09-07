#include "RealTimeArtGenerator.hpp"
#include "AIArtGenerator.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include "core/graphics/Graphics.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <xxhash.h>
#include <random>

namespace MagiTech {
namespace RealTimeArt {

// Global real-time art generator instance
std::unique_ptr<RealTimeArtGenerator> g_realTimeArtGenerator;

RealTimeArtGenerator::RealTimeArtGenerator() : shutdown_(false) {
    pool = std::make_unique<ThreadPool>(4);
    stats_ = {0, 0, 0, 0, 0.0f, 0.0f};
}

RealTimeArtGenerator::~RealTimeArtGenerator() {
    shutdown_ = true;
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

bool RealTimeArtGenerator::initialize(const AIArt::ModelConfig& aiConfig) {
    try {
        // Initialize AI art generator
        aiGenerator = std::make_shared<AIArt::AIArtGenerator>();
        if (!aiGenerator->initialize(aiConfig)) {
            Log::error("Failed to initialize AI art generator");
            return false;
        }
        
        // Start worker threads
        workers_.reserve(4);
        for (int i = 0; i < 2; ++i) {
            workers_.emplace_back(&RealTimeArtGenerator::workerThread, this);
        }
        for (int i = 0; i < 2; ++i) {
            workers_.emplace_back(&RealTimeArtGenerator::damageWorkerThread, this);
        }
        
        Log::info("Real-time art generator initialized successfully");
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to initialize real-time art generator: {}", e.what());
        return false;
    }
}

void RealTimeArtGenerator::shutdown() {
    shutdown_ = true;
    Log::info("Real-time art generator shutdown");
}

void RealTimeArtGenerator::generate(const GenDef& def, std::function<void(TextureHandle)> callback) {
    static uint64_t requestId = 0;
    tasks_.enqueue({def, callback, ++requestId});
    
    {
        std::lock_guard<std::mutex> lock(statsMutex_);
        stats_.totalRequests++;
    }
}

void RealTimeArtGenerator::generateCrossbow(const CrossbowParams& params, const GenDef& def, 
                                          std::function<void(TextureHandle)> callback) {
    GenDef crossbowDef = def;
    crossbowDef.prompt = generatePrompt(params, def);
    generate(crossbowDef, callback);
}

void RealTimeArtGenerator::generateBolt(const BoltParams& params, const GenDef& def, 
                                      std::function<void(TextureHandle)> callback) {
    GenDef boltDef = def;
    boltDef.prompt = generatePrompt(params, def);
    generate(boltDef, callback);
}

void RealTimeArtGenerator::generateArrow(const ArrowParams& params, const GenDef& def, 
                                       std::function<void(TextureHandle)> callback) {
    GenDef arrowDef = def;
    arrowDef.prompt = generatePrompt(params, def);
    generate(arrowDef, callback);
}

void RealTimeArtGenerator::editDamage(const DamageParams& params, std::function<void(TextureHandle)> callback) {
    static uint64_t requestId = 0;
    damageTasks_.enqueue({params, callback, ++requestId});
}

void RealTimeArtGenerator::addBulletHole(uint32_t baseTexId, float x, float y, float intensity, 
                                        std::function<void(TextureHandle)> callback) {
    DamageParams params;
    params.baseTexId = baseTexId;
    params.impactX = x;
    params.impactY = y;
    params.intensity = intensity;
    params.seed = std::random_device()();
    params.useAI = false;
    params.damageType = "bullet_hole";
    editDamage(params, callback);
}

void RealTimeArtGenerator::addCrack(uint32_t baseTexId, float x, float y, float intensity, 
                                   std::function<void(TextureHandle)> callback) {
    DamageParams params;
    params.baseTexId = baseTexId;
    params.impactX = x;
    params.impactY = y;
    params.intensity = intensity;
    params.seed = std::random_device()();
    params.useAI = false;
    params.damageType = "crack";
    editDamage(params, callback);
}

void RealTimeArtGenerator::addBurn(uint32_t baseTexId, float x, float y, float intensity, 
                                  std::function<void(TextureHandle)> callback) {
    DamageParams params;
    params.baseTexId = baseTexId;
    params.impactX = x;
    params.impactY = y;
    params.intensity = intensity;
    params.seed = std::random_device()();
    params.useAI = false;
    params.damageType = "burn";
    editDamage(params, callback);
}

void RealTimeArtGenerator::generateBatch(const std::vector<GenDef>& defs, 
                                       std::function<void(std::vector<TextureHandle>)> callback) {
    std::vector<std::future<TextureHandle>> futures;
    std::vector<TextureHandle> results;
    
    for (const auto& def : defs) {
        auto future = pool->enqueue([this, def]() {
            return runModel(def);
        });
        futures.push_back(std::move(future));
    }
    
    for (auto& future : futures) {
        results.push_back(future.get());
    }
    
    callback(results);
}

void RealTimeArtGenerator::generateCrossbowBatch(const std::vector<std::pair<CrossbowParams, GenDef>>& items,
                                               std::function<void(std::vector<TextureHandle>)> callback) {
    std::vector<GenDef> defs;
    for (const auto& item : items) {
        GenDef def = item.second;
        def.prompt = generatePrompt(item.first, item.second);
        defs.push_back(def);
    }
    generateBatch(defs, callback);
}

void RealTimeArtGenerator::update() {
    Result result;
    while (results_.try_dequeue(result)) {
        if (result.callback) {
            result.callback(result.texture);
        }
    }
}

void RealTimeArtGenerator::clearCache() {
    textureCache.clear();
    damageCache.clear();
    Log::info("Cleared real-time art cache");
}

size_t RealTimeArtGenerator::getCacheSize() const {
    return textureCache.size() + damageCache.size();
}

bool RealTimeArtGenerator::isCached(const std::string& key) const {
    return textureCache.find(key) != textureCache.end() || 
           damageCache.find(key) != damageCache.end();
}

RealTimeArtGenerator::Stats RealTimeArtGenerator::getStats() const {
    std::lock_guard<std::mutex> lock(statsMutex_);
    return stats_;
}

void RealTimeArtGenerator::workerThread() {
    Task task;
    while (!shutdown_) {
        if (tasks_.try_dequeue(task)) {
            auto start = std::chrono::high_resolution_clock::now();
            
            TextureHandle texture = runModel(task.def);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            {
                std::lock_guard<std::mutex> lock(statsMutex_);
                stats_.aiGenerations++;
                stats_.averageGenerationTime = 
                    (stats_.averageGenerationTime * (stats_.aiGenerations - 1) + duration.count()) / stats_.aiGenerations;
            }
            
            results_.enqueue({texture, task.callback, task.requestId});
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
}

void RealTimeArtGenerator::damageWorkerThread() {
    DamageTask task;
    while (!shutdown_) {
        if (damageTasks_.try_dequeue(task)) {
            auto start = std::chrono::high_resolution_clock::now();
            
            TextureHandle texture;
            if (task.params.useAI) {
                texture = runDamageModel(task.params);
            } else {
                texture = runShaderDamage(task.params);
            }
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            {
                std::lock_guard<std::mutex> lock(statsMutex_);
                stats_.shaderEdits++;
                stats_.averageDamageEditTime = 
                    (stats_.averageDamageEditTime * (stats_.shaderEdits - 1) + duration.count()) / stats_.shaderEdits;
            }
            
            results_.enqueue({texture, task.callback, task.requestId});
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runModel(const GenDef& def) {
    std::string hash = hashGenDef(def);
    
    // Check cache first
    if (isCached(hash)) {
        {
            std::lock_guard<std::mutex> lock(statsMutex_);
            stats_.cacheHits++;
        }
        return textureCache[hash];
    }
    
    // Generate using AI
    AIArt::ArtPrompt prompt = createArtPrompt(def);
    AIArt::ArtOutput output = aiGenerator->generateSprite(prompt);
    
    if (!output.success) {
        Log::error("Failed to generate sprite: {}", output.errorMessage);
        return {0, 0, 0, false};
    }
    
    // Load and process the generated image
    std::vector<uint8_t> rgbaData = loadImageData(output.spriteFile);
    TextureHandle texture = postProcessSprite(rgbaData, def);
    
    // Cache the result
    textureCache[hash] = texture;
    
    return texture;
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runDamageModel(const DamageParams& params) {
    std::string hash = hashDamageParams(params);
    
    // Check cache first
    if (damageCache.find(hash) != damageCache.end()) {
        return damageCache[hash];
    }
    
    // Generate using AI inpainting
    AIArt::ArtPrompt prompt = createDamagePrompt(params);
    AIArt::ArtOutput output = aiGenerator->generateSprite(prompt);
    
    if (!output.success) {
        Log::error("Failed to generate damage: {}", output.errorMessage);
        return {0, 0, 0, false};
    }
    
    // Load and process the generated image
    std::vector<uint8_t> rgbaData = loadImageData(output.spriteFile);
    TextureHandle texture = createTexture2D(rgbaData, params.outW, params.outH);
    
    // Cache the result
    damageCache[hash] = texture;
    
    return texture;
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runShaderDamage(const DamageParams& params) {
    std::string hash = hashDamageParams(params);
    
    // Check cache first
    if (damageCache.find(hash) != damageCache.end()) {
        return damageCache[hash];
    }
    
    // Generate using shader
    std::vector<uint8_t> rgbaData;
    if (params.damageType == "bullet_hole") {
        rgbaData = generateBulletHoleShader(params);
    } else if (params.damageType == "crack") {
        rgbaData = generateCrackShader(params);
    } else if (params.damageType == "burn") {
        rgbaData = generateBurnShader(params);
    } else {
        rgbaData = generateBulletHoleShader(params); // Default
    }
    
    TextureHandle texture = createTexture2D(rgbaData, 64, 64); // Default size
    
    // Cache the result
    damageCache[hash] = texture;
    
    return texture;
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::postProcessSprite(const std::vector<uint8_t>& rgbaData, const GenDef& def) {
    // Apply post-processing: palette quantization, alpha trimming, etc.
    std::vector<uint8_t> processedData = rgbaData;
    
    // Quantize to 32-color palette
    quantizePalette(processedData, 32);
    
    // Trim alpha borders
    trimAlphaBorders(processedData, def.outW, def.outH);
    
    // Create texture
    return createTexture2D(processedData, def.outW, def.outH);
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::packDirections(const std::vector<TextureHandle>& directions, const GenDef& def) {
    // Pack multiple direction sprites into a single texture sheet
    if (directions.size() != def.directions) {
        Log::error("Direction count mismatch: expected {}, got {}", def.directions, directions.size());
        return {0, 0, 0, false};
    }
    
    // Create a packed texture (for now, just return the first direction)
    return directions[0];
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::createTexture2D(const std::vector<uint8_t>& data, int width, int height) {
    // This would upload to GPU and return a texture handle
    // For now, create a placeholder
    static uint32_t nextTextureId = 1;
    return {nextTextureId++, width, height, true};
}

std::string RealTimeArtGenerator::hashGenDef(const GenDef& def) {
    XXH64_state_t state;
    XXH64_reset(&state, 0);
    
    XXH64_update(&state, def.prompt.c_str(), def.prompt.length());
    XXH64_update(&state, &def.outW, sizeof(def.outW));
    XXH64_update(&state, &def.outH, sizeof(def.outH));
    XXH64_update(&state, &def.directions, sizeof(def.directions));
    XXH64_update(&state, &def.seed, sizeof(def.seed));
    XXH64_update(&state, def.style.c_str(), def.style.length());
    XXH64_update(&state, def.palette.c_str(), def.palette.length());
    
    for (const auto& effect : def.effects) {
        XXH64_update(&state, effect.c_str(), effect.length());
    }
    
    return std::to_string(XXH64_digest(&state));
}

std::string RealTimeArtGenerator::hashDamageParams(const DamageParams& params) {
    XXH64_state_t state;
    XXH64_reset(&state, 0);
    
    XXH64_update(&state, &params.baseTexId, sizeof(params.baseTexId));
    XXH64_update(&state, &params.impactX, sizeof(params.impactX));
    XXH64_update(&state, &params.impactY, sizeof(params.impactY));
    XXH64_update(&state, &params.intensity, sizeof(params.intensity));
    XXH64_update(&state, &params.seed, sizeof(params.seed));
    XXH64_update(&state, &params.useAI, sizeof(params.useAI));
    XXH64_update(&state, params.prompt.c_str(), params.prompt.length());
    XXH64_update(&state, params.damageType.c_str(), params.damageType.length());
    
    return std::to_string(XXH64_digest(&state));
}

std::string RealTimeArtGenerator::generatePrompt(const CrossbowParams& params, const GenDef& def) {
    std::ostringstream prompt;
    prompt << def.prompt << ", " << params.stockMaterial << " stock, " 
           << params.limbMaterial << " limbs, " << params.stringMaterial << " string, "
           << "draw length " << params.drawLength << "m, draw weight " << params.drawWeight << "N, "
           << "clean lines, " << def.directions << "-directional, " << def.outW << "x" << def.outH;
    return prompt.str();
}

std::string RealTimeArtGenerator::generatePrompt(const BoltParams& params, const GenDef& def) {
    std::ostringstream prompt;
    prompt << def.prompt << ", length " << params.length << "m, "
           << "shaft radius " << params.shaftRadius << "m, ";
    if (params.barbedTip) {
        prompt << "barbed tip, ";
    }
    if (params.useFletching) {
        prompt << params.fletchMaterial << " fletching, ";
    }
    prompt << "tip mass " << params.tipMass << "kg, clean lines, " << def.outW << "x" << def.outH;
    return prompt.str();
}

std::string RealTimeArtGenerator::generatePrompt(const ArrowParams& params, const GenDef& def) {
    std::ostringstream prompt;
    prompt << def.prompt << ", shaft length " << params.shaftLength << "m, "
           << "shaft diameter " << params.shaftDiameter << "m, "
           << "spine rating " << params.spineRating << ", ";
    if (params.useFletching) {
        prompt << params.fletchStyle << " fletching, ";
    }
    prompt << "nock size " << params.nockSize << "m, tip mass " << params.tipMass << "kg, "
           << "clean lines, " << def.outW << "x" << def.outH;
    return prompt.str();
}

AIArt::ArtPrompt RealTimeArtGenerator::createArtPrompt(const GenDef& def) {
    AIArt::ArtPrompt prompt;
    prompt.description = def.prompt;
    prompt.style = def.style;
    prompt.resolution = def.outW;
    prompt.frameCount = def.directions;
    prompt.direction = def.directions == 8 ? "8-directional" : 
                      def.directions == 4 ? "4-directional" : "single";
    prompt.useAlpha = true;
    prompt.colorPalette = def.palette;
    prompt.specialEffects = def.effects;
    return prompt;
}

AIArt::ArtPrompt RealTimeArtGenerator::createDamagePrompt(const DamageParams& params) {
    AIArt::ArtPrompt prompt;
    prompt.description = "pixel-art " + params.damageType + ", " + params.prompt;
    prompt.style = "pixel-art";
    prompt.resolution = 64;
    prompt.frameCount = 1;
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.colorPalette = "starbound";
    prompt.specialEffects = {"damaged"};
    return prompt;
}

std::vector<uint8_t> RealTimeArtGenerator::generateBulletHoleShader(const DamageParams& params) {
    // Generate a simple bullet hole effect using procedural noise
    std::vector<uint8_t> data(64 * 64 * 4, 0);
    
    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    
    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            float dx = (x - params.impactX * 64) / 64.0f;
            float dy = (y - params.impactY * 64) / 64.0f;
            float distance = std::sqrt(dx * dx + dy * dy);
            
            if (distance < params.intensity * 0.3f) {
                // Bullet hole core
                int idx = (y * 64 + x) * 4;
                data[idx] = 0;     // R
                data[idx + 1] = 0; // G
                data[idx + 2] = 0; // B
                data[idx + 3] = 255; // A
            } else if (distance < params.intensity * 0.6f) {
                // Burn ring
                float alpha = (1.0f - distance / (params.intensity * 0.6f)) * 255;
                int idx = (y * 64 + x) * 4;
                data[idx] = 64;     // R
                data[idx + 1] = 32; // G
                data[idx + 2] = 16; // B
                data[idx + 3] = static_cast<uint8_t>(alpha);
            }
        }
    }
    
    return data;
}

std::vector<uint8_t> RealTimeArtGenerator::generateCrackShader(const DamageParams& params) {
    // Generate crack pattern using procedural noise
    std::vector<uint8_t> data(64 * 64 * 4, 0);
    
    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    
    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            float dx = (x - params.impactX * 64) / 64.0f;
            float dy = (y - params.impactY * 64) / 64.0f;
            float distance = std::sqrt(dx * dx + dy * dy);
            
            if (distance < params.intensity * 0.4f) {
                // Crack pattern
                float noise = dist(rng);
                if (noise < 0.3f) {
                    int idx = (y * 64 + x) * 4;
                    data[idx] = 32;     // R
                    data[idx + 1] = 32; // G
                    data[idx + 2] = 32; // B
                    data[idx + 3] = 255; // A
                }
            }
        }
    }
    
    return data;
}

std::vector<uint8_t> RealTimeArtGenerator::generateBurnShader(const DamageParams& params) {
    // Generate burn effect
    std::vector<uint8_t> data(64 * 64 * 4, 0);
    
    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    
    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            float dx = (x - params.impactX * 64) / 64.0f;
            float dy = (y - params.impactY * 64) / 64.0f;
            float distance = std::sqrt(dx * dx + dy * dy);
            
            if (distance < params.intensity * 0.5f) {
                // Burn effect
                float alpha = (1.0f - distance / (params.intensity * 0.5f)) * 255;
                int idx = (y * 64 + x) * 4;
                data[idx] = 128;   // R
                data[idx + 1] = 64; // G
                data[idx + 2] = 32; // B
                data[idx + 3] = static_cast<uint8_t>(alpha);
            }
        }
    }
    
    return data;
}

// Helper functions (would be implemented with actual image processing libraries)
std::vector<uint8_t> loadImageData(const std::string& path) {
    // Placeholder - would load actual image data
    return std::vector<uint8_t>(64 * 64 * 4, 128);
}

void quantizePalette(std::vector<uint8_t>& data, int colors) {
    // Placeholder - would quantize to specified color count
}

void trimAlphaBorders(std::vector<uint8_t>& data, int width, int height) {
    // Placeholder - would trim transparent borders
}

} // namespace RealTimeArt
} // namespace MagiTech 
