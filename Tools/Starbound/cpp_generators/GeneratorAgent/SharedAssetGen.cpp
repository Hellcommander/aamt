#include "SharedAssetGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <unordered_set>
#include <queue>

namespace MagiTech {
namespace Audio {

// Constants
constexpr size_t DEFAULT_BUFFER_SIZE = 1024;
constexpr size_t PACK_HEADER_SIZE = 64;
constexpr size_t MAX_DEPENDENCY_DEPTH = 10;
constexpr float DEFAULT_COMPRESSION_QUALITY = 0.8f;

// SharedAssetGen Implementation
SharedAssetGen::SharedAssetGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_compressionQuality(DEFAULT_COMPRESSION_QUALITY)
    , m_enableDeduplication(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize with default settings
    m_enableHotReload = true;
    m_enableCaching = true;
    m_enableParallelProcessing = true;
    
    // Initialize asset importers
    initializeAssetImporters();
}

SharedAssetGen::~SharedAssetGen() = default;

AudioBundle SharedAssetGen::process(const SharedAssetParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "shared_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        
        // Load shared asset definition if provided
        SharedAssetDefinition sharedDef;
        if (!params.sharedDefinitionPath.empty()) {
            sharedDef = loadSharedAssetDefinition(params.sharedDefinitionPath);
        } else {
            sharedDef = createDefaultSharedAssetDefinition(params);
        }
        
        // Process shared asset pipeline
        SharedAssetResult result = processSharedAssetPipeline(sharedDef, params);
        
        // Set the processed data (use first audio asset for compatibility)
        if (!result.audioAssets.empty()) {
            bundle.buffer = result.audioAssets[0].audioData;
            bundle.meta.duration = static_cast<float>(result.audioAssets[0].audioData.size()) / (result.audioAssets[0].sampleRate * result.audioAssets[0].numChannels);
        }
        
        // Calculate quality metrics
        if (!bundle.buffer.empty()) {
            bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
            bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
            bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
            bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
        }
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Shared Asset Definition Loading
SharedAssetDefinition SharedAssetGen::loadSharedAssetDefinition(const std::string& filePath) {
    SharedAssetDefinition def;
    
    // TODO: Implement YAML/JSON parsing for shared asset definitions
    // For now, create a basic definition
    def.name = "core_shared";
    def.version = "2.1.0";
    def.description = "Core shared assets for the game";
    
    // Add model assets
    AssetEntry heroModel;
    heroModel.id = "hero_model";
    heroModel.type = AssetType::MODEL;
    heroModel.source = "models/hero.glb";
    heroModel.dependencies = {"hero_material"};
    def.assets.push_back(heroModel);
    
    // Add material assets
    AssetEntry heroMaterial;
    heroMaterial.id = "hero_material";
    heroMaterial.type = AssetType::MATERIAL;
    heroMaterial.source = "materials/hero.mat";
    def.assets.push_back(heroMaterial);
    
    // Add texture assets
    AssetEntry uiTexture;
    uiTexture.id = "common_ui_texture";
    uiTexture.type = AssetType::TEXTURE;
    uiTexture.source = "textures/ui/common_ui.png";
    uiTexture.compression = {TextureCompression::BC7, 4};
    def.assets.push_back(uiTexture);
    
    // Add audio assets
    AssetEntry uiClickSfx;
    uiClickSfx.id = "ui_click_sfx";
    uiClickSfx.type = AssetType::AUDIO;
    uiClickSfx.source = "audio/ui_click.wav";
    uiClickSfx.normalizeLUFS = -16.0f;
    def.assets.push_back(uiClickSfx);
    
    // Add script assets
    AssetEntry gameplayScript;
    gameplayScript.id = "gameplay_script";
    gameplayScript.type = AssetType::SCRIPT;
    gameplayScript.source = "scripts/gameplay.lua";
    def.assets.push_back(gameplayScript);
    
    return def;
}

SharedAssetDefinition SharedAssetGen::createDefaultSharedAssetDefinition(const SharedAssetParams& params) {
    SharedAssetDefinition def;
    def.name = "default_shared";
    def.version = "1.0.0";
    def.description = "Default shared assets";
    
    // Create a single audio asset entry
    AssetEntry audioAsset;
    audioAsset.id = "default_audio";
    audioAsset.type = AssetType::AUDIO;
    audioAsset.source = params.filePath;
    audioAsset.normalizeLUFS = -14.0f;
    def.assets.push_back(audioAsset);
    
    return def;
}

// Shared Asset Pipeline Processing
SharedAssetResult SharedAssetGen::processSharedAssetPipeline(const SharedAssetDefinition& sharedDef, const SharedAssetParams& params) {
    SharedAssetResult result;
    
    // Step 1: Import and convert assets
    std::vector<ProcessedAsset> processedAssets;
    for (const auto& assetEntry : sharedDef.assets) {
        ProcessedAsset processed = importAsset(assetEntry, params);
        processedAssets.push_back(processed);
    }
    
    // Step 2: Resolve dependencies
    DependencyGraph dependencyGraph = resolveDependencies(sharedDef, processedAssets);
    
    // Step 3: Post-process assets
    std::vector<ProcessedAsset> postProcessedAssets = postProcessAssets(processedAssets, dependencyGraph);
    
    // Step 4: Deduplicate assets
    std::vector<ProcessedAsset> deduplicatedAssets = deduplicateAssets(postProcessedAssets);
    
    // Step 5: Generate manifest
    result.manifest = generateManifest(sharedDef, deduplicatedAssets, dependencyGraph);
    
    // Step 6: Create shared pack
    result.sharedPack = createSharedPack(sharedDef, deduplicatedAssets, result.manifest);
    
    // Step 7: Categorize assets by type
    categorizeAssets(deduplicatedAssets, result);
    
    result.processedAssets = deduplicatedAssets;
    result.dependencyGraph = dependencyGraph;
    result.sharedDef = sharedDef;
    
    return result;
}

// Asset Importer Initialization
void SharedAssetGen::initializeAssetImporters() {
    // Initialize model importer
    m_modelImporter = std::make_unique<ModelImporter>();
    
    // Initialize texture importer
    m_textureImporter = std::make_unique<TextureImporter>();
    
    // Initialize audio importer
    m_audioImporter = std::make_unique<AudioImporter>();
    
    // Initialize script compiler
    m_scriptCompiler = std::make_unique<ScriptCompiler>();
    
    // Initialize material processor
    m_materialProcessor = std::make_unique<MaterialProcessor>();
}

// Asset Import
ProcessedAsset SharedAssetGen::importAsset(const AssetEntry& assetEntry, const SharedAssetParams& params) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = assetEntry.type;
    processed.sourcePath = assetEntry.source;
    processed.dependencies = assetEntry.dependencies;
    
    // Import based on asset type
    switch (assetEntry.type) {
        case AssetType::MODEL:
            processed = importModel(assetEntry);
            break;
        case AssetType::MATERIAL:
            processed = importMaterial(assetEntry);
            break;
        case AssetType::TEXTURE:
            processed = importTexture(assetEntry);
            break;
        case AssetType::AUDIO:
            processed = importAudio(assetEntry);
            break;
        case AssetType::SCRIPT:
            processed = importScript(assetEntry);
            break;
    }
    
    // Add metadata
    processed.metadata = assetEntry.metadata;
    processed.compressionSettings = assetEntry.compression;
    processed.normalizeLUFS = assetEntry.normalizeLUFS;
    
    return processed;
}

// Model Import
ProcessedAsset SharedAssetGen::importModel(const AssetEntry& assetEntry) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = AssetType::MODEL;
    processed.sourcePath = assetEntry.source;
    
    // TODO: Implement actual model importing
    // For now, create placeholder data
    ModelData modelData;
    modelData.vertexCount = 1000;
    modelData.indexCount = 2000;
    modelData.boundingBox = {glm::vec3(-1.0f), glm::vec3(1.0f)};
    modelData.lodLevels = 3;
    
    processed.modelData = modelData;
    processed.blobData = generateTestModelData();
    processed.blobSize = processed.blobData.size();
    processed.checksum = calculateChecksum(processed.blobData);
    
    return processed;
}

// Material Import
ProcessedAsset SharedAssetGen::importMaterial(const AssetEntry& assetEntry) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = AssetType::MATERIAL;
    processed.sourcePath = assetEntry.source;
    
    // TODO: Implement actual material importing
    // For now, create placeholder data
    MaterialData materialData;
    materialData.shaderType = ShaderType::PBR;
    materialData.albedoColor = glm::vec4(1.0f);
    materialData.metallic = 0.0f;
    materialData.roughness = 0.5f;
    
    processed.materialData = materialData;
    processed.blobData = generateTestMaterialData();
    processed.blobSize = processed.blobData.size();
    processed.checksum = calculateChecksum(processed.blobData);
    
    return processed;
}

// Texture Import
ProcessedAsset SharedAssetGen::importTexture(const AssetEntry& assetEntry) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = AssetType::TEXTURE;
    processed.sourcePath = assetEntry.source;
    
    // TODO: Implement actual texture importing
    // For now, create placeholder data
    TextureData textureData;
    textureData.width = 512;
    textureData.height = 512;
    textureData.format = TextureFormat::RGBA8;
    textureData.mipLevels = 9;
    textureData.compression = assetEntry.compression;
    
    processed.textureData = textureData;
    processed.blobData = generateTestTextureData();
    processed.blobSize = processed.blobData.size();
    processed.checksum = calculateChecksum(processed.blobData);
    
    return processed;
}

// Audio Import
ProcessedAsset SharedAssetGen::importAudio(const AssetEntry& assetEntry) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = AssetType::AUDIO;
    processed.sourcePath = assetEntry.source;
    
    // TODO: Implement actual audio importing
    // For now, create placeholder data
    AudioData audioData;
    audioData.sampleRate = 44100;
    audioData.numChannels = 2;
    audioData.bitDepth = 16;
    audioData.duration = 5.0f;
    audioData.lufs = assetEntry.normalizeLUFS;
    
    processed.audioData = audioData;
    processed.blobData = generateTestAudioData();
    processed.blobSize = processed.blobData.size();
    processed.checksum = calculateChecksum(processed.blobData);
    
    return processed;
}

// Script Import
ProcessedAsset SharedAssetGen::importScript(const AssetEntry& assetEntry) {
    ProcessedAsset processed;
    processed.id = assetEntry.id;
    processed.type = AssetType::SCRIPT;
    processed.sourcePath = assetEntry.source;
    
    // TODO: Implement actual script compiling
    // For now, create placeholder data
    ScriptData scriptData;
    scriptData.language = ScriptLanguage::LUA;
    scriptData.bytecodeSize = 1024;
    scriptData.functionCount = 10;
    
    processed.scriptData = scriptData;
    processed.blobData = generateTestScriptData();
    processed.blobSize = processed.blobData.size();
    processed.checksum = calculateChecksum(processed.blobData);
    
    return processed;
}

// Dependency Resolution
DependencyGraph SharedAssetGen::resolveDependencies(const SharedAssetDefinition& sharedDef, const std::vector<ProcessedAsset>& assets) {
    DependencyGraph graph;
    
    // Build adjacency list
    for (const auto& asset : assets) {
        graph.adjacencyList[asset.id] = asset.dependencies;
        
        // Add reverse edges for dependency tracking
        for (const auto& dep : asset.dependencies) {
            graph.reverseDependencies[dep].push_back(asset.id);
        }
    }
    
    // Detect cycles
    std::vector<std::string> cycle = detectCycles(graph);
    if (!cycle.empty()) {
        throw std::runtime_error("Circular dependency detected: " + cycle[0]);
    }
    
    // Topological sort
    graph.topologicalOrder = topologicalSort(graph);
    
    return graph;
}

// Cycle Detection
std::vector<std::string> SharedAssetGen::detectCycles(const DependencyGraph& graph) {
    std::unordered_set<std::string> visited;
    std::unordered_set<std::string> recursionStack;
    std::vector<std::string> cycle;
    
    for (const auto& [node, _] : graph.adjacencyList) {
        if (visited.find(node) == visited.end()) {
            if (hasCycleDFS(node, graph, visited, recursionStack, cycle)) {
                return cycle;
            }
        }
    }
    
    return {};
}

bool SharedAssetGen::hasCycleDFS(const std::string& node, const DependencyGraph& graph, 
                                std::unordered_set<std::string>& visited,
                                std::unordered_set<std::string>& recursionStack,
                                std::vector<std::string>& cycle) {
    visited.insert(node);
    recursionStack.insert(node);
    
    auto it = graph.adjacencyList.find(node);
    if (it != graph.adjacencyList.end()) {
        for (const auto& neighbor : it->second) {
            if (visited.find(neighbor) == visited.end()) {
                if (hasCycleDFS(neighbor, graph, visited, recursionStack, cycle)) {
                    cycle.push_back(node);
                    return true;
                }
            } else if (recursionStack.find(neighbor) != recursionStack.end()) {
                cycle.push_back(node);
                return true;
            }
        }
    }
    
    recursionStack.erase(node);
    return false;
}

// Topological Sort
std::vector<std::string> SharedAssetGen::topologicalSort(const DependencyGraph& graph) {
    std::unordered_map<std::string, int> inDegree;
    std::queue<std::string> queue;
    std::vector<std::string> result;
    
    // Calculate in-degrees
    for (const auto& [node, dependencies] : graph.adjacencyList) {
        if (inDegree.find(node) == inDegree.end()) {
            inDegree[node] = 0;
        }
        for (const auto& dep : dependencies) {
            inDegree[dep]++;
        }
    }
    
    // Add nodes with no dependencies to queue
    for (const auto& [node, degree] : inDegree) {
        if (degree == 0) {
            queue.push(node);
        }
    }
    
    // Process queue
    while (!queue.empty()) {
        std::string node = queue.front();
        queue.pop();
        result.push_back(node);
        
        auto it = graph.adjacencyList.find(node);
        if (it != graph.adjacencyList.end()) {
            for (const auto& neighbor : it->second) {
                inDegree[neighbor]--;
                if (inDegree[neighbor] == 0) {
                    queue.push(neighbor);
                }
            }
        }
    }
    
    return result;
}

// Post-Processing
std::vector<ProcessedAsset> SharedAssetGen::postProcessAssets(const std::vector<ProcessedAsset>& assets, const DependencyGraph& graph) {
    std::vector<ProcessedAsset> postProcessed = assets;
    
    // Process in topological order
    for (const auto& assetId : graph.topologicalOrder) {
        auto it = std::find_if(postProcessed.begin(), postProcessed.end(),
                              [&assetId](const ProcessedAsset& asset) { return asset.id == assetId; });
        
        if (it != postProcessed.end()) {
            postProcessAsset(*it, postProcessed, graph);
        }
    }
    
    return postProcessed;
}

void SharedAssetGen::postProcessAsset(ProcessedAsset& asset, std::vector<ProcessedAsset>& allAssets, const DependencyGraph& graph) {
    switch (asset.type) {
        case AssetType::MODEL:
            postProcessModel(asset, allAssets);
            break;
        case AssetType::MATERIAL:
            postProcessMaterial(asset, allAssets);
            break;
        case AssetType::TEXTURE:
            postProcessTexture(asset, allAssets);
            break;
        case AssetType::AUDIO:
            postProcessAudio(asset, allAssets);
            break;
        case AssetType::SCRIPT:
            postProcessScript(asset, allAssets);
            break;
    }
}

void SharedAssetGen::postProcessModel(ProcessedAsset& model, std::vector<ProcessedAsset>& allAssets) {
    // Bind materials to model
    for (const auto& dep : model.dependencies) {
        auto materialIt = std::find_if(allAssets.begin(), allAssets.end(),
                                     [&dep](const ProcessedAsset& asset) { return asset.id == dep; });
        
        if (materialIt != allAssets.end() && materialIt->type == AssetType::MATERIAL) {
            model.modelData.materialId = dep;
        }
    }
}

void SharedAssetGen::postProcessMaterial(ProcessedAsset& material, std::vector<ProcessedAsset>& allAssets) {
    // Process material dependencies (textures, shaders)
    for (const auto& dep : material.dependencies) {
        auto depIt = std::find_if(allAssets.begin(), allAssets.end(),
                                 [&dep](const ProcessedAsset& asset) { return asset.id == dep; });
        
        if (depIt != allAssets.end()) {
            if (depIt->type == AssetType::TEXTURE) {
                material.materialData.textureIds.push_back(dep);
            }
        }
    }
}

void SharedAssetGen::postProcessTexture(ProcessedAsset& texture, std::vector<ProcessedAsset>& allAssets) {
    // Generate mipmaps, apply compression
    if (texture.compressionSettings.compression != TextureCompression::NONE) {
        texture.textureData.compressed = true;
        texture.textureData.compressionType = texture.compressionSettings.compression;
    }
}

void SharedAssetGen::postProcessAudio(ProcessedAsset& audio, std::vector<ProcessedAsset>& allAssets) {
    // Normalize audio, apply effects
    if (audio.normalizeLUFS != 0.0f) {
        audio.audioData.normalized = true;
        audio.audioData.targetLUFS = audio.normalizeLUFS;
    }
}

void SharedAssetGen::postProcessScript(ProcessedAsset& script, std::vector<ProcessedAsset>& allAssets) {
    // Compile script, resolve imports
    script.scriptData.compiled = true;
    script.scriptData.bytecodeSize = script.blobData.size();
}

// Deduplication
std::vector<ProcessedAsset> SharedAssetGen::deduplicateAssets(const std::vector<ProcessedAsset>& assets) {
    if (!m_enableDeduplication) {
        return assets;
    }
    
    std::vector<ProcessedAsset> deduplicated;
    std::unordered_map<std::string, std::string> checksumToId;
    
    for (const auto& asset : assets) {
        auto it = checksumToId.find(asset.checksum);
        if (it == checksumToId.end()) {
            // New unique asset
            checksumToId[asset.checksum] = asset.id;
            deduplicated.push_back(asset);
        } else {
            // Duplicate found, update references
            std::string originalId = it->second;
            // TODO: Update references to point to originalId instead of asset.id
        }
    }
    
    return deduplicated;
}

// Manifest Generation
SharedAssetManifest SharedAssetGen::generateManifest(const SharedAssetDefinition& sharedDef, 
                                                   const std::vector<ProcessedAsset>& assets,
                                                   const DependencyGraph& graph) {
    SharedAssetManifest manifest;
    
    manifest.packName = sharedDef.name;
    manifest.version = sharedDef.version;
    manifest.description = sharedDef.description;
    manifest.assetCount = static_cast<int>(assets.size());
    manifest.totalSize = 0;
    
    // Generate asset entries
    for (const auto& asset : assets) {
        ManifestEntry entry;
        entry.id = asset.id;
        entry.type = asset.type;
        entry.checksum = asset.checksum;
        entry.blobSize = asset.blobSize;
        entry.dependencies = asset.dependencies;
        entry.metadata = asset.metadata;
        
        manifest.entries.push_back(entry);
        manifest.totalSize += asset.blobSize;
    }
    
    // Add dependency graph
    manifest.dependencyGraph = graph;
    
    return manifest;
}

// Shared Pack Creation
SharedPack SharedAssetGen::createSharedPack(const SharedAssetDefinition& sharedDef,
                                          const std::vector<ProcessedAsset>& assets,
                                          const SharedAssetManifest& manifest) {
    SharedPack pack;
    
    pack.name = sharedDef.name;
    pack.version = sharedDef.version;
    pack.manifest = manifest;
    pack.assets = assets;
    pack.sharedDef = sharedDef;
    
    // Calculate total size
    pack.totalSize = PACK_HEADER_SIZE + manifest.totalSize;
    pack.creationTime = std::chrono::system_clock::now();
    
    // Generate pack checksum
    pack.checksum = calculatePackChecksum(manifest, assets);
    
    // TODO: Implement actual pack serialization
    // This would create the .sharedpack archive with header, manifest, and blob data
    
    return pack;
}

// Asset Categorization
void SharedAssetGen::categorizeAssets(const std::vector<ProcessedAsset>& assets, SharedAssetResult& result) {
    for (const auto& asset : assets) {
        switch (asset.type) {
            case AssetType::MODEL:
                result.modelAssets.push_back(asset);
                break;
            case AssetType::MATERIAL:
                result.materialAssets.push_back(asset);
                break;
            case AssetType::TEXTURE:
                result.textureAssets.push_back(asset);
                break;
            case AssetType::AUDIO:
                result.audioAssets.push_back(asset);
                break;
            case AssetType::SCRIPT:
                result.scriptAssets.push_back(asset);
                break;
        }
    }
}

// Test Data Generation
std::vector<uint8_t> SharedAssetGen::generateTestModelData() {
    std::vector<uint8_t> data(1024);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    for (auto& byte : data) {
        byte = static_cast<uint8_t>(dis(gen));
    }
    
    return data;
}

std::vector<uint8_t> SharedAssetGen::generateTestMaterialData() {
    std::vector<uint8_t> data(512);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    for (auto& byte : data) {
        byte = static_cast<uint8_t>(dis(gen));
    }
    
    return data;
}

std::vector<uint8_t> SharedAssetGen::generateTestTextureData() {
    std::vector<uint8_t> data(2048);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    for (auto& byte : data) {
        byte = static_cast<uint8_t>(dis(gen));
    }
    
    return data;
}

std::vector<uint8_t> SharedAssetGen::generateTestAudioData() {
    std::vector<uint8_t> data(4096);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    for (auto& byte : data) {
        byte = static_cast<uint8_t>(dis(gen));
    }
    
    return data;
}

std::vector<uint8_t> SharedAssetGen::generateTestScriptData() {
    std::vector<uint8_t> data(256);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    for (auto& byte : data) {
        byte = static_cast<uint8_t>(dis(gen));
    }
    
    return data;
}

// Checksum Calculation
std::string SharedAssetGen::calculateChecksum(const std::vector<uint8_t>& data) {
    // TODO: Implement proper SHA-256 checksum
    // For now, use a simple hash
    size_t hash = 0;
    for (uint8_t byte : data) {
        hash = hash * 31 + byte;
    }
    return std::to_string(hash);
}

std::string SharedAssetGen::calculatePackChecksum(const SharedAssetManifest& manifest, const std::vector<ProcessedAsset>& assets) {
    // TODO: Implement proper pack checksum calculation
    // For now, use manifest version as checksum
    return manifest.version;
}

// Quality calculation functions
float SharedAssetGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float SharedAssetGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float SharedAssetGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float SharedAssetGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void SharedAssetGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void SharedAssetGen::setCompressionQuality(float quality) {
    m_compressionQuality = clamp(quality, 0.0f, 1.0f);
}

void SharedAssetGen::setDeduplicationEnabled(bool enable) {
    m_enableDeduplication = enable;
}

// Processing Options
void SharedAssetGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void SharedAssetGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string SharedAssetGen::getLastError() const {
    return m_lastError;
}

void SharedAssetGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float SharedAssetGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

int SharedAssetGen::clamp(int value, int min, int max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech 
