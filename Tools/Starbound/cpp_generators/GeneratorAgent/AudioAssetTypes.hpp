#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <any>
#include <chrono>
#include <memory>
#include <atomic>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Audio {

// GPU Handle Types for OpenStarbound Integration
using AudioBufferHandle = uint32_t;
using AudioTextureHandle = uint32_t;
using AudioPipelineHandle = uint32_t;
using AudioDescriptorSet = uint32_t;

// Audio Format Enums
enum class AudioFormat {
    WAV, OGG, FLAC, MP3
};

enum class SampleRate {
    SR_8000 = 8000,
    SR_11025 = 11025,
    SR_16000 = 16000,
    SR_22050 = 22050,
    SR_44100 = 44100,
    SR_48000 = 48000,
    SR_96000 = 96000,
    SR_192000 = 192000
};

enum class BitDepth {
    BD_16 = 16,
    BD_24 = 24,
    BD_32 = 32,
    BD_FLOAT = 0
};

enum class ChannelLayout {
    MONO = 1,
    STEREO = 2,
    SURROUND_5_1 = 6,
    SURROUND_7_1 = 8
};

enum class WaveformType {
    SINE, SQUARE, SAW, TRIANGLE, NOISE, CUSTOM
};

enum class EffectType {
    REVERB, DELAY, CHORUS, FLANGER, DISTORTION, COMPRESSOR, EQUALIZER, FILTER
};

enum class MixerType {
    LINEAR, LOGARITHMIC, CUSTOM
};

enum class LODLevel {
    HIGH, MEDIUM, LOW, ULTRA_LOW
};

// Audio Buffer Type
using AudioBuffer = std::vector<float>;

// Parameter Structs with Enhanced Features
struct SoundParams {
    std::string id;
    float duration;
    bool loop;
    uint64_t hashKey() const;
};

struct SampleParams {
    std::string filePath;
    glm::vec2 trimRange;
    float pitchShift;
    float gain;
    
    // Enhanced parameters from new implementation
    SampleRate sampleRate = SampleRate::SR_44100;
    BitDepth bitDepth = BitDepth::BD_16;
    ChannelLayout channels = ChannelLayout::STEREO;
    bool normalize = true;
    bool trimSilence = false;
    glm::vec2 fadeInOut = glm::vec2(0.0f, 0.0f);
    bool enableGPUAcceleration = false;
    
    uint64_t hashKey() const;
};

struct SynthParams {
    std::string waveType;
    float frequency;
    glm::vec2 freqEnvelope;
    glm::vec2 ampEnvelope;
    bool polyphonic;
    
    // Enhanced parameters from new implementation
    WaveformType waveformType = WaveformType::SINE;
    float amplitude = 1.0f;
    float phase = 0.0f;
    glm::vec2 frequencyModulation = glm::vec2(0.0f, 0.0f);
    glm::vec2 amplitudeModulation = glm::vec2(0.0f, 0.0f);
    glm::vec2 phaseModulation = glm::vec2(0.0f, 0.0f);
    glm::vec4 adsrEnvelope = glm::vec4(0.1f, 0.1f, 0.7f, 0.2f); // Attack, Decay, Sustain, Release
    bool enableAntiAliasing = true;
    int oversamplingFactor = 4;
    int harmonicLimit = 8;
    bool enableGPUAcceleration = false;
    
    uint64_t hashKey() const;
};

struct EffectParams {
    std::vector<std::string> chain;
    std::unordered_map<std::string, std::any> settings;
    
    // Enhanced parameters from new implementation
    std::vector<EffectType> effectTypes;
    float processingQuality = 1.0f;
    int oversamplingFactor = 2;
    bool enableAntiAliasing = true;
    bool enableGPUAcceleration = false;
    
    // Effect-specific parameters
    struct ReverbSettings {
        float roomSize = 0.5f;
        float damping = 0.5f;
        float wetLevel = 0.33f;
        float dryLevel = 0.4f;
        float width = 1.0f;
        uint64_t hashKey() const;
    } reverb;
    
    struct DelaySettings {
        float delayTime = 0.5f;
        float feedback = 0.3f;
        float wetLevel = 0.5f;
        uint64_t hashKey() const;
    } delay;
    
    struct DistortionSettings {
        float drive = 0.5f;
        float range = 2400.0f;
        float blend = 0.5f;
        uint64_t hashKey() const;
    } distortion;
    
    struct CompressorSettings {
        float threshold = -20.0f;
        float ratio = 4.0f;
        float attack = 0.003f;
        float release = 0.25f;
        uint64_t hashKey() const;
    } compressor;
    
    uint64_t hashKey() const;
};

struct MixerParams {
    int channels;
    float masterGain;
    std::vector<float> trackGains;
    
    // Enhanced parameters from new implementation
    MixerType mixerType = MixerType::LINEAR;
    bool realTimeProcessing = false;
    int bufferSize = 1024;
    bool enableGPUAcceleration = false;
    std::vector<glm::vec2> panPositions; // Stereo panning
    std::vector<float> automationCurves;
    
    uint64_t hashKey() const;
};

struct ExportParams {
    std::string format;
    int sampleRate;
    int bitDepth;
    
    // Enhanced parameters from new implementation
    AudioFormat audioFormat = AudioFormat::WAV;
    SampleRate exportSampleRate = SampleRate::SR_44100;
    BitDepth exportBitDepth = BitDepth::BD_16;
    ChannelLayout exportChannels = ChannelLayout::STEREO;
    int compressionLevel = 5;
    bool enableDithering = true;
    bool enableNormalization = false;
    std::string metadata;
    bool enableGPUAcceleration = false;
    
    uint64_t hashKey() const;
};

struct LODParams {
    std::vector<int> sampleRates;
    std::vector<int> bitDepths;
    
    // Enhanced parameters from new implementation
    std::vector<LODLevel> lodLevels = {LODLevel::HIGH, LODLevel::MEDIUM, LODLevel::LOW};
    std::vector<SampleRate> lodSampleRates = {SampleRate::SR_44100, SampleRate::SR_22050, SampleRate::SR_11025};
    std::vector<BitDepth> lodBitDepths = {BitDepth::BD_16, BitDepth::BD_16, BitDepth::BD_16};
    std::vector<ChannelLayout> lodChannels = {ChannelLayout::STEREO, ChannelLayout::STEREO, ChannelLayout::MONO};
    bool enableGPUAcceleration = false;
    int optimizationLevel = 2;
    
    uint64_t hashKey() const;
};

// Performance Metrics
struct AudioPerformanceMetrics {
    std::atomic<uint64_t> cacheHits{0};
    std::atomic<uint64_t> cacheMisses{0};
    std::atomic<uint64_t> totalGenerations{0};
    std::atomic<uint64_t> gpuGenerations{0};
    std::atomic<uint64_t> totalProcessingTime{0};
    std::atomic<uint64_t> peakMemoryUsage{0};
    std::atomic<uint64_t> gpuMemoryUsage{0};
    std::atomic<uint64_t> gpuUtilization{0};
    
    void reset() {
        cacheHits = 0;
        cacheMisses = 0;
        totalGenerations = 0;
        gpuGenerations = 0;
        totalProcessingTime = 0;
        peakMemoryUsage = 0;
        gpuMemoryUsage = 0;
        gpuUtilization = 0;
    }
    
    double getCacheHitRate() const {
        uint64_t total = cacheHits.load() + cacheMisses.load();
        return total > 0 ? static_cast<double>(cacheHits.load()) / total : 0.0;
    }
    
    double getAverageProcessingTime() const {
        uint64_t generations = totalGenerations.load();
        return generations > 0 ? static_cast<double>(totalProcessingTime.load()) / generations : 0.0;
    }
};

// Audio Quality Metrics
struct AudioQualityMetrics {
    float peakAmplitude = 0.0f;
    float rmsAmplitude = 0.0f;
    float dynamicRange = 0.0f;
    float signalToNoiseRatio = 0.0f;
    float frequencyResponse = 0.0f;
    float distortion = 0.0f;
    
    bool isHighQuality() const {
        return peakAmplitude > 0.1f && 
               rmsAmplitude > 0.01f && 
               dynamicRange > 40.0f && 
               signalToNoiseRatio > 60.0f;
    }
};

// Enhanced Audio Bundle
struct AudioMetadata {
    std::string id;
    float duration;
    bool loop;
    
    // Enhanced metadata
    std::string artist;
    std::string title;
    std::string album;
    std::string genre;
    int year;
    std::string comment;
    AudioQualityMetrics quality;
    std::chrono::system_clock::time_point creationTime;
    
    uint64_t hashKey() const;
};

struct AudioBundle {
    AudioBuffer buffer;
    std::vector<AudioBuffer> lodBuffers;
    AudioMetadata meta;
    
    // Enhanced bundle with GPU resources
    AudioBufferHandle gpuBuffer = 0;
    AudioTextureHandle gpuTexture = 0;
    AudioPipelineHandle gpuPipeline = 0;
    AudioDescriptorSet gpuDescriptorSet = 0;
    
    // Performance tracking
    std::chrono::system_clock::time_point creationTime;
    AudioQualityMetrics quality;
    bool gpuAccelerated = false;
    
    // LOD information
    std::vector<LODLevel> lodLevels;
    std::vector<SampleRate> lodSampleRates;
    std::vector<BitDepth> lodBitDepths;
    std::vector<ChannelLayout> lodChannels;
    
    uint64_t hashKey() const;
};

// Utility Functions
template<typename T>
uint64_t hashCombine(uint64_t seed, const T& value) {
    return seed ^ (std::hash<T>{}(value) + 0x9e3779b9 + (seed << 6) + (seed >> 2));
}

} // namespace Audio
} // namespace MagiTech
