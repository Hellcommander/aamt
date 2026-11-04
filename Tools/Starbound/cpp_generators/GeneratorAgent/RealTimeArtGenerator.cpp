#include "RealTimeArtGenerator.hpp"
#include "GeneratorConcurrency.hpp"
#include "AIArtGenerator.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include <stb_image.h>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <iomanip>
#include <xxhash.h>
#include <random>

namespace MagiTech {
namespace RealTimeArt {

// Global real-time art generator instance
std::unique_ptr<RealTimeArtGenerator> g_realTimeArtGenerator;

namespace {

// Loads an image file as RGBA8 and resamples it (nearest neighbour) to width x height.
// Returns an empty vector when the file cannot be decoded.
std::vector<uint8_t> loadImageData(const std::string& path, int width, int height) {
    int w = 0, h = 0, channels = 0;
    stbi_uc* pixels = stbi_load(path.c_str(), &w, &h, &channels, 4);
    if (!pixels || w <= 0 || h <= 0 || width <= 0 || height <= 0) {
        if (pixels) stbi_image_free(pixels);
        return {};
    }
    std::vector<uint8_t> out(static_cast<size_t>(width) * height * 4);
    for (int y = 0; y < height; ++y) {
        const int sy = std::min(h - 1, y * h / height);
        for (int x = 0; x < width; ++x) {
            const int sx = std::min(w - 1, x * w / width);
            std::copy_n(pixels + (static_cast<size_t>(sy) * w + sx) * 4, 4, out.begin() + (static_cast<size_t>(y) * width + x) * 4);
        }
    }
    stbi_image_free(pixels);
    return out;
}

// Reduces the image to at most `colors` colours: the most frequent 5-bit-per-channel
// colours become the palette and every opaque pixel snaps to the nearest entry.
void quantizePalette(std::vector<uint8_t>& data, int colors) {
    if (colors <= 0 || data.size() < 4) return;
    auto key = [](const uint8_t* p) {
        return (static_cast<uint32_t>(p[0] >> 3) << 10) | (static_cast<uint32_t>(p[1] >> 3) << 5) | static_cast<uint32_t>(p[2] >> 3);
    };
    std::map<uint32_t, size_t> histogram;
    for (size_t i = 0; i + 3 < data.size(); i += 4) {
        if (data[i + 3] == 0) continue;
        histogram[key(&data[i])]++;
    }
    if (histogram.size() <= static_cast<size_t>(colors)) return;

    std::vector<std::pair<size_t, uint32_t>> byCount;
    byCount.reserve(histogram.size());
    for (const auto& [k, count] : histogram) byCount.emplace_back(count, k);
    std::partial_sort(byCount.begin(), byCount.begin() + colors, byCount.end(),
                      [](const auto& a, const auto& b) { return a.first > b.first; });

    std::vector<std::array<int, 3>> palette;
    for (int i = 0; i < colors; ++i) {
        const uint32_t k = byCount[i].second;
        palette.push_back({static_cast<int>(((k >> 10) & 31) << 3 | 4),
                           static_cast<int>(((k >> 5) & 31) << 3 | 4),
                           static_cast<int>((k & 31) << 3 | 4)});
    }
    for (size_t i = 0; i + 3 < data.size(); i += 4) {
        if (data[i + 3] == 0) continue;
        int best = 0;
        int bestDist = INT32_MAX;
        for (int p = 0; p < colors; ++p) {
            const int dr = data[i] - palette[p][0];
            const int dg = data[i + 1] - palette[p][1];
            const int db = data[i + 2] - palette[p][2];
            const int dist = dr * dr + dg * dg + db * db;
            if (dist < bestDist) { bestDist = dist; best = p; }
        }
        data[i] = static_cast<uint8_t>(palette[best][0]);
        data[i + 1] = static_cast<uint8_t>(palette[best][1]);
        data[i + 2] = static_cast<uint8_t>(palette[best][2]);
    }
}

// Crops away fully transparent borders and re-centres the content in the same canvas.
void trimAlphaBorders(std::vector<uint8_t>& data, int width, int height) {
    if (width <= 0 || height <= 0 || data.size() < static_cast<size_t>(width) * height * 4) return;
    int minX = width, minY = height, maxX = -1, maxY = -1;
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            if (data[(static_cast<size_t>(y) * width + x) * 4 + 3] != 0) {
                minX = std::min(minX, x); maxX = std::max(maxX, x);
                minY = std::min(minY, y); maxY = std::max(maxY, y);
            }
        }
    }
    if (maxX < 0) return;   // fully transparent
    const int contentW = maxX - minX + 1;
    const int contentH = maxY - minY + 1;
    const int offX = (width - contentW) / 2;
    const int offY = (height - contentH) / 2;
    if (offX == minX && offY == minY) return;

    std::vector<uint8_t> out(data.size(), 0);
    for (int y = 0; y < contentH; ++y) {
        std::copy_n(data.begin() + (static_cast<size_t>(minY + y) * width + minX) * 4, static_cast<size_t>(contentW) * 4,
                    out.begin() + (static_cast<size_t>(offY + y) * width + offX) * 4);
    }
    data.swap(out);
}

} // namespace

RealTimeArtGenerator::RealTimeArtGenerator() : shutdown_(false) {
    pool = std::make_unique<GeneratorTaskPool>(4);
    stats_ = Stats{};
}

RealTimeArtGenerator::~RealTimeArtGenerator() {
    shutdown();
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
        shutdown_ = false;
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
        Log::error("RealTimeArt", "Failed to initialize real-time art generator: {}", e.what());
        return false;
    }
}

void RealTimeArtGenerator::shutdown() {
    shutdown_ = true;
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    workers_.clear();
    if (pool) pool->stop();
    Log::info("Real-time art generator shutdown");
}

void RealTimeArtGenerator::generate(const GenDef& def, std::function<void(TextureHandle)> callback) {
    tasks_.enqueue({def, std::move(callback), ++nextRequestId_});

    {
        std::lock_guard<std::mutex> lock(statsMutex_);
        stats_.totalRequests++;
    }
}

void RealTimeArtGenerator::generateCrossbow(const CrossbowParams& params, const GenDef& def,
                                          std::function<void(TextureHandle)> callback) {
    GenDef crossbowDef = def;
    crossbowDef.prompt = generatePrompt(params, def);
    generate(crossbowDef, std::move(callback));
}

void RealTimeArtGenerator::generateBolt(const BoltParams& params, const GenDef& def,
                                      std::function<void(TextureHandle)> callback) {
    GenDef boltDef = def;
    boltDef.prompt = generatePrompt(params, def);
    generate(boltDef, std::move(callback));
}

void RealTimeArtGenerator::generateArrow(const ArrowParams& params, const GenDef& def,
                                       std::function<void(TextureHandle)> callback) {
    GenDef arrowDef = def;
    arrowDef.prompt = generatePrompt(params, def);
    generate(arrowDef, std::move(callback));
}

void RealTimeArtGenerator::editDamage(const DamageParams& params, std::function<void(TextureHandle)> callback) {
    damageTasks_.enqueue({params, std::move(callback), ++nextRequestId_});

    std::lock_guard<std::mutex> lock(statsMutex_);
    stats_.totalRequests++;
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
    editDamage(params, std::move(callback));
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
    editDamage(params, std::move(callback));
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
    editDamage(params, std::move(callback));
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

    if (callback) callback(results);
}

void RealTimeArtGenerator::generateCrossbowBatch(const std::vector<std::pair<CrossbowParams, GenDef>>& items,
                                               std::function<void(std::vector<TextureHandle>)> callback) {
    std::vector<GenDef> defs;
    for (const auto& item : items) {
        GenDef def = item.second;
        def.prompt = generatePrompt(item.first, item.second);
        defs.push_back(def);
    }
    generateBatch(defs, std::move(callback));
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
    std::lock_guard<std::mutex> lock(cacheMutex_);
    textureCache.clear();
    damageCache.clear();
    Log::info("Cleared real-time art cache");
}

size_t RealTimeArtGenerator::getCacheSize() const {
    std::lock_guard<std::mutex> lock(cacheMutex_);
    return textureCache.size() + damageCache.size();
}

bool RealTimeArtGenerator::isCached(const std::string& key) const {
    std::lock_guard<std::mutex> lock(cacheMutex_);
    return textureCache.find(key) != textureCache.end() ||
           damageCache.find(key) != damageCache.end();
}

RealTimeArtGenerator::Stats RealTimeArtGenerator::getStats() const {
    std::lock_guard<std::mutex> lock(statsMutex_);
    return stats_;
}

bool RealTimeArtGenerator::getTextureData(uint32_t textureId, std::vector<uint8_t>& rgba, int& width, int& height) const {
    std::lock_guard<std::mutex> lock(texturesMutex_);
    auto it = textures_.find(textureId);
    if (it == textures_.end()) return false;
    rgba = it->second.rgba;
    width = it->second.width;
    height = it->second.height;
    return true;
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

            results_.enqueue({texture, std::move(task.callback), task.requestId});
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

            results_.enqueue({texture, std::move(task.callback), task.requestId});
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runModel(const GenDef& def) {
    std::string hash = hashGenDef(def);

    // Check cache first
    {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        if (auto it = textureCache.find(hash); it != textureCache.end()) {
            std::lock_guard<std::mutex> statsLock(statsMutex_);
            stats_.cacheHits++;
            return it->second;
        }
    }

    if (!aiGenerator) {
        Log::error("RealTimeArt", "Cannot generate sprite: AI art generator not initialized");
        return {0, 0, 0, false};
    }

    // Generate one sprite per direction using AI
    std::vector<TextureHandle> directions;
    const int directionCount = std::max(1, def.directions);
    for (int d = 0; d < directionCount; ++d) {
        AIArt::ArtPrompt prompt = createArtPrompt(def);
        if (directionCount > 1) {
            prompt.description += ", facing direction " + std::to_string(d + 1) + " of " + std::to_string(directionCount);
        }
        AIArt::ArtOutput output = aiGenerator->generateSprite(prompt);
        if (!output.success) {
            Log::error("RealTimeArt", "Failed to generate sprite: {}", output.errorMessage);
            return {0, 0, 0, false};
        }

        // Load and process the generated image
        std::vector<uint8_t> rgbaData = loadImageData(output.spriteFile, def.outW, def.outH);
        if (rgbaData.empty()) {
            Log::error("RealTimeArt", "Generated sprite is not a readable image: {}", output.spriteFile);
            return {0, 0, 0, false};
        }
        directions.push_back(postProcessSprite(rgbaData, def));
    }

    TextureHandle texture = directionCount > 1 ? packDirections(directions, def) : directions.front();

    // Cache the result
    if (texture.isValid) {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        textureCache[hash] = texture;
    }

    return texture;
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runDamageModel(const DamageParams& params) {
    std::string hash = hashDamageParams(params);

    // Check cache first
    {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        if (auto it = damageCache.find(hash); it != damageCache.end()) {
            return it->second;
        }
    }

    if (!aiGenerator) {
        Log::error("RealTimeArt", "AI damage requested without an AI art generator; using shader damage");
        return runShaderDamage(params);
    }

    // Generate using AI inpainting
    AIArt::ArtPrompt prompt = createDamagePrompt(params);
    AIArt::ArtOutput output = aiGenerator->generateSprite(prompt);

    if (!output.success) {
        Log::error("RealTimeArt", "Failed to generate damage: {}", output.errorMessage);
        return {0, 0, 0, false};
    }

    // Load and process the generated image (same size as the base texture when known)
    int width = prompt.resolution, height = prompt.resolution;
    {
        std::lock_guard<std::mutex> lock(texturesMutex_);
        if (auto it = textures_.find(params.baseTexId); it != textures_.end()) {
            width = it->second.width;
            height = it->second.height;
        }
    }
    std::vector<uint8_t> rgbaData = loadImageData(output.spriteFile, width, height);
    if (rgbaData.empty()) {
        Log::error("RealTimeArt", "Generated damage is not a readable image: {}", output.spriteFile);
        return {0, 0, 0, false};
    }
    TextureHandle texture = createTexture2D(rgbaData, width, height);

    // Cache the result
    std::lock_guard<std::mutex> lock(cacheMutex_);
    damageCache[hash] = texture;

    return texture;
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::runShaderDamage(const DamageParams& params) {
    std::string hash = hashDamageParams(params);

    // Check cache first
    {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        if (auto it = damageCache.find(hash); it != damageCache.end()) {
            return it->second;
        }
    }

    // Generate the 64x64 damage overlay
    std::vector<uint8_t> overlay;
    if (params.damageType == "bullet_hole") {
        overlay = generateBulletHoleShader(params);
    } else if (params.damageType == "crack") {
        overlay = generateCrackShader(params);
    } else if (params.damageType == "burn") {
        overlay = generateBurnShader(params);
    } else {
        overlay = generateBulletHoleShader(params); // Default
    }

    // Composite onto the base texture when it is one of ours; otherwise return the overlay itself
    std::vector<uint8_t> base;
    int width = 64, height = 64;
    if (!getTextureData(params.baseTexId, base, width, height)) {
        base.assign(overlay.begin(), overlay.end());
        width = height = 64;
    } else {
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                const size_t o = (static_cast<size_t>(y * 64 / height) * 64 + (x * 64 / width)) * 4;
                const size_t b = (static_cast<size_t>(y) * width + x) * 4;
                const float a = overlay[o + 3] / 255.0f;
                for (int c = 0; c < 3; ++c) {
                    base[b + c] = static_cast<uint8_t>(overlay[o + c] * a + base[b + c] * (1.0f - a));
                }
                // Holes punch through: keep the base alpha unless the overlay is fully opaque black
                if (overlay[o + 3] == 255 && overlay[o] == 0 && overlay[o + 1] == 0 && overlay[o + 2] == 0) {
                    base[b + 3] = 0;
                }
            }
        }
    }

    TextureHandle texture = createTexture2D(base, width, height);

    // Cache the result
    std::lock_guard<std::mutex> lock(cacheMutex_);
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
    // Pack multiple direction sprites into a single horizontal texture sheet
    if (directions.size() != static_cast<size_t>(def.directions)) {
        Log::error("RealTimeArt", "Direction count mismatch: expected {}, got {}", def.directions, directions.size());
        return {0, 0, 0, false};
    }

    const int cellW = def.outW, cellH = def.outH;
    const int sheetW = cellW * static_cast<int>(directions.size());
    std::vector<uint8_t> sheet(static_cast<size_t>(sheetW) * cellH * 4, 0);
    for (size_t d = 0; d < directions.size(); ++d) {
        std::vector<uint8_t> cell;
        int w = 0, h = 0;
        if (!getTextureData(directions[d].id, cell, w, h) || w != cellW || h != cellH) {
            Log::error("RealTimeArt", "Direction {} has no pixel data of the expected size", d);
            return {0, 0, 0, false};
        }
        for (int y = 0; y < cellH; ++y) {
            std::copy_n(cell.begin() + static_cast<size_t>(y) * cellW * 4, static_cast<size_t>(cellW) * 4,
                        sheet.begin() + (static_cast<size_t>(y) * sheetW + d * cellW) * 4);
        }
    }
    return createTexture2D(sheet, sheetW, cellH);
}

RealTimeArtGenerator::TextureHandle RealTimeArtGenerator::createTexture2D(const std::vector<uint8_t>& data, int width, int height) {
    // Registers the pixels under a new handle; the renderer uploads them via getTextureData().
    if (width <= 0 || height <= 0 || data.size() < static_cast<size_t>(width) * height * 4) {
        return {0, 0, 0, false};
    }
    const uint32_t id = nextTextureId_++;
    {
        std::lock_guard<std::mutex> lock(texturesMutex_);
        textures_[id] = TexturePixels{data, width, height};
    }
    return {id, width, height, true};
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
    AIArt::ArtPrompt prompt{};
    prompt.description = def.prompt;
    prompt.style = def.style;
    prompt.resolution = def.outW;
    prompt.frameCount = 1;   // one sprite per request; directions are generated separately and packed
    prompt.direction = def.directions == 8 ? "8-directional" :
                      def.directions == 4 ? "4-directional" : "single";
    prompt.useAlpha = true;
    prompt.colorPalette = def.palette;
    prompt.specialEffects = def.effects;
    return prompt;
}

AIArt::ArtPrompt RealTimeArtGenerator::createDamagePrompt(const DamageParams& params) {
    AIArt::ArtPrompt prompt{};
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
    // Bullet hole: opaque core, scorched ring fading outwards, slightly jagged edge
    std::vector<uint8_t> data(64 * 64 * 4, 0);

    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> jitter(0.9f, 1.1f);

    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            float dx = (x - params.impactX * 64) / 64.0f;
            float dy = (y - params.impactY * 64) / 64.0f;
            float distance = std::sqrt(dx * dx + dy * dy) * jitter(rng);

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
                data[idx + 3] = static_cast<uint8_t>(std::clamp(alpha, 0.0f, 255.0f));
            }
        }
    }

    return data;
}

std::vector<uint8_t> RealTimeArtGenerator::generateCrackShader(const DamageParams& params) {
    // Crack pattern: random-walk fractures radiating from the impact point
    std::vector<uint8_t> data(64 * 64 * 4, 0);

    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);

    const int branches = 3 + static_cast<int>(params.intensity * 5.0f);
    const float maxLength = params.intensity * 0.4f * 64.0f;
    for (int b = 0; b < branches; ++b) {
        float angle = dist(rng) * 6.2831853f;
        float px = params.impactX * 64.0f;
        float py = params.impactY * 64.0f;
        for (float travelled = 0.0f; travelled < maxLength; travelled += 1.0f) {
            angle += (dist(rng) - 0.5f) * 0.6f;
            px += std::cos(angle);
            py += std::sin(angle);
            const int x = static_cast<int>(px), y = static_cast<int>(py);
            if (x < 0 || y < 0 || x >= 64 || y >= 64) break;
            int idx = (y * 64 + x) * 4;
            data[idx] = 32;     // R
            data[idx + 1] = 32; // G
            data[idx + 2] = 32; // B
            data[idx + 3] = 255; // A
        }
    }

    return data;
}

std::vector<uint8_t> RealTimeArtGenerator::generateBurnShader(const DamageParams& params) {
    // Burn: soft scorch mark with noisy edge
    std::vector<uint8_t> data(64 * 64 * 4, 0);

    std::mt19937 rng(params.seed);
    std::uniform_real_distribution<float> dist(0.85f, 1.0f);

    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            float dx = (x - params.impactX * 64) / 64.0f;
            float dy = (y - params.impactY * 64) / 64.0f;
            float distance = std::sqrt(dx * dx + dy * dy);

            if (distance < params.intensity * 0.5f) {
                // Burn effect
                float alpha = (1.0f - distance / (params.intensity * 0.5f)) * 255 * dist(rng);
                int idx = (y * 64 + x) * 4;
                data[idx] = 128;   // R
                data[idx + 1] = 64; // G
                data[idx + 2] = 32; // B
                data[idx + 3] = static_cast<uint8_t>(std::clamp(alpha, 0.0f, 255.0f));
            }
        }
    }

    return data;
}

} // namespace RealTimeArt
} // namespace MagiTech
