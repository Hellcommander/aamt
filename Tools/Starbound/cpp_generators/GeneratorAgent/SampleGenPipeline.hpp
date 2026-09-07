#pragma once

#include "AudioAssetTypes.hpp"
#include "SampleGen.hpp"
#include <memory>
#include <vector>
#include <unordered_map>
#include <filesystem>
#include <chrono>
#include <atomic>

// Forward declarations
namespace YAML { class Node; }
namespace Json { class Value; }

namespace MagiTech {
namespace Audio {

// Sample definition structures
struct LoopRange {
    size_t start = 0;
    size_t end = 0;
    bool enabled = false;
    std::string type = "none"; // "none", "sustain", "loop"
    bool autoDetect = false;
};

struct SampleDefinition {
    std::string id;
    std::string path;
    bool trimSilence = true;
    float normalizeLUFS = -14.0f;
    int rootKey = 60; // MIDI key number
    float bpm = 120.0f;
    LoopRange loop;
    std::vector<std::string> tags;
};

struct VelocityZone {
    std::string sampleId;
    int keyRange[2] = {0, 127};
    int velocityRange[2] = {1, 127};
};

struct InstrumentMapping {
    std::string instrument;
    std::vector<VelocityZone> zones;
};

struct VariationSettings {
    int pitchRange[2] = {-12, 12}; // semitones
    bool timeStretch = false;
    float targetBPM = 120.0f;
    bool enableVariations = true;
};

struct SamplePackDefinition {
    std::string name;
    std::vector<SampleDefinition> samples;
    InstrumentMapping mappings;
    VariationSettings variations;
    std::string outputPath;
    std::string audioFormat = "PCM"; // "PCM", "ADPCM", "OGG"
    int quality = 5; // 1-10
};

// Runtime structures
struct SampleEntry {
    AudioBuffer buffer;
    int rootKey = 60;
    float bpm = 120.0f;
    LoopRange loop;
    std::string id;
    std::vector<std::string> tags;
    std::chrono::system_clock::time_point lastModified;
};

struct SampleInstrument {
    std::string name;
    std::unordered_map<int, SampleEntry> keyMap;
    std::unordered_map<std::string, SampleEntry> sampleMap;
    std::vector<VelocityZone> zones;
    std::chrono::system_clock::time_point lastLoaded;
};

// Analysis results
struct SampleAnalysis {
    float rootPitch = 0.0f;
    float bpm = 120.0f;
    float rmsLevel = 0.0f;
    float lufsLevel = 0.0f;
    float peakLevel = 0.0f;
    std::vector<float> spectralPeaks;
    LoopRange detectedLoop;
    size_t silenceStart = 0;
    size_t silenceEnd = 0;
    bool hasStableLoop = false;
};

// Package file structure
struct SamplePackage {
    std::string name;
    std::unordered_map<std::string, AudioBuffer> audioBuffers;
    std::unordered_map<std::string, SampleEntry> samples;
    InstrumentMapping mappings;
    std::string metadataHash;
    std::chrono::system_clock::time_point created;
};

// Main pipeline class
class SampleGenPipeline {
public:
    SampleGenPipeline();
    ~SampleGenPipeline();
    
    // Pipeline stages
    bool importFromDefinition(const std::string& definitionPath);
    bool processSamples(const SamplePackDefinition& definition);
    bool analyzeSamples(const std::vector<SampleDefinition>& samples);
    bool generateVariations(const SamplePackDefinition& definition);
    bool packageSamples(const SamplePackDefinition& definition);
    bool loadRuntime(const std::string& packagePath);
    
    // Analysis methods
    SampleAnalysis analyzeSample(const AudioBuffer& buffer, uint32_t sampleRate);
    float detectRootPitch(const AudioBuffer& buffer, uint32_t sampleRate);
    float estimateBPM(const AudioBuffer& buffer, uint32_t sampleRate);
    LoopRange detectLoopPoints(const AudioBuffer& buffer, uint32_t sampleRate);
    float calculateLUFS(const AudioBuffer& buffer, uint32_t sampleRate);
    std::vector<float> findSpectralPeaks(const AudioBuffer& buffer, uint32_t sampleRate);
    
    // Processing methods
    AudioBuffer trimSilence(const AudioBuffer& buffer, float threshold = 0.01f);
    AudioBuffer normalizeAudio(const AudioBuffer& buffer, float targetLUFS);
    AudioBuffer applyLoop(const AudioBuffer& buffer, const LoopRange& loop);
    AudioBuffer pitchShift(const AudioBuffer& buffer, float semitones, uint32_t sampleRate);
    AudioBuffer timeStretch(const AudioBuffer& buffer, float sourceBPM, float targetBPM, uint32_t sampleRate);
    
    // Caching and hot-reload
    void enableHotReload(bool enabled);
    void setCacheCapacity(size_t capacity);
    void clearCache();
    bool isHotReloadEnabled() const;
    size_t getCacheSize() const;
    
    // Editor integration
    void updateSampleDefinition(const std::string& sampleId, const SampleDefinition& definition);
    void regenerateVariations(const std::string& sampleId);
    void rebuildPackage(const std::string& packageName);
    
    // Error handling
    std::string getLastError() const;
    void clearLastError();
    
    // Progress tracking
    struct Progress {
        std::atomic<float> percentage{0.0f};
        std::atomic<std::string> currentStage{""};
        std::atomic<bool> isComplete{false};
        std::atomic<std::string> errorMessage{""};
    };
    
    Progress& getProgress() { return m_progress; }

private:
    // File system operations
    bool loadDefinition(const std::string& path, SamplePackDefinition& definition);
    bool saveDefinition(const std::string& path, const SamplePackDefinition& definition);
    bool createPackage(const std::string& path, const SamplePackage& package);
    bool loadPackage(const std::string& path, SamplePackage& package);
    
    // Audio encoding/decoding
    bool encodeAudio(const AudioBuffer& buffer, const std::string& format, 
                    const std::string& outputPath, int quality);
    bool decodeAudio(const std::string& inputPath, AudioBuffer& buffer);
    
    // Hash computation
    std::string computeFileHash(const std::string& filePath);
    std::string computeDefinitionHash(const SamplePackDefinition& definition);
    
    // File watching
    void setupFileWatcher(const std::string& directory);
    void onFileChanged(const std::string& filePath);
    
    // Utility functions
    std::string getFileExtension(const std::string& path) const;
    bool fileExists(const std::string& path) const;
    std::string generateSampleId(const std::string& baseName, int variation = 0);
    
    // Member variables
    std::unique_ptr<SampleGen> m_sampleGen;
    std::unordered_map<std::string, SamplePackage> m_packages;
    std::unordered_map<std::string, SampleInstrument> m_instruments;
    std::unordered_map<std::string, SampleAnalysis> m_analyses;
    
    // Caching
    std::unordered_map<std::string, std::chrono::system_clock::time_point> m_fileHashes;
    std::unordered_map<std::string, std::string> m_definitionHashes;
    size_t m_cacheCapacity = 100;
    
    // Hot-reload
    bool m_hotReloadEnabled = false;
    std::vector<std::string> m_watchedDirectories;
    
    // Progress tracking
    Progress m_progress;
    
    // Error handling
    std::string m_lastError;
    
    // Constants
    static constexpr float SILENCE_THRESHOLD = 0.01f;
    static constexpr float DEFAULT_LUFS_TARGET = -14.0f;
    static constexpr int DEFAULT_SAMPLE_RATE = 44100;
    static constexpr int MAX_VARIATIONS = 128;
};

// YAML/JSON parsing helpers
namespace SampleDefParser {
    bool parseDefinition(const std::string& yamlContent, SamplePackDefinition& definition);
    bool parseSampleDefinition(const YAML::Node& node, SampleDefinition& sample);
    bool parseLoopRange(const YAML::Node& node, LoopRange& loop);
    bool parseVelocityZone(const YAML::Node& node, VelocityZone& zone);
    bool parseVariationSettings(const YAML::Node& node, VariationSettings& settings);
    
    std::string serializeDefinition(const SamplePackDefinition& definition);
    std::string serializeSampleDefinition(const SampleDefinition& sample);
    std::string serializeLoopRange(const LoopRange& loop);
    std::string serializeVelocityZone(const VelocityZone& zone);
    std::string serializeVariationSettings(const VariationSettings& settings);
}

// Editor integration helpers
namespace SampleGenEditor {
    struct WaveformView {
        AudioBuffer buffer;
        LoopRange loop;
        size_t trimStart = 0;
        size_t trimEnd = 0;
        bool isDragging = false;
        std::string selectedHandle = "";
    };
    
    struct InspectorPanel {
        SampleDefinition definition;
        SampleAnalysis analysis;
        bool isModified = false;
        std::vector<std::string> availableTags;
    };
    
    struct BatchPanel {
        std::vector<SampleDefinition> samples;
        std::vector<SampleAnalysis> analyses;
        bool showWaveforms = true;
        bool showMetadata = true;
    };
    
    void renderWaveformView(WaveformView& view);
    void renderInspectorPanel(InspectorPanel& panel);
    void renderBatchPanel(BatchPanel& panel);
    void renderProgressBar(const SampleGenPipeline::Progress& progress);
}

} // namespace Audio
} // namespace MagiTech 
