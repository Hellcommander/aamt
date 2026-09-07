#pragma once

#include "AudioAssetTypes.hpp"
#include <vector>
#include <string>
#include <memory>
#include <map>
#include <chrono>

namespace MagiTech {
namespace Audio {

// Forward declarations
struct SampleDefinition;
struct SampleResult;
struct SampleMetadata;
struct SamplePack;
struct SampleEntry;
struct ProcessedSample;
struct SampleVariation;
struct AudioAnalysis;
struct LoopInfo;
struct LoopSettings;
struct VariationSettings;
struct TimeStretchSettings;
struct MappingZone;
struct MappingDefinition;
struct SampleMetadataEntry;
struct VariationMetadataEntry;

// Loop Types
enum class LoopType {
    NONE,
    SUSTAIN,
    LOOP,
    PING_PONG
};

// SampleGen Class
class SampleGen {
public:
    SampleGen();
    ~SampleGen();
    
    // Main processing function
    AudioBundle process(const SampleParams& params);
    
    // Sample definition management
    SampleDefinition loadSampleDefinition(const std::string& filePath);
    SampleDefinition createDefaultSampleDefinition(const SampleParams& params);
    bool saveSampleDefinition(const SampleDefinition& def, const std::string& filePath);
    
    // Sample pipeline processing
    SampleResult processSamplePipeline(const SampleDefinition& sampleDef, const SampleParams& params);
    
    // Processing engine initialization
    void initializeProcessingEngines();
    
    // Sample import and processing
    ProcessedSample importSample(const SampleEntry& sampleEntry, const SampleParams& params);
    std::vector<float> decodeAudio(const std::string& filePath);
    AudioAnalysis analyzeAudio(const std::vector<float>& audio);
    std::vector<float> trimSilence(const std::vector<float>& audio);
    std::vector<float> normalizeLoudness(const std::vector<float>& audio, float targetLUFS);
    LoopInfo detectLoop(const std::vector<float>& audio, const LoopSettings& settings);
    std::vector<float> createLoop(const std::vector<float>& audio, const LoopInfo& loopInfo);
    
    // Variation generation
    std::vector<SampleVariation> generateVariations(const std::vector<ProcessedSample>& samples, const VariationSettings& variations);
    std::vector<float> pitchShift(const std::vector<float>& input, int semitones);
    std::vector<float> timeStretch(const std::vector<float>& input, const TimeStretchSettings& settings);
    
    // Metadata generation
    SampleMetadata generateMetadata(const SampleDefinition& sampleDef, const std::vector<ProcessedSample>& samples, const std::vector<SampleVariation>& variations);
    
    // Sample pack creation
    SamplePack createSamplePack(const SampleDefinition& sampleDef, const std::vector<ProcessedSample>& samples, const std::vector<SampleVariation>& variations);
    
    // Audio decoders
    class WAVDecoder {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> decode(const std::string& filePath);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class MP3Decoder {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> decode(const std::string& filePath);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class OGGDecoder {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> decode(const std::string& filePath);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    // Analysis engines
    class PitchDetector {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        int detectPitch(const std::vector<float>& audio, uint32_t sampleRate);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class TempoDetector {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        float detectTempo(const std::vector<float>& audio, uint32_t sampleRate);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class LoudnessAnalyzer {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        float analyzeLUFS(const std::vector<float>& audio, uint32_t sampleRate);
        float analyzePeak(const std::vector<float>& audio);
        float analyzeRMS(const std::vector<float>& audio);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class SpectralAnalyzer {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        float analyzeCentroid(const std::vector<float>& audio, uint32_t sampleRate);
        float analyzeRolloff(const std::vector<float>& audio, uint32_t sampleRate);
        float analyzeFlatness(const std::vector<float>& audio);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    // Processing engines
    class SilenceTrimmer {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> trim(const std::vector<float>& audio, float threshold);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class Normalizer {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> normalize(const std::vector<float>& audio, float targetLevel);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class LoopDetector {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        LoopInfo detectLoop(const std::vector<float>& audio, uint32_t sampleRate);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class PitchShifter {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> shift(const std::vector<float>& audio, int semitones);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    class TimeStretcher {
    public:
        void initialize(uint32_t sampleRate) { m_sampleRate = sampleRate; }
        std::vector<float> stretch(const std::vector<float>& audio, float stretchFactor);
    private:
        uint32_t m_sampleRate = 44100;
    };
    
    // Quality settings
    void setProcessingQuality(int quality);
    void setOversamplingFactor(int factor);
    void setAntiAliasingEnabled(bool enable);
    
    // Processing options
    void enableGPUAcceleration(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Error handling
    std::string getLastError() const;
    void clearLastError();
    
    // Utility functions
    float clamp(float value, float min, float max);
    float midiToFrequency(int midiNote);
    int frequencyToMidi(float frequency);
    
    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);
    
    // Test audio generation
    std::vector<float> generateTestAudio();

private:
    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    int m_oversamplingFactor;
    bool m_antiAliasingEnabled;
    int m_maxProcessingThreads;
    std::string m_lastError;
    
    // Sample processing settings
    uint32_t m_sampleRate;
    uint32_t m_bufferSize;
    uint32_t m_numChannels;
    bool m_enableAntiAliasing;
    bool m_enableOversampling;
    
    // Audio decoders
    std::unique_ptr<WAVDecoder> m_wavDecoder;
    std::unique_ptr<MP3Decoder> m_mp3Decoder;
    std::unique_ptr<OGGDecoder> m_oggDecoder;
    
    // Analysis engines
    std::unique_ptr<PitchDetector> m_pitchDetector;
    std::unique_ptr<TempoDetector> m_tempoDetector;
    std::unique_ptr<LoudnessAnalyzer> m_loudnessAnalyzer;
    std::unique_ptr<SpectralAnalyzer> m_spectralAnalyzer;
    
    // Processing engines
    std::unique_ptr<SilenceTrimmer> m_silenceTrimmer;
    std::unique_ptr<Normalizer> m_normalizer;
    std::unique_ptr<LoopDetector> m_loopDetector;
    std::unique_ptr<PitchShifter> m_pitchShifter;
    std::unique_ptr<TimeStretcher> m_timeStretcher;
    
    // Constants
    static constexpr float PI = 3.14159265359f;
    static constexpr float TWO_PI = 2.0f * PI;
    static constexpr float SEMITONE_RATIO = 1.059463094359f;
};

// Sample Definition Structures
struct SampleEntry {
    std::string id;
    std::string path;
    bool trimSilence = true;
    float normalizeLUFS = -14.0f;
    LoopSettings loop;
    std::map<std::string, float> parameters;
};

struct LoopSettings {
    LoopType type = LoopType::NONE;
    bool autoDetect = false;
    size_t startSample = 0;
    size_t endSample = 0;
    float crossfadeDuration = 0.1f;
    std::map<std::string, float> parameters;
};

struct MappingZone {
    std::string sampleId;
    std::pair<int, int> keyRange; // MIDI key range
    std::pair<int, int> velocityRange; // Velocity range
    std::map<std::string, float> parameters;
};

struct MappingDefinition {
    std::string instrument;
    std::vector<MappingZone> zones;
    std::map<std::string, std::string> metadata;
};

struct TimeStretchSettings {
    bool enabled = false;
    float targetBPM = 120.0f;
    float stretchFactor = 1.0f;
    std::map<std::string, float> parameters;
};

struct VariationSettings {
    std::pair<int, int> pitchRange = {-12, 12}; // semitones
    TimeStretchSettings timeStretch;
    bool enablePitchVariations = true;
    bool enableTimeVariations = false;
    std::map<std::string, float> parameters;
};

struct SampleDefinition {
    std::string name;
    std::string category;
    std::string description;
    std::vector<SampleEntry> samples;
    MappingDefinition mappings;
    VariationSettings variations;
    std::map<std::string, std::string> metadata;
    std::vector<std::string> tags;
    bool enableHotReload = true;
    bool enableCaching = true;
    bool enableParallelProcessing = true;
    int maxConcurrentSamples = 8;
};

// Audio Analysis Structures
struct AudioAnalysis {
    int rootKey = 60; // MIDI key number
    float frequency = 440.0f; // Hz
    float bpm = 120.0f;
    float lufs = -14.0f;
    float peak = 0.0f;
    float rms = 0.0f;
    float spectralCentroid = 1000.0f;
    float spectralRolloff = 8000.0f;
    float spectralFlatness = 0.5f;
    std::map<std::string, float> additionalMetrics;
};

struct LoopInfo {
    size_t startSample = 0;
    size_t endSample = 0;
    bool isValid = false;
    float confidence = 0.0f;
    std::map<std::string, float> parameters;
};

// Processed Sample Structures
struct ProcessedSample {
    std::string id;
    std::string originalPath;
    std::vector<float> audioData;
    uint32_t sampleRate;
    uint32_t numChannels;
    float duration;
    AudioAnalysis analysis;
    LoopInfo loopInfo;
    std::map<std::string, std::string> metadata;
};

struct SampleVariation {
    std::string sampleId;
    int pitchShift = 0;
    int midiNote = 60;
    bool timeStretch = false;
    float targetBPM = 120.0f;
    std::vector<float> audioData;
    uint32_t sampleRate;
    uint32_t numChannels;
    float duration;
    std::map<std::string, float> parameters;
};

// Sample Result Structures
struct SampleResult {
    std::vector<float> audioData;
    std::vector<ProcessedSample> processedSamples;
    std::vector<SampleVariation> variations;
    SampleMetadata metadata;
    SamplePack samplePack;
    SampleDefinition sampleDef;
    std::chrono::system_clock::time_point processingTime;
    bool success = true;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

// Metadata Structures
struct SampleMetadataEntry {
    std::string id;
    std::string originalPath;
    int rootKey;
    float frequency;
    float bpm;
    float lufs;
    float peak;
    float rms;
    float duration;
    LoopInfo loopInfo;
    float spectralCentroid;
    float spectralRolloff;
    float spectralFlatness;
    std::map<std::string, std::string> additionalMetadata;
};

struct VariationMetadataEntry {
    std::string sampleId;
    int pitchShift;
    int midiNote;
    bool timeStretch;
    float targetBPM;
    float duration;
    std::map<std::string, float> parameters;
};

struct SampleMetadata {
    std::string packName;
    std::string category;
    std::string description;
    uint32_t sampleRate;
    uint32_t bitDepth;
    uint32_t channels;
    int numSamples;
    int numVariations;
    std::vector<SampleMetadataEntry> samples;
    std::vector<VariationMetadataEntry> variations;
    MappingDefinition mappings;
    std::map<std::string, std::string> additionalMetadata;
};

struct SamplePack {
    std::string name;
    std::string version;
    SampleMetadata metadata;
    std::vector<ProcessedSample> samples;
    std::vector<SampleVariation> variations;
    SampleDefinition sampleDef;
    std::chrono::system_clock::time_point creationTime;
    std::string filePath;
    size_t totalSize;
    std::string checksum;
};

} // namespace Audio
} // namespace MagiTech 
