#include "SharedAssetGen.hpp"
#include "core/Log.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <sol/sol.hpp>
#include <stb_image.h>
#include <stb_image_write.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <unordered_set>
#include <queue>

namespace MagiTech {
namespace Audio {
namespace SharedAssets {

// Constants
constexpr size_t PACK_HEADER_SIZE = 64;
constexpr float DEFAULT_COMPRESSION_QUALITY = 0.8f;
constexpr float PI = 3.14159265359f;

namespace {

using Json = nlohmann::json;

std::vector<uint8_t> readFileBytes(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) return {};
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
}

std::string lowerExtension(const std::string& path) {
    std::string ext = std::filesystem::path(path).extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return ext;
}

uint64_t fnv1a(uint64_t h, const void* data, size_t size) {
    const auto* p = static_cast<const uint8_t*>(data);
    for (size_t i = 0; i < size; ++i) {
        h ^= p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

std::string hex64(uint64_t h) {
    std::ostringstream oss;
    oss << std::hex << std::setw(16) << std::setfill('0') << h;
    return oss.str();
}

// ---- model parsing ----------------------------------------------------------------------------

bool parseObj(const std::vector<uint8_t>& bytes, ModelData& model) {
    std::istringstream in(std::string(bytes.begin(), bytes.end()));
    std::string line;
    glm::vec3 mn(std::numeric_limits<float>::max()), mx(-std::numeric_limits<float>::max());
    uint32_t vertices = 0, indices = 0;
    while (std::getline(in, line)) {
        std::istringstream ls(line);
        std::string tag;
        ls >> tag;
        if (tag == "v") {
            glm::vec3 p(0.0f);
            ls >> p.x >> p.y >> p.z;
            mn = glm::min(mn, p);
            mx = glm::max(mx, p);
            ++vertices;
        } else if (tag == "f") {
            int corners = 0;
            std::string token;
            while (ls >> token) ++corners;
            if (corners >= 3) indices += static_cast<uint32_t>((corners - 2) * 3);   // fan triangulation
        } else if (tag == "usemtl" && model.materialId.empty()) {
            ls >> model.materialId;
        }
    }
    if (vertices == 0) return false;
    model.vertexCount = vertices;
    model.indexCount = indices;
    model.boundingBox = {mn, mx};
    model.lodLevels = 1;
    return true;
}

bool parseGltfJson(const Json& gltf, ModelData& model) {
    if (!gltf.contains("meshes") || !gltf.contains("accessors")) return false;
    const Json& accessors = gltf.at("accessors");
    glm::vec3 mn(std::numeric_limits<float>::max()), mx(-std::numeric_limits<float>::max());
    bool haveBounds = false;
    uint32_t vertices = 0, indices = 0, lodMeshes = 0;
    for (const auto& mesh : gltf.at("meshes")) {
        if (mesh.contains("name") && mesh.at("name").get<std::string>().find("LOD") != std::string::npos) ++lodMeshes;
        if (!mesh.contains("primitives")) continue;
        for (const auto& prim : mesh.at("primitives")) {
            if (prim.contains("attributes") && prim.at("attributes").contains("POSITION")) {
                const Json& acc = accessors.at(prim.at("attributes").at("POSITION").get<size_t>());
                vertices += acc.value("count", 0u);
                if (acc.contains("min") && acc.contains("max") && acc.at("min").size() >= 3) {
                    mn = glm::min(mn, glm::vec3(acc.at("min")[0].get<float>(), acc.at("min")[1].get<float>(), acc.at("min")[2].get<float>()));
                    mx = glm::max(mx, glm::vec3(acc.at("max")[0].get<float>(), acc.at("max")[1].get<float>(), acc.at("max")[2].get<float>()));
                    haveBounds = true;
                }
            }
            if (prim.contains("indices")) {
                indices += accessors.at(prim.at("indices").get<size_t>()).value("count", 0u);
            }
            if (model.materialId.empty() && prim.contains("material") && gltf.contains("materials")) {
                const Json& mat = gltf.at("materials").at(prim.at("material").get<size_t>());
                model.materialId = mat.value("name", std::string("material_") + std::to_string(prim.at("material").get<size_t>()));
            }
        }
    }
    model.vertexCount = vertices;
    model.indexCount = indices;
    model.boundingBox = haveBounds ? std::make_pair(mn, mx) : std::make_pair(glm::vec3(0.0f), glm::vec3(0.0f));
    model.lodLevels = std::max(1u, lodMeshes);
    return vertices > 0;
}

bool parseGlb(const std::vector<uint8_t>& bytes, ModelData& model) {
    // 12-byte header ("glTF", version, length) followed by the JSON chunk
    if (bytes.size() < 20 || std::memcmp(bytes.data(), "glTF", 4) != 0) return false;
    uint32_t chunkLength = 0, chunkType = 0;
    std::memcpy(&chunkLength, bytes.data() + 12, 4);
    std::memcpy(&chunkType, bytes.data() + 16, 4);
    if (chunkType != 0x4E4F534Au || 20ull + chunkLength > bytes.size()) return false;   // 'JSON'
    Json gltf = Json::parse(bytes.begin() + 20, bytes.begin() + 20 + chunkLength, nullptr, false);
    return !gltf.is_discarded() && parseGltfJson(gltf, model);
}

// ---- audio decoding ---------------------------------------------------------------------------

// Decodes RIFF/WAVE PCM (8/16/24/32-bit) and IEEE float (32-bit) into interleaved floats.
bool decodeWav(const std::vector<uint8_t>& bytes, std::vector<float>& samples, uint32_t& sampleRate,
               uint32_t& channels, uint32_t& bitDepth) {
    if (bytes.size() < 12 || std::memcmp(bytes.data(), "RIFF", 4) != 0 || std::memcmp(bytes.data() + 8, "WAVE", 4) != 0) {
        return false;
    }
    uint16_t format = 0;
    bool haveFmt = false;
    size_t pos = 12;
    while (pos + 8 <= bytes.size()) {
        uint32_t size = 0;
        std::memcpy(&size, bytes.data() + pos + 4, 4);
        const uint8_t* body = bytes.data() + pos + 8;
        const size_t available = std::min<size_t>(size, bytes.size() - (pos + 8));
        if (std::memcmp(bytes.data() + pos, "fmt ", 4) == 0 && available >= 16) {
            uint16_t ch = 0, bits = 0;
            std::memcpy(&format, body, 2);
            std::memcpy(&ch, body + 2, 2);
            std::memcpy(&sampleRate, body + 4, 4);
            std::memcpy(&bits, body + 14, 2);
            if (format == 0xFFFE && available >= 26) std::memcpy(&format, body + 24, 2);   // WAVE_FORMAT_EXTENSIBLE
            channels = ch;
            bitDepth = bits;
            haveFmt = true;
        } else if (std::memcmp(bytes.data() + pos, "data", 4) == 0 && haveFmt) {
            const uint32_t bytesPerSample = bitDepth / 8;
            if (bytesPerSample == 0 || channels == 0) return false;
            const size_t count = available / bytesPerSample;
            samples.resize(count);
            for (size_t i = 0; i < count; ++i) {
                const uint8_t* s = body + i * bytesPerSample;
                float v = 0.0f;
                if (format == 3 && bitDepth == 32) {
                    std::memcpy(&v, s, 4);
                } else if (format == 1) {
                    switch (bitDepth) {
                        case 8: v = (static_cast<int>(s[0]) - 128) / 128.0f; break;
                        case 16: { int16_t x; std::memcpy(&x, s, 2); v = x / 32768.0f; break; }
                        case 24: { int32_t x = (s[0] << 8) | (s[1] << 16) | (s[2] << 24); v = static_cast<float>(x >> 8) / 8388608.0f; break; }
                        case 32: { int32_t x; std::memcpy(&x, s, 4); v = static_cast<float>(x / 2147483648.0); break; }
                        default: return false;
                    }
                } else {
                    return false;
                }
                samples[i] = v;
            }
            return true;
        }
        pos += 8 + size + (size & 1);
    }
    return false;
}

// Integrated loudness estimate (ungated, unweighted mean square), in LUFS
float estimateLUFS(const std::vector<float>& samples) {
    if (samples.empty()) return -70.0f;
    double sum = 0.0;
    for (float s : samples) sum += static_cast<double>(s) * s;
    const double meanSquare = sum / static_cast<double>(samples.size());
    return meanSquare > 0.0 ? static_cast<float>(-0.691 + 10.0 * std::log10(meanSquare)) : -70.0f;
}

void appendLE(std::vector<uint8_t>& out, uint32_t v, int bytes) {
    for (int i = 0; i < bytes; ++i) out.push_back(static_cast<uint8_t>((v >> (8 * i)) & 0xFF));
}

// ---- definition JSON --------------------------------------------------------------------------

constexpr std::array<const char*, 5> kAssetTypes = {"model", "material", "texture", "audio", "script"};
constexpr std::array<const char*, 6> kCompressions = {"none", "bc1", "bc3", "bc7", "astc_4x4", "astc_8x8"};

template <typename E, size_t N>
E enumFromString(const std::string& s, const std::array<const char*, N>& names, E fallback) {
    std::string lower = s;
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    for (size_t i = 0; i < N; ++i)
        if (lower == names[i]) return static_cast<E>(i);
    return fallback;
}

SharedAssetDefinition coreSharedTemplate() {
    SharedAssetDefinition def;
    def.name = "core_shared";
    def.version = "2.1.0";
    def.description = "Core shared assets for the game";

    AssetEntry heroModel;
    heroModel.id = "hero_model";
    heroModel.type = AssetType::MODEL;
    heroModel.source = "models/hero.glb";
    heroModel.dependencies = {"hero_material"};
    def.assets.push_back(heroModel);

    AssetEntry heroMaterial;
    heroMaterial.id = "hero_material";
    heroMaterial.type = AssetType::MATERIAL;
    heroMaterial.source = "materials/hero.mat";
    def.assets.push_back(heroMaterial);

    AssetEntry uiTexture;
    uiTexture.id = "common_ui_texture";
    uiTexture.type = AssetType::TEXTURE;
    uiTexture.source = "textures/ui/common_ui.png";
    uiTexture.compression = {TextureCompression::BC7, 4, {}};
    def.assets.push_back(uiTexture);

    AssetEntry uiClickSfx;
    uiClickSfx.id = "ui_click_sfx";
    uiClickSfx.type = AssetType::AUDIO;
    uiClickSfx.source = "audio/ui_click.wav";
    uiClickSfx.normalizeLUFS = -16.0f;
    def.assets.push_back(uiClickSfx);

    AssetEntry gameplayScript;
    gameplayScript.id = "gameplay_script";
    gameplayScript.type = AssetType::SCRIPT;
    gameplayScript.source = "scripts/gameplay.lua";
    def.assets.push_back(gameplayScript);
    return def;
}

Json definitionToJson(const SharedAssetDefinition& def) {
    Json j;
    j["name"] = def.name;
    j["version"] = def.version;
    j["description"] = def.description;
    j["assets"] = Json::array();
    for (const auto& a : def.assets) {
        j["assets"].push_back({{"id", a.id},
                               {"type", kAssetTypes[static_cast<size_t>(a.type)]},
                               {"source", a.source},
                               {"dependencies", a.dependencies},
                               {"compression", {{"type", kCompressions[static_cast<size_t>(a.compression.compression)]},
                                                {"quality", a.compression.quality},
                                                {"parameters", a.compression.parameters}}},
                               {"normalizeLUFS", a.normalizeLUFS},
                               {"metadata", a.metadata}});
    }
    j["metadata"] = def.metadata;
    j["tags"] = def.tags;
    j["enableHotReload"] = def.enableHotReload;
    j["enableCaching"] = def.enableCaching;
    j["enableParallelProcessing"] = def.enableParallelProcessing;
    j["maxConcurrentAssets"] = def.maxConcurrentAssets;
    return j;
}

SharedAssetDefinition definitionFromJson(const Json& j) {
    SharedAssetDefinition def;
    def.name = j.value("name", std::string("shared"));
    def.version = j.value("version", std::string("1.0.0"));
    def.description = j.value("description", std::string());
    if (j.contains("assets")) {
        for (const auto& a : j.at("assets")) {
            AssetEntry entry;
            entry.id = a.at("id").get<std::string>();
            entry.type = enumFromString(a.value("type", std::string("audio")), kAssetTypes, AssetType::AUDIO);
            entry.source = a.value("source", std::string());
            if (a.contains("dependencies")) entry.dependencies = a.at("dependencies").get<std::vector<std::string>>();
            if (a.contains("compression")) {
                const Json& c = a.at("compression");
                entry.compression.compression = enumFromString(c.value("type", std::string("none")), kCompressions, TextureCompression::NONE);
                entry.compression.quality = c.value("quality", 4);
                if (c.contains("parameters")) entry.compression.parameters = c.at("parameters").get<std::map<std::string, float>>();
            }
            entry.normalizeLUFS = a.value("normalizeLUFS", 0.0f);
            if (a.contains("metadata")) entry.metadata = a.at("metadata").get<std::map<std::string, std::string>>();
            def.assets.push_back(entry);
        }
    }
    if (j.contains("metadata")) def.metadata = j.at("metadata").get<std::map<std::string, std::string>>();
    if (j.contains("tags")) def.tags = j.at("tags").get<std::vector<std::string>>();
    def.enableHotReload = j.value("enableHotReload", true);
    def.enableCaching = j.value("enableCaching", true);
    def.enableParallelProcessing = j.value("enableParallelProcessing", true);
    def.maxConcurrentAssets = j.value("maxConcurrentAssets", 8);
    return def;
}

Json manifestToJson(const SharedAssetManifest& manifest) {
    Json j;
    j["packName"] = manifest.packName;
    j["version"] = manifest.version;
    j["description"] = manifest.description;
    j["assetCount"] = manifest.assetCount;
    j["totalSize"] = manifest.totalSize;
    j["entries"] = Json::array();
    for (const auto& e : manifest.entries) {
        j["entries"].push_back({{"id", e.id}, {"type", kAssetTypes[static_cast<size_t>(e.type)]},
                                {"checksum", e.checksum}, {"blobSize", e.blobSize},
                                {"dependencies", e.dependencies}, {"metadata", e.metadata}});
    }
    j["loadOrder"] = manifest.dependencyGraph.topologicalOrder;
    j["metadata"] = manifest.additionalMetadata;
    return j;
}

} // namespace

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
        bundle.meta.id = params.id + "_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        bundle.creationTime = std::chrono::system_clock::now();

        // Load shared asset definition if provided
        SharedAssetDefinition sharedDef;
        if (!params.sharedDefinitionPath.empty()) {
            sharedDef = loadSharedAssetDefinition(params.sharedDefinitionPath);
        } else {
            sharedDef = createDefaultSharedAssetDefinition(params);
        }

        // Process shared asset pipeline
        SharedAssetResult result = processSharedAssetPipeline(sharedDef, params);

        // The bundle carries the first decoded audio asset
        for (const auto& audio : result.audioAssets) {
            if (audio.audioSamples.empty()) continue;
            bundle.buffer = audio.audioSamples;
            bundle.meta.duration = static_cast<float>(audio.audioSamples.size()) /
                                   static_cast<float>(std::max(1u, audio.sampleRate * audio.numChannels));
            break;
        }

        // Calculate quality metrics
        if (!bundle.buffer.empty()) {
            bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
            bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
            bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
            bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
            bundle.meta.quality = bundle.quality;
        }

        return bundle;

    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Shared Asset Definition Loading (JSON)
SharedAssetDefinition SharedAssetGen::loadSharedAssetDefinition(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        m_lastError = "Shared asset definition not found: " + filePath;
        Log::warn("SharedAssetGen", "{} (using built-in core_shared definition)", m_lastError);
        return coreSharedTemplate();
    }
    Json j = Json::parse(file, nullptr, false);
    if (j.is_discarded() || !j.is_object()) {
        m_lastError = "Invalid shared asset definition JSON: " + filePath;
        Log::error("SharedAssetGen", "{}", m_lastError);
        return coreSharedTemplate();
    }
    try {
        return definitionFromJson(j);
    } catch (const Json::exception& e) {
        m_lastError = std::string("Shared asset definition error in ") + filePath + ": " + e.what();
        Log::error("SharedAssetGen", "{}", m_lastError);
        return coreSharedTemplate();
    }
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
    audioAsset.normalizeLUFS = params.normalizeLUFS;
    def.assets.push_back(audioAsset);

    return def;
}

bool SharedAssetGen::saveSharedAssetDefinition(const SharedAssetDefinition& def, const std::string& filePath) {
    std::error_code ec;
    const std::filesystem::path path(filePath);
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream file(filePath);
    if (!file.is_open()) {
        m_lastError = "Cannot write shared asset definition: " + filePath;
        Log::error("SharedAssetGen", "{}", m_lastError);
        return false;
    }
    file << definitionToJson(def).dump(2);
    return static_cast<bool>(file);
}

// Shared Asset Pipeline Processing
SharedAssetResult SharedAssetGen::processSharedAssetPipeline(const SharedAssetDefinition& sharedDef, const SharedAssetParams& params) {
    SharedAssetResult result;
    result.processingTime = std::chrono::system_clock::now();

    // Step 1: Import and convert assets
    std::vector<ProcessedAsset> processedAssets;
    for (const auto& assetEntry : sharedDef.assets) {
        ProcessedAsset processed = importAsset(assetEntry, params);
        auto err = processed.metadata.find("error");
        if (err != processed.metadata.end()) result.warnings.push_back(err->second);
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
    result.success = result.warnings.empty();
    if (!result.success) result.errorMessage = result.warnings.front();

    return result;
}

// Asset Importer Initialization
void SharedAssetGen::initializeAssetImporters() {
    m_modelImporter = std::make_unique<ModelImporter>();
    m_textureImporter = std::make_unique<TextureImporter>();
    m_audioImporter = std::make_unique<AudioImporter>();
    m_scriptCompiler = std::make_unique<ScriptCompiler>();
    m_materialProcessor = std::make_unique<MaterialProcessor>();
}

// Asset Import
ProcessedAsset SharedAssetGen::importAsset(const AssetEntry& assetEntry, const SharedAssetParams& params) {
    ProcessedAsset processed;

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

    processed.id = assetEntry.id;
    processed.type = assetEntry.type;
    processed.sourcePath = assetEntry.source;
    processed.dependencies = assetEntry.dependencies;

    // Add metadata (importer diagnostics such as "error" are kept)
    for (const auto& [k, v] : assetEntry.metadata) processed.metadata[k] = v;
    processed.metadata["pack"] = params.id;
    processed.compressionSettings = assetEntry.compression;
    processed.normalizeLUFS = assetEntry.normalizeLUFS;

    return processed;
}

ProcessedAsset SharedAssetGen::importModel(const AssetEntry& assetEntry) {
    return m_modelImporter->import(assetEntry);
}

ProcessedAsset SharedAssetGen::importMaterial(const AssetEntry& assetEntry) {
    return m_materialProcessor->process(assetEntry);
}

ProcessedAsset SharedAssetGen::importTexture(const AssetEntry& assetEntry) {
    return m_textureImporter->import(assetEntry);
}

ProcessedAsset SharedAssetGen::importAudio(const AssetEntry& assetEntry) {
    return m_audioImporter->import(assetEntry);
}

ProcessedAsset SharedAssetGen::importScript(const AssetEntry& assetEntry) {
    return m_scriptCompiler->compile(assetEntry);
}

// ---- importers --------------------------------------------------------------------------------

ProcessedAsset SharedAssetGen::ModelImporter::import(const AssetEntry& entry) {
    ProcessedAsset processed;
    processed.id = entry.id;
    processed.type = AssetType::MODEL;
    processed.sourcePath = entry.source;
    processed.blobData = readFileBytes(entry.source);
    processed.blobSize = processed.blobData.size();
    if (processed.blobData.empty()) {
        processed.metadata["error"] = "Model not found or empty: " + entry.source;
        return processed;
    }

    // OBJ (text) and glTF (.gltf JSON / .glb binary) headers are understood; other formats are packed as-is
    const std::string ext = lowerExtension(entry.source);
    bool parsed = false;
    if (ext == ".obj") {
        parsed = parseObj(processed.blobData, processed.modelData);
    } else if (ext == ".glb") {
        parsed = parseGlb(processed.blobData, processed.modelData);
    } else if (ext == ".gltf") {
        Json gltf = Json::parse(processed.blobData.begin(), processed.blobData.end(), nullptr, false);
        parsed = !gltf.is_discarded() && parseGltfJson(gltf, processed.modelData);
    }
    processed.metadata["format"] = ext.empty() ? "unknown" : ext.substr(1);
    if (!parsed) processed.metadata["parsed"] = "false";
    return processed;
}

ProcessedAsset SharedAssetGen::MaterialProcessor::process(const AssetEntry& entry) {
    ProcessedAsset processed;
    processed.id = entry.id;
    processed.type = AssetType::MATERIAL;
    processed.sourcePath = entry.source;
    processed.blobData = readFileBytes(entry.source);
    processed.blobSize = processed.blobData.size();
    if (processed.blobData.empty()) {
        processed.metadata["error"] = "Material not found or empty: " + entry.source;
        return processed;
    }

    // Material files are JSON: {"shader": "pbr", "albedo": [r,g,b,a], "metallic": m, "roughness": r, "textures": [...]}
    Json j = Json::parse(processed.blobData.begin(), processed.blobData.end(), nullptr, false);
    if (j.is_discarded() || !j.is_object()) {
        processed.metadata["error"] = "Material is not valid JSON: " + entry.source;
        return processed;
    }
    MaterialData& m = processed.materialData;
    const std::string shader = j.value("shader", std::string("pbr"));
    m.shaderType = shader == "unlit" ? ShaderType::UNLIT : shader == "lit" ? ShaderType::LIT
                 : shader == "custom" ? ShaderType::CUSTOM : ShaderType::PBR;
    if (j.contains("albedo") && j.at("albedo").is_array()) {
        const Json& a = j.at("albedo");
        for (size_t i = 0; i < std::min<size_t>(4, a.size()); ++i) m.albedoColor[static_cast<int>(i)] = a[i].get<float>();
    }
    m.metallic = j.value("metallic", m.metallic);
    m.roughness = j.value("roughness", m.roughness);
    if (j.contains("textures")) m.textureIds = j.at("textures").get<std::vector<std::string>>();
    if (j.contains("parameters")) m.parameters = j.at("parameters").get<std::map<std::string, float>>();
    return processed;
}

ProcessedAsset SharedAssetGen::TextureImporter::import(const AssetEntry& entry) {
    ProcessedAsset processed;
    processed.id = entry.id;
    processed.type = AssetType::TEXTURE;
    processed.sourcePath = entry.source;
    processed.blobData = readFileBytes(entry.source);
    processed.blobSize = processed.blobData.size();
    if (processed.blobData.empty()) {
        processed.metadata["error"] = "Texture not found or empty: " + entry.source;
        return processed;
    }

    int w = 0, h = 0, n = 0;
    const int is16 = stbi_is_16_bit_from_memory(processed.blobData.data(), static_cast<int>(processed.blobData.size()));
    if (!stbi_info_from_memory(processed.blobData.data(), static_cast<int>(processed.blobData.size()), &w, &h, &n)) {
        processed.metadata["error"] = "Unsupported texture format: " + entry.source;
        return processed;
    }
    TextureData& t = processed.textureData;
    t.width = static_cast<uint32_t>(w);
    t.height = static_cast<uint32_t>(h);
    switch (n) {
        case 1: case 2: t.format = is16 ? TextureFormat::R16 : TextureFormat::R8; break;
        case 3: t.format = is16 ? TextureFormat::RGB16 : TextureFormat::RGB8; break;
        default: t.format = is16 ? TextureFormat::RGBA16 : TextureFormat::RGBA8; break;
    }
    t.mipLevels = 1 + static_cast<uint32_t>(std::floor(std::log2(static_cast<double>(std::max(w, h)))));
    t.compressionType = entry.compression.compression;
    t.parameters = entry.compression.parameters;
    t.parameters["compressionQuality"] = static_cast<float>(entry.compression.quality);
    return processed;
}

ProcessedAsset SharedAssetGen::AudioImporter::import(const AssetEntry& entry) {
    ProcessedAsset processed;
    processed.id = entry.id;
    processed.type = AssetType::AUDIO;
    processed.sourcePath = entry.source;
    processed.blobData = readFileBytes(entry.source);
    processed.blobSize = processed.blobData.size();
    if (processed.blobData.empty()) {
        processed.metadata["error"] = "Audio not found or empty: " + entry.source;
        return processed;
    }

    uint32_t sampleRate = 0, channels = 0, bitDepth = 0;
    if (!decodeWav(processed.blobData, processed.audioSamples, sampleRate, channels, bitDepth)) {
        processed.metadata["error"] = "Unsupported audio format (expected PCM/float WAV): " + entry.source;
        return processed;
    }
    processed.sampleRate = sampleRate;
    processed.numChannels = channels;
    AudioData& a = processed.audioData;
    a.sampleRate = sampleRate;
    a.numChannels = channels;
    a.bitDepth = bitDepth;
    a.duration = static_cast<float>(processed.audioSamples.size()) / static_cast<float>(std::max(1u, sampleRate * channels));
    a.lufs = estimateLUFS(processed.audioSamples);
    return processed;
}

ProcessedAsset SharedAssetGen::ScriptCompiler::compile(const AssetEntry& entry) {
    ProcessedAsset processed;
    processed.id = entry.id;
    processed.type = AssetType::SCRIPT;
    processed.sourcePath = entry.source;
    std::vector<uint8_t> source = readFileBytes(entry.source);
    if (source.empty()) {
        processed.metadata["error"] = "Script not found or empty: " + entry.source;
        return processed;
    }

    const std::string text(source.begin(), source.end());
    ScriptData& s = processed.scriptData;
    // count function definitions (named and anonymous)
    for (size_t pos = text.find("function"); pos != std::string::npos; pos = text.find("function", pos + 8)) {
        const bool startOk = pos == 0 || !(std::isalnum(static_cast<unsigned char>(text[pos - 1])) || text[pos - 1] == '_');
        const size_t end = pos + 8;
        const bool endOk = end >= text.size() || !(std::isalnum(static_cast<unsigned char>(text[end])) || text[end] == '_');
        if (startOk && endOk) ++s.functionCount;
    }

    const std::string ext = lowerExtension(entry.source);
    if (ext == ".lua") {
        // Compile to Lua bytecode; the blob becomes the precompiled chunk
        s.language = ScriptLanguage::LUA;
        sol::state lua;
        sol::load_result chunk = lua.load(text, "@" + entry.source);
        if (!chunk.valid()) {
            sol::error err = chunk;
            processed.metadata["error"] = std::string("Lua compile error: ") + err.what();
            processed.blobData = std::move(source);
        } else {
            sol::protected_function fn = chunk;
            sol::bytecode bytecode = fn.dump();
            const auto* bytes = reinterpret_cast<const uint8_t*>(bytecode.data());
            processed.blobData.assign(bytes, bytes + bytecode.size());
            s.compiled = true;
        }
    } else {
        s.language = ext == ".js" ? ScriptLanguage::JAVASCRIPT : ext == ".py" ? ScriptLanguage::PYTHON : ScriptLanguage::CUSTOM;
        processed.blobData = std::move(source);   // packed as source
    }
    s.bytecodeSize = static_cast<uint32_t>(processed.blobData.size());
    processed.blobSize = processed.blobData.size();
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
        std::string path;
        for (auto it = cycle.rbegin(); it != cycle.rend(); ++it) path += (path.empty() ? "" : " -> ") + *it;
        throw std::runtime_error("Circular dependency detected in '" + sharedDef.name + "': " + path);
    }

    // Topological sort
    graph.topologicalOrder = topologicalSort(graph);

    // Dependency depth (longest chain of dependencies below each asset)
    for (auto it = graph.topologicalOrder.rbegin(); it != graph.topologicalOrder.rend(); ++it) {
        int depth = 0;
        auto adj = graph.adjacencyList.find(*it);
        if (adj != graph.adjacencyList.end()) {
            for (const auto& dep : adj->second) depth = std::max(depth, graph.dependencyDepth[dep] + 1);
        }
        graph.dependencyDepth[*it] = depth;
        if (depth > static_cast<int>(MAX_DEPENDENCY_DEPTH)) {
            throw std::runtime_error("Dependency chain of '" + *it + "' exceeds the maximum depth");
        }
    }

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
                cycle.push_back(neighbor);
                cycle.push_back(node);
                return true;
            }
        }
    }

    recursionStack.erase(node);
    return false;
}

// Topological Sort: dependencies come before the assets that use them
std::vector<std::string> SharedAssetGen::topologicalSort(const DependencyGraph& graph) {
    std::unordered_map<std::string, int> remaining;   // unresolved dependency count per asset
    std::queue<std::string> queue;
    std::vector<std::string> result;

    for (const auto& [node, dependencies] : graph.adjacencyList) {
        remaining[node] += static_cast<int>(dependencies.size());
        for (const auto& dep : dependencies) remaining.try_emplace(dep, 0);
    }

    for (const auto& [node, count] : remaining) {
        if (count == 0) queue.push(node);
    }

    while (!queue.empty()) {
        std::string node = queue.front();
        queue.pop();
        result.push_back(node);

        auto it = graph.reverseDependencies.find(node);
        if (it != graph.reverseDependencies.end()) {
            for (const auto& dependent : it->second) {
                if (--remaining[dependent] == 0) queue.push(dependent);
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
    auto depth = graph.dependencyDepth.find(asset.id);
    if (depth != graph.dependencyDepth.end()) asset.metadata["dependencyDepth"] = std::to_string(depth->second);

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
    asset.blobSize = asset.blobData.size();
    asset.checksum = calculateChecksum(asset.blobData);
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

        if (depIt != allAssets.end() && depIt->type == AssetType::TEXTURE &&
            std::find(material.materialData.textureIds.begin(), material.materialData.textureIds.end(), dep) ==
                material.materialData.textureIds.end()) {
            material.materialData.textureIds.push_back(dep);
        }
    }
}

void SharedAssetGen::postProcessTexture(ProcessedAsset& texture, std::vector<ProcessedAsset>& allAssets) {
    // Record the GPU block compression the runtime should apply on upload
    if (texture.compressionSettings.compression != TextureCompression::NONE) {
        texture.textureData.compressed = true;
        texture.textureData.compressionType = texture.compressionSettings.compression;
        texture.metadata["compressionQuality"] = std::to_string(texture.compressionSettings.quality);
    }
}

void SharedAssetGen::postProcessAudio(ProcessedAsset& audio, std::vector<ProcessedAsset>& allAssets) {
    // Loudness-normalize decoded audio to the requested LUFS target
    if (audio.normalizeLUFS == 0.0f || audio.audioSamples.empty()) return;

    const float current = estimateLUFS(audio.audioSamples);
    const float gain = std::pow(10.0f, (audio.normalizeLUFS - current) / 20.0f);
    float peak = 0.0f;
    for (float& s : audio.audioSamples) {
        s *= gain;
        peak = std::max(peak, std::abs(s));
    }
    if (peak > 1.0f) {
        // prevent clipping: scale back to full scale
        for (float& s : audio.audioSamples) s /= peak;
    }
    audio.audioData.normalized = true;
    audio.audioData.targetLUFS = audio.normalizeLUFS;
    audio.audioData.lufs = estimateLUFS(audio.audioSamples);

    // Re-encode the blob as 16-bit PCM WAV so the pack holds the normalized audio
    std::vector<uint8_t> wav;
    const uint32_t channels = std::max(1u, audio.numChannels);
    const uint32_t dataBytes = static_cast<uint32_t>(audio.audioSamples.size() * 2);
    wav.insert(wav.end(), {'R', 'I', 'F', 'F'});
    appendLE(wav, 36 + dataBytes, 4);
    wav.insert(wav.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    appendLE(wav, 16, 4);
    appendLE(wav, 1, 2);
    appendLE(wav, channels, 2);
    appendLE(wav, audio.sampleRate, 4);
    appendLE(wav, audio.sampleRate * channels * 2, 4);
    appendLE(wav, channels * 2, 2);
    appendLE(wav, 16, 2);
    wav.insert(wav.end(), {'d', 'a', 't', 'a'});
    appendLE(wav, dataBytes, 4);
    for (float s : audio.audioSamples) {
        const int16_t v = static_cast<int16_t>(std::lround(std::clamp(s, -1.0f, 1.0f) * 32767.0f));
        appendLE(wav, static_cast<uint16_t>(v), 2);
    }
    audio.blobData = std::move(wav);
    audio.audioData.bitDepth = 16;
}

void SharedAssetGen::postProcessScript(ProcessedAsset& script, std::vector<ProcessedAsset>& allAssets) {
    // Resolve imports: script dependencies must be scripts present in the pack
    for (const auto& dep : script.dependencies) {
        auto depIt = std::find_if(allAssets.begin(), allAssets.end(),
                                  [&dep](const ProcessedAsset& asset) { return asset.id == dep; });
        if (depIt == allAssets.end()) {
            script.metadata["unresolvedImport"] = dep;
        }
    }
    script.scriptData.bytecodeSize = static_cast<uint32_t>(script.blobData.size());
}

// Deduplication
std::vector<ProcessedAsset> SharedAssetGen::deduplicateAssets(const std::vector<ProcessedAsset>& assets) {
    if (!m_enableDeduplication) {
        return assets;
    }

    std::vector<ProcessedAsset> deduplicated;
    std::unordered_map<std::string, std::string> checksumToId;
    std::unordered_map<std::string, std::string> aliasOf;   // removed id -> kept id

    for (const auto& asset : assets) {
        // Empty blobs (failed imports) are never merged
        auto it = asset.blobData.empty() ? checksumToId.end() : checksumToId.find(asset.checksum);
        if (it == checksumToId.end()) {
            if (!asset.blobData.empty()) checksumToId[asset.checksum] = asset.id;
            deduplicated.push_back(asset);
        } else {
            aliasOf[asset.id] = it->second;
        }
    }

    // Update references to point to the kept asset
    for (auto& asset : deduplicated) {
        for (auto& dep : asset.dependencies) {
            auto alias = aliasOf.find(dep);
            if (alias != aliasOf.end()) dep = alias->second;
        }
        std::sort(asset.dependencies.begin(), asset.dependencies.end());
        asset.dependencies.erase(std::unique(asset.dependencies.begin(), asset.dependencies.end()), asset.dependencies.end());
        if (asset.modelData.materialId.size() && aliasOf.count(asset.modelData.materialId)) {
            asset.modelData.materialId = aliasOf[asset.modelData.materialId];
        }
        for (auto& tex : asset.materialData.textureIds) {
            auto alias = aliasOf.find(tex);
            if (alias != aliasOf.end()) tex = alias->second;
        }
    }
    for (const auto& [removed, kept] : aliasOf) {
        auto keptIt = std::find_if(deduplicated.begin(), deduplicated.end(),
                                   [&kept](const ProcessedAsset& a) { return a.id == kept; });
        if (keptIt != deduplicated.end()) {
            std::string& aliases = keptIt->metadata["aliases"];
            aliases += (aliases.empty() ? "" : ",") + removed;
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
    manifest.additionalMetadata = sharedDef.metadata;

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

    // Generate pack checksum (the archive itself is written on demand by writeSharedPack)
    pack.checksum = calculatePackChecksum(manifest, assets);

    return pack;
}

bool SharedAssetGen::writeSharedPack(SharedPack& pack, const std::string& filePath) {
    std::error_code ec;
    const std::filesystem::path path(filePath);
    if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
    std::ofstream out(filePath, std::ios::binary);
    if (!out.is_open()) {
        m_lastError = "Cannot write shared pack: " + filePath;
        Log::error("SharedAssetGen", "{}", m_lastError);
        return false;
    }

    const std::string manifestJson = manifestToJson(pack.manifest).dump();
    char header[PACK_HEADER_SIZE] = {};
    std::memcpy(header, "SHRPACK1", 8);
    const uint32_t assetCount = static_cast<uint32_t>(pack.assets.size());
    const uint64_t manifestSize = manifestJson.size();
    std::memcpy(header + 8, &assetCount, 4);
    std::memcpy(header + 12, &manifestSize, 8);
    std::memcpy(header + 20, pack.checksum.data(), std::min<size_t>(pack.checksum.size(), 32));
    out.write(header, sizeof(header));
    out.write(manifestJson.data(), static_cast<std::streamsize>(manifestJson.size()));

    // Blobs in manifest order, each prefixed with its id and size
    for (const auto& asset : pack.assets) {
        const uint32_t idLen = static_cast<uint32_t>(asset.id.size());
        const uint64_t blobLen = asset.blobData.size();
        out.write(reinterpret_cast<const char*>(&idLen), 4);
        out.write(asset.id.data(), idLen);
        out.write(reinterpret_cast<const char*>(&blobLen), 8);
        if (blobLen) out.write(reinterpret_cast<const char*>(asset.blobData.data()), static_cast<std::streamsize>(blobLen));
    }
    if (!out) {
        m_lastError = "Write failed for shared pack: " + filePath;
        return false;
    }
    pack.filePath = filePath;
    return true;
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

// ---- test fixtures ------------------------------------------------------------------------------

std::vector<uint8_t> SharedAssetGen::generateTestModelData() {
    // Unit cube as Wavefront OBJ
    const std::string obj =
        "o cube\n"
        "v -0.5 -0.5 -0.5\nv 0.5 -0.5 -0.5\nv 0.5 0.5 -0.5\nv -0.5 0.5 -0.5\n"
        "v -0.5 -0.5 0.5\nv 0.5 -0.5 0.5\nv 0.5 0.5 0.5\nv -0.5 0.5 0.5\n"
        "usemtl default\n"
        "f 1 2 3 4\nf 5 8 7 6\nf 1 5 6 2\nf 2 6 7 3\nf 3 7 8 4\nf 5 1 4 8\n";
    return std::vector<uint8_t>(obj.begin(), obj.end());
}

std::vector<uint8_t> SharedAssetGen::generateTestMaterialData() {
    const Json j = {{"shader", "pbr"}, {"albedo", {0.8, 0.8, 0.8, 1.0}}, {"metallic", 0.0}, {"roughness", 0.5},
                    {"textures", Json::array()}};
    const std::string s = j.dump(2);
    return std::vector<uint8_t>(s.begin(), s.end());
}

std::vector<uint8_t> SharedAssetGen::generateTestTextureData() {
    // 16x16 RGBA checkerboard encoded as PNG
    constexpr int size = 16;
    std::vector<uint8_t> pixels(size * size * 4);
    for (int y = 0; y < size; ++y) {
        for (int x = 0; x < size; ++x) {
            const uint8_t v = ((x / 4 + y / 4) % 2) ? 255 : 32;
            uint8_t* p = &pixels[(y * size + x) * 4];
            p[0] = p[1] = p[2] = v;
            p[3] = 255;
        }
    }
    std::vector<uint8_t> png;
    stbi_write_png_to_func(
        [](void* ctx, void* data, int len) {
            auto* out = static_cast<std::vector<uint8_t>*>(ctx);
            const auto* bytes = static_cast<const uint8_t*>(data);
            out->insert(out->end(), bytes, bytes + len);
        },
        &png, size, size, 4, pixels.data(), size * 4);
    return png;
}

std::vector<uint8_t> SharedAssetGen::generateTestAudioData() {
    // 0.1 s 440 Hz mono sine, 16-bit PCM WAV at 44.1 kHz
    constexpr uint32_t sampleRate = 44100;
    constexpr uint32_t frames = sampleRate / 10;
    std::vector<uint8_t> wav;
    wav.insert(wav.end(), {'R', 'I', 'F', 'F'});
    appendLE(wav, 36 + frames * 2, 4);
    wav.insert(wav.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    appendLE(wav, 16, 4);
    appendLE(wav, 1, 2);
    appendLE(wav, 1, 2);
    appendLE(wav, sampleRate, 4);
    appendLE(wav, sampleRate * 2, 4);
    appendLE(wav, 2, 2);
    appendLE(wav, 16, 2);
    wav.insert(wav.end(), {'d', 'a', 't', 'a'});
    appendLE(wav, frames * 2, 4);
    for (uint32_t i = 0; i < frames; ++i) {
        const float s = 0.5f * std::sin(2.0f * PI * 440.0f * static_cast<float>(i) / sampleRate);
        appendLE(wav, static_cast<uint16_t>(static_cast<int16_t>(std::lround(s * 32767.0f))), 2);
    }
    return wav;
}

std::vector<uint8_t> SharedAssetGen::generateTestScriptData() {
    const std::string lua =
        "local M = {}\n"
        "function M.add(a, b) return a + b end\n"
        "function M.greet(name) return 'hello ' .. name end\n"
        "return M\n";
    return std::vector<uint8_t>(lua.begin(), lua.end());
}

// Checksum Calculation (64-bit FNV-1a, hex)
std::string SharedAssetGen::calculateChecksum(const std::vector<uint8_t>& data) {
    return hex64(fnv1a(14695981039346656037ULL, data.data(), data.size()));
}

std::string SharedAssetGen::calculatePackChecksum(const SharedAssetManifest& manifest, const std::vector<ProcessedAsset>& assets) {
    uint64_t h = 14695981039346656037ULL;
    h = fnv1a(h, manifest.packName.data(), manifest.packName.size());
    h = fnv1a(h, manifest.version.data(), manifest.version.size());
    for (const auto& asset : assets) {
        h = fnv1a(h, asset.id.data(), asset.id.size());
        h = fnv1a(h, asset.checksum.data(), asset.checksum.size());
    }
    return hex64(h);
}

// Quality calculation functions
float SharedAssetGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    float peak = 0.0f;
    for (float s : samples) peak = std::max(peak, std::abs(s));
    return peak;
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
    return (peak > 0.0f && rms > 0.0f) ? 20.0f * std::log10(peak / rms) : 0.0f;
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

} // namespace SharedAssets
} // namespace Audio
} // namespace MagiTech
