#pragma once

#include "AudioAssetTypes.hpp"
#include <vector>
#include <string>
#include <memory>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <chrono>

namespace MagiTech {
namespace Audio {

// Forward declarations
struct SharedAssetDefinition;
struct SharedAssetResult;
struct SharedAssetManifest;
struct SharedPack;
struct AssetEntry;
struct ProcessedAsset;
struct DependencyGraph;
struct ManifestEntry;
struct ModelData;
struct MaterialData;
struct TextureData;
struct AudioData;
struct ScriptData;
struct CompressionSettings;

// Asset Types
enum class AssetType {
    MODEL,
    MATERIAL,
    TEXTURE,
    AUDIO,
    SCRIPT
};

// Texture Compression Types
enum class TextureCompression {
    NONE,
    BC1,
    BC3,
    BC7,
    ASTC_4x4,
    ASTC_8x8
};

// Shader Types
enum class ShaderType {
    UNLIT,
    LIT,
    PBR,
    CUSTOM
};

// Texture Formats
enum class TextureFormat {
    RGBA8,
    RGBA16,
    RGB8,
    RGB16,
    R8,
    R16
};

// Script Languages
enum class ScriptLanguage {
    LUA,
    JAVASCRIPT,
    PYTHON,
    CUSTOM
};

// SharedAssetGen Class
class SharedAssetGen {
public:
    SharedAssetGen();
    ~SharedAssetGen();
    
    // Main processing function
    AudioBundle process(const SharedAssetParams& params);
    
    // Shared asset definition management
    SharedAssetDefinition loadSharedAssetDefinition(const std::string& filePath);
    SharedAssetDefinition createDefaultSharedAssetDefinition(const SharedAssetParams& params);
    bool saveSharedAssetDefinition(const SharedAssetDefinition& def, const std::string& filePath);
    
    // Shared asset pipeline processing
    SharedAssetResult processSharedAssetPipeline(const SharedAssetDefinition& sharedDef, const SharedAssetParams& params);
    
    // Asset importer initialization
    void initializeAssetImporters();
    
    // Asset import and processing
    ProcessedAsset importAsset(const AssetEntry& assetEntry, const SharedAssetParams& params);
    ProcessedAsset importModel(const AssetEntry& assetEntry);
    ProcessedAsset importMaterial(const AssetEntry& assetEntry);
    ProcessedAsset importTexture(const AssetEntry& assetEntry);
    ProcessedAsset importAudio(const AssetEntry& assetEntry);
    ProcessedAsset importScript(const AssetEntry& assetEntry);
    
    // Dependency resolution
    DependencyGraph resolveDependencies(const SharedAssetDefinition& sharedDef, const std::vector<ProcessedAsset>& assets);
    std::vector<std::string> detectCycles(const DependencyGraph& graph);
    bool hasCycleDFS(const std::string& node, const DependencyGraph& graph, 
                    std::unordered_set<std::string>& visited,
                    std::unordered_set<std::string>& recursionStack,
                    std::vector<std::string>& cycle);
    std::vector<std::string> topologicalSort(const DependencyGraph& graph);
    
    // Post-processing
    std::vector<ProcessedAsset> postProcessAssets(const std::vector<ProcessedAsset>& assets, const DependencyGraph& graph);
    void postProcessAsset(ProcessedAsset& asset, std::vector<ProcessedAsset>& allAssets, const DependencyGraph& graph);
    void postProcessModel(ProcessedAsset& model, std::vector<ProcessedAsset>& allAssets);
    void postProcessMaterial(ProcessedAsset& material, std::vector<ProcessedAsset>& allAssets);
    void postProcessTexture(ProcessedAsset& texture, std::vector<ProcessedAsset>& allAssets);
    void postProcessAudio(ProcessedAsset& audio, std::vector<ProcessedAsset>& allAssets);
    void postProcessScript(ProcessedAsset& script, std::vector<ProcessedAsset>& allAssets);
    
    // Deduplication
    std::vector<ProcessedAsset> deduplicateAssets(const std::vector<ProcessedAsset>& assets);
    
    // Manifest generation
    SharedAssetManifest generateManifest(const SharedAssetDefinition& sharedDef, 
                                       const std::vector<ProcessedAsset>& assets,
                                       const DependencyGraph& graph);
    
    // Shared pack creation
    SharedPack createSharedPack(const SharedAssetDefinition& sharedDef,
                              const std::vector<ProcessedAsset>& assets,
                              const SharedAssetManifest& manifest);
    
    // Asset categorization
    void categorizeAssets(const std::vector<ProcessedAsset>& assets, SharedAssetResult& result);
    
    // Asset importers
    class ModelImporter {
    public:
        void initialize() {}
        ProcessedAsset import(const AssetEntry& entry);
    };
    
    class TextureImporter {
    public:
        void initialize() {}
        ProcessedAsset import(const AssetEntry& entry);
    };
    
    class AudioImporter {
    public:
        void initialize() {}
        ProcessedAsset import(const AssetEntry& entry);
    };
    
    class ScriptCompiler {
    public:
        void initialize() {}
        ProcessedAsset compile(const AssetEntry& entry);
    };
    
    class MaterialProcessor {
    public:
        void initialize() {}
        ProcessedAsset process(const AssetEntry& entry);
    };
    
    // Quality settings
    void setProcessingQuality(int quality);
    void setCompressionQuality(float quality);
    void setDeduplicationEnabled(bool enable);
    
    // Processing options
    void enableGPUAcceleration(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Error handling
    std::string getLastError() const;
    void clearLastError();
    
    // Utility functions
    float clamp(float value, float min, float max);
    int clamp(int value, int min, int max);
    std::string calculateChecksum(const std::vector<uint8_t>& data);
    std::string calculatePackChecksum(const SharedAssetManifest& manifest, const std::vector<ProcessedAsset>& assets);
    
    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);
    
    // Test data generation
    std::vector<uint8_t> generateTestModelData();
    std::vector<uint8_t> generateTestMaterialData();
    std::vector<uint8_t> generateTestTextureData();
    std::vector<uint8_t> generateTestAudioData();
    std::vector<uint8_t> generateTestScriptData();

private:
    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    float m_compressionQuality;
    bool m_enableDeduplication;
    int m_maxProcessingThreads;
    std::string m_lastError;
    
    // Processing settings
    bool m_enableHotReload;
    bool m_enableCaching;
    bool m_enableParallelProcessing;
    
    // Asset importers
    std::unique_ptr<ModelImporter> m_modelImporter;
    std::unique_ptr<TextureImporter> m_textureImporter;
    std::unique_ptr<AudioImporter> m_audioImporter;
    std::unique_ptr<ScriptCompiler> m_scriptCompiler;
    std::unique_ptr<MaterialProcessor> m_materialProcessor;
    
    // Constants
    static constexpr size_t PACK_HEADER_SIZE = 64;
    static constexpr size_t MAX_DEPENDENCY_DEPTH = 10;
    static constexpr float DEFAULT_COMPRESSION_QUALITY = 0.8f;
};

// Asset Definition Structures
struct CompressionSettings {
    TextureCompression compression = TextureCompression::NONE;
    int quality = 4;
    std::map<std::string, float> parameters;
};

struct AssetEntry {
    std::string id;
    AssetType type;
    std::string source;
    std::vector<std::string> dependencies;
    CompressionSettings compression;
    float normalizeLUFS = 0.0f;
    std::map<std::string, std::string> metadata;
};

struct SharedAssetDefinition {
    std::string name;
    std::string version;
    std::string description;
    std::vector<AssetEntry> assets;
    std::map<std::string, std::string> metadata;
    std::vector<std::string> tags;
    bool enableHotReload = true;
    bool enableCaching = true;
    bool enableParallelProcessing = true;
    int maxConcurrentAssets = 8;
};

// Asset Data Structures
struct ModelData {
    uint32_t vertexCount = 0;
    uint32_t indexCount = 0;
    std::pair<glm::vec3, glm::vec3> boundingBox;
    uint32_t lodLevels = 1;
    std::string materialId;
    std::map<std::string, float> parameters;
};

struct MaterialData {
    ShaderType shaderType = ShaderType::PBR;
    glm::vec4 albedoColor = glm::vec4(1.0f);
    float metallic = 0.0f;
    float roughness = 0.5f;
    std::vector<std::string> textureIds;
    std::map<std::string, float> parameters;
};

struct TextureData {
    uint32_t width = 0;
    uint32_t height = 0;
    TextureFormat format = TextureFormat::RGBA8;
    uint32_t mipLevels = 1;
    bool compressed = false;
    TextureCompression compressionType = TextureCompression::NONE;
    std::map<std::string, float> parameters;
};

struct AudioData {
    uint32_t sampleRate = 44100;
    uint32_t numChannels = 2;
    uint32_t bitDepth = 16;
    float duration = 0.0f;
    float lufs = -14.0f;
    bool normalized = false;
    float targetLUFS = -14.0f;
    std::map<std::string, float> parameters;
};

struct ScriptData {
    ScriptLanguage language = ScriptLanguage::LUA;
    uint32_t bytecodeSize = 0;
    uint32_t functionCount = 0;
    bool compiled = false;
    std::map<std::string, std::string> parameters;
};

// Processed Asset Structure
struct ProcessedAsset {
    std::string id;
    AssetType type;
    std::string sourcePath;
    std::vector<std::string> dependencies;
    std::vector<uint8_t> blobData;
    size_t blobSize = 0;
    std::string checksum;
    std::map<std::string, std::string> metadata;
    CompressionSettings compressionSettings;
    float normalizeLUFS = 0.0f;
    
    // Type-specific data
    ModelData modelData;
    MaterialData materialData;
    TextureData textureData;
    AudioData audioData;
    ScriptData scriptData;
    
    // Audio compatibility
    std::vector<float> audioData;
    uint32_t sampleRate = 44100;
    uint32_t numChannels = 2;
};

// Dependency Graph Structure
struct DependencyGraph {
    std::unordered_map<std::string, std::vector<std::string>> adjacencyList;
    std::unordered_map<std::string, std::vector<std::string>> reverseDependencies;
    std::vector<std::string> topologicalOrder;
    std::map<std::string, int> dependencyDepth;
};

// Manifest Structures
struct ManifestEntry {
    std::string id;
    AssetType type;
    std::string checksum;
    size_t blobSize = 0;
    std::vector<std::string> dependencies;
    std::map<std::string, std::string> metadata;
};

struct SharedAssetManifest {
    std::string packName;
    std::string version;
    std::string description;
    int assetCount = 0;
    size_t totalSize = 0;
    std::vector<ManifestEntry> entries;
    DependencyGraph dependencyGraph;
    std::map<std::string, std::string> additionalMetadata;
};

// Shared Pack Structure
struct SharedPack {
    std::string name;
    std::string version;
    SharedAssetManifest manifest;
    std::vector<ProcessedAsset> assets;
    SharedAssetDefinition sharedDef;
    std::chrono::system_clock::time_point creationTime;
    std::string filePath;
    size_t totalSize = 0;
    std::string checksum;
};

// Shared Asset Result Structure
struct SharedAssetResult {
    std::vector<ProcessedAsset> processedAssets;
    std::vector<ProcessedAsset> modelAssets;
    std::vector<ProcessedAsset> materialAssets;
    std::vector<ProcessedAsset> textureAssets;
    std::vector<ProcessedAsset> audioAssets;
    std::vector<ProcessedAsset> scriptAssets;
    SharedAssetManifest manifest;
    SharedPack sharedPack;
    DependencyGraph dependencyGraph;
    SharedAssetDefinition sharedDef;
    std::chrono::system_clock::time_point processingTime;
    bool success = true;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

} // namespace Audio
} // namespace MagiTech 
